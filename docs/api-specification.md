# API Specification - MVP BackTest Trading Bot

## Base URL
```
http://localhost:8000
```

## Endpoints

### 1. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

### 2. Available Symbols
```http
GET /symbols
```

**Response:**
```json
{
  "symbols": [
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT",
    "ADA/USDT",
    "SOL/USDT"
  ]
}
```

### 3. Available Intervals
```http
GET /intervals
```

**Response:**
```json
{
  "intervals": [
    "1m",
    "5m",
    "15m",
    "1h",
    "4h",
    "1d"
  ]
}
```

### 4. Backtest Execution
```http
GET /backtest
```

**Query Parameters:**
- `symbol` (string, required): Trading pair (e.g., "BTC/USDT")
- `interval` (string, required): Time interval (e.g., "15m")
- `lookback_period` (integer, optional): Candles for volume average (default: 20)
- `volume_threshold` (float, optional): Volume spike multiplier (default: 1.5)
- `min_price_change` (float, optional): Minimum price change (default: 0.005)
- `take_profit` (float, optional): Take profit percentage (default: 0.02)
- `stop_loss` (float, optional): Stop loss percentage (default: 0.01)
- `max_trades` (integer, optional): Maximum trades (default: 100)
- `initial_capital` (float, optional): Starting capital (default: 10000)

**Example Request:**
```http
GET /backtest?symbol=BTC/USDT&interval=15m&lookback_period=20&volume_threshold=1.5&take_profit=0.02&stop_loss=0.01
```

**Response:**
```json
{
  "success": true,
  "data": {
    "candles": [
      {
        "timestamp": "2024-01-15T10:00:00Z",
        "open": 42000.0,
        "high": 42500.0,
        "low": 41800.0,
        "close": 42300.0,
        "volume": 150.5
      }
    ],
    "trades": [
      {
        "id": "trade_1",
        "entry_time": "2024-01-15T10:15:00Z",
        "exit_time": "2024-01-15T10:45:00Z",
        "direction": "long",
        "entry_price": 42300.0,
        "exit_price": 43146.0,
        "size": 1000.0,
        "pnl": 20.0,
        "exit_reason": "take_profit"
      }
    ],
    "statistics": {
      "total_trades": 25,
      "winning_trades": 17,
      "losing_trades": 8,
      "win_rate": 0.68,
      "total_pnl": 150.0,
      "total_return": 0.015,
      "max_drawdown": 0.05,
      "sharpe_ratio": 1.2,
      "avg_trade_duration": 1800
    },
    "parameters": {
      "symbol": "BTC/USDT",
      "interval": "15m",
      "lookback_period": 20,
      "volume_threshold": 1.5,
      "take_profit": 0.02,
      "stop_loss": 0.01
    }
  },
  "execution_time": 1.23
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "Symbol BTC/INVALID is not supported",
    "details": {
      "available_symbols": ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
    }
  }
}
```

## Error Codes

### 400 Bad Request
- `INVALID_PARAMETERS`: Invalid or missing required parameters
- `INVALID_SYMBOL`: Unsupported trading pair
- `INVALID_INTERVAL`: Unsupported time interval
- `INVALID_RANGE`: Parameter values out of valid range

### 500 Internal Server Error
- `DATA_FETCH_ERROR`: Failed to fetch market data
- `STRATEGY_ERROR`: Strategy execution failed
- `CALCULATION_ERROR`: Statistical calculation failed

## Rate Limiting
- 100 requests per minute per IP
- 1000 requests per hour per IP

## CORS
- Allowed origins: `http://localhost:3000`, `http://localhost:5173`
- Allowed methods: `GET`, `POST`, `OPTIONS`
- Allowed headers: `Content-Type`, `Authorization`
