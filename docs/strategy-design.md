# Strategy Design - MVP Trading Strategy

## Strategy Overview
Простая стратегия на основе анализа объема и ценового движения для входа в позицию с фиксированными TP/SL.

## Core Logic

### Signal Detection
1. **Volume Spike**: Объем текущей свечи > средний объем за N периодов * threshold
2. **Price Movement**: Цена движется в направлении объема
3. **Entry Condition**: Оба условия выполняются одновременно

### Entry Logic
```python
def detect_entry_signal(candles, current_idx, params):
    """
    Detect entry signal based on volume and price movement
    
    Args:
        candles: DataFrame with OHLCV data
        current_idx: Current candle index
        params: Strategy parameters
    
    Returns:
        dict: Signal info (direction, confidence, timestamp)
    """
    current = candles.iloc[current_idx]
    lookback = candles.iloc[current_idx-params['lookback_period']:current_idx]
    
    # Volume analysis
    avg_volume = lookback['volume'].mean()
    volume_spike = current['volume'] > avg_volume * params['volume_threshold']
    
    # Price movement analysis
    price_change = (current['close'] - current['open']) / current['open']
    significant_move = abs(price_change) > params['min_price_change']
    
    # Signal direction
    if volume_spike and significant_move:
        direction = 'long' if price_change > 0 else 'short'
        return {
            'signal': True,
            'direction': direction,
            'confidence': min(abs(price_change) * 10, 1.0),
            'timestamp': current['timestamp'],
            'price': current['close']
        }
    
    return {'signal': False}
```

### Risk Management

#### Take Profit (TP)
```python
def calculate_take_profit(entry_price, direction, tp_percentage):
    """
    Calculate take profit price
    
    Args:
        entry_price: Entry price
        direction: 'long' or 'short'
        tp_percentage: TP percentage (e.g., 0.02 for 2%)
    
    Returns:
        float: Take profit price
    """
    if direction == 'long':
        return entry_price * (1 + tp_percentage)
    else:
        return entry_price * (1 - tp_percentage)
```

#### Stop Loss (SL)
```python
def calculate_stop_loss(entry_price, direction, sl_percentage):
    """
    Calculate stop loss price
    
    Args:
        entry_price: Entry price
        direction: 'long' or 'short'
        sl_percentage: SL percentage (e.g., 0.01 for 1%)
    
    Returns:
        float: Stop loss price
    """
    if direction == 'long':
        return entry_price * (1 - sl_percentage)
    else:
        return entry_price * (1 + sl_percentage)
```

### Exit Logic
```python
def check_exit_conditions(trade, current_candle):
    """
    Check if trade should be closed
    
    Args:
        trade: Active trade object
        current_candle: Current market data
    
    Returns:
        dict: Exit info (should_exit, reason, price)
    """
    current_price = current_candle['close']
    
    # Check TP
    if trade['direction'] == 'long' and current_price >= trade['take_profit']:
        return {
            'should_exit': True,
            'reason': 'take_profit',
            'price': trade['take_profit']
        }
    
    if trade['direction'] == 'short' and current_price <= trade['take_profit']:
        return {
            'should_exit': True,
            'reason': 'take_profit',
            'price': trade['take_profit']
        }
    
    # Check SL
    if trade['direction'] == 'long' and current_price <= trade['stop_loss']:
        return {
            'should_exit': True,
            'reason': 'stop_loss',
            'price': trade['stop_loss']
        }
    
    if trade['direction'] == 'short' and current_price >= trade['stop_loss']:
        return {
            'should_exit': True,
            'reason': 'stop_loss',
            'price': trade['stop_loss']
        }
    
    return {'should_exit': False}
```

## Strategy Parameters

### Default Configuration
```python
DEFAULT_PARAMS = {
    'symbol': 'BTC/USDT',
    'interval': '15m',
    'lookback_period': 20,      # Candles for volume average
    'volume_threshold': 1.5,    # Volume spike multiplier
    'min_price_change': 0.005,  # Minimum price change (0.5%)
    'take_profit': 0.02,        # Take profit (2%)
    'stop_loss': 0.01,          # Stop loss (1%)
    'max_trades': 100,          # Maximum trades per backtest
    'initial_capital': 10000    # Starting capital
}
```

