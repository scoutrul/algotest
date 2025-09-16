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
  $: liquidityState = $liquidityStore;

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
          on:reloadData={handleChartReload}
        />
        
        <!-- 💧 Liquidity Widget -->
        <div class="liquidity-widget">
          <LiquidityChart
            symbol={config.selectedSymbol?.replace('/', '') || 'BTCUSDT'}
            height={300}
            showLevels={true}
            opacity={0.7}
            minVolume={0.01}
            maxLevels={15}
          />
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

  
  /* 💧 Liquidity Widget Styles */
  .liquidity-widget {
    margin-top: 16px;
    border-radius: 8px;
    overflow: hidden;
    background: rgba(20, 20, 20, 0.95);
    border: 1px solid rgba(0, 188, 212, 0.2);
    box-shadow: 0 2px 12px rgba(0, 188, 212, 0.1);
    transition: all 0.3s ease;
  }

  .liquidity-widget:hover {
    border-color: rgba(0, 188, 212, 0.4);
    box-shadow: 0 4px 20px rgba(0, 188, 212, 0.15);
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
