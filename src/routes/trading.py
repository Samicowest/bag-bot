import os
from flask import Blueprint, request, jsonify
from src.models.trading_session import TradingSession, Trade, BotConfig, db
from src.services.mexc_api import MexcApiClient
from src.services.strategy_engine import BaggingStrategyEngine
from src.services.risk_manager import RiskManager
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_env_api_credentials():
    """Get API credentials from environment variables"""
    return {
        'api_key': os.getenv('MEXC_API_KEY', ''),
        'api_secret': os.getenv('MEXC_API_SECRET', '')
    }

trading_bp = Blueprint('trading', __name__)

@trading_bp.route('/config/from-env', methods=['POST'])
def create_config_from_env():
    """Create configuration from environment variables"""
    try:
        data = request.get_json() or {}
        config_name = data.get('config_name', 'Environment Config')
        
        # Get credentials from environment
        env_creds = get_env_api_credentials()
        
        if not env_creds['api_key'] or not env_creds['api_secret']:
            return jsonify({
                'success': False,
                'error': 'API credentials not found in environment variables'
            }), 400
        
        # Check if configuration already exists
        existing_config = BotConfig.query.filter_by(config_name=config_name).first()
        
        if existing_config:
            # Update existing configuration
            existing_config.api_key = env_creds['api_key']
            existing_config.api_secret = env_creds['api_secret']
            existing_config.symbol = os.getenv('DEFAULT_SYMBOL', 'BSTUSDT')
            existing_config.min_order_size = float(os.getenv('DEFAULT_MIN_ORDER_SIZE', '15.0'))
            existing_config.max_order_size = float(os.getenv('DEFAULT_MAX_ORDER_SIZE', '75.0'))
            existing_config.profit_threshold = float(os.getenv('DEFAULT_PROFIT_THRESHOLD', '0.02'))
            existing_config.stop_loss_threshold = float(os.getenv('DEFAULT_STOP_LOSS_THRESHOLD', '0.05'))
            existing_config.trading_interval_minutes = int(os.getenv('DEFAULT_TRADING_INTERVAL', '15'))
            existing_config.updated_at = datetime.utcnow()
            config = existing_config
        else:
            # Create new configuration
            config = BotConfig(
                config_name=config_name,
                api_key=env_creds['api_key'],
                api_secret=env_creds['api_secret'],
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
        
        # Test API credentials
        api_client = MexcApiClient(config.api_key, config.api_secret)
        is_valid, message = api_client.validate_api_credentials()
        
        return jsonify({
            'success': True,
            'message': 'Configuration created/updated from environment variables',
            'config': config.to_dict(),
            'api_validation': {
                'valid': is_valid,
                'message': message
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to create configuration from environment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/config', methods=['GET', 'POST'])
def manage_config():
    """Manage bot configuration"""
    if request.method == 'GET':
        configs = BotConfig.query.all()
        return jsonify([config.to_dict() for config in configs])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Create new configuration
            config = BotConfig(
                config_name=data.get('config_name'),
                api_key=data.get('api_key'),
                api_secret=data.get('api_secret'),
                symbol=data.get('symbol', 'BST/USDT'),
                min_order_size=data.get('min_order_size', 10.0),
                max_order_size=data.get('max_order_size', 100.0),
                profit_threshold=data.get('profit_threshold', 0.02),
                stop_loss_threshold=data.get('stop_loss_threshold', 0.05),
                trading_interval_minutes=data.get('trading_interval_minutes', 15)
            )
            
            db.session.add(config)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Configuration created successfully',
                'config': config.to_dict()
            })
            
        except Exception as e:
            logger.error(f"Failed to create configuration: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/config/<int:config_id>', methods=['PUT', 'DELETE'])
def update_config(config_id):
    """Update or delete bot configuration"""
    config = BotConfig.query.get_or_404(config_id)
    
    if request.method == 'PUT':
        try:
            data = request.get_json()
            
            # Update configuration fields
            for field in ['config_name', 'symbol', 'min_order_size', 'max_order_size', 
                         'profit_threshold', 'stop_loss_threshold', 'trading_interval_minutes', 'is_active']:
                if field in data:
                    setattr(config, field, data[field])
            
            # Handle sensitive fields separately
            if 'api_key' in data:
                config.api_key = data['api_key']
            if 'api_secret' in data:
                config.api_secret = data['api_secret']
            
            # If setting this config as active, deactivate all others
            if data.get('is_active', False):
                other_configs = BotConfig.query.filter(BotConfig.id != config.id).all()
                for other_config in other_configs:
                    other_config.is_active = False
            
            config.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Configuration updated successfully',
                'config': config.to_dict()
            })
            
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(config)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Configuration deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Failed to delete configuration: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/config/<int:config_id>/validate', methods=['POST'])
def validate_api_credentials(config_id):
    """Validate API credentials"""
    try:
        config = BotConfig.query.get_or_404(config_id)
        
        if not config.api_key or not config.api_secret:
            return jsonify({
                'success': False,
                'error': 'API credentials not configured'
            }), 400
        
        # Test API connection
        api_client = MexcApiClient(config.api_key, config.api_secret)
        is_valid, message = api_client.validate_api_credentials()
        
        return jsonify({
            'success': is_valid,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Failed to validate API credentials: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/sessions', methods=['GET', 'POST'])
def manage_sessions():
    """Manage trading sessions"""
    if request.method == 'GET':
        sessions = TradingSession.query.order_by(TradingSession.created_at.desc()).all()
        return jsonify([session.to_dict() for session in sessions])
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            
            # Check if there's already an active session
            active_session = TradingSession.query.filter_by(status='active').first()
            if active_session:
                return jsonify({
                    'success': False,
                    'error': 'An active session already exists. Complete or pause it first.'
                }), 400
            
            # Create new trading session
            session = TradingSession(
                session_name=data.get('session_name'),
                initial_capital=data.get('initial_capital'),
                current_capital=data.get('initial_capital'),
                cycle_duration_days=data.get('cycle_duration_days', 30)
            )
            
            db.session.add(session)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Trading session created successfully',
                'session': session.to_dict()
            })
            
        except Exception as e:
            logger.error(f"Failed to create trading session: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/sessions/<int:session_id>', methods=['GET', 'PUT'])
def manage_session(session_id):
    """Get or update a specific trading session"""
    session = TradingSession.query.get_or_404(session_id)
    
    if request.method == 'GET':
        # Include trades in the response
        session_data = session.to_dict()
        session_data['trades'] = [trade.to_dict() for trade in session.trades]
        return jsonify(session_data)
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            
            # Update session fields
            for field in ['session_name', 'status', 'cycle_duration_days']:
                if field in data:
                    setattr(session, field, data[field])
            
            session.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Session updated successfully',
                'session': session.to_dict()
            })
            
        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/sessions/<int:session_id>/complete', methods=['POST'])