### Parameter Validation
```python
def validate_strategy_params(params):
    """
    Validate strategy parameters
    
    Args:
        params: Strategy parameters dict
    
    Returns:
        tuple: (is_valid, errors)
    """
    errors = []
    
    # Required parameters
    required = ['symbol', 'interval', 'lookback_period', 'volume_threshold']
    for param in required:
        if param not in params:
            errors.append(f"Missing required parameter: {param}")
    
    # Numeric validations
    if params.get('volume_threshold', 0) <= 1.0:
        errors.append("Volume threshold must be > 1.0")
    
    if params.get('take_profit', 0) <= 0:
        errors.append("Take profit must be > 0")
    
    if params.get('stop_loss', 0) <= 0:
        errors.append("Stop loss must be > 0")
    
    if params.get('lookback_period', 0) < 5:
        errors.append("Lookback period must be >= 5")
    
    return len(errors) == 0, errors
```

## Backtest Execution Flow

### Main Backtest Loop
```python
def run_backtest(candles, params):
    """
    Execute backtest with given parameters
    
    Args:
        candles: Historical OHLCV data
        params: Strategy parameters
    
    Returns:
        dict: Backtest results
    """
    trades = []
    active_trades = []
    capital = params['initial_capital']
    
    # Start from lookback_period to have enough history
    for i in range(params['lookback_period'], len(candles)):
        current_candle = candles.iloc[i]
        
        # Check exit conditions for active trades
        for trade in active_trades[:]:  # Copy to avoid modification during iteration
            exit_info = check_exit_conditions(trade, current_candle)
            if exit_info['should_exit']:
                # Close trade
                trade['exit_time'] = current_candle['timestamp']
                trade['exit_price'] = exit_info['price']
                trade['pnl'] = calculate_pnl(trade)
                trades.append(trade)
                active_trades.remove(trade)
                capital += trade['pnl']
        
        # Check for new entry signals (if no active trades)
        if len(active_trades) == 0 and len(trades) < params['max_trades']:
            signal = detect_entry_signal(candles, i, params)
            if signal['signal']:
                # Open new trade
                trade = create_trade(signal, current_candle, params)
                active_trades.append(trade)
                capital -= trade['size']  # Reserve capital
    
    # Close any remaining active trades
    for trade in active_trades:
        trade['exit_time'] = candles.iloc[-1]['timestamp']
        trade['exit_price'] = candles.iloc[-1]['close']
        trade['pnl'] = calculate_pnl(trade)
        trades.append(trade)
    
    return {
        'trades': trades,
        'statistics': calculate_statistics(trades, params['initial_capital']),
        'final_capital': capital
    }
```

## Performance Metrics

### Key Statistics
```python
def calculate_statistics(trades, initial_capital):
    """
    Calculate backtest performance statistics
    
    Args:
        trades: List of completed trades
        initial_capital: Starting capital
    
    Returns:
        dict: Performance statistics
    """
    if not trades:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0
        }
    
    total_trades = len(trades)
    winning_trades = len([t for t in trades if t['pnl'] > 0])
    win_rate = winning_trades / total_trades
    
    total_pnl = sum(t['pnl'] for t in trades)
    returns = [t['pnl'] / initial_capital for t in trades]
    
    # Calculate max drawdown
    cumulative_returns = []
    cumulative = 0
    for ret in returns:
        cumulative += ret
        cumulative_returns.append(cumulative)
    
    max_drawdown = 0
    peak = 0
    for cum_ret in cumulative_returns:
        if cum_ret > peak:
            peak = cum_ret
        drawdown = peak - cum_ret
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # Sharpe ratio (simplified)
    if len(returns) > 1:
        mean_return = sum(returns) / len(returns)
        std_return = (sum((r - mean_return) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe_ratio = mean_return / std_return if std_return > 0 else 0
    else:
        sharpe_ratio = 0
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': total_trades - winning_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'total_return': total_pnl / initial_capital,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'avg_trade_duration': calculate_avg_duration(trades)
    }
```

## Creative Phase Requirements

### Algorithm Optimization
- **Parameter Tuning**: Genetic algorithm for optimal parameters
- **Multi-timeframe Analysis**: Combining different intervals
- **Risk Management**: Dynamic position sizing

### Advanced Features
- **Market Regime Detection**: Bull/bear market adaptation
- **Correlation Analysis**: Multi-asset strategies
- **Machine Learning**: Signal prediction models
