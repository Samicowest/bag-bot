import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from src.models.trading_session import TradingSession, Trade, BotConfig

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Risk management module for the bagging strategy bot
    """
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.max_daily_trades = 10
        self.max_position_size_percent = 0.3  # Maximum 30% of capital in a single trade
        self.max_drawdown_percent = 0.15  # Maximum 15% drawdown allowed
        
    def validate_trade(self, signal: Dict, session: TradingSession) -> bool:
        """Validate if a trade should be executed based on risk parameters"""
        try:
            # Check if trading is enabled
            if not self.config.is_active:
                logger.warning("Trading is disabled in configuration")
                return False
            
            # Check daily trade limit
            if not self._check_daily_trade_limit(session):
                logger.warning("Daily trade limit exceeded")
                return False
            
            # Check position size limits
            if not self._check_position_size_limit(signal, session):
                logger.warning("Position size limit exceeded")
                return False
            
            # Check maximum drawdown
            if not self._check_drawdown_limit(session):
                logger.warning("Maximum drawdown limit exceeded")
                return False
            
            # Check minimum order size
            if not self._check_minimum_order_size(signal):
                logger.warning("Order size below minimum threshold")
                return False
            
            # Check maximum order size
            if not self._check_maximum_order_size(signal):
                logger.warning("Order size above maximum threshold")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Risk validation failed: {e}")
            return False
    
    def _check_daily_trade_limit(self, session: TradingSession) -> bool:
        """Check if daily trade limit has been exceeded"""
        try:
            today = datetime.utcnow().date()
            today_trades = [
                trade for trade in session.trades 
                if trade.timestamp.date() == today
            ]
            
            return len(today_trades) < self.max_daily_trades
            
        except Exception as e:
            logger.error(f"Failed to check daily trade limit: {e}")
            return False
    
    def _check_position_size_limit(self, signal: Dict, session: TradingSession) -> bool:
        """Check if position size is within acceptable limits"""
        try:
            if signal['action'] == 'buy':
                trade_amount = signal.get('amount_usdt', 0)
                max_allowed = session.initial_capital * self.max_position_size_percent
                return trade_amount <= max_allowed
            
            elif signal['action'] == 'sell':
                # For sell orders, we're reducing risk, so always allow
                return True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check position size limit: {e}")
            return False
    
    def _check_drawdown_limit(self, session: TradingSession) -> bool:
        """Check if current drawdown is within acceptable limits"""
        try:
            current_value = session.current_capital
            initial_value = session.initial_capital
            
            drawdown = (initial_value - current_value) / initial_value
            
            return drawdown <= self.max_drawdown_percent
            
        except Exception as e:
            logger.error(f"Failed to check drawdown limit: {e}")
            return False
    
    def _check_minimum_order_size(self, signal: Dict) -> bool:
        """Check if order size meets minimum requirements"""
        try:
            if signal['action'] == 'buy':
                return signal.get('amount_usdt', 0) >= self.config.min_order_size
            elif signal['action'] == 'sell':
                # For sell orders, check against minimum BST amount (approximate)
                return signal.get('amount_bst', 0) * 0.08 >= self.config.min_order_size  # Assuming ~$0.08 BST price
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check minimum order size: {e}")
            return False
    
    def _check_maximum_order_size(self, signal: Dict) -> bool:
        """Check if order size is below maximum limits"""
        try:
            if signal['action'] == 'buy':
                return signal.get('amount_usdt', 0) <= self.config.max_order_size
            elif signal['action'] == 'sell':
                # For sell orders, check against maximum BST amount (approximate)
                return signal.get('amount_bst', 0) * 0.08 <= self.config.max_order_size  # Assuming ~$0.08 BST price
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to check maximum order size: {e}")
            return False
    
    def calculate_position_risk(self, session: TradingSession) -> Dict:
        """Calculate current position risk metrics"""
        try:
            # Calculate basic risk metrics
            current_capital = session.current_capital
            initial_capital = session.initial_capital
            
            # Calculate drawdown
            drawdown = max(0, (initial_capital - current_capital) / initial_capital)
            
            # Calculate trade frequency (trades per day)
            session_days = max(1, (datetime.utcnow() - session.start_date).days)
            trade_frequency = len(session.trades) / session_days
            
            # Calculate win rate
            profitable_trades = 0
            total_completed_trades = 0
            
            for trade in session.trades:
                if trade.status == 'FILLED' and trade.executed_price:
                    total_completed_trades += 1
                    # Simple profit calculation (this could be more sophisticated)
                    if trade.side == 'SELL':
                        profitable_trades += 1
            
            win_rate = profitable_trades / total_completed_trades if total_completed_trades > 0 else 0
            
            # Risk score (0-100, higher is riskier)
            risk_score = (
                drawdown * 40 +  # Drawdown contributes 40% to risk score
                min(trade_frequency / 5, 1) * 30 +  # Trade frequency contributes 30%
                (1 - win_rate) * 30  # Poor win rate contributes 30%
            ) * 100
            
            return {
                'drawdown_percent': drawdown * 100,
                'trade_frequency': trade_frequency,
                'win_rate_percent': win_rate * 100,
                'total_trades': len(session.trades),
                'risk_score': min(100, risk_score),
                'risk_level': self._get_risk_level(risk_score)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate position risk: {e}")
            return {}
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to risk level description"""
        if risk_score < 20:
            return 'LOW'
        elif risk_score < 40:
            return 'MODERATE'
        elif risk_score < 60:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def get_risk_recommendations(self, session: TradingSession) -> List[str]:
        """Get risk management recommendations based on current position"""
        recommendations = []
        
        try:
            risk_metrics = self.calculate_position_risk(session)
            
            # Drawdown recommendations
            if risk_metrics.get('drawdown_percent', 0) > 10:
                recommendations.append("Consider reducing position sizes due to high drawdown")
            
            # Trade frequency recommendations
            if risk_metrics.get('trade_frequency', 0) > 3:
                recommendations.append("High trade frequency detected - consider longer intervals")
            
            # Win rate recommendations
            if risk_metrics.get('win_rate_percent', 0) < 40:
                recommendations.append("Low win rate - review strategy parameters")
            
            # Risk score recommendations
            risk_score = risk_metrics.get('risk_score', 0)
            if risk_score > 60:
                recommendations.append("CRITICAL: Consider pausing trading and reviewing strategy")
            elif risk_score > 40:
                recommendations.append("HIGH RISK: Reduce position sizes and increase monitoring")
            
            # Capital preservation recommendations
            if session.current_capital < session.initial_capital * 0.9:
                recommendations.append("Capital below 90% - focus on capital preservation")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate risk recommendations: {e}")
            return ["Error generating recommendations - manual review required"]
    
    def should_emergency_stop(self, session: TradingSession) -> Tuple[bool, str]:
        """Determine if emergency stop should be triggered"""
        try:
            # Check critical drawdown
            if session.current_capital < session.initial_capital * (1 - self.max_drawdown_percent):
                return True, f"Emergency stop: Drawdown exceeded {self.max_drawdown_percent*100}%"
            
            # Check if session has been running too long without progress
            session_days = (datetime.utcnow() - session.start_date).days
            if session_days > session.cycle_duration_days * 1.5:  # 50% over planned duration
                return True, "Emergency stop: Session duration exceeded planned cycle"
            
            # Check for excessive trading without results
            if len(session.trades) > 50 and session.current_capital < session.initial_capital * 0.95:
                return True, "Emergency stop: Excessive trading with poor results"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Failed to check emergency stop conditions: {e}")
            return True, f"Emergency stop: Error in risk assessment - {str(e)}"
    
    def log_risk_event(self, event_type: str, description: str, session: TradingSession):
        """Log risk management events"""
        try:
            logger.warning(f"RISK EVENT [{event_type}] Session: {session.session_name} - {description}")
            
            # Here you could also save to database or send alerts
            # For now, we'll just log it
            
        except Exception as e:
            logger.error(f"Failed to log risk event: {e}")

