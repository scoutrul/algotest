<!-- Controls Component for Symbol and Interval Selection -->
<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { configStore } from '../stores/config.js';
  import { liquidityStore, liquidityState } from '../stores/liquidity.js';
  import { apiClient } from '../utils/api.js';

  // Props
  export let selectedSymbol = 'BTC/USDT';
  export let selectedInterval = '15m';
  export let loading = false;

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // Store subscriptions
  $: availableSymbols = $configStore.availableSymbols;
  $: availableIntervals = $configStore.availableIntervals;

  // Liquidity state
  let liquidityFeatureAvailable = true;

  // Event handlers
  function handleSymbolChange(event) {
    selectedSymbol = event.target.value;
    configStore.setSelectedSymbol(selectedSymbol);
    // Dispatch event to update chart data only (no backtest)
    dispatch('symbolChanged', { symbol: selectedSymbol, interval: selectedInterval });
  }

  function handleIntervalChange(event) {
    selectedInterval = event.target.value;
    configStore.setSelectedInterval(selectedInterval);
    // Dispatch event to update chart data only (no backtest)
    dispatch('intervalChanged', { symbol: selectedSymbol, interval: selectedInterval });
  }

  function handleQuickBacktest() {
    // Ensure we have valid values
    const symbol = selectedSymbol && selectedSymbol !== 'undefined' ? selectedSymbol : 'BTC/USDT';
    const interval = selectedInterval && selectedInterval !== 'undefined' ? selectedInterval : '15m';
    
    const params = {
      symbol,
      interval,
      ...$configStore.strategyParams
    };
    
    console.log('Running backtest with params:', params);
    dispatch('backtest', params);
  }

  function handleLiquidityToggle() {
    if ($liquidityState.visible) {
      liquidityStore.hide();
    } else {
      liquidityStore.show();
      // Load liquidity data for current symbol
      const symbol = selectedSymbol && selectedSymbol !== 'undefined' ? selectedSymbol : 'BTC/USDT';
      liquidityStore.loadCurrentOrderBook(symbol.replace('/', ''));
    }
    
    // Dispatch event to notify chart about liquidity toggle
    dispatch('liquidityToggled', { 
      visible: !$liquidityState.visible,
      symbol: selectedSymbol 
    });
  }



  // Check liquidity feature availability on mount
  onMount(async () => {
    try {
      liquidityFeatureAvailable = await apiClient.isLiquidityFeatureAvailable();
      if (liquidityFeatureAvailable) {
        liquidityStore.enable();
        console.log('✅ Liquidity feature enabled');
      } else {
        console.log('⚠️ Liquidity feature not available');
      }
    } catch (error) {
      console.warn('Failed to check liquidity feature availability:', error);
      liquidityFeatureAvailable = false;
    }
  });
</script>

<div class="controls">
  <div class="control-group">
    <label for="symbol-select">Symbol</label>
    <select
      id="symbol-select"
      bind:value={selectedSymbol}
      on:change={handleSymbolChange}
      disabled={loading}
      class="control-select"
    >
      {#each availableSymbols as symbol}
        <option value={symbol}>{symbol}</option>
      {/each}
    </select>
  </div>

  <div class="control-group">
    <label for="interval-select">Interval</label>
    <select
      id="interval-select"
      bind:value={selectedInterval}
      on:change={handleIntervalChange}
      disabled={loading}
      class="control-select"
    >
      {#each availableIntervals as interval}
        <option value={interval}>{interval}</option>
      {/each}
    </select>
  </div>

  <div class="control-group">
    <button 
      class="btn btn-primary"
      on:click={handleQuickBacktest}
      disabled={loading || !availableSymbols.length || !availableIntervals.length}
    >
      {loading ? 'Running...' : 'Quick Backtest'}
    </button>
  </div>

  <!-- 🚀 Liquidity Toggle Button -->
  {#if liquidityFeatureAvailable}
    <div class="control-group">
      <button 
        class="btn {$liquidityState.visible ? 'btn-liquidity-active' : 'btn-liquidity'}"
        on:click={handleLiquidityToggle}
        disabled={$liquidityState.loading}
        title={$liquidityState.visible ? 'Hide liquidity overlay' : 'Show liquidity overlay'}
      >
        {#if $liquidityState.loading}
          <span class="loading-spinner"></span>
          Loading...
        {:else if $liquidityState.visible}
          <span class="icon">💧</span>
          Hide Liquidity
        {:else}
          <span class="icon">💧</span>
          Show Liquidity
        {/if}
      </button>
      
      <!-- Status indicator -->
      {#if $liquidityState.visible}
        <div class="liquidity-status">
          {#if $liquidityState.hasData}
            <span class="status-indicator status-active" title="Liquidity data loaded">●</span>
          {:else}
            <span class="status-indicator status-loading" title="Loading liquidity data">●</span>
          {/if}
          <span class="status-text">
            {$liquidityState.hasData ? 'Active' : 'Loading...'}
          </span>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .controls {
    display: flex;
    align-items: end;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .control-group {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .control-group label {
    font-size: 0.875rem;
    font-weight: 500;
    color: white;
    margin-bottom: 0.25rem;
  }

  .control-select {
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.875rem;
    background: white;
    color: #333;
    min-width: 120px;
  }

  .control-select:focus {
    outline: none;
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
  }

  .control-select:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
    color: #333;
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    min-width: 120px;
  }

  .btn:hover:not(:disabled) {
    background: #f5f5f5;
    border-color: #bbb;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary {
    background: #3498db;
    color: white;
    border-color: #3498db;
  }

  .btn-primary:hover:not(:disabled) {
    background: #2980b9;
    border-color: #2980b9;
  }

  /* 🚀 Liquidity button styles */
  .btn-liquidity {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: 1px solid #667eea;
  }

  .btn-liquidity:hover:not(:disabled) {
    background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
  }

  .btn-liquidity-active {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
    border: 1px solid #11998e;
    box-shadow: 0 2px 4px rgba(17, 153, 142, 0.3);
  }

  .btn-liquidity-active:hover:not(:disabled) {
    background: linear-gradient(135deg, #0e8074 0%, #2dd4bf 100%);
    transform: translateY(-1px);
    box-shadow: 0 4px 8px rgba(17, 153, 142, 0.4);
  }

  .icon {
    font-size: 1rem;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,0.2));
  }

  .loading-spinner {
    width: 12px;
    height: 12px;
    border: 2px solid rgba(255,255,255,0.3);
    border-radius: 50%;
    border-top-color: white;
    animation: spin 1s ease-in-out infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Liquidity status indicator */
  .liquidity-status {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: rgba(255, 255, 255, 0.8);
    margin-top: 0.25rem;
  }

  .status-indicator {
    font-size: 0.5rem;
    line-height: 1;
  }

  .status-active {
    color: #38ef7d;
    animation: pulse 2s ease-in-out infinite;
  }

  .status-loading {
    color: #ffd700;
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .status-text {
    font-weight: 500;
  }

  /* Responsive design */
  @media (max-width: 768px) {
    .controls {
      flex-direction: column;
      align-items: stretch;
      gap: 0.75rem;
    }

    .control-group {
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
    }

    .control-group label {
      margin-bottom: 0;
      min-width: 80px;
    }

    .control-select {
      flex: 1;
      min-width: auto;
    }

    .btn {
      width: 100%;
    }

    .liquidity-status {
      justify-content: center;
      margin-top: 0.5rem;
    }
  }
</style>
