# Project Brief

## Project Overview
- **Type**: MVP BackTest Trading Bot
- **Location**: /Users/tonsky/Desktop/projects/algotest
- **Status**: Planning Phase
- **Architecture**: Two-service monorepo (Backend + Frontend)

## Core Requirements
- **Backend**: Python 3.10+ with FastAPI, ccxt, pandas
- **Frontend**: Svelte + lightweight-charts
- **Data Source**: Binance API via ccxt
- **Strategy**: Simple signal-based trading with TP/SL

## MVP Use Case
1. User selects coin (BTC/USDT), interval (15m), strategy params
2. Backend fetches data → runs strategy → returns trades
3. Frontend renders candles + trades on chart + statistics table

## Key Features
- Historical data fetching from Binance
- Backtesting engine with configurable parameters
- Interactive chart visualization
- Trade statistics and performance metrics

## Context
- Пользователь предпочитает ответы на русском языке
- Проект начинается с нуля в пустой папке
- Требуется структурированный подход к разработке
