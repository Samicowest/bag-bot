import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from src.services.mexc_api import MexcApiClient
from src.models.trading_session import TradingSession, Trade, BotConfig, db
from src.services.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class BaggingStrategyEngine:
    """
    Core strategy engine implementing the bagging strategy for BST token accumulation
    """
    
    def __init__(self, config: BotConfig, api_client: MexcApiClient):
        self.config = config
        self.api_client = api_client
        self.risk_manager = RiskManager(config)
        self.session: Optional[TradingSession] = None
        self.is_running = False
        
    def start_trading_session(self, session_name: str, initial_capital: float) -> TradingSession:
        """Start a new trading session"""
        try:
            # Create new trading session
            self.session = TradingSession(
                session_name=session_name,
                initial_capital=initial_capital,
                current_capital=initial_capital,
                status='active',
                cycle_duration_days=30
            )
            
            db.session.add(self.session)
            db.session.commit()
            
            logger.info(f"Started new trading session: {session_name} with capital: {initial_capital} USDT")
            return self.session
            
        except Exception as e:
            logger.error(f"Failed to start trading session: {e}")
            raise
    
    def load_active_session(self) -> Optional[TradingSession]:
        """Load the active trading session"""
        try:
            self.session = TradingSession.query.filter_by(status='active').first()
            if self.session:
                logger.info(f"Loaded active session: {self.session.session_name}")
            return self.session
            
        except Exception as e:
            logger.error(f"Failed to load active session: {e}")
            return None
    
    def analyze_market_conditions(self) -> Dict:
        """Analyze current market conditions for BST/USDT"""
        try:
            # Get current price and 24hr statistics
            ticker = self.api_client.get_24hr_ticker(self.config.symbol)
            current_price = float(ticker.get('lastPrice', 0))
            price_change_percent = float(ticker.get('priceChangePercent', 0))
            volume = float(ticker.get('volume', 0))
            
            # Get order book for market depth analysis
            order_book = self.api_client.get_order_book(self.config.symbol, limit=20)
            
            # Calculate bid-ask spread
            best_bid = float(order_book['bids'][0][0]) if order_book['bids'] else 0
            best_ask = float(order_book['asks'][0][0]) if order_book['asks'] else 0
            spread = (best_ask - best_bid) / best_bid * 100 if best_bid > 0 else 0
            
            # Analyze market sentiment
            market_sentiment = self._analyze_market_sentiment(price_change_percent, volume, spread)
            
            return {
                'current_price': current_price,
                'price_change_percent': price_change_percent,
                'volume': volume,
                'best_bid': best_bid,
                'best_ask': best_ask,
                'spread_percent': spread,
                'market_sentiment': market_sentiment,
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze market conditions: {e}")
            raise
    
    def _analyze_market_sentiment(self, price_change: float, volume: float, spread: float) -> str:
        """Analyze market sentiment based on price action and volume"""
        if price_change < -2.0 and volume > 100000:
            return 'strong_bearish'
        elif price_change < -1.0:
            return 'bearish'
        elif price_change > 2.0 and volume > 100000:
            return 'strong_bullish'
        elif price_change > 1.0:
            return 'bullish'
        elif spread > 1.0:
            return 'low_liquidity'
        else:
            return 'neutral'
    
    def generate_trading_signal(self, market_data: Dict) -> Dict:
        """Generate trading signal based on bagging strategy logic"""
        if not self.session:
            return {'action': 'hold', 'reason': 'No active session'}
        
        try:
            # Get current balances
            usdt_balance = self.api_client.get_balance('USDT')
            bst_balance = self.api_client.get_balance('BST')
            
            current_price = market_data['current_price']
            market_sentiment = market_data['market_sentiment']
            
            # Calculate current position value
            total_bst_value = bst_balance['total'] * current_price
            total_portfolio_value = usdt_balance['total'] + total_bst_value
            
            # Bagging strategy logic
            signal = self._apply_bagging_logic(
                usdt_balance=usdt_balance['total'],
                bst_balance=bst_balance['total'],
                current_price=current_price,
                market_sentiment=market_sentiment,
                total_portfolio_value=total_portfolio_value
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"Failed to generate trading signal: {e}")
            return {'action': 'hold', 'reason': f'Error: {str(e)}'}
    
    def _apply_bagging_logic(self, usdt_balance: float, bst_balance: float, 
                           current_price: float, market_sentiment: str, 
                           total_portfolio_value: float) -> Dict:
        """Apply the core bagging strategy logic"""
        
        # Calculate allocation percentages
        usdt_percentage = usdt_balance / total_portfolio_value if total_portfolio_value > 0 else 0
        bst_value = bst_balance * current_price
        bst_percentage = bst_value / total_portfolio_value if total_portfolio_value > 0 else 0
        
        # Strategy parameters
        target_usdt_percentage = 0.7  # Keep 70% in USDT for buying opportunities
        min_buy_threshold = 0.8  # Buy when USDT > 80%
        profit_take_threshold = 0.3  # Sell when USDT < 30%
        
        # Determine action based on bagging strategy
        if usdt_percentage > min_buy_threshold and market_sentiment in ['bearish', 'strong_bearish', 'neutral']:
            # Good buying opportunity - market is down or neutral and we have USDT
            buy_amount = min(
                usdt_balance * 0.2,  # Use 20% of available USDT
                self.config.max_order_size
            )
            
            if buy_amount >= self.config.min_order_size:
                return {
                    'action': 'buy',
                    'amount_usdt': buy_amount,
                    'reason': f'Bagging opportunity: {market_sentiment} market, USDT allocation: {usdt_percentage:.1%}'
                }
        
        elif usdt_percentage < profit_take_threshold and bst_balance > 0:
            # Consider selling some BST to recover USDT
            current_bst_value = bst_balance * current_price
            
            # Only sell if we have profit or need to rebalance
            if current_bst_value > self.session.initial_capital * 0.1:  # Have at least 10% of initial capital in BST
                sell_percentage = 0.3  # Sell 30% of BST holdings
                sell_amount = bst_balance * sell_percentage
                
                return {
                    'action': 'sell',
                    'amount_bst': sell_amount,
                    'reason': f'Profit taking: Low USDT allocation ({usdt_percentage:.1%}), BST value: ${current_bst_value:.2f}'
                }
        
        elif market_sentiment == 'strong_bullish' and bst_balance > 0:
            # Strong bullish market - consider taking some profits
            profit_percentage = (total_portfolio_value - self.session.initial_capital) / self.session.initial_capital
            
            if profit_percentage > 0.1:  # 10% profit
                sell_amount = bst_balance * 0.2  # Sell 20% of holdings
                
                return {
                    'action': 'sell',
                    'amount_bst': sell_amount,
                    'reason': f'Strong bullish market profit taking: {profit_percentage:.1%} profit'
                }
        
        return {
            'action': 'hold',
            'reason': f'No trading signal: USDT {usdt_percentage:.1%}, BST {bst_percentage:.1%}, Sentiment: {market_sentiment}'
        }
    
    def execute_trade(self, signal: Dict) -> Optional[Trade]:
        """Execute a trade based on the generated signal"""
        if signal['action'] == 'hold':
            return None
        
        try:
            if signal['action'] == 'buy':
                return self._execute_buy_order(signal['amount_usdt'])
            elif signal['action'] == 'sell':
                return self._execute_sell_order(signal['amount_bst'])
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            raise
    
    def _execute_buy_order(self, usdt_amount: float) -> Trade:
        """Execute a buy order for BST"""
        try:
            # Calculate BST quantity to buy
            quantity = self.api_client.calculate_order_size(self.config.symbol, usdt_amount)
            
            # Validate order size
            min_order_info = self.api_client.get_minimum_order_size(self.config.symbol)
            if quantity < min_order_info['min_qty']:
                raise ValueError(f"Order quantity {quantity} below minimum {min_order_info['min_qty']}")
            
            # Place market buy order
            order_response = self.api_client.place_order(
                symbol=self.config.symbol,
                side='BUY',
                order_type='MARKET',
                quantity=quantity
            )
            
            # Create trade record
            trade = Trade(
                session_id=self.session.id,
                order_id=order_response.get('orderId'),
                symbol=self.config.symbol,
                side='BUY',
                order_type='MARKET',
                quantity=quantity,
                status=order_response.get('status', 'NEW')
            )
            
            db.session.add(trade)
            db.session.commit()
            
            logger.info(f"Executed buy order: {quantity} BST for ~{usdt_amount} USDT")
            return trade
            
        except Exception as e:
            logger.error(f"Failed to execute buy order: {e}")
            raise
    
    def _execute_sell_order(self, bst_amount: float) -> Trade:
        """Execute a sell order for BST"""
        try:
            # Validate order size
            min_order_info = self.api_client.get_minimum_order_size(self.config.symbol)
            if bst_amount < min_order_info['min_qty']:
                raise ValueError(f"Order quantity {bst_amount} below minimum {min_order_info['min_qty']}")
            
            # Place market sell order
            order_response = self.api_client.place_order(
                symbol=self.config.symbol,
                side='SELL',
                order_type='MARKET',
                quantity=bst_amount
            )
            
            # Create trade record
            trade = Trade(
                session_id=self.session.id,
                order_id=order_response.get('orderId'),
                symbol=self.config.symbol,
                side='SELL',
                order_type='MARKET',
                quantity=bst_amount,
                status=order_response.get('status', 'NEW')
            )
            
            db.session.add(trade)
            db.session.commit()
            
            logger.info(f"Executed sell order: {bst_amount} BST")
            return trade
            
        except Exception as e:
            logger.error(f"Failed to execute sell order: {e}")
            raise
    
    def update_session_metrics(self):
        """Update trading session metrics"""
        if not self.session:
            return
        
        try:
            # Get current balances
            usdt_balance = self.api_client.get_balance('USDT')
            bst_balance = self.api_client.get_balance('BST')
            
            # Update session data
            self.session.current_capital = usdt_balance['total']
            self.session.accumulated_tokens = bst_balance['total']
            self.session.updated_at = datetime.utcnow()
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to update session metrics: {e}")
    
    def check_cycle_completion(self) -> bool:
        """Check if the current trading cycle should be completed"""
        if not self.session:
            return False
        
        # Check if cycle duration has been reached
        cycle_end_date = self.session.start_date + timedelta(days=self.session.cycle_duration_days)
        
        if datetime.utcnow() >= cycle_end_date:
            return True
        
        # Check if capital preservation goal is met
        if self.session.current_capital >= self.session.initial_capital * 0.95:  # 95% capital preservation
            return True
        
        return False
    
    def complete_trading_cycle(self) -> Dict:
        """Complete the current trading cycle and generate report"""
        if not self.session:
            raise ValueError("No active session to complete")
        
        try:
            # Update final metrics
            self.update_session_metrics()
            
            # Calculate performance
            final_usdt = self.session.current_capital
            final_bst = self.session.accumulated_tokens
            
            # Get current BST price for valuation
            ticker = self.api_client.get_ticker_price(self.config.symbol)
            current_price = float(ticker.get('price', 0))
            
            total_value = final_usdt + (final_bst * current_price)
            capital_preserved = final_usdt >= self.session.initial_capital * 0.95
            
            # Mark session as completed
            self.session.status = 'completed'
            self.session.end_date = datetime.utcnow()
            db.session.commit()
            
            report = {
                'session_id': self.session.id,
                'session_name': self.session.session_name,
                'initial_capital': self.session.initial_capital,
                'final_usdt': final_usdt,
                'final_bst': final_bst,
                'bst_value_usdt': final_bst * current_price,
                'total_value': total_value,
                'capital_preserved': capital_preserved,
                'profit_loss': total_value - self.session.initial_capital,
                'profit_loss_percent': (total_value - self.session.initial_capital) / self.session.initial_capital * 100,
                'duration_days': (self.session.end_date - self.session.start_date).days,
                'total_trades': len(self.session.trades)
            }
            
            logger.info(f"Completed trading cycle: {report}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to complete trading cycle: {e}")
            raise
    
    def run_strategy_cycle(self) -> Dict:
        """Run one complete strategy cycle"""
        try:
            # Analyze market conditions
            market_data = self.analyze_market_conditions()
            
            # Generate trading signal
            signal = self.generate_trading_signal(market_data)
            
            # Execute trade if signal is not hold
            trade = None
            if signal['action'] != 'hold':
                # Check risk management
                if self.risk_manager.validate_trade(signal, self.session):
                    trade = self.execute_trade(signal)
                else:
                    signal['action'] = 'hold'
                    signal['reason'] = 'Trade blocked by risk management'
            
            # Update session metrics
            self.update_session_metrics()
            
            # Check if cycle should be completed
            cycle_complete = self.check_cycle_completion()
            
            return {
                'timestamp': datetime.utcnow(),
                'market_data': market_data,
                'signal': signal,
                'trade_executed': trade.to_dict() if trade else None,
                'cycle_complete': cycle_complete,
                'session_metrics': self.session.to_dict() if self.session else None
            }
            
        except Exception as e:
            logger.error(f"Strategy cycle failed: {e}")
            raise

