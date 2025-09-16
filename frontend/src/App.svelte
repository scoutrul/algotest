<!-- Main App Component - Adaptive Multi-Panel Layout -->
<script>
  import { onMount } from 'svelte';
  import Chart from './components/Chart.svelte';
  import StrategyForm from './components/StrategyForm.svelte';
  import Statistics from './components/Statistics.svelte';
  import Controls from './components/Controls.svelte';
  import DataManager from './components/DataManager.svelte';
  import LiquidityChart from './components/charts/LiquidityChart.svelte';
  import { backtestStore } from './stores/backtest.js';
  import { configStore } from './stores/config.js';
  import { liquidityStore } from './stores/liquidity.js';

  // Reactive state
  let chartFullscreen = false;
  let strategyPanelCollapsed = false;
  let statsPanelCollapsed = false;
  let loading = false;
  let isBackfilling = false;
  let error = null;
  let activeTab = 'backtest'; // 'backtest' or 'data'

  // Store subscriptions
  $: backtestData = $backtestStore;
  $: config = $configStore;

  onMount(async () => {
    try {
      // Load initial configuration with error handling
      await Promise.allSettled([
        configStore.loadConfig(),
        configStore.loadSymbols(),
        configStore.loadIntervals()
      ]);

      // 💧 Initialize liquidity feature
      try {
        await liquidityStore.loadStats();
        // Enable liquidity feature by default
        liquidityStore.enable();
        console.log('✅ Liquidity feature initialized successfully');
      } catch (liquidityErr) {
        console.warn('⚠️ Failed to initialize liquidity feature:', liquidityErr);
        // Don't block app startup if liquidity fails
      }
    } catch (err) {
      console.error('Error loading configuration:', err);
      error = err.message;
    }
  });

  // Handle backtest execution
  async function handleBacktest(params) {
    loading = true;
    error = null;
    
    try {
      // Ensure we have valid symbol and interval
      const backtestParams = {
        symbol: config.selectedSymbol || 'BTC/USDT',
        interval: config.selectedInterval || '15m',
        ...config.strategyParams,
        ...params
      };
      
      await backtestStore.runBacktest(backtestParams);
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  // Handle symbol/interval changes (update chart data only)
  async function handleSymbolChanged(event) {
    await updateChartData(event.detail.symbol, event.detail.interval);
  }

  async function handleIntervalChanged(event) {
    await updateChartData(event.detail.symbol, event.detail.interval);
  }

  // Update chart data without running backtest
  async function updateChartData(symbol, interval) {
    loading = true;
    error = null;
    
    try {
      // First clear old data immediately
      backtestStore.updateCandles([]);
      backtestStore.updateTrades([]);
      backtestStore.updateStatistics(null);
      
      const { apiClient } = await import('./utils/api.js');
      
      // Fetch only candle data for the chart
      const result = await apiClient.runBacktest({
        symbol,
        interval,
        ...config.strategyParams
      });
      
      // Update with new data
      backtestStore.updateCandles(result.candles || []);
      
    } catch (err) {
      console.error('Error updating chart data:', err);
      error = `Failed to load data for ${symbol} ${interval}`;
    } finally {
      loading = false;
    }
  }

  // Handle panel toggles
  function toggleStrategyPanel() {
    strategyPanelCollapsed = !strategyPanelCollapsed;
  }

  function toggleStatsPanel() {
    statsPanelCollapsed = !statsPanelCollapsed;
  }

  function toggleChartFullscreen() {
    chartFullscreen = !chartFullscreen;
  }

  // 🚀 Handle liquidity toggle
  function handleLiquidityToggled(event) {
    console.log('Liquidity toggled:', event.detail);
    // The store is already updated by the Controls component
    // Chart.svelte will react to the store changes automatically
  }
</script>

<main class="trading-app" class:fullscreen={chartFullscreen}>
  <!-- Header with controls -->
  <header class="app-header">
    <div class="header-content">
      <h1 class="app-title">BackTest Trading Bot</h1>
      <div class="header-controls">
        {#if activeTab === 'backtest'}
          <Controls
            bind:selectedSymbol={config.selectedSymbol}
            bind:selectedInterval={config.selectedInterval}
            {loading}
            on:backtest={handleBacktest}
            on:symbolChanged={handleSymbolChanged}
            on:intervalChanged={handleIntervalChanged}
            on:liquidityToggled={handleLiquidityToggled}
          />
        {/if}
      </div>
    </div>

    <!-- Tab navigation -->
    <nav class="tab-nav">
      <button
        class="tab-btn {activeTab === 'backtest' ? 'active' : ''}"
        on:click={() => activeTab = 'backtest'}
      >
        Backtesting
      </button>
      <button
        class="tab-btn {activeTab === 'data' ? 'active' : ''}"
        on:click={() => activeTab = 'data'}
      >
        Data Management
      </button>
    </nav>
  </header>

  <!-- Main content area -->
  {#if activeTab === 'backtest'}
    <div class="app-main">
      <!-- Chart panel -->
      <section class="chart-panel" class:fullscreen={chartFullscreen}>
        <Chart
          candles={backtestData.candles}
          trades={backtestData.trades}
          symbol={config.selectedSymbol}
          interval={config.selectedInterval}
          bind:fullscreen={chartFullscreen}
          {loading}
                      bind:isBackfilling
          />
          <div class="liquidity-under-chart">
            <div class="liquidity-under-chart__header">
              <h3>💧 Liquidity Analysis</h3>
              <div class="liquidity-controls">
                <label class="control-item">
                  <span class="control-label">Opacity:</span>
                  <input
                    type="range"
                    min="0.1"
                    max="1.0"
                    step="0.05"
                    bind:value={$liquidityStore.settings.opacity}
                    on:input={(e) => liquidityStore.setOpacity(parseFloat(e.target.value))}
                    class="range-input"
                  />
                  <span class="control-value">{Math.round($liquidityStore.settings.opacity * 100)}%</span>
                </label>
                
                <label class="control-item">
                  <span class="control-label">Min Vol:</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    bind:value={$liquidityStore.settings.minVolume}
                    on:change={(e) => liquidityStore.setMinVolume(parseFloat(e.target.value))}
                    class="number-input"
                  />
                </label>
                
                <label class="control-item">
                  <span class="control-label">Max Levels:</span>
                  <input
                    type="number"
                    min="5"
                    max="50"
                    step="1"
                    bind:value={$liquidityStore.settings.maxLevels}
                    on:change={(e) => liquidityStore.setMaxLevels(parseInt(e.target.value))}
                    class="number-input"
                  />
                </label>
                
                <label class="control-item checkbox-item">
                  <input
                    type="checkbox"
                    bind:checked={$liquidityStore.settings.autoUpdate}
                    on:change={(e) => {
                      if (e.target.checked) {
                        liquidityStore.startAutoUpdate(config.selectedSymbol || 'BTCUSDT');
                      } else {
                        liquidityStore.stopAutoUpdate();
                      }
                    }}
                    class="checkbox-input"
                  />
                  <span class="control-label">Auto-update</span>
                </label>
              </div>
            </div>
            <div class="liquidity-under-chart__content">
              <LiquidityChart
                symbol={config.selectedSymbol || 'BTCUSDT'}
                height={220}
                opacity={$liquidityStore.settings.opacity}
                minVolume={$liquidityStore.settings.minVolume}
                maxLevels={$liquidityStore.settings.maxLevels}
              />
            </div>
          </div>
        </section>

      <!-- Strategy parameters panel -->
      <aside class="strategy-panel" class:collapsed={strategyPanelCollapsed}>
        <StrategyForm
          bind:params={config.strategyParams}
          bind:collapsed={strategyPanelCollapsed}
          {loading}
          on:backtest={handleBacktest}
        />
      </aside>

      <!-- Statistics panel -->
      <aside class="stats-panel" class:collapsed={statsPanelCollapsed}>
        <Statistics
          statistics={backtestData.statistics}
          trades={backtestData.trades}
          bind:collapsed={statsPanelCollapsed}
          {loading}
        />
      </aside>
    </div>
  
  {:else if activeTab === 'data'}
    <div class="app-main">
      <!-- Data management panel -->
      <section class="data-panel">
        <DataManager />
      </section>
    </div>
  {/if}

  <!-- Error overlay -->
  {#if error}
    <div class="error-overlay">
      <div class="error-content">
        <h3>Error</h3>
        <p>{error}</p>
        <button on:click={() => error = null}>Close</button>
      </div>
    </div>
  {/if}

  <!-- Loading overlay -->
  {#if loading}
    <div class="loading-overlay">
      <div class="loading-spinner"></div>
      <p>Running backtest...</p>
    </div>
  {/if}
</main>

<style>
  /* Global styles */
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: #f5f5f5;
    color: #333;
  }

  /* Main app layout */
  .trading-app {
    display: grid;
    grid-template-areas: 
      "header"
      "main";
    grid-template-rows: auto 1fr;
    height: 100vh;
    background: white;
  }

  .trading-app.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 1000;
  }

  /* Header */
  .app-header {
    grid-area: header;
    background: #2c3e50;
    color: white;
    padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    max-width: 1400px;
    margin: 0 auto;
  }

  .app-title {
    font-size: 1.5rem;
    font-weight: 600;
  }

  /* Tab navigation */
  .tab-nav {
    display: flex;
    gap: 0.5rem;
    border-bottom: 1px solid #34495e;
  }

  .tab-btn {
    background: transparent;
    border: none;
    color: #bdc3c7;
    padding: 0.75rem 1.5rem;
    cursor: pointer;
    border-radius: 4px 4px 0 0;
    transition: all 0.2s ease;
    font-size: 0.9rem;
    font-weight: 500;
  }

  .tab-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #ecf0f1;
  }

  .tab-btn.active {
    background: #3498db;
    color: white;
  }

  /* Data panel */
  .data-panel {
    grid-area: chart;
    padding: 1rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  /* Main content area */
  .app-main {
    display: grid;
    grid-template-areas: 
      "chart"
      "strategy"
      "stats";
    grid-template-rows: minmax(400px, 1fr) auto auto;
    gap: 1rem;
    padding: 1rem;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
  }

  /* Chart panel */
  .chart-panel {
    grid-area: chart;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    overflow: hidden;
  }

  .chart-panel.fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 1000;
    border-radius: 0;
  }

  /* Strategy panel */
  .strategy-panel {
    grid-area: strategy;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
  }

  .strategy-panel.collapsed {
    max-height: 60px;
    overflow: hidden;
  }

  /* Statistics panel */
  .stats-panel {
    grid-area: stats;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
  }

  .stats-panel.collapsed {
    max-height: 60px;
    overflow: hidden;
  }

  /* Error overlay */
  .error-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0,0,0,0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 2000;
  }

  .error-content {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    max-width: 400px;
    text-align: center;
  }

  .error-content h3 {
    color: #e74c3c;
    margin-bottom: 1rem;
  }

  .error-content button {
    background: #3498db;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    margin-top: 1rem;
  }

  /* Loading overlay */
  .loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(255,255,255,0.9);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    z-index: 1500;
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  /* 💧 Liquidity Layout Styles */


  /* 💧 Liquidity Layout Styles */
  .liquidity-under-chart {
    margin-top: 12px;
    background: rgba(0, 0, 0, 0.25);
    border: 1px solid rgba(0, 188, 212, 0.25);
    border-radius: 8px;
    overflow: hidden;
  }
  .liquidity-under-chart__header {
    padding: 8px 12px;
    border-bottom: 1px solid rgba(0, 188, 212, 0.2);
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 12px;
  }
  .liquidity-under-chart__header h3 {
    margin: 0;
    font-size: 14px;
    color: #00bcd4;
    font-weight: 600;
    flex-shrink: 0;
  }
  .liquidity-under-chart__content {
    padding: 8px 8px 0 8px;
  }

  /* Liquidity Controls */
  .liquidity-controls {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 8px 12px;
    align-items: center;
    min-width: 0;
    flex: 1;
  }

  .control-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    color: #bbb;
    min-width: 0;
    background: rgba(0, 0, 0, 0.2);
    padding: 4px 6px;
    border-radius: 4px;
    border: 1px solid rgba(0, 188, 212, 0.1);
  }

  .control-label {
    white-space: nowrap;
    font-weight: 500;
    font-size: 10px;
    min-width: max-content;
  }

  .control-value {
    min-width: 35px;
    text-align: center;
    color: #00bcd4;
    font-weight: 600;
    font-size: 10px;
    background: rgba(0, 188, 212, 0.1);
    padding: 1px 4px;
    border-radius: 2px;
  }

  .range-input {
    width: 50px;
    height: 4px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
    flex: 1;
    min-width: 40px;
  }

  .range-input::-webkit-slider-thumb {
    appearance: none;
    width: 10px;
    height: 10px;
    background: #00bcd4;
    border-radius: 50%;
    cursor: pointer;
  }

  .number-input {
    width: 45px;
    padding: 2px 4px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(0, 188, 212, 0.3);
    border-radius: 3px;
    color: #fff;
    font-size: 10px;
    text-align: center;
    flex-shrink: 0;
  }

  .number-input:focus {
    outline: none;
    border-color: #00bcd4;
    box-shadow: 0 0 4px rgba(0, 188, 212, 0.3);
  }

  .checkbox-item {
    display: flex;
    align-items: center;
    gap: 4px;
    justify-content: flex-start;
  }

  .checkbox-input {
    width: 12px;
    height: 12px;
    accent-color: #00bcd4;
    flex-shrink: 0;
  }

  /* Responsive adjustments */
  @media (max-width: 1024px) {
    .liquidity-controls {
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 6px 8px;
    }
    .control-item {
      padding: 3px 4px;
    }
  }

  /* Responsive design for liquidity layout */
  @media (max-width: 1200px) {
    .liquidity-layout {
      grid-template-columns: 1fr;
      grid-template-rows: 1fr auto;
      grid-template-areas: 
        "chart"
        "panel";
    }
    
    .liquidity-panel-section {
      max-height: 50vh;
    }
  }

  @media (max-width: 768px) {
    .section-header {
      padding: 16px;
      flex-direction: column;
      gap: 12px;
      align-items: flex-start;
    }
    
    .section-title {
      font-size: 20px;
    }
    
    .chart-container {
      padding: 16px;
    }
  }



  /* Responsive design */
  @media (min-width: 768px) {
    .app-main {
      grid-template-areas: 
        "chart"
        "strategy"
        "stats";
      grid-template-columns: 1fr;
      grid-template-rows: minmax(500px, 1fr) auto auto;
    }
  }

  @media (min-width: 1024px) {
    .app-main {
      grid-template-areas: 
        "chart"
        "strategy"
        "stats";
      grid-template-columns: 1fr;
      grid-template-rows: minmax(600px, 1fr) auto auto;
    }
  }

  @media (min-width: 1400px) {
    .app-main {
      grid-template-areas: 
        "chart"
        "strategy"
        "stats";
      grid-template-columns: 1fr;
      grid-template-rows: minmax(700px, 1fr) auto auto;
    }
  }
</style>
