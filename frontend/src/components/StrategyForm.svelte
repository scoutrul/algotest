<!-- Strategy Parameters Form Component -->
<script>
  import { createEventDispatcher } from 'svelte';
  import { configStore } from '../stores/config.js';

  // Props
  export let params = {};
  export let collapsed = false;
  export let loading = false;

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // Reactive statements
  $: validation = configStore.validateParams(params);

  // Form handlers
  function handleSubmit(event) {
    event.preventDefault();
    
    if (validation.valid) {
      dispatch('backtest', params);
    }
  }

  function handleReset() {
    configStore.resetToDefaults();
  }

  function toggleCollapsed() {
    collapsed = !collapsed;
  }

  function updateParam(key, value) {
    params = { ...params, [key]: value };
  }

  function handleNumberInput(event, key) {
    const value = parseFloat(event.target.value);
    if (!isNaN(value)) {
      updateParam(key, value);
    }
  }

  function handleIntegerInput(event, key) {
    const value = parseInt(event.target.value);
    if (!isNaN(value)) {
      updateParam(key, value);
    }
  }
</script>

<div class="strategy-form">
  <!-- Form header -->
  <div class="form-header">
    <h3>Strategy Parameters</h3>
    <button class="btn btn-secondary" on:click={toggleCollapsed}>
      {collapsed ? 'Expand' : 'Collapse'}
    </button>
  </div>

  {#if !collapsed}
    <form on:submit={handleSubmit} class="strategy-form-content">
      <!-- Volume Analysis Parameters -->
      <div class="form-section">
        <h4>Volume Analysis</h4>
        
        <div class="form-group">
          <label for="lookback-period">Lookback Period</label>
          <input 
            type="number" 
            id="lookback-period"
            bind:value={params.lookback_period}
            on:input={(e) => handleIntegerInput(e, 'lookback_period')}
            min="5" 
            max="100"
            step="1"
            class="form-input"
            class:error={validation.errors.some(e => e.includes('Lookback period'))}
          />
          <small>Number of candles for volume average calculation</small>
        </div>

        <div class="form-group">
          <label for="volume-threshold">Volume Threshold</label>
          <input 
            type="number" 
            id="volume-threshold"
            bind:value={params.volume_threshold}
            on:input={(e) => handleNumberInput(e, 'volume_threshold')}
            min="1.0" 
            max="5.0" 
            step="0.1"
            class="form-input"
            class:error={validation.errors.some(e => e.includes('Volume threshold'))}
          />
          <small>Volume spike multiplier (1.5 = 150% of average)</small>
        </div>

        <div class="form-group">
          <label for="min-price-change">Min Price Change</label>
          <input 
            type="number" 
            id="min-price-change"
            bind:value={params.min_price_change}
            on:input={(e) => handleNumberInput(e, 'min_price_change')}
            min="0.001" 
            max="0.1" 
            step="0.001"
            class="form-input"
          />
          <small>Minimum price change for signal detection (0.005 = 0.5%)</small>
        </div>
      </div>

      <!-- Risk Management Parameters -->
      <div class="form-section">
        <h4>Risk Management</h4>
        
        <div class="form-group">
          <label for="take-profit">Take Profit (%)</label>
          <input 
            type="number" 
            id="take-profit"
            bind:value={params.take_profit}
            on:input={(e) => handleNumberInput(e, 'take_profit')}
            min="0.001" 
            max="0.5" 
            step="0.001"
            class="form-input"
            class:error={validation.errors.some(e => e.includes('Take profit'))}
          />
          <small>Take profit percentage (0.02 = 2%)</small>
        </div>

        <div class="form-group">
          <label for="stop-loss">Stop Loss (%)</label>
          <input 
            type="number" 
            id="stop-loss"
            bind:value={params.stop_loss}
            on:input={(e) => handleNumberInput(e, 'stop_loss')}
            min="0.001" 
            max="0.5" 
            step="0.001"
            class="form-input"
            class:error={validation.errors.some(e => e.includes('Stop loss'))}
          />
          <small>Stop loss percentage (0.01 = 1%)</small>
        </div>

        <div class="form-group">
          <label for="initial-capital">Initial Capital</label>
          <input 
            type="number" 
            id="initial-capital"
            bind:value={params.initial_capital}
            on:input={(e) => handleNumberInput(e, 'initial_capital')}
            min="100" 
            max="1000000" 
            step="100"
            class="form-input"
            class:error={validation.errors.some(e => e.includes('Initial capital'))}
          />
          <small>Starting capital for backtesting</small>
        </div>
      </div>

      <!-- Backtest Parameters -->
      <div class="form-section">
        <h4>Backtest Settings</h4>
        
        <div class="form-group">
          <label for="max-trades">Max Trades</label>
          <input 
            type="number" 
            id="max-trades"
            bind:value={params.max_trades}
            on:input={(e) => handleIntegerInput(e, 'max_trades')}
            min="1" 
            max="1000" 
            step="1"
            class="form-input"
          />
          <small>Maximum number of trades per backtest</small>
        </div>
      </div>

      <!-- Validation Errors -->
      {#if !validation.valid}
        <div class="validation-errors">
          <h5>Validation Errors:</h5>
          <ul>
            {#each validation.errors as error}
              <li>{error}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- Form Actions -->
      <div class="form-actions">
        <button 
          type="submit" 
          class="btn btn-primary"
          disabled={!validation.valid || loading}
        >
          {loading ? 'Running...' : 'Run Backtest'}
        </button>
        <button 
          type="button" 
          class="btn btn-secondary" 
          on:click={handleReset}
          disabled={loading}
        >
          Reset to Defaults
        </button>
      </div>
    </form>
  {/if}
</div>

<style>
  .strategy-form {
    background: white;
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.3s ease;
  }

  .form-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
  }

  .form-header h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: #2c3e50;
  }

  .strategy-form-content {
    padding: 1.5rem;
  }

  .form-section {
    margin-bottom: 2rem;
  }

  .form-section:last-of-type {
    margin-bottom: 1rem;
  }

  .form-section h4 {
    margin: 0 0 1rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: #34495e;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 0.5rem;
  }

  .form-group {
    margin-bottom: 1.5rem;
  }

  .form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #2c3e50;
  }

  .form-input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.875rem;
    transition: border-color 0.2s ease;
  }

  .form-input:focus {
    outline: none;
    border-color: #3498db;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
  }

  .form-input.error {
    border-color: #e74c3c;
  }

  .form-input.error:focus {
    box-shadow: 0 0 0 2px rgba(231, 76, 60, 0.2);
  }

  .form-group small {
    display: block;
    margin-top: 0.25rem;
    color: #7f8c8d;
    font-size: 0.75rem;
  }

  .validation-errors {
    background: #fdf2f2;
    border: 1px solid #fecaca;
    border-radius: 4px;
    padding: 1rem;
    margin-bottom: 1.5rem;
  }

  .validation-errors h5 {
    margin: 0 0 0.5rem 0;
    color: #dc2626;
    font-size: 0.875rem;
    font-weight: 600;
  }

  .validation-errors ul {
    margin: 0;
    padding-left: 1.25rem;
  }

  .validation-errors li {
    color: #dc2626;
    font-size: 0.75rem;
    margin-bottom: 0.25rem;
  }

  .form-actions {
    display: flex;
    gap: 1rem;
    padding-top: 1rem;
    border-top: 1px solid #e0e0e0;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1.5rem;
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

  .btn-secondary {
    background: #95a5a6;
    color: white;
    border-color: #95a5a6;
  }

  .btn-secondary:hover:not(:disabled) {
    background: #7f8c8d;
    border-color: #7f8c8d;
  }

  /* Responsive design */
  @media (max-width: 768px) {
    .form-actions {
      flex-direction: column;
    }

    .btn {
      width: 100%;
    }
  }
</style>
