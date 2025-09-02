"""
Setup helper utilities for the Bagging Strategy Bot
"""

import os
import sys
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.models.trading_session import BotConfig, db
from src.services.mexc_api import MexcApiClient
from src.utils.config import ConfigManager
from flask import Flask

logger = logging.getLogger(__name__)

class SetupHelper:
    """Helper class for setting up bot configuration"""
    
    def __init__(self):
        self.app = self._create_app()
    
    def _create_app(self) -> Flask:
        """Create Flask app for database operations"""
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = ConfigManager.get_database_url()
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = ConfigManager.get_flask_secret_key()
        db.init_app(app)
        return app
    
    def create_config_from_env(self, config_name: str = "Environment Config") -> Optional[BotConfig]:
        """Create configuration from environment variables"""
        
        with self.app.app_context():
            # Create tables if they don't exist
            db.create_all()
            
            # Get credentials and config from environment
            credentials = ConfigManager.get_mexc_credentials()
            trading_config = ConfigManager.get_default_trading_config()
            
            if not credentials['api_key'] or not credentials['api_secret']:
                logger.error("API credentials not found in environment variables")
                return None
            
            # Check if configuration already exists
            existing_config = BotConfig.query.filter_by(config_name=config_name).first()
            
            if existing_config:
                logger.info(f"Updating existing configuration: {config_name}")
                existing_config.api_key = credentials['api_key']
                existing_config.api_secret = credentials['api_secret']
                existing_config.symbol = trading_config['symbol']
                existing_config.min_order_size = trading_config['min_order_size']
                existing_config.max_order_size = trading_config['max_order_size']
                existing_config.profit_threshold = trading_config['profit_threshold']
                existing_config.stop_loss_threshold = trading_config['stop_loss_threshold']
                existing_config.trading_interval_minutes = trading_config['trading_interval_minutes']
                existing_config.updated_at = datetime.utcnow()
                config = existing_config
            else:
                logger.info(f"Creating new configuration: {config_name}")
                config = BotConfig(
                    config_name=config_name,
                    api_key=credentials['api_key'],
                    api_secret=credentials['api_secret'],
                    symbol=trading_config['symbol'],
                    min_order_size=trading_config['min_order_size'],
                    max_order_size=trading_config['max_order_size'],
                    profit_threshold=trading_config['profit_threshold'],
                    stop_loss_threshold=trading_config['stop_loss_threshold'],
                    trading_interval_minutes=trading_config['trading_interval_minutes'],
                    is_active=True
                )
                db.session.add(config)
            
            # Deactivate other configurations
            other_configs = BotConfig.query.filter(BotConfig.id != (config.id if hasattr(config, 'id') else 0)).all()
            for other_config in other_configs:
                other_config.is_active = False
            
            db.session.commit()
            logger.info(f"Configuration saved with ID: {config.id}")
            
            return config
    
    def validate_api_credentials(self, config: BotConfig) -> tuple[bool, str]:
        """Validate API credentials"""
        try:
            api_client = MexcApiClient(config.api_key, config.api_secret)
            return api_client.validate_api_credentials()
        except Exception as e:
            return False, f"Validation failed: {str(e)}"
    
    def get_account_summary(self, config: BotConfig) -> Dict[str, Any]:
        """Get account summary including balances and market data"""
        try:
            api_client = MexcApiClient(config.api_key, config.api_secret)
            
            # Get account info
            account_info = api_client.get_account_info()
            balances = []
            
            for balance in account_info.get('balances', []):
                if float(balance.get('free', 0)) > 0 or float(balance.get('locked', 0)) > 0:
                    balances.append({
                        'asset': balance.get('asset'),
                        'free': float(balance.get('free', 0)),
                        'locked': float(balance.get('locked', 0)),
                        'total': float(balance.get('free', 0)) + float(balance.get('locked', 0))
                    })
            
            # Get market data for configured symbol
            market_data = {}
            try:
                ticker = api_client.get_24hr_ticker(config.symbol)
                market_data = {
                    'symbol': config.symbol,
                    'price': float(ticker.get('lastPrice', 0)),
                    'change_percent': float(ticker.get('priceChangePercent', 0)),
                    'volume': float(ticker.get('volume', 0)),
                    'high': float(ticker.get('highPrice', 0)),
                    'low': float(ticker.get('lowPrice', 0))
                }
            except Exception as e:
                logger.warning(f"Could not fetch market data for {config.symbol}: {e}")
                market_data = {'error': str(e)}
            
            return {
                'balances': balances,
                'market_data': market_data,
                'account_status': 'active'
            }
            
        except Exception as e:
            logger.error(f"Failed to get account summary: {e}")
            return {'error': str(e)}
    
    def list_configurations(self) -> list[Dict[str, Any]]:
        """List all configurations"""
        with self.app.app_context():
            configs = BotConfig.query.all()
            return [config.to_dict() for config in configs]
    
    def activate_configuration(self, config_id: int) -> bool:
        """Activate a specific configuration"""
        with self.app.app_context():
            try:
                # Deactivate all configurations
                BotConfig.query.update({'is_active': False})
                
                # Activate the specified configuration
                config = BotConfig.query.get(config_id)
                if config:
                    config.is_active = True
                    db.session.commit()
                    logger.info(f"Activated configuration: {config.config_name}")
                    return True
                else:
                    logger.error(f"Configuration with ID {config_id} not found")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to activate configuration: {e}")
                db.session.rollback()
                return False
    
    def delete_configuration(self, config_id: int) -> bool:
        """Delete a configuration"""
        with self.app.app_context():
            try:
                config = BotConfig.query.get(config_id)
                if config:
                    db.session.delete(config)
                    db.session.commit()
                    logger.info(f"Deleted configuration: {config.config_name}")
                    return True
                else:
                    logger.error(f"Configuration with ID {config_id} not found")
                    return False
                    
            except Exception as e:
                logger.error(f"Failed to delete configuration: {e}")
                db.session.rollback()
                return False