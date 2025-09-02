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
    if (params.limit !== undefined) queryParams.append('limit', params.limit);

    return this.request(`/api/v1/backtest?${queryParams.toString()}`);
  }

  async runBacktestPost(params) {
    return this.request(`/api/v1/backtest`, {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async runBacktest(params) {
    // Use GET for simple cases, POST when strategy_params or timeframe present
    const hasComplex = params && (params.start_time || params.end_time || params.strategy_params);
    if (hasComplex) {
      return this.runBacktestPost(params);
    }
    return this.runBacktestGet(params);
  }

  // Strategy/engine info
  async getEngineInfo() {
    return this.request(`/api/v1/engine/info`);
  }

  async getStrategyInfo() {
    return this.request(`/api/v1/strategy/info`);
  }

  // Candles pagination for backfill
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
}

export const apiClient = new ApiClient();
