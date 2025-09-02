#!/usr/bin/env python3
"""
Simple API Setup Script for Bagging Strategy Bot
This script sets up the API configuration using environment variables
"""

import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Make sure environment variables are set.")

# Import Flask and database models
try:
    from flask import Flask
    from src.models.trading_session import BotConfig, db
    from src.services.mexc_api import MexcApiClient
    from datetime import datetime
    print("✅ Successfully imported required modules")
except ImportError as e:
    print(f"❌ Failed to import required modules: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

def create_flask_app():
    """Create Flask app for database operations"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'src', 'database', 'app.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')
    db.init_app(app)
    return app

def setup_api_config():
    """Setup API configuration directly in database"""
    
    # Check if environment variables are set
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ API credentials not found in environment variables!")
        print("Please check your .env file contains:")
        print("MEXC_API_KEY=your_api_key_here")
        print("MEXC_API_SECRET=your_api_secret_here")
        return False
    
    print(f"🔑 Found API credentials in environment")
    print(f"API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"API Secret: {api_secret[:8]}...{api_secret[-4:]}")
    
    print("\n🚀 Setting up configuration...")
    
    try:
        # Create Flask app and database context
        app = create_flask_app()
        
        with app.app_context():
            # Create tables if they don't exist
            db.create_all()
            
            config_name = "Default MEXC Config"
            
            # Check if configuration already exists
            existing_config = BotConfig.query.filter_by(config_name=config_name).first()
            
            if existing_config:
                print("📝 Updating existing configuration...")
                existing_config.api_key = api_key
                existing_config.api_secret = api_secret
                existing_config.symbol = os.getenv('DEFAULT_SYMBOL', 'BSTUSDT')
                existing_config.min_order_size = float(os.getenv('DEFAULT_MIN_ORDER_SIZE', '15.0'))
                existing_config.max_order_size = float(os.getenv('DEFAULT_MAX_ORDER_SIZE', '75.0'))
                existing_config.profit_threshold = float(os.getenv('DEFAULT_PROFIT_THRESHOLD', '0.02'))
                existing_config.stop_loss_threshold = float(os.getenv('DEFAULT_STOP_LOSS_THRESHOLD', '0.05'))
                existing_config.trading_interval_minutes = int(os.getenv('DEFAULT_TRADING_INTERVAL', '15'))
                existing_config.updated_at = datetime.utcnow()
                existing_config.is_active = True
                config = existing_config
            else:
                print("🆕 Creating new configuration...")
                config = BotConfig(
                    config_name=config_name,
                    api_key=api_key,
                    api_secret=api_secret,
                    symbol=os.getenv('DEFAULT_SYMBOL', 'BSTUSDT'),
                    min_order_size=float(os.getenv('DEFAULT_MIN_ORDER_SIZE', '15.0')),
                    max_order_size=float(os.getenv('DEFAULT_MAX_ORDER_SIZE', '75.0')),
                    profit_threshold=float(os.getenv('DEFAULT_PROFIT_THRESHOLD', '0.02')),
                    stop_loss_threshold=float(os.getenv('DEFAULT_STOP_LOSS_THRESHOLD', '0.05')),
                    trading_interval_minutes=int(os.getenv('DEFAULT_TRADING_INTERVAL', '15')),
                    is_active=True
                )
                db.session.add(config)
            
            # Deactivate other configurations
            other_configs = BotConfig.query.filter(BotConfig.id != (config.id if hasattr(config, 'id') else 0)).all()
            for other_config in other_configs:
                other_config.is_active = False
            
            db.session.commit()
            
            print("✅ Configuration saved to database!")
            print(f"Configuration ID: {config.id}")
            
            # Display configuration details
            print(f"\n📋 Configuration Details:")
            print(f"  Name: {config.config_name}")
            print(f"  Symbol: {config.symbol}")
            print(f"  Min Order Size: ${config.min_order_size}")
            print(f"  Max Order Size: ${config.max_order_size}")
            print(f"  Profit Threshold: {config.profit_threshold * 100}%")
            print(f"  Stop Loss Threshold: {config.stop_loss_threshold * 100}%")
            print(f"  Trading Interval: {config.trading_interval_minutes} minutes")
            
            # Test API credentials
            print(f"\n🔐 Testing API credentials...")
            try:
                api_client = MexcApiClient(config.api_key, config.api_secret)
                is_valid, message = api_client.validate_api_credentials()
                
                if is_valid:
                    print(f"  ✅ {message}")
                    
                    # Try to get account info
                    try:
                        account_info = api_client.get_account_info()
                        balances = account_info.get('balances', [])
                        
                        print(f"\n💰 Account Balances:")
                        non_zero_balances = [b for b in balances if float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0]
                        
                        if non_zero_balances:
                            for balance in non_zero_balances[:10]:  # Show first 10 non-zero balances
                                asset = balance.get('asset')
                                free = float(balance.get('free', 0))
                                locked = float(balance.get('locked', 0))
                                total = free + locked
                                print(f"  {asset}: {total:.8f} (Free: {free:.8f}, Locked: {locked:.8f})")
                        else:
                            print("  No balances found or all balances are zero")
                            
                    except Exception as e:
                        print(f"  ⚠️  Could not fetch account balances: {e}")
                    
                    # Try to get market data for the configured symbol
                    try:
                        print(f"\n📈 Market Data for {config.symbol}:")
                        ticker = api_client.get_24hr_ticker(config.symbol)
                        price = float(ticker.get('lastPrice', 0))
                        change = float(ticker.get('priceChangePercent', 0))
                        volume = float(ticker.get('volume', 0))
                        print(f"  Current Price: ${price:.6f}")
                        print(f"  24h Change: {change:.2f}%")
                        print(f"  24h Volume: {volume:,.0f}")
                        
                    except Exception as e:
                        print(f"  ⚠️  Could not fetch market data for {config.symbol}: {e}")
                        print(f"     This might be normal if {config.symbol} is not available on MEXC")
                        print(f"     You may need to adjust the symbol in your .env file")
                
                else:
                    print(f"  ❌ {message}")
                    return False
                    
            except Exception as e:
                print(f"  ❌ API validation failed: {e}")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False

def show_env_status():
    """Show current environment variable status"""
    print("🔍 Environment Variables Status:")
    print("-" * 40)
    
    vars_to_check = [
        'MEXC_API_KEY',
        'MEXC_API_SECRET',
        'DEFAULT_SYMBOL',
        'DEFAULT_MIN_ORDER_SIZE',
        'DEFAULT_MAX_ORDER_SIZE',
        'DEFAULT_PROFIT_THRESHOLD',
        'DEFAULT_STOP_LOSS_THRESHOLD',
        'DEFAULT_TRADING_INTERVAL'
    ]
    
    for var in vars_to_check:
        value = os.getenv(var)
        if value:
            if 'KEY' in var or 'SECRET' in var:
                # Mask sensitive values
                display_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
            else:
                display_value = value
            print(f"  ✅ {var}: {display_value}")
        else:
            print(f"  ❌ {var}: Not set")

if __name__ == "__main__":
    print("🤖 Bagging Strategy Bot - API Setup")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        show_env_status()
    else:
        show_env_status()
        print("\n" + "=" * 50)
        
        success = setup_api_config()
        
        if success:
            print("\n🎉 Setup completed successfully!")
            print("You can now start the bot with: python src/main.py")
            print("Or access the web interface at: http://localhost:5000")
        else:
            print("\n💡 Setup Instructions:")
            print("1. Make sure your .env file contains the correct API credentials")
            print("2. Install requirements: pip install -r requirements.txt")
            print("3. Run this script again: python setup_api.py")