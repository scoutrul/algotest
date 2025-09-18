<!-- Controls Component for Symbol and Interval Selection -->
<script>
  import { createEventDispatcher, onMount } from 'svelte';
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
  function handleSymbolChange(symbol) {
    selectedSymbol = symbol;
    configStore.setSelectedSymbol(selectedSymbol);
    // Dispatch event to update chart data only (no backtest)
    dispatch('symbolChanged', { symbol: selectedSymbol, interval: selectedInterval });
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




</script>

<div class="controls">
  <div class="control-group">
    <label for="symbol-badges">Symbol</label>
    <div class="badge-container" id="symbol-badges" role="group" aria-label="Select trading symbol">
      {#each availableSymbols as symbol}
        <button
          class="badge {selectedSymbol === symbol ? 'badge-active' : 'badge-inactive'}"
          on:click={() => handleSymbolChange(symbol)}
          disabled={loading}
        >
          {symbol}
        </button>
      {/each}
    </div>
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

  .badge-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.25rem;
  }

  .badge {
    padding: 0.375rem 0.75rem;
    border: 1px solid #ddd;
    border-radius: 20px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    background: white;
    color: #333;
    min-width: auto;
    white-space: nowrap;
  }

  .badge:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .badge-active {
    background: #3498db;
    color: white;
    border-color: #3498db;
    box-shadow: 0 2px 4px rgba(52, 152, 219, 0.3);
  }

  .badge-active:hover:not(:disabled) {
    background: #2980b9;
    border-color: #2980b9;
    box-shadow: 0 4px 8px rgba(52, 152, 219, 0.4);
  }

  .badge-inactive {
    background: white;
    color: #666;
    border-color: #ddd;
  }

  .badge-inactive:hover:not(:disabled) {
    background: #f8f9fa;
    border-color: #bbb;
    color: #333;
  }

  .badge:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .badge:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
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


  /* Responsive design */
  @media (max-width: 768px) {
    .controls {
      flex-direction: column;
      align-items: stretch;
      gap: 0.75rem;
    }

    .control-group {
      flex-direction: column;
      align-items: stretch;
    }

    .control-group label {
      margin-bottom: 0.5rem;
      text-align: center;
    }

    .badge-container {
      justify-content: center;
      gap: 0.375rem;
    }

    .badge {
      font-size: 0.8rem;
      padding: 0.3rem 0.6rem;
    }

    .btn {
      width: 100%;
    }
  }

  /* Extra small screens */
  @media (max-width: 480px) {
    .badge-container {
      gap: 0.25rem;
    }

    .badge {
      font-size: 0.75rem;
      padding: 0.25rem 0.5rem;
    }
  }
</style>