def complete_session(session_id):
    """Complete a trading session"""
    try:
        session = TradingSession.query.get_or_404(session_id)
        
        if session.status != 'active':
            return jsonify({
                'success': False,
                'error': 'Only active sessions can be completed'
            }), 400
        
        # Get active configuration
        config = BotConfig.query.filter_by(is_active=True).first()
        if not config:
            
            return jsonify({
                'success': False,
                'error': 'No active configuration found'
            }), 400
        
        # Initialize strategy engine and complete cycle
        api_client = MexcApiClient(config.api_key, config.api_secret)
        strategy_engine = BaggingStrategyEngine(config, api_client)
        strategy_engine.session = session
        
        completion_report = strategy_engine.complete_trading_cycle()
        
        return jsonify({
            'success': True,
            'message': 'Session completed successfully',
            'report': completion_report
        })
        
    except Exception as e:
        logger.error(f"Failed to complete session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/market-data', methods=['GET'])
def get_market_data():
    """Get current market data for BST/USDT"""
    try:
        # Get active configuration
        config = BotConfig.query.filter_by(is_active=True).first()
        if not config:
            return jsonify({
                'success': False,
                'error': 'No active configuration found'
            }), 400
        
        # Get market data
        api_client = MexcApiClient(config.api_key, config.api_secret)
        strategy_engine = BaggingStrategyEngine(config, api_client)
        
        market_data = strategy_engine.analyze_market_conditions()
        
        return jsonify({
            'success': True,
            'market_data': market_data
        })
        
    except Exception as e:
        logger.error(f"Failed to get market data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategy/analyze', methods=['POST'])
def analyze_strategy():
    """Analyze current strategy and generate trading signal"""
    try:
        # Get active configuration and session
        config = BotConfig.query.filter_by(is_active=True).first()
        session = TradingSession.query.filter_by(status='active').first()
        
        if not config:
            return jsonify({
                'success': False,
                'error': 'No active configuration found'
            }), 400
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'No active trading session found'
            }), 400
        
        # Run strategy analysis
        api_client = MexcApiClient(config.api_key, config.api_secret)
        strategy_engine = BaggingStrategyEngine(config, api_client)
        strategy_engine.session = session
        
        cycle_result = strategy_engine.run_strategy_cycle()
        
        return jsonify({
            'success': True,
            'analysis': cycle_result
        })
        
    except Exception as e:
        logger.error(f"Failed to analyze strategy: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/strategy/execute', methods=['POST'])
def execute_strategy():
    """Execute a single strategy cycle"""
    try:
        data = request.get_json()
        force_execute = data.get('force_execute', False)
        
        # Get active configuration and session
        config = BotConfig.query.filter_by(is_active=True).first()
        session = TradingSession.query.filter_by(status='active').first()
        
        if not config:
            return jsonify({
                'success': False,
                'error': 'No active configuration found'
            }), 400
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'No active trading session found'
            }), 400
        
        # Initialize strategy engine
        api_client = MexcApiClient(config.api_key, config.api_secret)
        strategy_engine = BaggingStrategyEngine(config, api_client)
        strategy_engine.session = session
        
        # Run strategy cycle
        cycle_result = strategy_engine.run_strategy_cycle()
        
        # If force_execute is True and signal is not hold, execute the trade
        if force_execute and cycle_result['signal']['action'] != 'hold':
            trade = strategy_engine.execute_trade(cycle_result['signal'])
            cycle_result['trade_executed'] = trade.to_dict() if trade else None
        
        return jsonify({
            'success': True,
            'execution_result': cycle_result
        })
        
    except Exception as e:
        logger.error(f"Failed to execute strategy: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/risk/assessment', methods=['GET'])
def get_risk_assessment():
    """Get risk assessment for active session"""
    try:
        session = TradingSession.query.filter_by(status='active').first()
        config = BotConfig.query.filter_by(is_active=True).first()
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'No active trading session found'
            }), 400
        
        if not config:
            return jsonify({
                'success': False,
                'error': 'No active configuration found'
            }), 400
        
        # Generate risk assessment
        risk_manager = RiskManager(config)
        risk_metrics = risk_manager.calculate_position_risk(session)
        recommendations = risk_manager.get_risk_recommendations(session)
        should_stop, stop_reason = risk_manager.should_emergency_stop(session)
        
        return jsonify({
            'success': True,
            'risk_assessment': {
                'metrics': risk_metrics,
                'recommendations': recommendations,
                'emergency_stop_required': should_stop,
                'emergency_stop_reason': stop_reason
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get risk assessment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/balances', methods=['GET'])
def get_balances():
    """Get current account balances"""
    import traceback
    try:
        logger.debug("[BALANCES] Fetching active configuration...")
        config = BotConfig.query.filter_by(is_active=True).first()
        if not config:
            logger.error("[BALANCES] No active configuration found.")
            return jsonify({
                'success': False,
                'error': 'No active configuration found'
            }), 400

        logger.debug(f"[BALANCES] Using config: {config.to_dict()}")
        api_client = MexcApiClient(config.api_key, config.api_secret)
        logger.debug("[BALANCES] Created MexcApiClient.")

        # Get USDT and BST balances
        usdt_balance = api_client.get_balance('USDT')
        logger.debug(f"[BALANCES] USDT balance: {usdt_balance}")
        bst_balance = api_client.get_balance('BST')
        logger.debug(f"[BALANCES] BST balance: {bst_balance}")

        # Get current BST price
        ticker = api_client.get_ticker_price(config.symbol)
        logger.debug(f"[BALANCES] Ticker: {ticker}")
        bst_price = float(ticker.get('price', 0))
        logger.debug(f"[BALANCES] BST price: {bst_price}")

        total_value = usdt_balance['total'] + (bst_balance['total'] * bst_price)
        logger.debug(f"[BALANCES] Total value (USDT): {total_value}")

        return jsonify({
            'success': True,
            'balances': {
                'USDT': usdt_balance,
                'BST': bst_balance,
                'BST_price': bst_price,
                'total_value_usdt': total_value
            }
        })

    except Exception as e:
        logger.error(f"[BALANCES] Failed to get balances: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@trading_bp.route('/bot/start', methods=['POST'])
def start_bot():
    """Start the trading bot"""
    try:
        from src.services.bot_scheduler import bot_scheduler
        
        success = bot_scheduler.start()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Bot started successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to start bot'
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/bot/stop', methods=['POST'])
def stop_bot():
    """Stop the trading bot"""
    try:
        from src.services.bot_scheduler import bot_scheduler
        
        success = bot_scheduler.stop()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Bot stopped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to stop bot'
            }), 500
            
    except Exception as e:
        logger.error(f"Failed to stop bot: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/bot/status', methods=['GET'])
def get_bot_status():
    """Get bot status"""
    try:
        from src.services.bot_scheduler import bot_scheduler
        
        status = bot_scheduler.get_status()
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        logger.error(f"Failed to get bot status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@trading_bp.route('/bot/force-cycle', methods=['POST'])
def force_bot_cycle():
    """Force execute a single bot cycle"""
    try:
        from src.services.bot_scheduler import bot_scheduler
        
        cycle_result = bot_scheduler.force_cycle()
        
        return jsonify({
            'success': True,
            'cycle_result': cycle_result
        })
        
    except Exception as e:
        logger.error(f"Failed to force bot cycle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

