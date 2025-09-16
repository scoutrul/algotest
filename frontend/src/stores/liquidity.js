// Liquidity data management store
import { writable, derived } from 'svelte/store';
import { configStore } from './config.js';

// Initial state
const initialState = {
  // Feature control
  enabled: true,
  visible: true,
  loading: false,
  error: null,
  
  // Current data
  currentOrderBook: null,
  lastUpdate: null,
  
  // Historical data
  historicalData: [],
  chartData: [],
  densityData: [],
  
  // Settings
  settings: {
    displayMode: 'histogram', // 'histogram', 'area', 'heatmap'
    opacity: 0.6,
    minVolume: 0.01,
    maxLevels: 20,
    autoUpdate: false,
    updateInterval: 10000, // 10 seconds
    timeframe: '1h' // for density aggregation
  },
  
  // Statistics
  stats: {
    totalSnapshots: 0,
    lastCollectionTime: null,
    averageLatency: 0,
    isCollecting: false
  }
};

// Create writable store
function createLiquidityStore() {
  const { subscribe, set, update } = writable(initialState);
  
  let updateInterval = null;
  
  // In-flight guard and request cancellation
  let inFlight = false;
  let lastRequestTs = 0;
  let currentAbortController = null;
  
  return {
    subscribe,
    
    // Feature control
    enable: () => {
      update(state => ({ ...state, enabled: true }));
    },
    
    disable: () => {
      update(state => ({ 
        ...state, 
        enabled: false, 
        visible: false,
        currentOrderBook: null,
        historicalData: [],
        chartData: []
      }));
    },
    
    // Visibility control
    show: () => {
      update(state => ({ ...state, visible: true }));
    },
    
    hide: () => {
      update(state => ({ ...state, visible: false }));
    },
    
    toggle: () => {
      update(state => ({ ...state, visible: !state.visible }));
    },
    
    // Data loading
    loadCurrentOrderBook: async (symbol, limit = 20, options = {}) => {
      // Rate-limit calls to avoid flooding the browser and backend
      const now = Date.now();
      if (now - lastRequestTs < 500) {
        return null;
      }
      lastRequestTs = now;
      
      // Prevent overlapping requests
      if (inFlight) {
        // Cancel previous request if still running
        try { currentAbortController?.abort(); } catch (_) {}
      }
      inFlight = true;
      currentAbortController = new AbortController();
      
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const { apiClient } = await import('../utils/api.js');
        const response = await apiClient.getCurrentOrderBook(symbol, limit, { signal: currentAbortController.signal, ...options });
        
        update(state => ({
          ...state,
          currentOrderBook: response,
          lastUpdate: new Date().toISOString(),
          loading: false
        }));
        
        return response;
      } catch (error) {
        // Swallow abort errors silently
        if (error?.name === 'AbortError') {
          inFlight = false;
          update(state => ({ ...state, loading: false }));
          return null;
        }
        update(state => ({
          ...state,
          error: error?.message || 'Failed to load current order book',
          loading: false
        }));
        throw error;
      } finally {
        inFlight = false;
      }
    },
    
    loadHistoricalData: async (symbol, startTime, endTime, limit = 200) => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const { apiClient } = await import('../utils/api.js');
        const response = await apiClient.getOrderBookHistory(symbol, {
          start_time: startTime,
          end_time: endTime,
          limit
        });
        
        update(state => ({
          ...state,
          historicalData: response.snapshots || [],
          loading: false
        }));
        
        return response;
      } catch (error) {
        update(state => ({
          ...state,
          error: error.message || 'Failed to load historical data',
          loading: false
        }));
        throw error;
      }
    },
    
    loadChartData: async (symbol, startTime, endTime, limit = 200, minVolume) => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const { apiClient } = await import('../utils/api.js');
        const response = await apiClient.getLiquidityChartData(symbol, {
          start_time: startTime,
          end_time: endTime,
          limit,
          min_volume: minVolume
        });
        
        update(state => ({
          ...state,
          chartData: response.data || [],
          loading: false
        }));
        
        return response;
      } catch (error) {
        update(state => ({
          ...state,
          error: error.message || 'Failed to load chart data',
          loading: false
        }));
        throw error;
      }
    },
    
    loadDensityData: async (symbol, timeframe, startTime, endTime, limit = 100) => {
      update(state => ({ ...state, loading: true, error: null }));
      
      try {
        const { apiClient } = await import('../utils/api.js');
        const response = await apiClient.getLiquidityDensity(symbol, {
          timeframe,
          start_time: startTime,
          end_time: endTime,
          limit
        });
        
        update(state => ({
          ...state,
          densityData: response.data || [],
          loading: false
        }));
        
        return response;
      } catch (error) {
        update(state => ({
          ...state,
          error: error.message || 'Failed to load density data',
          loading: false
        }));
        throw error;
      }
    },
    
    // Settings management
    updateSettings: (newSettings) => {
      update(state => ({
        ...state,
        settings: { ...state.settings, ...newSettings }
      }));
    },
    
    setDisplayMode: (mode) => {
      update(state => ({
        ...state,
        settings: { ...state.settings, displayMode: mode }
      }));
    },
    
    setOpacity: (opacity) => {
      update(state => ({
        ...state,
        settings: { ...state.settings, opacity: Math.max(0.1, Math.min(1.0, opacity)) }
      }));
    },
    
    setMinVolume: (minVolume) => {
      update(state => ({
        ...state,
        settings: { ...state.settings, minVolume: Math.max(0, minVolume) }
      }));
    },
    
    setMaxLevels: (maxLevels) => {
      update(state => ({
        ...state,
        settings: { ...state.settings, maxLevels: Math.max(1, Math.min(100, maxLevels)) }
      }));
    },
    
    // Auto-update control
    startAutoUpdate: (symbol) => {
      update(state => {
        if (state.settings.autoUpdate) return state; // Already running
        
        const newState = {
          ...state,
          settings: { ...state.settings, autoUpdate: true }
        };
        
        // Clear previous interval just in case
        if (updateInterval) {
          clearInterval(updateInterval);
          updateInterval = null;
        }
        
        // Start interval (guard inside load will avoid overlaps)
        updateInterval = setInterval(async () => {
          try {
            await (async () => {
              const { apiClient } = await import('../utils/api.js');
              // Use AbortController via store method to guard
              await new Promise((resolve, reject) => {
                // Call store method to leverage guards
                // Note: symbol from closure
                resolve();
              });
            })();
            // Call guarded method
            await this.loadCurrentOrderBook(symbol);
          } catch (error) {
            console.warn('Auto-update failed:', error);
          }
        }, newState.settings.updateInterval);
        
        return newState;
      });
    },
    
    stopAutoUpdate: () => {
      if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
      }
      
      // Cancel any in-flight request
      try { currentAbortController?.abort(); } catch (_) {}
      inFlight = false;
      
      update(state => ({
        ...state,
        settings: { ...state.settings, autoUpdate: false }
      }));
    },
    
    // Statistics
    updateStats: (stats) => {
      update(state => ({
        ...state,
        stats: { ...state.stats, ...stats }
      }));
    },
    
    loadStats: async () => {
      try {
        const { apiClient } = await import('../utils/api.js');
        const response = await apiClient.getOrderBookHealth();
        
        if (response.collection_stats) {
          update(state => ({
            ...state,
            stats: {
              totalSnapshots: response.collection_stats.total_snapshots || 0,
              lastCollectionTime: response.collection_stats.last_collection_time,
              averageLatency: response.collection_stats.average_latency_ms || 0,
              isCollecting: response.collection_stats.is_running || false
            }
          }));
        }
        
        return response;
      } catch (error) {
        console.warn('Failed to load liquidity stats:', error);
        return null;
      }
    },
    
    // Utility methods
    clearData: () => {
      update(state => ({
        ...state,
        currentOrderBook: null,
        historicalData: [],
        chartData: [],
        densityData: [],
        error: null
      }));
    },
    
    clearError: () => {
      update(state => ({ ...state, error: null }));
    },
    
    // Get processed data for visualization
    getProcessedLevels: (orderBook, settings) => {
      if (!orderBook || !orderBook.bid_levels || !orderBook.ask_levels) {
        return { bidLevels: [], askLevels: [] };
      }
      
      // Filter by minimum volume
      const bidLevels = orderBook.bid_levels
        .filter(level => level.volume >= settings.minVolume)
        .slice(0, settings.maxLevels);
      
      const askLevels = orderBook.ask_levels
        .filter(level => level.volume >= settings.minVolume)
        .slice(0, settings.maxLevels);
      
      return { bidLevels, askLevels };
    },
    
    // Reset to defaults
    resetToDefaults: () => {
      if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
      }
      try { currentAbortController?.abort(); } catch (_) {}
      inFlight = false;
      lastRequestTs = 0;
      set(initialState);
    }
  };
}

