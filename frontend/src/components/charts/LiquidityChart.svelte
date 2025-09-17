<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { createChart, ColorType } from 'lightweight-charts';
  import { liquidityStore } from '../../stores/liquidity.js';
  import { apiClient } from '../../utils/api.js';
  import { configStore } from '../../stores/config.js';

  const dispatch = createEventDispatcher();

  let chartContainer;
  let chart;
  let liquiditySeries;
  let isInitialized = false;
  let isDisposed = false;
  
  // Props
  export let symbol = 'BTCUSDT';
  export let height = 400;
  export let showLevels = true;
  export let opacity = 0.6;
  export let minVolume = 0.01;
  export let maxLevels = 20;

  // Local state
  let currentOrderBook = null;
  let isVisible = false;
  let loading = false;
  let error = null;

  // Timeframe from global config
  let selectedInterval = '1m';

  // Subscribe to liquidity store
  const unsubscribe = liquidityStore.subscribe(state => {
    // Widget should render whenever feature is enabled, independent of overlay toggle
    isVisible = state.enabled;
    loading = state.loading;
    error = state.error;
    currentOrderBook = state.currentOrderBook;
    
    // Update chart when data changes
    if (isInitialized && isVisible && currentOrderBook) {
      safeUpdateLiquidityVisualization();
    }
  });

  // Subscribe to global config for timeframe changes
  const unsubscribeConfig = configStore.subscribe(state => {
    const newInterval = state.selectedInterval || '1m';
    const intervalChanged = newInterval !== selectedInterval;
    selectedInterval = newInterval;
    if (intervalChanged && isInitialized && isVisible && !isDisposed) {
      // Reload with new effective range
      loadCurrentOrderBook();
    }
  });

  function ensureSeries() {
    if (!chart || isDisposed) return;
    if (!liquiditySeries) {
      try {
        liquiditySeries = chart.addHistogramSeries({
          color: '#26a69a',
          priceFormat: { type: 'volume' },
          priceLineVisible: false,
          lastValueVisible: false,
        });
      } catch (_) {}
    }
  }

  // Map timeframe to multiplier for how many levels to fetch/display
  function getLevelsMultiplier(interval) {
    const map = {
      '1m': 1.0,
      '3m': 1.5,
      '5m': 2.0,
      '15m': 4.0,
      '30m': 6.0,
      '1h': 8.0,
      '2h': 10.0,
      '4h': 12.0,
      '6h': 14.0,
      '8h': 16.0,
      '12h': 18.0,
      '1d': 20.0
    };
    return map[interval] || 1.0;
  }

  // Effective levels count based on timeframe
  $: effectiveMaxLevels = Math.max(1, Math.min(200, Math.round(maxLevels * getLevelsMultiplier(selectedInterval))));

  onMount(() => {
    if (!chartContainer) return;

    try {
      chart = createChart(chartContainer, {
        width: chartContainer.clientWidth,
        height: height,
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: '#D1D4DC',
        },
        grid: {
          vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
          horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
        },
        timeScale: {
          visible: false,
        },
        rightPriceScale: {
          borderVisible: false,
          scaleMargins: { top: 0.1, bottom: 0.1 },
        },
        leftPriceScale: { visible: false },
        crosshair: {
          mode: 1,
          vertLine: { width: 1, color: 'rgba(224, 227, 235, 0.5)', style: 0 },
          horzLine: { width: 1, color: 'rgba(224, 227, 235, 0.5)', style: 0 },
        },
      });

      ensureSeries();
      isInitialized = true;

      const resizeObserver = new ResizeObserver(entries => {
        if (entries.length > 0 && entries[0].contentRect) {
          const { width } = entries[0].contentRect;
          try { chart?.applyOptions({ width, height }); } catch (_) {}
        }
      });
      resizeObserver.observe(chartContainer);

      if (isVisible) {
        loadCurrentOrderBook();
      }

      return () => {
        try { resizeObserver.disconnect(); } catch (_) {}
        try { chart?.remove(); } catch (_) {}
        isDisposed = true;
        chart = null;
        liquiditySeries = null;
      };
    } catch (err) {
      console.error('Failed to initialize liquidity chart:', err);
      error = err.message;
    }
  });

  onDestroy(() => {
    try { unsubscribe && unsubscribe(); } catch (_) {}
    try { unsubscribeConfig && unsubscribeConfig(); } catch (_) {}
    try { chart?.remove(); } catch (_) {}
    isDisposed = true;
    chart = null;
    liquiditySeries = null;
  });

  async function loadCurrentOrderBook() {
    if (loading) return;
    
    try {
      loading = true;
      error = null;
      
      // Use the store's built-in loadCurrentOrderBook method
      const orderBook = await liquidityStore.loadCurrentOrderBook(symbol, Math.min(100, effectiveMaxLevels * 2));
      
      if (isInitialized && isVisible) {
        safeUpdateLiquidityVisualization();
      }
      
      dispatch('dataLoaded', orderBook);
    } catch (err) {
      console.error('Failed to load order book:', err);
      error = err.message;
      dispatch('error', err);
    } finally {
      loading = false;
    }
  }

  function safeUpdateLiquidityVisualization() {
    if (isDisposed) return;
    if (!chart || !isVisible) return;
    ensureSeries();
    if (!liquiditySeries) return;
    
    try {
      updateLiquidityVisualization();
    } catch (e) {
      // If series was disposed under us, recreate once and retry
      try {
        liquiditySeries = null;
        ensureSeries();
        if (liquiditySeries) updateLiquidityVisualization();
      } catch (_) {}
    }
  }

  function updateLiquidityVisualization() {
    if (!chart || !liquiditySeries || isDisposed) return;

    const bidLevels = currentOrderBook?.bid_levels
      ?.filter(level => level.volume >= minVolume)
      ?.slice(0, effectiveMaxLevels) || [];
    const askLevels = currentOrderBook?.ask_levels
      ?.filter(level => level.volume >= minVolume)
      ?.slice(0, effectiveMaxLevels) || [];

    const histogramData = [];
    if (bidLevels.length > 0) {
      const maxBid = Math.max(...bidLevels.map(l => l.volume));
      bidLevels.forEach((level, index) => {
        histogramData.push({
          time: index,
          value: -level.volume,
          color: `rgba(76, 175, 80, ${opacity * (maxBid ? level.volume / maxBid : 0)})`,
        });
      });
    }
    if (askLevels.length > 0) {
      const maxAsk = Math.max(...askLevels.map(l => l.volume));
      askLevels.forEach((level, index) => {
        histogramData.push({
          time: (bidLevels.length + index),
          value: level.volume,
          color: `rgba(244, 67, 54, ${opacity * (maxAsk ? level.volume / maxAsk : 0)})`,
        });
      });
    }

    try {
      liquiditySeries.setData(histogramData);
      chart.timeScale().fitContent();
    } catch (_) {
      // swallow if chart/series disposed during HMR/toggle
    }
  }

  // Reactivity
  $: if (symbol && isInitialized && !isDisposed) {
    loadCurrentOrderBook();
  }

  $: if (isInitialized && isVisible && !isDisposed) {
    safeUpdateLiquidityVisualization();
  }

  // Public methods
  export function refresh() { if (!isDisposed) loadCurrentOrderBook(); }
  export function clear() {
    if (!isDisposed && liquiditySeries) {
      try { liquiditySeries.setData([]); } catch (_) {}
    }
  }

  // Ensure the widget becomes visible by default when mounted
  $: if (isInitialized && !isDisposed && chart && !error) {
    try { ensureSeries(); } catch (_) {}
  }
