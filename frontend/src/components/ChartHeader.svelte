<script>
  export let symbol = 'BTC/USDT';
  export let interval = '15m';
  export let livePrice = null;
  export let livePriceChange = null;
  export let loading = false;
  export let isBackfilling = false;
</script>

<div class="chart-header">
  <div class="chart-title">
    <h3>
      {symbol} - {interval}
      {#if livePrice !== null}
        <span class="live-price-header">
          / ${livePrice?.toFixed(2)}
          {#if livePriceChange !== null}
            <span class="price-change {livePriceChange >= 0 ? 'positive' : 'negative'}">
              {livePriceChange >= 0 ? '+' : ''}{livePriceChange?.toFixed(2)}
            </span>
          {/if}
        </span>
      {/if}
    </h3>
    {#if loading || isBackfilling}
      <span class="loading-indicator">
        <div class="spinner"></div>
        Loading data...
      </span>
    {/if}
  </div>

  <div class="chart-controls">
    <slot />
  </div>
</div>

<style>
  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #e0e0e0;
    background: #f8f9fa;
  }

  .chart-title {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .chart-title h3 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: #2c3e50;
  }

  .live-price-header {
    color: #3498db;
    font-weight: 700;
    margin-left: 0.5rem;
  }

  .live-price-header .price-change {
    font-size: 0.875rem;
    font-weight: 600;
    margin-left: 0.25rem;
  }

  .live-price-header .price-change.positive { color: #28a745; }
  .live-price-header .price-change.negative { color: #dc3545; }

  .loading-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #3498db;
    font-size: 0.875rem;
    font-weight: 500;
    margin-left: 1rem;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid #e0e0e0;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>
