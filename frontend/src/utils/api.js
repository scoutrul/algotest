// API client for backend communication
const API_BASE_URL = 'http://localhost:8000/api/v1';

class ApiClient {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  // Generic request method
  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }
      
      return await response.json();
    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error('Unable to connect to backend server. Please ensure the backend is running.');
      }
      throw error;
    }
  }

  // Health check
  async getHealth() {
    return this.request('/health');
  }

  // Get available symbols
  async getSymbols() {
    return this.request('/symbols');
  }

  // Get available intervals
  async getIntervals() {
    return this.request('/intervals');
  }

  // Get configuration
  async getConfig() {
    return this.request('/config');
  }

  // Run backtest (GET)
  async runBacktestGet(params) {
    const queryParams = new URLSearchParams();
    
    // Validate required parameters
    if (!params.symbol || params.symbol === 'undefined') {
      throw new Error('Symbol is required');
    }
    if (!params.interval || params.interval === 'undefined') {
      throw new Error('Interval is required');
    }
    
    // Add required parameters
    queryParams.append('symbol', params.symbol);
    queryParams.append('interval', params.interval);
    
    // Add optional strategy parameters
    if (params.lookback_period !== undefined) {
      queryParams.append('lookback_period', params.lookback_period);
    }
    if (params.volume_threshold !== undefined) {
      queryParams.append('volume_threshold', params.volume_threshold);
    }
    if (params.min_price_change !== undefined) {
      queryParams.append('min_price_change', params.min_price_change);
    }
    if (params.take_profit !== undefined) {
      queryParams.append('take_profit', params.take_profit);
    }
    if (params.stop_loss !== undefined) {
      queryParams.append('stop_loss', params.stop_loss);
    }
    if (params.max_trades !== undefined) {
      queryParams.append('max_trades', params.max_trades);
    }
    if (params.initial_capital !== undefined) {
      queryParams.append('initial_capital', params.initial_capital);
    }
    if (params.limit !== undefined) {
      queryParams.append('limit', params.limit);
    }
    
    return this.request(`/backtest?${queryParams.toString()}`);
  }

  // Run backtest (POST)
  async runBacktestPost(params) {
    return this.request('/backtest', {
      method: 'POST',
      body: JSON.stringify(params)
    });
  }

  // Run backtest (auto-detect method)
  async runBacktest(params) {
    // Use GET method for simple parameters, POST for complex ones
    const hasComplexParams = params.start_time || params.end_time || Object.keys(params.strategy_params || {}).length > 5;
    
    if (hasComplexParams) {
      return this.runBacktestPost(params);
    } else {
      // Convert to GET format
      const getParams = {
        symbol: params.symbol,
        interval: params.interval,
        ...params.strategy_params,
        limit: params.limit
      };
      return this.runBacktestGet(getParams);
    }
  }

  // Get engine info
  async getEngineInfo() {
    return this.request('/engine/info');
  }

  // Get strategy info
  async getStrategyInfo() {
    return this.request('/strategy/info');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