</script>

<div class="liquidity-chart-container" class:visible={isVisible}>
  {#if isVisible}
    <div class="chart-header">
      <h4 class="chart-title">💧 Liquidity Depth - {symbol}</h4>
      <div class="chart-controls">
        <button 
          class="refresh-btn"
          on:click={refresh}
          disabled={loading}
          title="Refresh liquidity data"
        >
          {loading ? '🔄' : '↻'}
        </button>
      </div>
    </div>
    
    <div 
      bind:this={chartContainer} 
      class="chart-container"
      style="height: {height}px;"
    ></div>
    
    {#if error}
      <div class="error-message">
        ⚠️ {error}
      </div>
    {/if}
    
    {#if currentOrderBook}
      <div class="liquidity-info">
        <div class="info-row">
          <span class="label">Spread:</span>
          <span class="value">{currentOrderBook.spread?.toFixed(6)} ({currentOrderBook.spread_percentage?.toFixed(4)}%)</span>
        </div>
        <div class="info-row">
          <span class="label">Best Bid:</span>
          <span class="value bid">{currentOrderBook.best_bid?.toFixed(2)}</span>
        </div>
        <div class="info-row">
          <span class="label">Best Ask:</span>
          <span class="value ask">{currentOrderBook.best_ask?.toFixed(2)}</span>
        </div>
        <div class="info-row">
          <span class="label">Total Volume:</span>
          <span class="value">{((currentOrderBook.total_bid_volume || 0) + (currentOrderBook.total_ask_volume || 0))?.toFixed(4)}</span>
        </div>
      </div>
    {/if}
  {/if}
</div>

<style>
  .liquidity-chart-container {
    background: rgba(30, 30, 30, 0.9);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    overflow: hidden;
    transition: all 0.3s ease;
  }

  .liquidity-chart-container.visible {
    box-shadow: 0 4px 20px rgba(0, 150, 136, 0.2);
  }

  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: rgba(0, 0, 0, 0.3);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  .chart-title {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: #00bcd4;
  }

  .chart-controls { display: flex; gap: 8px; }

  .refresh-btn {
    background: rgba(0, 188, 212, 0.2);
    border: 1px solid rgba(0, 188, 212, 0.3);
    color: #00bcd4;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s ease;
  }
  .refresh-btn:hover:not(:disabled) { background: rgba(0, 188, 212, 0.3); transform: scale(1.05); }
  .refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .chart-container { position: relative; background: transparent; }

  .error-message {
    padding: 12px;
    background: rgba(244, 67, 54, 0.1);
    border: 1px solid rgba(244, 67, 54, 0.3);
    color: #f44336;
    font-size: 12px;
    text-align: center;
  }

  .liquidity-info { padding: 12px 16px; background: rgba(0, 0, 0, 0.2); border-top: 1px solid rgba(255, 255, 255, 0.1); }
  .info-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 12px; }
  .info-row:last-child { margin-bottom: 0; }
  .label { color: #bbb; font-weight: 500; }
  .value { color: #fff; font-family: 'Courier New', monospace; }
  .value.bid { color: #4caf50; }
  .value.ask { color: #f44336; }
</style>
