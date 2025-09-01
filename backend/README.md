# BackTest Trading Bot - Backend

Backend service for the MVP BackTest Trading Bot, implementing a Hybrid Adaptive Strategy for cryptocurrency trading analysis.

## Features

- **Hybrid Adaptive Strategy**: Combines volume analysis, price analysis, and risk management
- **Binance Integration**: Fetches historical OHLCV data via ccxt
- **FastAPI**: Modern, fast web framework with automatic API documentation
- **Comprehensive Backtesting**: Full backtest execution with detailed statistics
- **Risk Management**: Dynamic position sizing and TP/SL management

## Architecture

### Core Components

1. **DataFetcher**: Retrieves historical market data from Binance
2. **HybridStrategy**: Main strategy orchestrator
   - **VolumeAnalyzer**: Detects volume-based signals
   - **PriceAnalyzer**: Analyzes price patterns and momentum
   - **RiskManager**: Manages position sizing and risk
   - **SignalCombiner**: Combines multiple signal sources
3. **BacktestEngine**: Orchestrates complete backtest execution
4. **API**: RESTful endpoints for frontend integration

### Strategy Logic

The Hybrid Adaptive Strategy works as follows:

1. **Volume Analysis**: Detects volume spikes above adaptive thresholds
2. **Price Analysis**: Identifies significant price movements and trends
3. **Signal Combination**: Combines volume and price signals with weighted scoring
4. **Risk Management**: Applies position sizing and TP/SL rules
5. **Backtest Execution**: Simulates trading with historical data

## Installation

### Prerequisites

- Python 3.10+
- pip or poetry

### Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   python -m app.main
   ```

3. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/v1/health

## API Endpoints

### Core Endpoints

- `GET /api/v1/health` - Health check
- `GET /api/v1/symbols` - Available trading symbols
- `GET /api/v1/intervals` - Available time intervals
- `GET /api/v1/backtest` - Run backtest (GET with query parameters)
- `POST /api/v1/backtest` - Run backtest (POST with request body)

### Example Usage

#### Run Backtest (GET)
```bash
curl "http://localhost:8000/api/v1/backtest?symbol=BTC/USDT&interval=15m&take_profit=0.02&stop_loss=0.01"
```

#### Run Backtest (POST)
```bash
curl -X POST "http://localhost:8000/api/v1/backtest" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "interval": "15m",
    "strategy_params": {
      "take_profit": 0.02,
      "stop_loss": 0.01,
      "volume_threshold": 1.5
    }
  }'
```

## Configuration

Configuration is managed through `app/config.py`:

- **API Settings**: Title, version, CORS origins
- **Strategy Parameters**: Default values for backtesting
- **Data Limits**: Maximum candles, timeouts
- **Supported Assets**: Available symbols and intervals

## Strategy Parameters

### Core Parameters

- `lookback_period`: Number of candles for volume average (default: 20)
- `volume_threshold`: Volume spike multiplier (default: 1.5)
- `min_price_change`: Minimum price change for signals (default: 0.005)
- `take_profit`: Take profit percentage (default: 0.02)
- `stop_loss`: Stop loss percentage (default: 0.01)
- `max_trades`: Maximum trades per backtest (default: 100)
- `initial_capital`: Starting capital (default: 10000)

### Advanced Parameters

- `volume_weight`: Weight for volume signals (default: 0.4)
- `price_weight`: Weight for price signals (default: 0.4)
- `momentum_weight`: Weight for momentum signals (default: 0.2)
- `min_combined_score`: Minimum score for signal execution (default: 0.5)

## Development

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── models/              # Data models
│   │   ├── strategy.py      # Strategy parameters
│   │   └── backtest.py      # Backtest results
│   ├── services/            # Business logic
│   │   ├── data_fetcher.py  # Binance data
│   │   ├── strategy.py      # Main strategy
│   │   ├── backtest.py      # Backtest engine
│   │   └── strategy/        # Strategy modules
│   │       ├── volume_analyzer.py
│   │       ├── price_analyzer.py
│   │       ├── risk_manager.py
│   │       └── signal_combiner.py
│   └── api/                 # API endpoints
│       └── backtest.py      # Backtest endpoints
├── requirements.txt
└── README.md
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Code Quality

```bash
# Format code
black app/

# Lint code
flake8 app/
```

## Performance

- **Data Fetching**: Cached with 5-minute TTL
- **Signal Processing**: Optimized pandas operations
- **Memory Usage**: Efficient data structures
- **API Response**: Typically < 1 second for 500 candles

## Error Handling

- **Validation**: Pydantic models for request/response validation
- **API Errors**: Structured error responses with details
- **Logging**: Comprehensive logging for debugging
- **Graceful Degradation**: Fallback mechanisms for data issues

## Monitoring

- **Health Checks**: `/api/v1/health` endpoint
- **Logging**: Structured logging with configurable levels
- **Metrics**: Execution time and performance tracking
- **Error Tracking**: Detailed error messages and stack traces

## Future Enhancements

- **Multiple Exchanges**: Support for additional exchanges
- **Advanced Strategies**: More sophisticated trading algorithms
- **Real-time Data**: WebSocket integration for live data
- **Machine Learning**: ML-based signal prediction
- **Portfolio Management**: Multi-asset backtesting
