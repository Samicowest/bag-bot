# API Reference - Bagging Strategy Bot

This document provides comprehensive API reference documentation for the Bagging Strategy Trading Bot. All endpoints use RESTful conventions and return JSON responses.

## Base URL

```
http://localhost:5000/api/trading
```

## Authentication

The bot uses MEXC API credentials configured through the web interface. No additional authentication is required for local API access.

## Response Format

All API responses follow this standard format:

```json
{
  "success": boolean,
  "message": "Human readable message",
  "data": object,
  "error": "Error message (only present when success is false)"
}
```

## Configuration Endpoints

### Get All Configurations

Retrieve all bot configurations.

**Endpoint**: `GET /config`

**Parameters**: None

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "config_name": "Conservative BST Bagging",
      "symbol": "BST/USDT",
      "min_order_size": 10.0,
      "max_order_size": 100.0,
      "profit_threshold": 0.02,
      "stop_loss_threshold": 0.05,
      "trading_interval_minutes": 15,
      "is_active": true,
      "created_at": "2025-07-10T09:00:00Z",
      "updated_at": "2025-07-10T09:00:00Z"
    }
  ]
}
```

### Create Configuration

Create a new bot configuration.

**Endpoint**: `POST /config`

**Parameters**:
```json
{
  "config_name": "string (required)",
  "api_key": "string (required)",
  "api_secret": "string (required)",
  "symbol": "string (optional, default: BST/USDT)",
  "min_order_size": "number (optional, default: 10.0)",
  "max_order_size": "number (optional, default: 100.0)",
  "profit_threshold": "number (optional, default: 0.02)",
  "stop_loss_threshold": "number (optional, default: 0.05)",
  "trading_interval_minutes": "number (optional, default: 15)"
}
```

**Example Request**:
```json
{
  "config_name": "My BST Strategy",
  "api_key": "mx0vgl...",
  "api_secret": "a1b2c3...",
  "min_order_size": 15.0,
  "max_order_size": 75.0,
  "trading_interval_minutes": 20
}
```

**Response**:
```json
{
  "success": true,
  "message": "Configuration created successfully",
  "data": {
    "id": 2,
    "config_name": "My BST Strategy",
    // ... other configuration fields
  }
}
```

### Update Configuration

Update an existing configuration.

**Endpoint**: `PUT /config/{config_id}`

**Parameters**: Same as create configuration (all optional)

**Response**: Updated configuration object

### Delete Configuration

Delete a configuration.

**Endpoint**: `DELETE /config/{config_id}`

**Response**:
```json
{
  "success": true,
  "message": "Configuration deleted successfully"
}
```

### Validate API Credentials

Test MEXC API credentials for a configuration.

**Endpoint**: `POST /config/{config_id}/validate`

**Response**:
```json
{
  "success": true,
  "message": "API credentials are valid"
}
```

## Session Management Endpoints

### Get All Sessions

Retrieve all trading sessions.

**Endpoint**: `GET /sessions`

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "session_name": "July 2025 Accumulation",
      "initial_capital": 1000.0,
      "current_capital": 950.0,
      "accumulated_tokens": 125.5,
      "status": "active",
      "start_date": "2025-07-01T00:00:00Z",
      "end_date": null,
      "cycle_duration_days": 30,
      "created_at": "2025-07-01T00:00:00Z",
      "updated_at": "2025-07-10T09:00:00Z"
    }
  ]
}
```

### Create Session

Create a new trading session.

**Endpoint**: `POST /sessions`

**Parameters**:
```json
{
  "session_name": "string (required)",
  "initial_capital": "number (required)",
  "cycle_duration_days": "number (optional, default: 30)"
}
```

**Response**: Created session object

### Get Session Details

Get detailed information about a specific session including trade history.

**Endpoint**: `GET /sessions/{session_id}`

