// Backtest state management store
import { writable } from 'svelte/store';

// Initial state
const initialState = {
  candles: [],
  trades: [],
  statistics: null,
  parameters: null,
  executionTime: 0,
  success: false,
  error: null,
  loading: false
};

// Create writable store
function createBacktestStore() {
  const { subscribe, set, update } = writable(initialState);

  return {
    subscribe,
    
    // Reset store to initial state
    reset: () => set(initialState),
    
    // Set loading state
    setLoading: (loading) => update(state => ({ ...state, loading })),
    
    // Set error state
    setError: (error) => update(state => ({ ...state, error, loading: false })),
    
    // Run backtest
    runBacktest: async (params) => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        // Dynamic import to avoid circular dependencies
        const { apiClient } = await import('../utils/api.js');
        const result = await apiClient.runBacktest(params);
        
        update(state => ({
          ...state,
          candles: result.candles || [],
          trades: result.trades || [],
          statistics: result.statistics || null,
          parameters: result.parameters || null,
          executionTime: result.execution_time || 0,
          success: result.success || false,
          error: result.error_message || null,
          loading: false
        }));
        
        return result;
      } catch (error) {
        update(state => ({
          ...state,
          error: error.message || 'Backtest failed',
          loading: false
        }));
        throw error;
      }
    },
    
    // Update specific data
    updateCandles: (candles) => update(state => ({ ...state, candles })),
    updateTrades: (trades) => update(state => ({ ...state, trades })),
    updateStatistics: (statistics) => update(state => ({ ...state, statistics })),
    
    // Get recent trades for display
    getRecentTrades: (limit = 10) => {
      let trades = [];
      subscribe(state => {
        trades = (state.trades || []).slice(-limit);
      })();
      return trades;
    }
  };
}

// Export store instance
export const backtestStore = createBacktestStore();
