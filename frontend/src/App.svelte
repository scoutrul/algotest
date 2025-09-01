<!-- Main App Component - Adaptive Multi-Panel Layout -->
<script>
  import { onMount } from 'svelte';
  import Chart from './components/Chart.svelte';
  import StrategyForm from './components/StrategyForm.svelte';
  import Statistics from './components/Statistics.svelte';
  import Controls from './components/Controls.svelte';
  import { backtestStore } from './stores/backtest.js';
  import { configStore } from './stores/config.js';

  // Reactive state
  let chartFullscreen = false;
  let strategyPanelCollapsed = false;
  let statsPanelCollapsed = false;
  let loading = false;
  let error = null;

  // Store subscriptions
  $: backtestData = $backtestStore;
  $: config = $configStore;

  onMount(async () => {
    try {
      // Load initial configuration
      await configStore.loadConfig();
      await configStore.loadSymbols();
      await configStore.loadIntervals();
    } catch (err) {
      error = err.message;
    }
  });

  // Handle backtest execution
  async function handleBacktest(params) {
    loading = true;
    error = null;
    
    try {
      await backtestStore.runBacktest(params);
    } catch (err) {
      error = err.message;
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
</script>

<main class="trading-app" class:fullscreen={chartFullscreen}>
  <!-- Header with controls -->
  <header class="app-header">
    <div class="header-content">
      <h1 class="app-title">BackTest Trading Bot</h1>
      <div class="header-controls">
        <Controls 
          bind:selectedSymbol={config.selectedSymbol}
          bind:selectedInterval={config.selectedInterval}
          {loading}
          on:backtest={handleBacktest}
        />
      </div>
    </div>
  </header>

  <!-- Main content area -->
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
      />
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

  /* Main content area */
  .app-main {
    display: grid;
    grid-template-areas: 
      "chart"
      "strategy"
      "stats";
    grid-template-rows: 1fr auto auto;
    gap: 1rem;
    padding: 1rem;
    max-width: 1400px;
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

  /* Responsive design */
  @media (min-width: 768px) {
    .app-main {
      grid-template-areas: 
        "chart chart"
        "strategy stats";
      grid-template-columns: 1fr 1fr;
      grid-template-rows: 1fr auto;
    }
  }

  @media (min-width: 1024px) {
    .app-main {
      grid-template-areas: 
        "chart chart strategy"
        "chart chart stats";
      grid-template-columns: 2fr 1fr;
      grid-template-rows: 1fr 1fr;
    }
  }

  @media (min-width: 1400px) {
    .app-main {
      grid-template-areas: 
        "chart chart strategy"
        "chart chart stats";
      grid-template-columns: 2fr 1fr;
      grid-template-rows: 1fr 1fr;
    }
  }
</style>
