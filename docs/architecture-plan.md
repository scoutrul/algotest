# Architecture Plan - MVP BackTest Trading Bot

## Overview
Двухсервисная архитектура для торгового бота с бэктестингом на исторических данных Binance.

## System Architecture

```
┌─────────────────┐    HTTP/REST    ┌─────────────────┐
│   Frontend      │◄──────────────►│   Backend       │
│   (Svelte)      │                 │   (FastAPI)     │
│                 │                 │                 │
│ • Chart UI      │                 │ • Data Fetcher  │
│ • Form Controls │                 │ • Strategy      │
│ • Statistics    │                 │ • API Endpoints │
└─────────────────┘                 └─────────────────┘
                                             │
                                             │ ccxt
                                             ▼
                                    ┌─────────────────┐
                                    │   Binance API   │
                                    │   (Historical   │
                                    │    OHLCV Data)  │
                                    └─────────────────┘
```

## Backend Architecture (Python/FastAPI)

### Core Modules
1. **DataFetcher** - получение исторических данных
2. **StrategyRunner** - логика торговой стратегии
3. **BacktestEngine** - движок бэктестинга
4. **API** - REST endpoints

### API Endpoints
- `GET /backtest` - основной endpoint для бэктестинга
- `GET /health` - проверка состояния сервиса
- `GET /symbols` - список доступных торговых пар

### Data Flow
1. Получение параметров стратегии
2. Загрузка исторических данных через ccxt
3. Применение стратегии к данным
4. Расчет статистики и результатов
5. Возврат JSON с результатами

## Frontend Architecture (Svelte)

### Components
1. **Chart** - отображение свечей и сделок
2. **StrategyForm** - форма параметров стратегии
3. **Statistics** - таблица результатов
4. **Controls** - управление интервалом и символом

### Libraries
- **lightweight-charts** - TradingView графики
- **Svelte** - реактивный UI фреймворк

## Data Models

### Strategy Parameters
```json
{
  "symbol": "BTC/USDT",
  "interval": "15m",
  "lookback_period": 100,
  "volume_threshold": 1.5,
  "take_profit": 0.02,
  "stop_loss": 0.01
}
```

### Backtest Response
```json
{
  "candles": [...],
  "trades": [...],
  "statistics": {
    "total_trades": 25,
    "win_rate": 0.68,
    "total_pnl": 0.15,
    "max_drawdown": 0.05
  }
}
```

## Technology Stack

### Backend
- **Python 3.10+**
- **FastAPI** - веб фреймворк
- **ccxt** - криптобиржевые API
- **pandas** - обработка данных
- **uvicorn** - ASGI сервер

### Frontend
- **Svelte** - UI фреймворк
- **lightweight-charts** - графики
- **Vite** - сборщик

### Development
- **Docker** - контейнеризация
- **Git** - версионный контроль
