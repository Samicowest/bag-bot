"""
Configuration utilities for the Bagging Strategy Bot
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration from environment variables and defaults"""
    
    @staticmethod
    def get_mexc_credentials() -> Dict[str, str]:
        """Get MEXC API credentials from environment variables"""
        api_key = os.getenv('MEXC_API_KEY', '')
        api_secret = os.getenv('MEXC_API_SECRET', '')
        
        if not api_key or not api_secret:
            logger.warning("MEXC API credentials not found in environment variables")
        
        return {
            'api_key': api_key,
            'api_secret': api_secret
        }
    
    @staticmethod
    def get_default_trading_config() -> Dict[str, Any]:
        """Get default trading configuration from environment variables"""
        return {
            'symbol': os.getenv('DEFAULT_SYMBOL', 'BSTUSDT'),
            'min_order_size': float(os.getenv('DEFAULT_MIN_ORDER_SIZE', '15.0')),
            'max_order_size': float(os.getenv('DEFAULT_MAX_ORDER_SIZE', '75.0')),
            'profit_threshold': float(os.getenv('DEFAULT_PROFIT_THRESHOLD', '0.02')),
            'stop_loss_threshold': float(os.getenv('DEFAULT_STOP_LOSS_THRESHOLD', '0.05')),
            'trading_interval_minutes': int(os.getenv('DEFAULT_TRADING_INTERVAL', '15'))
        }
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL from environment variables"""
        return os.getenv('DATABASE_URL', 'sqlite:///src/database/app.db')
    
    @staticmethod
    def get_flask_secret_key() -> str:
        """Get Flask secret key from environment variables"""
        return os.getenv('FLASK_SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')
    
    @staticmethod
    def get_log_level() -> str:
        """Get logging level from environment variables"""
        return os.getenv('LOG_LEVEL', 'INFO').upper()
    
    @staticmethod
    def is_development() -> bool:
        """Check if running in development mode"""
        return os.getenv('FLASK_ENV', 'production').lower() == 'development'
    
    @staticmethod
    def validate_required_config() -> bool:
        """Validate that all required configuration is present"""
        credentials = ConfigManager.get_mexc_credentials()
        
        if not credentials['api_key'] or not credentials['api_secret']:
            logger.error("Missing required MEXC API credentials")
            return False
        
        return True
    
    @staticmethod
    def get_all_config() -> Dict[str, Any]:
        """Get all configuration as a dictionary"""
        return {
            'mexc_credentials': ConfigManager.get_mexc_credentials(),
            'trading_config': ConfigManager.get_default_trading_config(),
            'database_url': ConfigManager.get_database_url(),
            'flask_secret_key': ConfigManager.get_flask_secret_key(),
            'log_level': ConfigManager.get_log_level(),
            'is_development': ConfigManager.is_development()
        }

def setup_logging():
    """Setup logging configuration"""
    log_level = ConfigManager.get_log_level()
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bot.log') if not ConfigManager.is_development() else logging.NullHandler()
        ]
    )
    
    # Set specific loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)