**Response**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "session_name": "July 2025 Accumulation",
    // ... session fields
    "trades": [
      {
        "id": 1,
        "order_id": "12345",
        "symbol": "BST/USDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": 150.0,
        "executed_quantity": 150.0,
        "executed_price": 0.0825,
        "status": "FILLED",
        "timestamp": "2025-07-10T09:00:00Z",
        "commission": 0.02,
        "commission_asset": "BST"
      }
    ]
  }
}
```

### Update Session

Update session properties.

**Endpoint**: `PUT /sessions/{session_id}`

**Parameters**:
```json
{
  "session_name": "string (optional)",
  "status": "string (optional: active, paused, completed)",
  "cycle_duration_days": "number (optional)"
}
```

### Complete Session

Manually complete a trading session.

**Endpoint**: `POST /sessions/{session_id}/complete`

**Response**:
```json
{
  "success": true,
  "message": "Session completed successfully",
  "data": {
    "session_id": 1,
    "session_name": "July 2025 Accumulation",
    "initial_capital": 1000.0,
    "final_usdt": 950.0,
    "final_bst": 125.5,
    "bst_value_usdt": 103.125,
    "total_value": 1053.125,
    "capital_preserved": true,
    "profit_loss": 53.125,
    "profit_loss_percent": 5.31,
    "duration_days": 10,
    "total_trades": 8
  }
}
```

## Bot Control Endpoints

### Start Bot

Start the automated trading bot.

**Endpoint**: `POST /bot/start`

**Response**:
```json
{
  "success": true,
  "message": "Bot started successfully"
}
```

### Stop Bot

Stop the automated trading bot.

**Endpoint**: `POST /bot/stop`

**Response**:
```json
{
  "success": true,
  "message": "Bot stopped successfully"
}
```

### Get Bot Status

Get current bot operational status.

**Endpoint**: `GET /bot/status`

**Response**:
```json
{
  "success": true,
  "data": {
    "is_running": true,
    "has_active_session": true,
    "config_active": true,
    "thread_alive": true
  }
}
```

### Force Bot Cycle

Manually trigger a single strategy cycle.

**Endpoint**: `POST /bot/force-cycle`

**Response**:
```json
{
  "success": true,
  "data": {
    "timestamp": "2025-07-10T09:00:00Z",
    "market_data": {
      "current_price": 0.0823,
      "price_change_percent": -2.5,
      "volume": 150000,
      "market_sentiment": "bearish"
    },
    "signal": {
      "action": "buy",
      "amount_usdt": 50.0,
      "reason": "Bagging opportunity: bearish market, USDT allocation: 85%"
    },
    "trade_executed": {
      "id": 15,
      "side": "BUY",
      "quantity": 607.3,
      "status": "FILLED"
    },
    "cycle_complete": false
  }
}
```

## Market Data Endpoints

### Get Market Data

Get current market analysis for BST/USDT.

**Endpoint**: `GET /market-data`

**Response**:
```json
{
  "success": true,
  "data": {
    "current_price": 0.0823,
    "price_change_percent": -2.5,
    "volume": 150000.0,
    "best_bid": 0.0822,
    "best_ask": 0.0824,
    "spread_percent": 0.24,
    "market_sentiment": "bearish",
    "timestamp": "2025-07-10T09:00:00Z"
  }
}
```

### Get Account Balances

Get current USDT and BST balances.

**Endpoint**: `GET /balances`

**Response**:
```json
{
  "success": true,
  "data": {
    "USDT": {
      "asset": "USDT",
      "free": 850.0,
      "locked": 0.0,
      "total": 850.0
    },
    "BST": {
      "asset": "BST",
      "free": 1250.5,
      "locked": 0.0,
      "total": 1250.5
    },
    "BST_price": 0.0823,
    "total_value_usdt": 952.91
  }
}
```

## Strategy Analysis Endpoints

### Analyze Strategy

Perform strategy analysis without executing trades.

**Endpoint**: `POST /strategy/analyze`

**Response**:
```json
{
  "success": true,
  "data": {
    "timestamp": "2025-07-10T09:00:00Z",
    "market_data": {
      "current_price": 0.0823,
      "market_sentiment": "bearish"
    },
    "signal": {
      "action": "buy",
      "amount_usdt": 50.0,
      "reason": "Bagging opportunity: bearish market, USDT allocation: 85%"
    },
    "trade_executed": null,
    "cycle_complete": false,
    "session_metrics": {
      "current_capital": 850.0,
      "accumulated_tokens": 1250.5
    }
  }
}
```

### Execute Strategy

Execute a complete strategy cycle with optional trade execution.

**Endpoint**: `POST /strategy/execute`

**Parameters**:
```json
{
  "force_execute": "boolean (optional, default: false)"
}
```

**Response**: Same as analyze strategy, but may include executed trade details

## Risk Management Endpoints

### Get Risk Assessment

Get comprehensive risk analysis for the active session.

**Endpoint**: `GET /risk/assessment`

**Response**:
```json
{
  "success": true,
  "data": {
    "metrics": {
      "drawdown_percent": 5.0,
      "trade_frequency": 2.5,
      "win_rate_percent": 75.0,
      "total_trades": 8,
      "risk_score": 25.5,
      "risk_level": "MODERATE"
    },
    "recommendations": [
      "Consider reducing position sizes due to recent volatility",
      "Monitor market conditions closely"
    ],
    "emergency_stop_required": false,
    "emergency_stop_reason": ""
  }
}
```

## Error Handling

### Common Error Responses

**400 Bad Request**:
```json
{
  "success": false,
  "error": "Invalid request parameters"
}
```

**404 Not Found**:
```json
{
  "success": false,
  "error": "Resource not found"
}
```

**500 Internal Server Error**:
```json
{
  "success": false,
  "error": "Internal server error: detailed error message"
}
```

### Error Codes

| HTTP Code | Description | Common Causes |
|-----------|-------------|---------------|
| 400 | Bad Request | Missing required parameters, invalid data types |
| 401 | Unauthorized | Invalid API credentials |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists, conflicting state |
| 500 | Internal Server Error | Database errors, API failures, system issues |

## Rate Limiting

The bot implements internal rate limiting to comply with MEXC API restrictions:

- **Market Data**: 1200 requests per minute
- **Trading Operations**: 100 requests per 10 seconds
- **Account Information**: 600 requests per minute

## WebSocket Support

Currently, the bot uses REST API polling. WebSocket support for real-time updates is planned for future releases.

## SDK Examples

### Python SDK Usage

```python
import requests

