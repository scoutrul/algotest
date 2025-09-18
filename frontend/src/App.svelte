<!-- Main App Component - Adaptive Multi-Panel Layout -->
<script>
  import { onMount } from 'svelte';
  import Chart from './components/Chart.svelte';
  import StrategyForm from './components/StrategyForm.svelte';
  import Statistics from './components/Statistics.svelte';
  import Controls from './components/Controls.svelte';
  import DataManager from './components/DataManager.svelte';
  import LiquidityPanel from './components/panels/LiquidityPanel.svelte';
  import { backtestStore } from './stores/backtest.js';
  import { configStore } from './stores/config.js';
  import { liquidityStore } from './stores/liquidity.js';

  // Reactive state
  let chartFullscreen = false;
  let strategyPanelCollapsed = true; // Collapsed by default
  let statsPanelCollapsed = true; // Collapsed by default
  let liquidityPanelCollapsed = true; // Collapsed by default
  let loading = false;
  let isBackfilling = false;
  let error = null;
  let activeTab = 'backtest'; // 'backtest' or 'data'

  // Store subscriptions
  $: backtestData = $backtestStore;
  $: config = $configStore;
  $: liquidityState = $liquidityStore;

  onMount(async () => {
    try {
      // Load initial configuration with error handling
      await Promise.allSettled([
        configStore.loadConfig(),
        configStore.loadSymbols(),
        configStore.loadIntervals()
      ]);

      // 💾 Load panel collapsed states from localStorage
      const savedStrategyPanelState = localStorage.getItem('strategyPanelCollapsed');
      if (savedStrategyPanelState !== null) {
        strategyPanelCollapsed = JSON.parse(savedStrategyPanelState);
      }

      const savedStatsPanelState = localStorage.getItem('statsPanelCollapsed');
      if (savedStatsPanelState !== null) {
        statsPanelCollapsed = JSON.parse(savedStatsPanelState);
      }

      const savedLiquidityPanelState = localStorage.getItem('liquidityPanelCollapsed');
      if (savedLiquidityPanelState !== null) {
        liquidityPanelCollapsed = JSON.parse(savedLiquidityPanelState);
      }

      // 💧 Initialize liquidity feature
      try {
        await liquidityStore.loadStats();
        // Liquidity state is already loaded from localStorage in the store
        console.log('✅ Liquidity feature initialized successfully with persisted state');
        console.log(`💾 Loaded persisted state: symbol=${config.selectedSymbol}, interval=${config.selectedInterval}, liquidity visible=${liquidityState.visible}`);
      } catch (liquidityErr) {
        console.warn('⚠️ Failed to initialize liquidity feature:', liquidityErr);
        // Don't block app startup if liquidity fails
      }

      // 📊 Load initial chart data with persisted symbol/interval
      console.log('Loading initial chart data with persisted settings...');
      await updateChartData(config.selectedSymbol, config.selectedInterval);
      
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
    configStore.setSelectedInterval(event.detail.interval);
    await updateChartData(event.detail.symbol, event.detail.interval);
  }


  // Update chart data without running backtest
  async function updateChartData(symbol, interval) {
    loading = true;
    error = null;
    
    try {
      const { apiClient } = await import('./utils/api.js');
      
      // Fetch only candle data for the chart
      const result = await apiClient.runBacktest({
        symbol,
        interval,
        ...config.strategyParams
      });
      
      const candles = Array.isArray(result?.candles) ? result.candles.map(candle => ({
        ...candle,
        timestamp: typeof candle.timestamp === 'string' ? candle.timestamp : candle.timestamp.toISOString()
      })) : [];
      backtestStore.updateCandles(candles);
      
      // Stop loading immediately after successful update
      loading = false;
    } catch (err) {
      console.error('Error updating chart data:', err);
      error = `Failed to load data for ${symbol} ${interval}`;
    } finally {
      // Safety: ensure we always clear loading
      loading = false;
    }
  }

  // Handle panel toggles
  function toggleStrategyPanel() {
    strategyPanelCollapsed = !strategyPanelCollapsed;
    localStorage.setItem('strategyPanelCollapsed', JSON.stringify(strategyPanelCollapsed));
  }

  function toggleStatsPanel() {
    statsPanelCollapsed = !statsPanelCollapsed;
    localStorage.setItem('statsPanelCollapsed', JSON.stringify(statsPanelCollapsed));
  }

  function toggleLiquidityPanel() {
    liquidityPanelCollapsed = !liquidityPanelCollapsed;
    localStorage.setItem('liquidityPanelCollapsed', JSON.stringify(liquidityPanelCollapsed));
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

  // Handle chart reload request (after reinitialization)
  async function handleChartReload(event) {
    console.log('Chart requested data reload:', event.detail);
    const { symbol, interval } = event.detail;
    await updateChartData(symbol, interval);
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
          liquidityFeatureAvailable={true}
          selectedSymbol={config.selectedSymbol}
          availableIntervals={config.availableIntervals}
          selectedInterval={config.selectedInterval}
          on:reloadData={handleChartReload}
          on:liquidityToggled={handleLiquidityToggled}
          on:intervalChanged={handleIntervalChanged}
        />
        
      </section>
      
      <!-- 💧 Liquidity Panel -->
      <aside class="liquidity-panel" class:collapsed={liquidityPanelCollapsed}>
        <div class="panel-header" role="button" tabindex="0" on:click={toggleLiquidityPanel} on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), toggleLiquidityPanel())}>
          <h3 class="panel-title">
            <span class="icon">💧</span>
            Liquidity Analysis
          </h3>
          <span class="collapse-indicator">
            {liquidityPanelCollapsed ? '▼' : '▲'}
          </span>
        </div>
        {#if !liquidityPanelCollapsed}
          <LiquidityPanel
            symbol={config.selectedSymbol?.replace('/', '') || 'BTCUSDT'}
          />
        {/if}
      </aside>

      <!-- Strategy parameters panel -->
      <aside class="strategy-panel" class:collapsed={strategyPanelCollapsed}>
        <div class="panel-header" role="button" tabindex="0" on:click={toggleStrategyPanel} on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), toggleStrategyPanel())}>
          <h3 class="panel-title">
            <span class="icon">⚙️</span>
            Strategy Parameters
          </h3>
          <span class="collapse-indicator">
            {strategyPanelCollapsed ? '▼' : '▲'}
          </span>
        </div>
        {#if !strategyPanelCollapsed}
          <StrategyForm
            bind:params={config.strategyParams}
            bind:collapsed={strategyPanelCollapsed}
            {loading}
            on:backtest={handleBacktest}
          />
        {/if}
      </aside>

      <!-- Statistics panel -->
      <aside class="stats-panel" class:collapsed={statsPanelCollapsed}>
        <div class="panel-header" role="button" tabindex="0" on:click={toggleStatsPanel} on:keydown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), toggleStatsPanel())}>
          <h3 class="panel-title">
            <span class="icon">📊</span>
            Backtest Results
          </h3>
          <span class="collapse-indicator">
            {statsPanelCollapsed ? '▼' : '▲'}
          </span>
        </div>
        {#if !statsPanelCollapsed}
          <Statistics
            statistics={backtestData.statistics}
            trades={backtestData.trades}
            bind:collapsed={statsPanelCollapsed}
            {loading}
          />
        {/if}
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
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    padding: 1rem;
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
    align-items: flex-start;
  }

  /* Chart panel */
  .chart-panel {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    overflow: hidden;
    flex: 1 1 700px;
    min-width: 600px;
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
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
    overflow: hidden;
    flex: 1 1 700px;
    min-width: 600px;
  }

  .strategy-panel.collapsed {
    max-height: 60px;
    overflow: hidden;
  }

  .strategy-panel .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: rgba(52, 152, 219, 0.1);
    border-bottom: 1px solid rgba(52, 152, 219, 0.2);
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .strategy-panel .panel-header:hover {
    background: rgba(52, 152, 219, 0.15);
  }

  .strategy-panel .panel-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #3498db;
  }

  .strategy-panel .panel-title .icon {
    font-size: 18px;
  }

  .strategy-panel .collapse-indicator {
    color: #3498db;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s ease;
  }

  /* Statistics panel */
  .stats-panel {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
    overflow: hidden;
    flex: 1 1 700px;
    min-width: 600px;
  }

  .stats-panel.collapsed {
    max-height: 60px;
    overflow: hidden;
  }

  .stats-panel .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: rgba(46, 204, 113, 0.1);
    border-bottom: 1px solid rgba(46, 204, 113, 0.2);
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .stats-panel .panel-header:hover {
    background: rgba(46, 204, 113, 0.15);
  }

  .stats-panel .panel-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #2ecc71;
  }

  .stats-panel .panel-title .icon {
    font-size: 18px;
  }

  .stats-panel .collapse-indicator {
    color: #2ecc71;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s ease;
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

  
  /* 💧 Liquidity panel */
  .liquidity-panel {
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transition: all 0.3s ease;
    overflow: hidden;
    flex: 0 1 360px;
    min-width: 320px;
  }

  .liquidity-panel.collapsed {
    max-height: 60px;
    overflow: hidden;
  }

  .liquidity-panel .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: rgba(0, 188, 212, 0.1);
    border-bottom: 1px solid rgba(0, 188, 212, 0.2);
    cursor: pointer;
    transition: background-color 0.2s ease;
  }

  .liquidity-panel .panel-header:hover {
    background: rgba(0, 188, 212, 0.15);
  }

  .liquidity-panel .panel-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #00bcd4;
  }

  .liquidity-panel .panel-title .icon {
    font-size: 18px;
  }

  .liquidity-panel .collapse-indicator {
    color: #00bcd4;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s ease;
  }

  /* Responsive design */
  @media (min-width: 1024px) {
    .chart-panel { flex: 1 1 760px; min-width: 720px; }
    .strategy-panel { flex: 1 1 760px; min-width: 720px; }
    .stats-panel { flex: 1 1 760px; min-width: 720px; }
    .liquidity-panel { flex: 0 1 380px; min-width: 340px; }
  }

  @media (min-width: 1400px) {
    .app-main { max-width: 1400px; }
    .chart-panel { flex: 1 1 900px; min-width: 820px; }
    .strategy-panel { flex: 1 1 900px; min-width: 820px; }
    .stats-panel { flex: 1 1 900px; min-width: 820px; }
    .liquidity-panel { flex: 0 1 420px; min-width: 360px; }
  }
</style>
