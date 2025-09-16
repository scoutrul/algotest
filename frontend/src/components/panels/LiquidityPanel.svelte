<script>
  import { onMount, onDestroy } from 'svelte';
  import { liquidityStore } from '../../stores/liquidity.js';
  import { apiClient } from '../../utils/api.js';

  // Props
  export let symbol = 'BTCUSDT';

  // Local state
  let enabled = false;
  let visible = false;
  let loading = false;
  let error = null;
  let currentOrderBook = null;
  let stats = {};
  let settings = {};
  let lastUpdate = null;

  // Processed levels for display
  let processedBidLevels = [];
  let processedAskLevels = [];

  // Auto-update interval
  let autoUpdateInterval = null;

  // Subscribe to liquidity store
  const unsubscribe = liquidityStore.subscribe(state => {
    enabled = state.enabled;
    visible = state.visible;
    loading = state.loading;
    error = state.error;
    currentOrderBook = state.currentOrderBook;
    stats = state.stats;
    settings = state.settings;
    lastUpdate = state.lastUpdate;

    // Process order book levels when data changes
    if (currentOrderBook && settings) {
      const { bidLevels, askLevels } = processOrderBookLevels(currentOrderBook, settings);
      processedBidLevels = bidLevels;
      processedAskLevels = askLevels;
    }
  });

  onMount(async () => {
    // Load initial stats
    await loadStats();
    
    // Enable feature by default
    if (!enabled) {
      liquidityStore.enable();
    }
  });

  onDestroy(() => {
    if (unsubscribe) unsubscribe();
    stopAutoUpdate();
  });

  // Process order book levels based on settings
  function processOrderBookLevels(orderBook, settings) {
    if (!orderBook || !orderBook.bid_levels || !orderBook.ask_levels) {
      return { bidLevels: [], askLevels: [] };
    }

    const bidLevels = orderBook.bid_levels
      .filter(level => level.volume >= settings.minVolume)
      .slice(0, settings.maxLevels);

    const askLevels = orderBook.ask_levels
      .filter(level => level.volume >= settings.minVolume)
      .slice(0, settings.maxLevels);

    return { bidLevels, askLevels };
  }

  // Load collection statistics
  async function loadStats() {
    try {
      const health = await apiClient.getOrderBookHealth();
      if (health.collection_stats) {
        liquidityStore.updateStats({
          totalSnapshots: health.collection_stats.total_snapshots || 0,
          lastCollectionTime: health.collection_stats.last_collection_time,
          averageLatency: health.collection_stats.average_latency_ms || 0,
          isCollecting: health.collection_stats.is_running || false
        });
      }
    } catch (err) {
      console.warn('Failed to load liquidity stats:', err);
    }
  }

  // Load current order book
  async function loadCurrentOrderBook() {
    await liquidityStore.loadCurrentOrderBook(symbol);
  }

  // Start auto-update
  function startAutoUpdate() {
    if (autoUpdateInterval) return;
    
    autoUpdateInterval = setInterval(async () => {
      await loadCurrentOrderBook();
      await loadStats();
    }, settings.updateInterval);
    
    liquidityStore.updateSettings({ autoUpdate: true });
  }

  // Stop auto-update
  function stopAutoUpdate() {
    if (autoUpdateInterval) {
      clearInterval(autoUpdateInterval);
      autoUpdateInterval = null;
    }
    liquidityStore.updateSettings({ autoUpdate: false });
  }

  // Event handlers
  function handleToggleFeature() {
    if (enabled) {
      liquidityStore.disable();
      stopAutoUpdate();
    } else {
      liquidityStore.enable();
      loadCurrentOrderBook();
    }
  }

  function handleToggleVisibility() {
    liquidityStore.toggle();
    if (!visible && enabled) {
      loadCurrentOrderBook();
    }
  }

  function handleOpacityChange(event) {
    liquidityStore.setOpacity(parseFloat(event.target.value));
  }

  function handleMinVolumeChange(event) {
    liquidityStore.setMinVolume(parseFloat(event.target.value));
  }

  function handleMaxLevelsChange(event) {
    liquidityStore.setMaxLevels(parseInt(event.target.value, 10));
  }

  function handleAutoUpdateToggle(event) {
    if (event.target.checked) {
      startAutoUpdate();
    } else {
      stopAutoUpdate();
    }
  }

  function handleUpdateIntervalChange(event) {
    const newInterval = parseInt(event.target.value, 10);
    liquidityStore.updateSettings({ updateInterval: newInterval });
    
    // Restart auto-update with new interval if it's running
    if (settings.autoUpdate) {
      stopAutoUpdate();
      setTimeout(startAutoUpdate, 100);
    }
  }

  function handleTimeframeChange(event) {
    liquidityStore.updateSettings({ timeframe: event.target.value });
  }

  function handleRefresh() {
    loadCurrentOrderBook();
    loadStats();
  }

  function handleTriggerCollection() {
    apiClient.triggerOrderBookCollection([symbol])
      .then(() => {
        console.log('Collection triggered successfully');
        setTimeout(() => loadCurrentOrderBook(), 2000);
      })
      .catch(err => console.error('Failed to trigger collection:', err));
  }

  // Reactive statements
  $: if (symbol && enabled && visible) {
    loadCurrentOrderBook();
  }

  // Format numbers for display
  function formatNumber(num, decimals = 4) {
    if (num === null || num === undefined) return 'N/A';
    return typeof num === 'number' ? num.toFixed(decimals) : num.toString();
  }

  function formatVolume(volume) {
    if (volume >= 1000) {
      return (volume / 1000).toFixed(2) + 'K';
    }
    return volume.toFixed(4);
  }

  function formatTime(timestamp) {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleTimeString();
  }