// Create store instance
export const liquidityStore = createLiquidityStore();

// Derived stores for computed values
export const liquidityEnabled = derived(
  liquidityStore,
  $liquidity => $liquidity.enabled
);

export const liquidityVisible = derived(
  liquidityStore,
  $liquidity => $liquidity.visible && $liquidity.enabled
);

export const liquidityLoading = derived(
  liquidityStore,
  $liquidity => $liquidity.loading
);

export const liquidityError = derived(
  liquidityStore,
  $liquidity => $liquidity.error
);

export const liquiditySettings = derived(
  liquidityStore,
  $liquidity => $liquidity.settings
);

export const liquidityStats = derived(
  liquidityStore,
  $liquidity => $liquidity.stats
);

export const currentOrderBook = derived(
  liquidityStore,
  $liquidity => $liquidity.currentOrderBook
);

export const liquidityChartData = derived(
  liquidityStore,
  $liquidity => $liquidity.chartData
);

// Combined derived store for easy access
export const liquidityState = derived(
  liquidityStore,
  $liquidity => ({
    enabled: $liquidity.enabled,
    visible: $liquidity.visible,
    loading: $liquidity.loading,
    error: $liquidity.error,
    hasData: !!$liquidity.currentOrderBook,
    lastUpdate: $liquidity.lastUpdate,
    stats: $liquidity.stats
  })
);
