// API client for backend communication
const API_BASE_URL = 'http://localhost:8000/api/v1';

export class ApiClient {
  constructor(baseUrl = (import.meta.env && import.meta.env.VITE_API_BASE_URL) || (typeof window !== 'undefined' && window.API_BASE_URL) || 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async request(path, options = {}) {
    const url = `${this.baseUrl}${path}`;
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Request failed: ${res.status}`);
    }
    return res.json();
  }

  // Basic endpoints
  async getHealth() {
    return this.request(`/api/v1/health`);
  }

  async getSymbols() {
    return this.request(`/api/v1/symbols`);
  }

  async getIntervals() {
    return this.request(`/api/v1/intervals`);
  }

  async getConfig() {
    return this.request(`/api/v1/config`);
  }

  // Backtest
  async runBacktestGet(params) {
    const queryParams = new URLSearchParams();

    if (!params || !params.symbol) throw new Error('Symbol is required');
    if (!params.interval) throw new Error('Interval is required');

    queryParams.append('symbol', params.symbol);
    queryParams.append('interval', params.interval);

    if (params.lookback_period !== undefined) queryParams.append('lookback_period', params.lookback_period);
    if (params.volume_threshold !== undefined) queryParams.append('volume_threshold', params.volume_threshold);
    if (params.min_price_change !== undefined) queryParams.append('min_price_change', params.min_price_change);
    if (params.take_profit !== undefined) queryParams.append('take_profit', params.take_profit);
    if (params.stop_loss !== undefined) queryParams.append('stop_loss', params.stop_loss);
    if (params.max_trades !== undefined) queryParams.append('max_trades', params.max_trades);
    if (params.initial_capital !== undefined) queryParams.append('initial_capital', params.initial_capital);

    return this.request(`/api/v1/backtest?${queryParams}`);
  }

  async runBacktestPost(params) {
    return this.request(`/api/v1/backtest`, {
      method: 'POST',
      body: JSON.stringify(params)
    });
  }

  // Market Data
  async getMarketData(symbol, interval, limit = 1000, startTime = null, endTime = null) {
    const queryParams = new URLSearchParams();
    queryParams.append('symbol', symbol);
    queryParams.append('interval', interval);
    queryParams.append('limit', limit);
    if (startTime) queryParams.append('start_time', startTime);
    if (endTime) queryParams.append('end_time', endTime);

    return this.request(`/api/v1/market/data?${queryParams}`);
  }

  async syncMarketData(symbol, interval, limit = 1000) {
    const queryParams = new URLSearchParams();
    queryParams.append('symbol', symbol);
    queryParams.append('interval', interval);
    queryParams.append('limit', limit);

    return this.request(`/api/v1/data/sync?${queryParams}`, {
      method: 'POST'
    });
  }

  // Legacy method compatibility for Chart.svelte
  async getCandles({ symbol, interval, limit = 500, start_time = null, end_time = null }) {
    if (!symbol) throw new Error('symbol is required');
    if (!interval) throw new Error('interval is required');
    const params = new URLSearchParams({ symbol, interval, limit: String(limit) });
    if (end_time) {
      params.append('end_time', new Date(end_time).toISOString());
    } else if (start_time) {
      // Fallback for backward compatibility, but prefer end_time
      params.append('start_time', new Date(start_time).toISOString());
    }
    return this.request(`/api/v1/candles?${params.toString()}`);
  }

  // Strategy/engine info
  async getEngineInfo() {
    return this.request(`/api/v1/engine/info`);
  }

  async getStrategyInfo() {
    return this.request(`/api/v1/strategy/info`);
  }

  // Backtest compatibility
  async runBacktest(params) {
    // Use GET for simple cases, POST when strategy_params or timeframe present
    const hasComplex = params && (params.start_time || params.end_time || params.strategy_params);
    if (hasComplex) {
      return this.runBacktestPost(params);
    }
    return this.runBacktestGet(params);
  }

  // 🚀 Order Book / Liquidity API Methods
  
  /**
   * Get Order Book service health status
   */
  async getOrderBookHealth() {
    return this.request(`/api/v1/orderbook/health`);
  }

  /**
   * Test exchange connection for Order Book data
   */
  async testOrderBookConnection() {
    return this.request(`/api/v1/orderbook/test-connection`);
  }

  /**
   * Get current Order Book snapshot for a symbol
   */
  async getCurrentOrderBook(symbol, limit = 20) {
    const queryParams = new URLSearchParams();
    queryParams.append('limit', limit);
    // Convert BTC/USDT to BTCUSDT for API
    const apiSymbol = symbol.replace('/', '');
    return this.request(`/api/v1/orderbook/${encodeURIComponent(apiSymbol)}/current?${queryParams}`);
  }

  /**
   * Get historical Order Book snapshots
   */
  async getOrderBookHistory(symbol, options = {}) {
    const queryParams = new URLSearchParams();
    
    if (options.start_time) queryParams.append('start_time', options.start_time);
    if (options.end_time) queryParams.append('end_time', options.end_time);
    if (options.limit) queryParams.append('limit', options.limit);
    if (options.order) queryParams.append('order', options.order);

    return this.request(`/api/v1/orderbook/${encodeURIComponent(symbol)}/history?${queryParams}`);
  }

  /**
   * Get Order Book data formatted for Lightweight Charts
   */
  async getLiquidityChartData(symbol, options = {}) {
    const queryParams = new URLSearchParams();
    
    if (options.start_time) queryParams.append('start_time', options.start_time);
    if (options.end_time) queryParams.append('end_time', options.end_time);
    if (options.limit) queryParams.append('limit', options.limit);
    if (options.min_volume !== undefined) queryParams.append('min_volume', options.min_volume);

    return this.request(`/api/v1/orderbook/${encodeURIComponent(symbol)}/liquidity-chart?${queryParams}`);
  }

  /**
   * Get aggregated liquidity density data
   */
  async getLiquidityDensity(symbol, options = {}) {
    const queryParams = new URLSearchParams();
    
    if (options.timeframe) queryParams.append('timeframe', options.timeframe);
    if (options.start_time) queryParams.append('start_time', options.start_time);
    if (options.end_time) queryParams.append('end_time', options.end_time);
    if (options.limit) queryParams.append('limit', options.limit);

    return this.request(`/api/v1/orderbook/${encodeURIComponent(symbol)}/density?${queryParams}`);
  }

  /**
   * Get available symbols with Order Book data
   */
  async getOrderBookSymbols() {
    return this.request(`/api/v1/orderbook/symbols`);
  }

  /**
   * Trigger immediate Order Book collection
   */
  async triggerOrderBookCollection(symbols = null) {
    const queryParams = new URLSearchParams();
    if (symbols && symbols.length > 0) {
      symbols.forEach(symbol => queryParams.append('symbols', symbol));
    }

    return this.request(`/api/v1/orderbook/collect-now?${queryParams}`, {
      method: 'POST'
    });
  }

  // Helper methods for common use cases
  
  /**
   * Get Order Book data for the last N hours
   */
  async getOrderBookLastHours(symbol, hours = 24, limit = 200) {
    const endTime = Date.now();
    const startTime = endTime - (hours * 60 * 60 * 1000);
    
    return this.getLiquidityChartData(symbol, {
      start_time: startTime,
      end_time: endTime,
      limit
    });
  }

  /**
   * Get current liquidity state with processed levels
   */
  async getCurrentLiquidityState(symbol, minVolume = 0.01, maxLevels = 20) {
    const orderBook = await this.getCurrentOrderBook(symbol, maxLevels * 2);
    
    if (!orderBook || !orderBook.bid_levels || !orderBook.ask_levels) {
      return null;
    }

    // Process and filter levels
    const bidLevels = orderBook.bid_levels
      .filter(level => level.volume >= minVolume)
      .slice(0, maxLevels);
    
    const askLevels = orderBook.ask_levels
      .filter(level => level.volume >= minVolume)
      .slice(0, maxLevels);

    return {
      ...orderBook,
      processed_bid_levels: bidLevels,
      processed_ask_levels: askLevels,
      filtered_levels_count: {
        bid: bidLevels.length,
        ask: askLevels.length
      }
    };
  }

  /**
   * Check if liquidity feature is available
   */
  async isLiquidityFeatureAvailable() {
    try {
      const health = await this.getOrderBookHealth();
      return health.feature_enabled === true;
    } catch (error) {
      console.warn('Liquidity feature availability check failed:', error);
      return false;
    }
  }
}

// Export default client instance
export const apiClient = new ApiClient();
