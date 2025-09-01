<!-- Controls Component for Symbol and Interval Selection -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { configStore } from '../stores/config.js';

  // Props
  export let selectedSymbol = 'BTC/USDT';
  export let selectedInterval = '15m';
  export let loading = false;

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // Store subscriptions
  $: availableSymbols = $configStore.availableSymbols;
  $: availableIntervals = $configStore.availableIntervals;

  // Event handlers
  function handleSymbolChange(event) {
    selectedSymbol = event.target.value;
    configStore.setSelectedSymbol(selectedSymbol);
  }

  function handleIntervalChange(event) {
    selectedInterval = event.target.value;
    configStore.setSelectedInterval(selectedInterval);
  }

  function handleQuickBacktest() {
    const params = {
      symbol: selectedSymbol,
      interval: selectedInterval,
      ...$configStore.strategyParams
    };
    dispatch('backtest', params);
  }
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
    padding: 0.5rem 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
    color: #333;
    font-size: 0.875rem;
    min-width: 120px;
    cursor: pointer;
    transition: border-color 0.2s ease;
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
  }
</style>
