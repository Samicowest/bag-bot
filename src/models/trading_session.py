from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class TradingSession(db.Model):
    __tablename__ = 'trading_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(100), nullable=False)
    initial_capital = db.Column(db.Float, nullable=False)
    current_capital = db.Column(db.Float, nullable=False)
    accumulated_tokens = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='active')  # active, paused, completed
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    cycle_duration_days = db.Column(db.Integer, default=30)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to trades
    trades = db.relationship('Trade', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_name': self.session_name,
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'accumulated_tokens': self.accumulated_tokens,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'cycle_duration_days': self.cycle_duration_days,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Trade(db.Model):
    __tablename__ = 'trades'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('trading_sessions.id'), nullable=False)
    order_id = db.Column(db.String(100), unique=True)
    symbol = db.Column(db.String(20), nullable=False, default='BST/USDT')
    side = db.Column(db.String(10), nullable=False)  # BUY or SELL
    order_type = db.Column(db.String(10), nullable=False, default='MARKET')
    quantity = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float)
    executed_quantity = db.Column(db.Float, default=0.0)
    executed_price = db.Column(db.Float)
    status = db.Column(db.String(20), default='NEW')  # NEW, FILLED, PARTIALLY_FILLED, CANCELED
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    exchange_timestamp = db.Column(db.DateTime)
    commission = db.Column(db.Float, default=0.0)
    commission_asset = db.Column(db.String(10))
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'order_id': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'executed_quantity': self.executed_quantity,
            'executed_price': self.executed_price,
            'status': self.status,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'exchange_timestamp': self.exchange_timestamp.isoformat() if self.exchange_timestamp else None,
            'commission': self.commission,
            'commission_asset': self.commission_asset
        }

class BotConfig(db.Model):
    __tablename__ = 'bot_config'
    
    id = db.Column(db.Integer, primary_key=True)
    config_name = db.Column(db.String(100), nullable=False, unique=True)
    api_key = db.Column(db.String(200))
    api_secret = db.Column(db.String(200))
    symbol = db.Column(db.String(20), default='BST/USDT')
    min_order_size = db.Column(db.Float, default=10.0)
    max_order_size = db.Column(db.Float, default=100.0)
    profit_threshold = db.Column(db.Float, default=0.02)  # 2% profit threshold
    stop_loss_threshold = db.Column(db.Float, default=0.05)  # 5% stop loss
    trading_interval_minutes = db.Column(db.Integer, default=15)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'config_name': self.config_name,
            'symbol': self.symbol,
            'min_order_size': self.min_order_size,
            'max_order_size': self.max_order_size,
            'profit_threshold': self.profit_threshold,
            'stop_loss_threshold': self.stop_loss_threshold,
            'trading_interval_minutes': self.trading_interval_minutes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

