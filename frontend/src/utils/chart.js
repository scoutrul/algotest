// Chart utility functions
export const chartUtils = {
  // Format timestamp for chart display
  formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
  },

  // Format price for display
  formatPrice(price, decimals = 2) {
    return parseFloat(price).toFixed(decimals);
  },

  // Format percentage
  formatPercentage(value, decimals = 2) {
    return `${(value * 100).toFixed(decimals)}%`;
  },

  // Calculate color based on value
  getValueColor(value, neutral = 0) {
    if (value > neutral) return '#26a69a'; // Green
    if (value < neutral) return '#ef5350'; // Red
    return '#95a5a6'; // Gray
  },

  // Generate trade marker
  createTradeMarker(trade, type = 'entry') {
    const time = type === 'entry' 
      ? Math.floor(new Date(trade.entry_time).getTime() / 1000)
      : Math.floor(new Date(trade.exit_time).getTime() / 1000);
    
    const price = type === 'entry' ? trade.entry_price : trade.exit_price;
    
    return {
      time,
      position: trade.direction === 'long' ? 'belowBar' : 'aboveBar',
      color: trade.direction === 'long' ? '#26a69a' : '#ef5350',
      shape: type === 'entry' 
        ? (trade.direction === 'long' ? 'arrowUp' : 'arrowDown')
        : 'circle',
      text: `${type.toUpperCase()} @ ${this.formatPrice(price)}`,
      size: 1,
    };
  },

  // Calculate chart dimensions
  calculateDimensions(container) {
    const rect = container.getBoundingClientRect();
    return {
      width: rect.width,
      height: Math.max(400, rect.height)
    };
  },

  // Validate chart data
  validateCandleData(candles) {
    if (!Array.isArray(candles)) return false;
    
    return candles.every(candle => 
      candle.timestamp &&
      typeof candle.open === 'number' &&
      typeof candle.high === 'number' &&
      typeof candle.low === 'number' &&
      typeof candle.close === 'number' &&
      typeof candle.volume === 'number'
    );
  },

  // Convert candles to chart format
  convertCandlesToChartFormat(candles) {
    return candles.map(candle => ({
      time: Math.floor(new Date(candle.timestamp).getTime() / 1000),
      open: parseFloat(candle.open),
      high: parseFloat(candle.high),
      low: parseFloat(candle.low),
      close: parseFloat(candle.close),
    }));
  },

  // Calculate price range for zoom
  calculatePriceRange(candles) {
    if (!candles.length) return { min: 0, max: 100 };
    
    const prices = candles.flatMap(c => [c.low, c.high]);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const padding = (max - min) * 0.1; // 10% padding
    
    return {
      min: min - padding,
      max: max + padding
    };
  },

  // Generate chart colors based on theme
  getChartColors(theme = 'light') {
    if (theme === 'dark') {
      return {
        background: '#1e1e1e',
        textColor: '#ffffff',
        gridColor: '#2d2d2d',
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderUpColor: '#26a69a',
        borderDownColor: '#ef5350',
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
      };
    }
    
    return {
      background: '#ffffff',
      textColor: '#333333',
      gridColor: '#f0f0f0',
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    };
  }
};
