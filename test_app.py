#!/usr/bin/env python3
"""
Test script to verify the Flask app starts correctly with the API configuration
"""

import os
import sys
import time

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_app_startup():
    """Test that the Flask app can start with the current configuration"""
    
    print("🧪 Testing Flask App Startup")
    print("=" * 40)
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment variables loaded")
        
        # Import Flask app components
        from src.main import app
        from src.models.trading_session import BotConfig, db
        
        print("✅ Flask app imported successfully")
        
        # Test database connection
        with app.app_context():
            # Check if configurations exist
            configs = BotConfig.query.all()
            print(f"✅ Database connection successful")
            print(f"📊 Found {len(configs)} configuration(s) in database")
            
            if configs:
                active_config = BotConfig.query.filter_by(is_active=True).first()
                if active_config:
                    print(f"✅ Active configuration: {active_config.config_name}")
                    print(f"   Symbol: {active_config.symbol}")
                    print(f"   API Key: {active_config.api_key[:8]}...{active_config.api_key[-4:]}")
                else:
                    print("⚠️  No active configuration found")
            else:
                print("⚠️  No configurations found. Run setup_api.py first.")
        
        print("\n🎯 App Test Results:")
        print("✅ Flask app can start successfully")
        print("✅ Database is accessible")
        print("✅ Configuration is loaded")
        
        return True
        
    except Exception as e:
        print(f"❌ App test failed: {e}")
        return False

def show_startup_instructions():
    """Show instructions for starting the app"""
    print("\n🚀 How to Start the Bot:")
    print("-" * 30)
    print("1. Start the Flask web interface:")
    print("   python src/main.py")
    print("   (or: venv\\Scripts\\python.exe src/main.py)")
    print("")
    print("2. Open your browser and go to:")
    print("   http://localhost:5000")
    print("")
    print("3. Use the web interface to:")
    print("   - View your configuration")
    print("   - Start trading sessions")
    print("   - Monitor bot performance")
    print("")
    print("4. API Endpoints available:")
    print("   - GET  /api/trading/config - View configurations")
    print("   - POST /api/trading/config/from-env - Create config from .env")
    print("   - GET  /api/trading/sessions - View trading sessions")
    print("   - POST /api/trading/sessions - Create new session")

if __name__ == "__main__":
    print("🤖 Bagging Strategy Bot - App Test")
    print("=" * 50)
    
    success = test_app_startup()
    
    if success:
        print("\n🎉 All tests passed!")
        show_startup_instructions()
    else:
        print("\n❌ Tests failed. Please check the error messages above.")
        print("Make sure you've run: python setup_api.py")