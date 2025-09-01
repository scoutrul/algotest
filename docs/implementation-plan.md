# Implementation Plan - MVP BackTest Trading Bot

## Phase 1: Backend Foundation (Level 3 Planning)

### 1.1 Project Structure Setup
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── models/              # Data models
│   │   ├── __init__.py
│   │   ├── strategy.py      # Strategy parameters
│   │   └── backtest.py      # Backtest results
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── data_fetcher.py  # Binance data
│   │   ├── strategy.py      # Trading strategy
│   │   └── backtest.py      # Backtest engine
│   └── api/                 # API endpoints
│       ├── __init__.py
│       └── backtest.py      # Backtest endpoints
├── requirements.txt
├── Dockerfile
└── README.md
```

### 1.2 Core Services Implementation

#### DataFetcher Service
- **Purpose**: Получение исторических OHLCV данных с Binance
- **Dependencies**: ccxt, pandas
- **Key Methods**:
  - `fetch_candles(symbol, interval, limit)`
  - `validate_symbol(symbol)`
  - `get_available_intervals()`

#### Strategy Service
- **Purpose**: Логика торговой стратегии
- **Key Components**:
  - Signal detection (объем + цена)
  - Entry/exit logic
  - TP/SL management
- **Key Methods**:
  - `detect_signals(candles, params)`
  - `calculate_entry_exit(signals, params)`
  - `apply_risk_management(trades, params)`

#### Backtest Engine
- **Purpose**: Выполнение бэктестинга
- **Key Methods**:
  - `run_backtest(strategy_params)`
  - `calculate_statistics(trades)`
  - `generate_report(results)`

### 1.3 API Endpoints

#### GET /backtest
- **Parameters**: symbol, interval, strategy_params
- **Response**: candles, trades, statistics
- **Error Handling**: Invalid symbols, API limits

#### GET /health
- **Purpose**: Health check
- **Response**: Service status

#### GET /symbols
- **Purpose**: Available trading pairs
- **Response**: List of supported symbols

## Phase 2: Frontend Foundation

### 2.1 Project Structure Setup
```
frontend/
├── src/
│   ├── App.svelte           # Main app component
│   ├── main.js              # Entry point
│   ├── components/
│   │   ├── Chart.svelte     # Trading chart
│   │   ├── StrategyForm.svelte # Parameters form
│   │   ├── Statistics.svelte # Results table
│   │   └── Controls.svelte  # Symbol/interval controls
│   ├── stores/
│   │   ├── backtest.js      # Backtest state
│   │   └── config.js        # App configuration
│   └── utils/
│       ├── api.js           # API client
│       └── chart.js         # Chart utilities
├── package.json
├── vite.config.js
└── README.md
```

### 2.2 Core Components

#### Chart Component
- **Library**: lightweight-charts
- **Features**:
  - OHLCV candlestick display
  - Trade entry/exit markers
  - Zoom and pan controls
  - Time range selection

#### StrategyForm Component
- **Fields**:
  - Symbol selection (BTC/USDT, ETH/USDT, etc.)
  - Interval selection (1m, 5m, 15m, 1h, 4h, 1d)
  - Lookback period (N candles)
  - Volume threshold multiplier
  - Take profit percentage
  - Stop loss percentage
- **Validation**: Client-side form validation

#### Statistics Component
- **Metrics**:
  - Total trades count
  - Win rate percentage
  - Total PnL
  - Maximum drawdown
  - Average trade duration

## Phase 3: Integration & Testing

### 3.1 API Integration
- **CORS Configuration**: Backend CORS for frontend
- **Error Handling**: Unified error responses
- **Data Validation**: Request/response validation

### 3.2 Development Workflow
- **Backend**: `uvicorn app.main:app --reload`
- **Frontend**: `npm run dev`
- **Docker**: Multi-stage builds for production

### 3.3 Testing Strategy
- **Backend**: Unit tests for services, integration tests for API
- **Frontend**: Component tests, API integration tests
- **E2E**: Basic user flow testing

## Dependencies & Configuration

### Backend Dependencies
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
ccxt==4.1.77
pandas==2.1.3
pydantic==2.5.0
python-multipart==0.0.6
```

### Frontend Dependencies
```
svelte@^4.0.0
vite@^5.0.0
lightweight-charts@^4.1.0
@vitejs/plugin-svelte@^5.0.0
```

## Challenges & Mitigations

### Challenge 1: API Rate Limits
- **Issue**: Binance API rate limiting
- **Mitigation**: Request caching, batch processing

### Challenge 2: Data Quality
- **Issue**: Missing or invalid historical data
- **Mitigation**: Data validation, fallback mechanisms

### Challenge 3: Chart Performance
- **Issue**: Large datasets affecting chart rendering
- **Mitigation**: Data pagination, virtual scrolling

### Challenge 4: Strategy Complexity
- **Issue**: Complex strategy logic
- **Mitigation**: Modular design, comprehensive testing

## Creative Phase Components

### Strategy Design
- **Type**: Algorithm Design
- **Focus**: Signal detection logic, risk management
- **Requirements**: Mathematical modeling, backtesting validation

### UI/UX Design
- **Type**: Interface Design
- **Focus**: Chart layout, form usability, data visualization
- **Requirements**: Trading interface best practices, responsive design
