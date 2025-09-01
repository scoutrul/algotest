// Configuration state management store
import { writable } from 'svelte/store';
import { apiClient } from '../utils/api.js';

// Initial state
const initialState = {
  selectedSymbol: 'BTC/USDT',
  selectedInterval: '15m',
  strategyParams: {
    lookback_period: 20,
    volume_threshold: 1.5,
    min_price_change: 0.005,
    take_profit: 0.02,
    stop_loss: 0.01,
    max_trades: 100,
    initial_capital: 10000
  },
  availableSymbols: [],
  availableIntervals: [],
  loading: false,
  error: null
};

// Create writable store
function createConfigStore() {
  const { subscribe, set, update } = writable(initialState);

  return {
    subscribe,
    
    // Load configuration from API
    loadConfig: async () => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const config = await apiClient.getConfig();
        
        update(state => ({
          ...state,
          strategyParams: {
            ...state.strategyParams,
            ...config.default_strategy_params
          },
          loading: false
        }));
        
        return config;
      } catch (error) {
        update(state => ({
          ...state,
          error: error.message || 'Failed to load configuration',
          loading: false
        }));
        throw error;
      }
    },
    
    // Load available symbols
    loadSymbols: async () => {
      try {
        const response = await apiClient.getSymbols();
        
        update(state => ({
          ...state,
          availableSymbols: response.symbols || []
        }));
        
        return response.symbols;
      } catch (error) {
        update(state => ({
          ...state,
          error: error.message || 'Failed to load symbols'
        }));
        throw error;
      }
    },
    
    // Load available intervals
    loadIntervals: async () => {
      try {
        const response = await apiClient.getIntervals();
        
        update(state => ({
          ...state,
          availableIntervals: response.intervals || []
        }));
        
        return response.intervals;
      } catch (error) {
        update(state => ({
          ...state,
          error: error.message || 'Failed to load intervals'
        }));
        throw error;
      }
    },
    
    // Update selected symbol
    setSelectedSymbol: (symbol) => {
      update(state => ({ ...state, selectedSymbol: symbol }));
    },
    
    // Update selected interval
    setSelectedInterval: (interval) => {
      update(state => ({ ...state, selectedInterval: interval }));
    },
    
    // Update strategy parameters
    updateStrategyParams: (params) => {
      update(state => ({
        ...state,
        strategyParams: { ...state.strategyParams, ...params }
      }));
    },
    
    // Reset to defaults
    resetToDefaults: () => {
      update(state => ({
        ...state,
        strategyParams: initialState.strategyParams
      }));
    },
    
    // Validate parameters
    validateParams: (params) => {
      const errors = [];
      
      if (params.lookback_period < 5 || params.lookback_period > 100) {
        errors.push('Lookback period must be between 5 and 100');
      }
      
      if (params.volume_threshold <= 1.0 || params.volume_threshold > 5.0) {
        errors.push('Volume threshold must be between 1.0 and 5.0');
      }
      
      if (params.take_profit <= 0 || params.take_profit > 0.5) {
        errors.push('Take profit must be between 0 and 0.5 (50%)');
      }
      
      if (params.stop_loss <= 0 || params.stop_loss > 0.5) {
        errors.push('Stop loss must be between 0 and 0.5 (50%)');
      }
      
      if (params.stop_loss >= params.take_profit) {
        errors.push('Stop loss must be smaller than take profit');
      }
      
      if (params.initial_capital <= 0) {
        errors.push('Initial capital must be greater than 0');
      }
      
      return {
        valid: errors.length === 0,
        errors
      };
    }
  };
}

// Export store instance
export const configStore = createConfigStore();
