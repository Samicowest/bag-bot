#!/usr/bin/env python3
"""
Configuration Setup Script for Bagging Strategy Bot
This script helps set up the initial configuration with API keys
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from src.models.trading_session import BotConfig, db
from src.services.mexc_api import MexcApiClient
from flask import Flask

def create_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def setup_api_configuration():
    """Set up API configuration with provided credentials"""
    
    # Your MEXC API credentials
    API_KEY = "mx0vglm9obNeHebaD7"
    API_SECRET = "7b209e8796bf44dc969148f609844e9d"
    
    app = create_app()
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if configuration already exists
        existing_config = BotConfig.query.filter_by(config_name="Default MEXC Config").first()
        
        if existing_config:
            print("Updating existing configuration...")
            existing_config.api_key = API_KEY
            existing_config.api_secret = API_SECRET
            existing_config.is_active = True
            config = existing_config
        else:
            print("Creating new configuration...")
            # Create new configuration with moderate settings
            config = BotConfig(
                config_name="Default MEXC Config",
                api_key=API_KEY,
                api_secret=API_SECRET,
                symbol="BSTUSDT",  # MEXC uses BSTUSDT format
                min_order_size=15.0,
                max_order_size=75.0,
                profit_threshold=0.02,  # 2%
                stop_loss_threshold=0.05,  # 5%
                trading_interval_minutes=15,
                is_active=True
            )
            db.session.add(config)
        
        # Deactivate other configurations
        other_configs = BotConfig.query.filter(BotConfig.id != (config.id if hasattr(config, 'id') else 0)).all()
        for other_config in other_configs:
            other_config.is_active = False
        
        db.session.commit()
        
        print(f"Configuration saved with ID: {config.id}")
        
        # Test API credentials
        print("Testing API credentials...")
        try:
            api_client = MexcApiClient(API_KEY, API_SECRET)
            is_valid, message = api_client.validate_api_credentials()
            
            if is_valid:
                print("✅ API credentials are valid!")
                print(f"Message: {message}")
                
                # Get account info to show balances
                try:
                    account_info = api_client.get_account_info()
                    print("\n📊 Account Balances:")
                    balances = account_info.get('balances', [])
                    for balance in balances:
                        if float(balance.get('free', 0)) > 0 or float(balance.get('locked', 0)) > 0:
                            asset = balance.get('asset')
                            free = float(balance.get('free', 0))
                            locked = float(balance.get('locked', 0))
                            total = free + locked
                            print(f"  {asset}: {total:.8f} (Free: {free:.8f}, Locked: {locked:.8f})")
                
                except Exception as e:
                    print(f"⚠️  Could not fetch account balances: {e}")
                
                # Test BST market data
                try:
                    print("\n📈 BST Market Data:")
                    ticker = api_client.get_24hr_ticker("BSTUSDT")
                    price = float(ticker.get('lastPrice', 0))
                    change = float(ticker.get('priceChangePercent', 0))
                    volume = float(ticker.get('volume', 0))
                    print(f"  Current Price: ${price:.6f}")
                    print(f"  24h Change: {change:.2f}%")
                    print(f"  24h Volume: {volume:,.0f} BST")
                    
                except Exception as e:
                    print(f"⚠️  Could not fetch BST market data: {e}")
                    print("    This might be normal if BST/USDT is not available on MEXC")
                    print("    You may need to adjust the symbol in the configuration")
            
            else:
                print("❌ API credentials validation failed!")
                print(f"Error: {message}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to test API credentials: {e}")
            return False
        
        print(f"\n✅ Configuration setup completed successfully!")
        print(f"Configuration Name: {config.config_name}")
        print(f"Symbol: {config.symbol}")
        print(f"Min Order Size: ${config.min_order_size}")
        print(f"Max Order Size: ${config.max_order_size}")
        print(f"Profit Threshold: {config.profit_threshold * 100}%")
        print(f"Stop Loss Threshold: {config.stop_loss_threshold * 100}%")
        print(f"Trading Interval: {config.trading_interval_minutes} minutes")
        
        return True

def list_configurations():
    """List all existing configurations"""
    app = create_app()
    
    with app.app_context():
        configs = BotConfig.query.all()
        
        if not configs:
            print("No configurations found.")
            return
        
        print("\n📋 Existing Configurations:")
        print("-" * 80)
        for config in configs:
            status = "🟢 ACTIVE" if config.is_active else "⚪ INACTIVE"
            print(f"{status} ID: {config.id} | Name: {config.config_name}")
            print(f"    Symbol: {config.symbol} | Min/Max Order: ${config.min_order_size}/${config.max_order_size}")
            print(f"    Profit: {config.profit_threshold*100}% | Stop Loss: {config.stop_loss_threshold*100}%")
            print(f"    Interval: {config.trading_interval_minutes}min | Created: {config.created_at}")
            print("-" * 80)

if __name__ == "__main__":
    print("🤖 Bagging Strategy Bot - Configuration Setup")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_configurations()
    else:
        success = setup_api_configuration()
        if success:
            print("\n🚀 You can now start the bot with: python src/main.py")
            print("   Or run the web interface and navigate to the trading configuration page")
        else:
            print("\n❌ Setup failed. Please check your API credentials and try again.")
            sys.exit(1)