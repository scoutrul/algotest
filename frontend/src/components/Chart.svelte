<!-- Trading Chart Component with TradingView Lightweight Charts -->
<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { createChart } from 'lightweight-charts';
  import { chartUtils } from '../utils/chart.js';

  // Props
  export let candles = [];
  export let trades = [];
  export let symbol = 'BTC/USDT';
  export let interval = '15m';
  export let fullscreen = false;
  export let loading = false;

  // Component state
  let chartContainer;
  let chart;
  let candlestickSeries;
  let tradeMarkers = [];
  let resizeObserver;

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // Reactive statements
  $: if (chart && candles.length > 0) {
    updateChart();
  }

  $: if (chart && trades.length > 0) {
    updateTradeMarkers();
  }

  onMount(() => {
    initializeChart();
    setupResizeObserver();
  });

  onDestroy(() => {
    if (resizeObserver) {
      resizeObserver.disconnect();
    }
    if (chart) {
      chart.remove();
    }
  });

  function initializeChart() {
    if (!chartContainer) return;

    // Create chart
    chart = createChart(chartContainer, {
      width: chartContainer.clientWidth,
      height: chartContainer.clientHeight,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#cccccc',
      },
      timeScale: {
        borderColor: '#cccccc',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Create candlestick series
    candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderDownColor: '#ef5350',
      borderUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      wickUpColor: '#26a69a',
    });

    // Handle resize
    chart.applyOptions({
      width: chartContainer.clientWidth,
      height: chartContainer.clientHeight,
    });
  }

  function setupResizeObserver() {
    if (!chartContainer) return;

    resizeObserver = new ResizeObserver(entries => {
      if (chart && entries.length > 0) {
        const { width, height } = entries[0].contentRect;
        chart.applyOptions({ width, height });
      }
    });

    resizeObserver.observe(chartContainer);
  }

  function updateChart() {
    if (!candlestickSeries || !candles.length) return;

    // Convert candles to chart format
    const chartData = candles.map(candle => ({
      time: Math.floor(new Date(candle.timestamp).getTime() / 1000),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    // Update candlestick series
    candlestickSeries.setData(chartData);

    // Fit content
    chart.timeScale().fitContent();
  }

  function updateTradeMarkers() {
    if (!candlestickSeries || !trades.length) return;

    // Clear existing markers
    candlestickSeries.setMarkers([]);

    // Create trade markers
    const markers = trades.map(trade => {
      const entryTime = Math.floor(new Date(trade.entry_time).getTime() / 1000);
      const exitTime = trade.exit_time ? Math.floor(new Date(trade.exit_time).getTime() / 1000) : null;

      const markers = [];

      // Entry marker
      markers.push({
        time: entryTime,
        position: trade.direction === 'long' ? 'belowBar' : 'aboveBar',
        color: trade.direction === 'long' ? '#26a69a' : '#ef5350',
        shape: trade.direction === 'long' ? 'arrowUp' : 'arrowDown',
        text: `${trade.direction.toUpperCase()} @ ${trade.entry_price.toFixed(2)}`,
        size: 1,
      });

      // Exit marker (if trade is closed)
      if (exitTime && trade.exit_price) {
        const exitColor = trade.pnl > 0 ? '#26a69a' : '#ef5350';
        const exitShape = trade.exit_reason === 'take_profit' ? 'circle' : 'square';
        
        markers.push({
          time: exitTime,
          position: trade.direction === 'long' ? 'aboveBar' : 'belowBar',
          color: exitColor,
          shape: exitShape,
          text: `${trade.exit_reason.toUpperCase()} @ ${trade.exit_price.toFixed(2)} (${trade.pnl > 0 ? '+' : ''}${trade.pnl.toFixed(2)})`,
          size: 1,
        });
      }

      return markers;
    }).flat();

    // Set markers
    candlestickSeries.setMarkers(markers);
  }

  function toggleFullscreen() {
    fullscreen = !fullscreen;
    dispatch('toggleFullscreen', { fullscreen });
  }

  function resetZoom() {
    if (chart) {
      chart.timeScale().fitContent();
    }
  }

  function exportChart() {
    if (chart) {
      // Simple export functionality
      const canvas = chartContainer.querySelector('canvas');
      if (canvas) {
        const link = document.createElement('a');
        link.download = `${symbol}_${interval}_chart.png`;
        link.href = canvas.toDataURL();
        link.click();
      }
    }
  }
</script>

<div class="chart-container">
  <!-- Chart header -->
  <div class="chart-header">
    <div class="chart-title">
      <h3>{symbol} - {interval}</h3>
      {#if loading}
        <span class="loading-indicator">Loading...</span>
      {/if}
    </div>
    <div class="chart-controls">
      <button class="btn btn-secondary" on:click={resetZoom} title="Reset Zoom">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        </svg>
      </button>
      <button class="btn btn-secondary" on:click={exportChart} title="Export Chart">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
        </svg>
      </button>
      <button class="btn btn-primary" on:click={toggleFullscreen} title="Toggle Fullscreen">
        {fullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
      </button>
    </div>
  </div>

  <!-- Chart wrapper -->
  <div class="chart-wrapper" bind:this={chartContainer}>
    {#if !candles.length && !loading}
      <div class="chart-placeholder">
        <div class="placeholder-content">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor" opacity="0.3">
            <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
          </svg>
          <h4>No Data Available</h4>
          <p>Run a backtest to see the chart</p>
        </div>
      </div>
    {/if}
  </div>

  <!-- Chart legend -->
  {#if trades.length > 0}
    <div class="chart-legend">
      <div class="legend-item">
        <span class="legend-color long"></span>
        <span>Long Entry</span>
      </div>
      <div class="legend-item">
        <span class="legend-color short"></span>
        <span>Short Entry</span>
      </div>
      <div class="legend-item">
        <span class="legend-color profit"></span>
        <span>Take Profit</span>
      </div>
      <div class="legend-item">
        <span class="legend-color loss"></span>
        <span>Stop Loss</span>
      </div>
    </div>
  {/if}
</div>

<style>
  .chart-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: white;
  }

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

  .loading-indicator {
    color: #3498db;
    font-size: 0.875rem;
    font-style: italic;
  }

  .chart-controls {
    display: flex;
    gap: 0.5rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.5rem 1rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background: white;
    color: #333;
    text-decoration: none;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn:hover {
    background: #f5f5f5;
    border-color: #bbb;
  }

  .btn-primary {
    background: #3498db;
    color: white;
    border-color: #3498db;
  }

  .btn-primary:hover {
    background: #2980b9;
    border-color: #2980b9;
  }

  .btn-secondary {
    background: #95a5a6;
    color: white;
    border-color: #95a5a6;
  }

  .btn-secondary:hover {
    background: #7f8c8d;
    border-color: #7f8c8d;
  }

  .chart-wrapper {
    flex: 1;
    position: relative;
    min-height: 400px;
  }

  .chart-placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #999;
  }

  .placeholder-content {
    text-align: center;
  }

  .placeholder-content h4 {
    margin: 1rem 0 0.5rem;
    color: #666;
  }

  .placeholder-content p {
    margin: 0;
    color: #999;
  }

  .chart-legend {
    display: flex;
    gap: 1rem;
    padding: 1rem;
    border-top: 1px solid #e0e0e0;
    background: #f8f9fa;
    flex-wrap: wrap;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
  }

  .legend-color {
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }

  .legend-color.long {
    background: #26a69a;
  }

  .legend-color.short {
    background: #ef5350;
  }

  .legend-color.profit {
    background: #26a69a;
    border-radius: 50%;
  }

  .legend-color.loss {
    background: #ef5350;
  }

  /* Responsive adjustments */
  @media (max-width: 768px) {
    .chart-header {
      flex-direction: column;
      gap: 1rem;
      align-items: stretch;
    }

    .chart-controls {
      justify-content: center;
    }

    .chart-legend {
      justify-content: center;
    }
  }
</style>
