// localStorage utilities for persisting app state
const STORAGE_KEYS = {
  SELECTED_SYMBOL: 'algotest_selected_symbol',
  SELECTED_INTERVAL: 'algotest_selected_interval', 
  LIQUIDITY_VISIBLE: 'algotest_liquidity_visible',
  LIQUIDITY_ENABLED: 'algotest_liquidity_enabled'
};

// Safe localStorage operations with fallbacks
export const storage = {
  // Get value from localStorage with fallback
  get(key, fallback = null) {
    if (typeof window === 'undefined') return fallback;
    
    try {
      const value = localStorage.getItem(key);
      if (value === null) return fallback;
      
      // Try to parse as JSON, fallback to string
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    } catch (error) {
      console.warn(`Failed to get ${key} from localStorage:`, error);
      return fallback;
    }
  },

  // Set value in localStorage
  set(key, value) {
    if (typeof window === 'undefined') return;
    
    try {
      const serialized = typeof value === 'string' ? value : JSON.stringify(value);
      localStorage.setItem(key, serialized);
    } catch (error) {
      console.warn(`Failed to set ${key} in localStorage:`, error);
    }
  },

  // Remove value from localStorage
  remove(key) {
    if (typeof window === 'undefined') return;
    
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn(`Failed to remove ${key} from localStorage:`, error);
    }
  },

  // Clear all app data from localStorage
  clearAll() {
    if (typeof window === 'undefined') return;
    
    Object.values(STORAGE_KEYS).forEach(key => {
      try {
        localStorage.removeItem(key);
      } catch (error) {
        console.warn(`Failed to remove ${key}:`, error);
      }
    });
  }
};

// Specific getters/setters for app state
export const appStorage = {
  // Symbol persistence
  getSelectedSymbol() {
    return storage.get(STORAGE_KEYS.SELECTED_SYMBOL, 'BTC/USDT');
  },
  
  setSelectedSymbol(symbol) {
    storage.set(STORAGE_KEYS.SELECTED_SYMBOL, symbol);
    console.log('💾 Saved selected symbol to localStorage:', symbol);
  },

  // Interval persistence  
  getSelectedInterval() {
    return storage.get(STORAGE_KEYS.SELECTED_INTERVAL, '15m');
  },
  
  setSelectedInterval(interval) {
    storage.set(STORAGE_KEYS.SELECTED_INTERVAL, interval);
    console.log('💾 Saved selected interval to localStorage:', interval);
  },

  // Liquidity visibility persistence
  getLiquidityVisible() {
    return storage.get(STORAGE_KEYS.LIQUIDITY_VISIBLE, true);
  },
  
  setLiquidityVisible(visible) {
    storage.set(STORAGE_KEYS.LIQUIDITY_VISIBLE, visible);
    console.log('💾 Saved liquidity visible to localStorage:', visible);
  },

  // Liquidity enabled persistence
  getLiquidityEnabled() {
    return storage.get(STORAGE_KEYS.LIQUIDITY_ENABLED, true);
  },
  
  setLiquidityEnabled(enabled) {
    storage.set(STORAGE_KEYS.LIQUIDITY_ENABLED, enabled);
    console.log('💾 Saved liquidity enabled to localStorage:', enabled);
  },

  // Load all persisted state
  loadPersistedState() {
    return {
      selectedSymbol: appStorage.getSelectedSymbol(),
      selectedInterval: appStorage.getSelectedInterval(),
      liquidityVisible: appStorage.getLiquidityVisible(),
      liquidityEnabled: appStorage.getLiquidityEnabled()
    };
  }
};

export { STORAGE_KEYS };