</script>

<div class="liquidity-panel">
  <div class="panel-header">
    <h3 class="panel-title">
      <span class="icon">💧</span>
      Liquidity Analysis
    </h3>
    <label class="feature-toggle">
      <input 
        type="checkbox" 
        checked={enabled} 
        on:change={handleToggleFeature}
        class="toggle-input"
      >
      <span class="toggle-slider"></span>
      <span class="toggle-label">Enabled</span>
    </label>
  </div>

  {#if enabled}
    <div class="panel-content">
      <!-- Visibility Control -->
      <div class="control-section">
        <label class="control-item">
          <input 
            type="checkbox" 
            checked={visible} 
            on:change={handleToggleVisibility}
            class="checkbox"
          >
          <span class="control-label">Show on Chart</span>
        </label>
      </div>

      <!-- Settings Section -->
      <div class="settings-section">
        <h4 class="section-title">Display Settings</h4>
        
        <div class="setting-item">
          <label for="opacity" class="setting-label">
            Opacity: <span class="setting-value">{(settings.opacity * 100).toFixed(0)}%</span>
          </label>
          <input
            type="range"
            id="opacity"
            min="0.1"
            max="1.0"
            step="0.05"
            value={settings.opacity}
            on:input={handleOpacityChange}
            class="range-input"
          />
        </div>

        <div class="setting-item">
          <label for="minVolume" class="setting-label">Min Volume:</label>
          <input
            type="number"
            id="minVolume"
            min="0"
            step="0.01"
            value={settings.minVolume}
            on:change={handleMinVolumeChange}
            class="number-input"
          />
        </div>

        <div class="setting-item">
          <label for="maxLevels" class="setting-label">Max Levels:</label>
          <input
            type="number"
            id="maxLevels"
            min="1"
            max="100"
            step="1"
            value={settings.maxLevels}
            on:change={handleMaxLevelsChange}
            class="number-input"
          />
        </div>

        <div class="setting-item">
          <label for="timeframe" class="setting-label">Timeframe:</label>
          <select
            id="timeframe"
            value={settings.timeframe}
            on:change={handleTimeframeChange}
            class="select-input"
          >
            <option value="5m">5 Minutes</option>
            <option value="15m">15 Minutes</option>
            <option value="1h">1 Hour</option>
            <option value="4h">4 Hours</option>
            <option value="1d">1 Day</option>
          </select>
        </div>
      </div>

      <!-- Auto-update Section -->
      <div class="auto-update-section">
        <h4 class="section-title">Auto-update</h4>
        
        <label class="control-item">
          <input 
            type="checkbox" 
            checked={settings.autoUpdate} 
            on:change={handleAutoUpdateToggle}
            class="checkbox"
          >
          <span class="control-label">Auto-update Current OB</span>
        </label>

        {#if settings.autoUpdate}
          <div class="setting-item">
            <label for="updateInterval" class="setting-label">Interval (ms):</label>
            <input
              type="number"
              id="updateInterval"
              min="1000"
              step="1000"
              value={settings.updateInterval}
              on:change={handleUpdateIntervalChange}
              class="number-input"
            />
          </div>
        {/if}
      </div>

      <!-- Current Order Book Section -->
      {#if loading}
        <div class="loading-section">
          <div class="loading-spinner"></div>
          <span>Loading liquidity data...</span>
        </div>
      {:else if error}
        <div class="error-section">
          <span class="error-icon">⚠️</span>
          <span class="error-text">{error}</span>
          <button class="retry-btn" on:click={handleRefresh}>Retry</button>
        </div>
      {:else if currentOrderBook}
        <div class="orderbook-section">
          <div class="section-header">
            <h4 class="section-title">Current Order Book ({symbol})</h4>
            <button class="refresh-btn" on:click={handleRefresh} title="Refresh data">
              ↻
            </button>
          </div>

          <div class="orderbook-info">
            <div class="info-item">
              <span class="info-label">Last Update:</span>
              <span class="info-value">{formatTime(lastUpdate)}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Best Bid:</span>
              <span class="info-value bid">{formatNumber(currentOrderBook.best_bid, 2)}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Best Ask:</span>
              <span class="info-value ask">{formatNumber(currentOrderBook.best_ask, 2)}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Spread:</span>
              <span class="info-value">{formatNumber(currentOrderBook.spread, 6)} ({formatNumber(currentOrderBook.spread_percentage, 4)}%)</span>
            </div>
            <div class="info-item">
              <span class="info-label">Total Bid Vol:</span>
              <span class="info-value">{formatVolume(currentOrderBook.total_bid_volume)}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Total Ask Vol:</span>
              <span class="info-value">{formatVolume(currentOrderBook.total_ask_volume)}</span>
            </div>
          </div>

          <!-- Order Book Levels -->
          <div class="levels-container">
            <div class="levels-column">
              <h5 class="levels-title bid">Bids ({processedBidLevels.length})</h5>
              <div class="levels-list">
                {#each processedBidLevels as level (level.price)}
                  <div class="level-item bid">
                    <span class="level-price">{formatNumber(level.price, 2)}</span>
                    <span class="level-volume">{formatVolume(level.volume)}</span>
                  </div>
                {/each}
              </div>
            </div>
            
            <div class="levels-column">
              <h5 class="levels-title ask">Asks ({processedAskLevels.length})</h5>
              <div class="levels-list">
                {#each processedAskLevels as level (level.price)}
                  <div class="level-item ask">
                    <span class="level-price">{formatNumber(level.price, 2)}</span>
                    <span class="level-volume">{formatVolume(level.volume)}</span>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </div>
      {/if}

      <!-- Statistics Section -->
      <div class="stats-section">
        <div class="section-header">
          <h4 class="section-title">Collection Statistics</h4>
          <button class="trigger-btn" on:click={handleTriggerCollection} title="Trigger collection">
            🔄
          </button>
        </div>

        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-label">Status:</span>
            <span class="stat-value {stats.isCollecting ? 'collecting' : 'stopped'}">
              {stats.isCollecting ? 'Running' : 'Stopped'}
            </span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Total Snapshots:</span>
            <span class="stat-value">{formatNumber(stats.totalSnapshots, 0)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Last Collection:</span>
            <span class="stat-value">{formatTime(stats.lastCollectionTime)}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Avg Latency:</span>
            <span class="stat-value">{formatNumber(stats.averageLatency, 2)} ms</span>
          </div>
        </div>
      </div>
    </div>
  {:else}
    <div class="disabled-message">
      <span class="disabled-icon">⏸️</span>
      <p>Liquidity analysis feature is currently disabled.</p>
      <p class="disabled-hint">Enable it to start collecting and visualizing order book data.</p>
    </div>
  {/if}
</div>

<style>
  .liquidity-panel {
    background: linear-gradient(135deg, rgba(30, 30, 30, 0.95), rgba(40, 40, 40, 0.95));
    border-radius: 12px;
    border: 1px solid rgba(0, 188, 212, 0.3);
    box-shadow: 0 4px 20px rgba(0, 188, 212, 0.1);
    overflow: hidden;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: rgba(0, 188, 212, 0.1);
    border-bottom: 1px solid rgba(0, 188, 212, 0.2);
  }

  .panel-title {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: #00bcd4;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .icon {
    font-size: 20px;
  }

  .feature-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }

  .toggle-input {
    display: none;
  }

  .toggle-slider {
    width: 44px;
    height: 24px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 12px;
    position: relative;
    transition: all 0.3s ease;
  }

  .toggle-slider::before {
    content: '';
    position: absolute;
    top: 2px;
    left: 2px;
    width: 20px;
    height: 20px;
    background: white;
    border-radius: 50%;
    transition: all 0.3s ease;
  }

  .toggle-input:checked + .toggle-slider {
    background: #00bcd4;
  }

  .toggle-input:checked + .toggle-slider::before {
    transform: translateX(20px);
  }

  .toggle-label {
    color: #fff;
    font-size: 14px;
    font-weight: 500;
  }

  .panel-content {
    padding: 20px;
  }

  .control-section, .settings-section, .auto-update-section, .orderbook-section, .stats-section {
    margin-bottom: 24px;
  }

  .section-title {
    margin: 0 0 12px 0;
    font-size: 14px;
    font-weight: 600;
    color: #00bcd4;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .control-item {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
  }

  .control-label {
    color: #fff;
    font-size: 14px;
  }

  .checkbox {
    appearance: none;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(0, 188, 212, 0.5);
    border-radius: 3px;
    background: transparent;
    cursor: pointer;
    position: relative;
  }

  .checkbox:checked {
    background: #00bcd4;
    border-color: #00bcd4;
  }

  .checkbox:checked::after {
    content: '✓';
    position: absolute;
    top: -2px;
    left: 1px;
    color: white;
    font-size: 12px;
    font-weight: bold;
  }

  .setting-item {
    margin-bottom: 12px;
  }

  .setting-label {
    display: block;
    color: #bbb;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 4px;
  }

  .setting-value {
    color: #00bcd4;
    font-weight: 600;
  }

  .range-input {
    width: 100%;
    appearance: none;
    height: 4px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
    outline: none;
  }

  .range-input::-webkit-slider-thumb {
    appearance: none;
    width: 16px;
    height: 16px;
    background: #00bcd4;
    border-radius: 50%;
    cursor: pointer;
  }

  .number-input, .select-input {
    width: 100%;
    padding: 8px 12px;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 6px;
    color: #fff;
    font-size: 13px;
  }

  .number-input:focus, .select-input:focus {
    outline: none;
    border-color: #00bcd4;
    box-shadow: 0 0 0 2px rgba(0, 188, 212, 0.2);
  }

  .loading-section {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 20px;
    color: #00bcd4;
    font-size: 14px;
  }

  .loading-spinner {
    width: 20px;
    height: 20px;
    border: 2px solid rgba(0, 188, 212, 0.3);
    border-top: 2px solid #00bcd4;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error-section {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px;
    background: rgba(244, 67, 54, 0.1);
    border: 1px solid rgba(244, 67, 54, 0.3);
    border-radius: 6px;
    color: #f44336;
    font-size: 13px;
  }

  .error-icon {
    font-size: 16px;
  }

  .retry-btn {
    background: rgba(244, 67, 54, 0.2);
    border: 1px solid rgba(244, 67, 54, 0.3);
    color: #f44336;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    margin-left: auto;
  }

  .refresh-btn, .trigger-btn {
    background: rgba(0, 188, 212, 0.2);
    border: 1px solid rgba(0, 188, 212, 0.3);
    color: #00bcd4;
    padding: 6px 10px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s ease;
  }

  .refresh-btn:hover, .trigger-btn:hover {
    background: rgba(0, 188, 212, 0.3);
    transform: scale(1.05);
  }

  .orderbook-info {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 16px;
  }

  .info-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
  }

  .info-label {
    color: #bbb;
    font-weight: 500;
  }

  .info-value {
    color: #fff;
    font-family: 'Courier New', monospace;
    font-weight: 600;
  }

  .info-value.bid {
    color: #4caf50;
  }

  .info-value.ask {
    color: #f44336;
  }

  .levels-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .levels-title {
    margin: 0 0 8px 0;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .levels-title.bid {
    color: #4caf50;
  }

  .levels-title.ask {
    color: #f44336;
  }

  .levels-list {
    max-height: 200px;
    overflow-y: auto;
  }

  .level-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 8px;
    margin-bottom: 2px;
    border-radius: 4px;
    font-size: 11px;
    font-family: 'Courier New', monospace;
  }

  .level-item.bid {
    background: rgba(76, 175, 80, 0.1);
    border-left: 2px solid #4caf50;
  }

  .level-item.ask {
    background: rgba(244, 67, 54, 0.1);
    border-left: 2px solid #f44336;
  }

  .level-price {
    color: #fff;
    font-weight: 600;
  }

  .level-volume {
    color: #bbb;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .stat-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
  }

  .stat-label {
    color: #bbb;
    font-weight: 500;
  }

  .stat-value {
    color: #fff;
    font-family: 'Courier New', monospace;
    font-weight: 600;
  }

  .stat-value.collecting {
    color: #4caf50;
  }

  .stat-value.stopped {
    color: #f44336;
  }

  .disabled-message {
    padding: 40px 20px;
    text-align: center;
    color: #666;
  }

  .disabled-icon {
    font-size: 48px;
    display: block;
    margin-bottom: 16px;
  }

  .disabled-message p {
    margin: 8px 0;
  }

  .disabled-hint {
    font-size: 13px;
    color: #888;
  }

  /* Scrollbar styling */
  .levels-list::-webkit-scrollbar {
    width: 4px;
  }

  .levels-list::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
  }

  .levels-list::-webkit-scrollbar-thumb {
    background: rgba(0, 188, 212, 0.5);
    border-radius: 2px;
  }

  .levels-list::-webkit-scrollbar-thumb:hover {
    background: rgba(0, 188, 212, 0.7);
  }
</style>