class BaggingBotAPI:
    def __init__(self, base_url="http://localhost:5000/api/trading"):
        self.base_url = base_url
    
    def get_market_data(self):
        response = requests.get(f"{self.base_url}/market-data")
        return response.json()
    
    def create_session(self, name, capital, duration=30):
        data = {
            "session_name": name,
            "initial_capital": capital,
            "cycle_duration_days": duration
        }
        response = requests.post(f"{self.base_url}/sessions", json=data)
        return response.json()
    
    def start_bot(self):
        response = requests.post(f"{self.base_url}/bot/start")
        return response.json()

# Usage
api = BaggingBotAPI()
market_data = api.get_market_data()
print(f"BST Price: ${market_data['data']['current_price']}")
```

### JavaScript SDK Usage

```javascript
class BaggingBotAPI {
    constructor(baseUrl = '/api/trading') {
        this.baseUrl = baseUrl;
    }
    
    async getMarketData() {
        const response = await fetch(`${this.baseUrl}/market-data`);
        return await response.json();
    }
    
    async createSession(name, capital, duration = 30) {
        const response = await fetch(`${this.baseUrl}/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_name: name,
                initial_capital: capital,
                cycle_duration_days: duration
            })
        });
        return await response.json();
    }
    
    async startBot() {
        const response = await fetch(`${this.baseUrl}/bot/start`, {
            method: 'POST'
        });
        return await response.json();
    }
}

// Usage
const api = new BaggingBotAPI();
api.getMarketData().then(data => {
    console.log(`BST Price: $${data.data.current_price}`);
});
```

## Changelog

### Version 1.0.0
- Initial API release
- Core trading functionality
- Configuration management
- Session management
- Risk assessment

### Planned Features
- WebSocket real-time updates
- Advanced analytics endpoints
- Multi-exchange support
- Portfolio optimization endpoints
- Backtesting API

This API reference provides comprehensive documentation for integrating with the Bagging Strategy Bot. For additional support or feature requests, please refer to the main documentation or contact support.

