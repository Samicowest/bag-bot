import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from src.models.trading_session import TradingSession, BotConfig, db
from src.services.mexc_api import MexcApiClient
from src.services.strategy_engine import BaggingStrategyEngine
from src.services.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class BotScheduler:
    """
    Scheduler for automated trading bot execution
    """
    
    def __init__(self):
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.strategy_engine: Optional[BaggingStrategyEngine] = None
        self.config: Optional[BotConfig] = None
        
    def start(self) -> bool:
        """Start the bot scheduler"""
        if self.is_running:
            logger.warning("Bot scheduler is already running")
            return False
        
        try:
            # Load active configuration
            self.config = BotConfig.query.filter_by(is_active=True).first()
            if not self.config:
                logger.error("No active configuration found")
                return False
            
            # Initialize API client and strategy engine
            api_client = MexcApiClient(self.config.api_key, self.config.api_secret)
            self.strategy_engine = BaggingStrategyEngine(self.config, api_client)
            
            # Load or create active session
            active_session = self.strategy_engine.load_active_session()
            if not active_session:
                logger.warning("No active session found. Bot will wait for session creation.")
            
            # Start the scheduler thread
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            
            self.is_running = True
            logger.info("Bot scheduler started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start bot scheduler: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the bot scheduler"""
        if not self.is_running:
            logger.warning("Bot scheduler is not running")
            return False
        
        try:
            self.stop_event.set()
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=10)
            
            self.is_running = False
            logger.info("Bot scheduler stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop bot scheduler: {e}")
            return False
    
    def _run_scheduler(self):
        """Main scheduler loop"""
        logger.info("Bot scheduler loop started")
        
        while not self.stop_event.is_set():
            try:
                # Check if we have an active session
                if not self.strategy_engine.session:
                    self.strategy_engine.load_active_session()
                
                if self.strategy_engine.session:
                    # Run strategy cycle
                    cycle_result = self.strategy_engine.run_strategy_cycle()
                    
                    # Log the cycle result
                    signal = cycle_result.get('signal', {})
                    logger.info(f"Strategy cycle completed: {signal.get('action', 'unknown')} - {signal.get('reason', 'no reason')}")
                    
                    # Check if cycle should be completed
                    if cycle_result.get('cycle_complete', False):
                        completion_report = self.strategy_engine.complete_trading_cycle()
                        logger.info(f"Trading cycle completed: {completion_report}")
                        
                        # Reset for next cycle
                        self.strategy_engine.session = None
                    
                    # Check for emergency stop conditions
                    risk_manager = RiskManager(self.config)
                    should_stop, stop_reason = risk_manager.should_emergency_stop(self.strategy_engine.session)
                    
                    if should_stop:
                        logger.critical(f"Emergency stop triggered: {stop_reason}")
                        # Pause the session instead of stopping completely
                        self.strategy_engine.session.status = 'paused'
                        db.session.commit()
                        self.strategy_engine.session = None
                
                else:
                    logger.debug("No active session found, waiting...")
                
                # Wait for the next cycle
                interval_seconds = self.config.trading_interval_minutes * 60
                self.stop_event.wait(timeout=interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                # Wait a bit before retrying to avoid rapid error loops
                self.stop_event.wait(timeout=60)
    
    def get_status(self) -> dict:
        """Get current scheduler status"""
        return {
            'is_running': self.is_running,
            'has_active_session': self.strategy_engine.session is not None if self.strategy_engine else False,
            'config_active': self.config is not None,
            'thread_alive': self.thread.is_alive() if self.thread else False
        }
    
    def force_cycle(self) -> dict:
        """Force execute a single strategy cycle"""
        if not self.strategy_engine:
            raise ValueError("Strategy engine not initialized")
        
        if not self.strategy_engine.session:
            self.strategy_engine.load_active_session()
            if not self.strategy_engine.session:
                raise ValueError("No active session found")
        
        return self.strategy_engine.run_strategy_cycle()

# Global scheduler instance
bot_scheduler = BotScheduler()

