import hashlib
import hmac
import time
import requests
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MexcApiClient:
    """
    MEXC Exchange API Client for the Bagging Strategy Bot
    """
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.mexc.com"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'X-MEXC-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        })
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature for API requests"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _get_timestamp(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(time.time() * 1000)
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """Make HTTP request to MEXC API"""
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        if signed:
            params['timestamp'] = self._get_timestamp()
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            params['signature'] = self._generate_signature(query_string)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise
    
    def get_account_info(self) -> Dict:
        """Get account information including balances"""
        return self._make_request('GET', '/api/v3/account', signed=True)
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get symbol information"""
        params = {'symbol': symbol}
        return self._make_request('GET', '/api/v3/exchangeInfo', params)
    
    def get_ticker_price(self, symbol: str) -> Dict:
        """Get current price for a symbol"""
        params = {'symbol': symbol}
        return self._make_request('GET', '/api/v3/ticker/price', params)
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Get order book for a symbol"""
        params = {'symbol': symbol, 'limit': limit}
        return self._make_request('GET', '/api/v3/depth', params)
    
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, 
                   price: Optional[float] = None, time_in_force: str = 'GTC') -> Dict:
        """Place a new order"""
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': quantity,
            'timeInForce': time_in_force
        }
        
        if price is not None and order_type.upper() == 'LIMIT':
            params['price'] = price
        
        return self._make_request('POST', '/api/v3/order', params, signed=True)
    
    def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """Get order status"""
        params = {'symbol': symbol, 'orderId': order_id}
        return self._make_request('GET', '/api/v3/order', params, signed=True)
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """Cancel an order"""
        params = {'symbol': symbol, 'orderId': order_id}
        return self._make_request('DELETE', '/api/v3/order', params, signed=True)
    
    def get_open_orders(self, symbol: str) -> List[Dict]:
        """Get all open orders for a symbol"""
        params = {'symbol': symbol}
        return self._make_request('GET', '/api/v3/openOrders', params, signed=True)
    
    def get_trade_history(self, symbol: str, limit: int = 500) -> List[Dict]:
        """Get trade history for a symbol"""
        params = {'symbol': symbol, 'limit': limit}
        return self._make_request('GET', '/api/v3/myTrades', params, signed=True)
    
    def get_balance(self, asset: str) -> Dict:
        """Get balance for a specific asset"""
        account_info = self.get_account_info()
        balances = account_info.get('balances', [])
        
        for balance in balances:
            if balance.get('asset') == asset.upper():
                return {
                    'asset': balance.get('asset'),
                    'free': float(balance.get('free', 0)),
                    'locked': float(balance.get('locked', 0)),
                    'total': float(balance.get('free', 0)) + float(balance.get('locked', 0))
                }
        
        return {'asset': asset.upper(), 'free': 0.0, 'locked': 0.0, 'total': 0.0}
    
    def get_24hr_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker statistics"""
        params = {'symbol': symbol}
        return self._make_request('GET', '/api/v3/ticker/24hr', params)
    
    def validate_api_credentials(self) -> Tuple[bool, str]:
        """Validate API credentials by making a test request"""
        try:
            account_info = self.get_account_info()
            if 'balances' in account_info:
                return True, "API credentials are valid"
            else:
                return False, "Invalid API response format"
        except Exception as e:
            return False, f"API validation failed: {str(e)}"
    
    def calculate_order_size(self, symbol: str, usdt_amount: float) -> float:
        """Calculate order size in base currency based on USDT amount"""
        try:
            ticker = self.get_ticker_price(symbol)
            current_price = float(ticker.get('price', 0))
            
            if current_price <= 0:
                raise ValueError("Invalid price received from exchange")
            
            quantity = usdt_amount / current_price
            return quantity
        
        except Exception as e:
            logger.error(f"Failed to calculate order size: {e}")
            raise
    
    def get_minimum_order_size(self, symbol: str) -> Dict:
        """Get minimum order size and other trading rules for a symbol"""
        try:
            exchange_info = self.get_symbol_info(symbol)
            symbols = exchange_info.get('symbols', [])
            
            for symbol_info in symbols:
                if symbol_info.get('symbol') == symbol:
                    filters = symbol_info.get('filters', [])
                    
                    min_qty = 0.0
                    min_notional = 0.0
                    step_size = 0.0
                    
                    for filter_info in filters:
                        if filter_info.get('filterType') == 'LOT_SIZE':
                            min_qty = float(filter_info.get('minQty', 0))
                            step_size = float(filter_info.get('stepSize', 0))
                        elif filter_info.get('filterType') == 'MIN_NOTIONAL':
                            min_notional = float(filter_info.get('minNotional', 0))
                    
                    return {
                        'min_qty': min_qty,
                        'min_notional': min_notional,
                        'step_size': step_size,
                        'status': symbol_info.get('status'),
                        'base_asset': symbol_info.get('baseAsset'),
                        'quote_asset': symbol_info.get('quoteAsset')
                    }
            
            raise ValueError(f"Symbol {symbol} not found in exchange info")
        
        except Exception as e:
            logger.error(f"Failed to get minimum order size: {e}")
            raise

