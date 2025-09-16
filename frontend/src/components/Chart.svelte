<!-- Trading Chart Component with TradingView Lightweight Charts -->
<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { chartUtils } from '../utils/chart.js';
  import { apiClient } from '../utils/api.js';
  let createChartFn = null;

  // Props
  export let candles = [];
  export let trades = [];
  export let symbol = 'BTC/USDT';
  export let interval = '15m';
  export let fullscreen = false;
  export let loading = false;

  // Export loading states for parent components
  export let isBackfilling = false;

  // Component state
  let chartContainer;
  let chart;
  let candlestickSeries;
  let tradeMarkers = [];
  let resizeObserver;
  let initialHeight = 0;
  let lastWidth = 0;
  let isLoadingMore = false;

  // Sync internal loading state with exported prop
  $: isBackfilling = isLoadingMore;
  let backfillCursor = null;
  let reachedHistoryStart = false;
  let lastRequestedCursor = null;
  let pendingBackfill = null;
  let debounceTimer = null;
  let leftPlaceholders = [];

  // Limit concurrent backfill requests to prevent cascade
  let activeBackfillCount = 0;
  const MAX_CONCURRENT_BACKFILLS = 2;
  let initialLoadComplete = false;
  let lastTriggerTime = 0;
  const intervalToSec = {
    '1m': 60, '15m': 900, '1h': 3600, '4h': 14400, '12h': 43200,
    '1d': 86400, '1w': 604800, '1M': 2592000
  };

  // Event dispatcher
  const dispatch = createEventDispatcher();

  // Track symbol/interval changes to reset viewport
  let lastSymbol = symbol;
  let lastInterval = interval;
  
  // Function to completely reinitialize chart (like tab switching does)
  function reinitializeChart() {
    console.log('🔄 Completely reinitializing chart for symbol change');
    
    try {
      // Destroy current chart completely
      if (chart) {
        chart.remove();
        chart = null;
      }
      
      // Reset all state variables
      candlestickSeries = null;
      leftPlaceholders = [];
      backfillCursor = null;
      reachedHistoryStart = false;
      
      // Force a small delay then reinitialize
      setTimeout(() => {
        if (chartContainer) {
          initializeChart();
          // After reinit, update with current data if available
          if (candles.length > 0) {
            setTimeout(() => {
              updateChart({ preserveViewport: false });
            }, 100);
          }
        }
      }, 50);
      
    } catch (error) {
      console.warn('Failed to reinitialize chart:', error);
    }
  }

  // Legacy function kept for compatibility
  function forcePriceScaleReset() {
    // Just call the full reinitialize now
    reinitializeChart();
  }
  
  // Reactive statements for symbol/interval changes
  $: if (chart) {
    // Check if symbol or interval changed - completely reinitialize if so
    const symbolChanged = symbol !== lastSymbol;
    const intervalChanged = interval !== lastInterval;
    
    if (symbolChanged || intervalChanged) {
      lastSymbol = symbol;
      lastInterval = interval;
      console.log(`Symbol/interval changed: ${symbol} ${interval}, completely reinitializing chart`);
      
      // Completely reinitialize chart (like tab switching does)
      reinitializeChart();
    }
  }
  
  // Separate reactive block for candle updates
  $: if (chart && candles.length > 0) {
    console.log('Reactive updateChart triggered, candles:', candles.length, 'symbol:', symbol, 'activeBackfillCount:', activeBackfillCount);
    
    // If symbol/interval matches current, it's new data for current symbol
    if (symbol === lastSymbol && interval === lastInterval) {
      updateChart({ preserveViewport: true });
    } else {
      // This is new data for a different symbol - reset viewport
      updateChart({ preserveViewport: false });
    }
  }

  $: if (chart && trades.length > 0) {
    updateTradeMarkers();
  }

  onMount(async () => {
    try {
      if (typeof window === 'undefined') return;
      const mod = await import('lightweight-charts');
      createChartFn = mod.createChart;
      initializeChart();
      setupResizeObserver();
      setupBackfill();
      // initial load if no candles yet
      console.log('Chart init: checking candles', {
        candlesExists: !!candles,
        candlesLength: candles?.length || 0
      });

      if (!candles || candles.length === 0) {
        const nowBatch = await apiClient.getCandles({ symbol, interval, limit: 1000 });
        if (nowBatch && nowBatch.length) {
          candles = nowBatch;
          backfillCursor = candles[0].timestamp;
          ensureLeftBuffer(500);
          updateChart({ preserveViewport: false });
          initialLoadComplete = true;
          console.log('Initial load complete, starting automatic backfill');

          // Start automatic backfill with 1-2 historical batches
          console.log('Setting timeout for automatic backfill...');
          setTimeout(() => {
            console.log('Timeout triggered, calling performAutomaticBackfill...');
            performAutomaticBackfill(2);
          }, 100);
        }
      } else {
        initialLoadComplete = true;
        console.log('Data already exists, setting timeout for automatic backfill...');
        // If data already exists, still do automatic backfill
        setTimeout(() => {
          console.log('Timeout triggered for existing data, calling performAutomaticBackfill...');
          performAutomaticBackfill(2);
        }, 100);
      }
    } catch (e) {
      console.error('Chart init failed:', e);
    }
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

    if (!createChartFn) return;
    // Create chart
    chart = createChartFn(chartContainer, {
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
        autoScale: true,
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
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
    // Lock initial height to prevent infinite growth on reflows
    if (!initialHeight) initialHeight = chartContainer.clientHeight || 400;
    chart.applyOptions({
      width: chartContainer.clientWidth || 800,
      height: initialHeight,
    });
  }

  function setupResizeObserver() {
    if (!chartContainer) return;

    resizeObserver = new ResizeObserver(entries => {
      if (!chart || entries.length === 0) return;
      const { width, height } = entries[0].contentRect;
      if (width === lastWidth) return; // avoid vertical growth loops
      lastWidth = width;
      chart.applyOptions({ width, height: initialHeight || height });
    });

    resizeObserver.observe(chartContainer);
  }

  function ensureLeftBuffer(count = 500) {
    if (!candles || candles.length === 0) return;
    const sec = intervalToSec[interval] || 900;
    const oldest = Math.floor(new Date(candles[0].timestamp).getTime() / 1000);

    // Get the oldest candle to base placeholder prices on (for seamless connection)
    const oldestCandle = candles[0];
    if (!oldestCandle) return;

    // Use the open price of the oldest candle for flat placeholders
    const flatPrice = oldestCandle.open;

    // Get existing times from both real candles and placeholders to avoid overlaps
    const existingTimes = new Set();
    (candles || []).forEach(candle => {
      existingTimes.add(Math.floor(new Date(candle.timestamp).getTime() / 1000));
    });
    leftPlaceholders.forEach(p => {
      existingTimes.add(p.time);
    });

    const needed = [];
    for (let i = 1; i <= count; i++) {
      const time = oldest - i * sec;
      if (!existingTimes.has(time)) {
        // Create flat candles with the same price for all OHLC values
        needed.push({
          time,
          open: flatPrice,
          high: flatPrice,
          low: flatPrice,
          close: flatPrice
        });
      }
    }

    // Add new placeholders
    leftPlaceholders.push(...needed);
    leftPlaceholders.sort((a,b) => a.time - b.time);

    // cap buffer length
    if (leftPlaceholders.length > 5000) {
      leftPlaceholders = leftPlaceholders.slice(-5000);
    }
  }

  function updateChart({ preserveViewport = false } = {}) {
    if (!candlestickSeries) return;

    // Convert candles to chart format
    const realData = (candles || []).map(candle => ({
      time: Math.floor(new Date(candle.timestamp).getTime() / 1000),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    })).sort((a,b) => a.time - b.time);

    // Update backfill cursor to oldest candle
    backfillCursor = candles && candles.length ? candles[0].timestamp : backfillCursor;

    // Create loading placeholders with special styling during backfill
    const loadingPlaceholders = leftPlaceholders.map(placeholder => ({
      ...placeholder,
      // Add loading indicator styling during backfill
      ...(isLoadingMore ? {
        loading: true
      } : {})
    }));

    // Compose placeholders + real data, sort and deduplicate
    const combinedData = [...loadingPlaceholders, ...realData];

    // Sort by time ascending
    combinedData.sort((a, b) => a.time - b.time);

    // Remove duplicates by time (keep the one with more data - real data preferred)
    const seenTimes = new Set();
    const chartData = combinedData.filter(item => {
      if (seenTimes.has(item.time)) {
        return false;
      }
      seenTimes.add(item.time);
      return true;
    });

    // Update candlestick series without changing viewport
    candlestickSeries.setData(chartData);

    if (!preserveViewport && realData.length) {
      // Reset both time and price scales when viewport needs reset
      chart.timeScale().fitContent();
      
      // Force price scale to fit the new data range
      try {
        // Get price scale and reset its auto-scaling
        const priceScale = chart.priceScale('right');
        if (priceScale) {
          // Force recalculation of price range
          priceScale.applyOptions({
            autoScale: true,
            scaleMargins: {
              top: 0.1,    // 10% margin at top
              bottom: 0.1  // 10% margin at bottom
            }
          });
        }
        
        // Additional method: use series price range if available
        if (candlestickSeries && realData.length > 0) {
          // Calculate min/max from actual data
          const prices = realData.flatMap(d => [d.high, d.low]);
          const minPrice = Math.min(...prices);
          const maxPrice = Math.max(...prices);
          
          console.log(`Price range for ${symbol}: ${minPrice.toFixed(2)} - ${maxPrice.toFixed(2)}`);
          
          // Force visible range to match data range with margins
          const margin = (maxPrice - minPrice) * 0.1; // 10% margin
          try {
            // Force price scale to auto-fit the new range
            const priceScale = chart.priceScale('right');
            if (priceScale) {
              // Reset price scale options to force recalculation
              priceScale.applyOptions({
                autoScale: true,
                scaleMargins: {
                  top: 0.1,
                  bottom: 0.1,
                },
              });
            }
            // Force time scale to fit content which triggers price scale recalculation
            chart.timeScale().fitContent();
          } catch (e) {
            console.log('Using fallback price scale method:', e);
            chart.timeScale().fitContent();
          }
        }
      } catch (error) {
        console.warn('Failed to reset price scale:', error);
      }
    }
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

  async function performAutomaticBackfill(maxRequests = 2) {
    console.log('performAutomaticBackfill called with:', {
      chart: !!chart,
      initialLoadComplete,
      reachedHistoryStart,
      candlesLength: candles?.length || 0,
      backfillCursor,
      maxRequests
    });

    if (!chart || reachedHistoryStart) {
      console.log('performAutomaticBackfill: early return due to conditions');
      return;
    }

    console.log(`Starting automatic backfill with max ${maxRequests} requests`);

    for (let i = 0; i < maxRequests; i++) {
      if (activeBackfillCount >= MAX_CONCURRENT_BACKFILLS || reachedHistoryStart) {
        console.log(`Automatic backfill stopped at request ${i + 1}/${maxRequests}`);
        break;
      }

      const cursor = backfillCursor || (candles.length ? candles[0].timestamp : null);
      if (!cursor) break;

      // Don't duplicate request for same cursor
      if (lastRequestedCursor === cursor) break;

      try {
        console.log(`Automatic backfill request ${i + 1}/${maxRequests} for cursor:`, cursor);

        activeBackfillCount++;
        isLoadingMore = true;
        lastRequestedCursor = cursor;

        // Fetch older data using end_time (get data BEFORE cursor)
        const older = await apiClient.getCandles({
          symbol,
          interval,
          end_time: cursor,
          limit: 1000
        });

        if (older && older.length) {
          // Replace matching placeholders by time
          const olderTimes = new Set(older.map(c => Math.floor(new Date(c.timestamp).getTime() / 1000)));
          leftPlaceholders = leftPlaceholders.filter(p => !olderTimes.has(p.time));

          // Prepend new real candles (filter out duplicates)
          const existing = new Set((candles || []).map(c => new Date(c.timestamp).getTime()));
          const onlyNew = older.filter(c => !existing.has(new Date(c.timestamp).getTime()));

          if (onlyNew.length) {
            console.log(`Automatic backfill: adding ${onlyNew.length} candles from batch ${i + 1}`);
            candles = [...onlyNew, ...(candles || [])].sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
            backfillCursor = candles[0].timestamp;
            ensureLeftBuffer(500);
            updateChart({ preserveViewport: true });
          } else {
            // Nothing new, move cursor one interval back
            const ts = new Date(cursor).getTime() - (intervalToSec[interval] || 900) * 1000;
            backfillCursor = new Date(ts).toISOString();
          }
        } else {
          reachedHistoryStart = true;
          console.log('Automatic backfill: reached history start');
          break;
        }

        // Small delay between requests to prevent overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 100));

      } catch (e) {
        console.warn(`Automatic backfill error on request ${i + 1}:`, e);
        break;
      } finally {
        isLoadingMore = false;
        activeBackfillCount = Math.max(0, activeBackfillCount - 1);
      }
    }

    console.log(`Automatic backfill completed. Total candles: ${candles.length}`);
  }

  function setupBackfill() {
    if (!chart) return;

    console.log('Setting up backfill for', symbol, interval);

    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      // Guard against null/undefined range or missing properties
      if (!range || range.from == null || range.to == null || reachedHistoryStart) {
        console.log('Viewport change ignored:', { 
          noRange: !range, 
          invalidFrom: range?.from == null,
          invalidTo: range?.to == null,
          reachedHistoryStart 
        });
        return;
      }

      console.log('📊 Viewport changed:', {
        from: range.from,
        to: range.to,
        reachedHistoryStart,
        initialLoadComplete,
        triggerActivated: false
      });

      // Debug logging
      console.log('Backfill check:', {
        from: range.from,
        to: range.to,
        windowWidth: range.to - range.from,
        candlesCount: candles?.length || 0,
        isLoading: isLoadingMore
      });

      // Improved trigger: load when less than 20% of screen width remains on the left
      const windowWidth = range.to - range.from;
      const triggerThreshold = range.from + (windowWidth * 0.20); // Trigger when < 20% remains

      // Alternative trigger: check if we're close to placeholders (more reliable)
      const visibleStartTime = Math.floor(range.from);
      const oldestCandleTime = candles?.length ? Math.floor(new Date(candles[0].timestamp).getTime() / 1000) : null;
      const hasPlaceholdersNearby = oldestCandleTime && (visibleStartTime - oldestCandleTime) < 50; // Within 50 seconds of oldest data

      // Debug: show if we actually have placeholders
      const hasVisiblePlaceholders = leftPlaceholders.some(p => p.time >= visibleStartTime && p.time <= range.to);

      console.log('Trigger check:', {
        rangeFrom: range.from,
        triggerThreshold,
        shouldTrigger: range.from < triggerThreshold,
        visibleStartTime,
        oldestCandleTime,
        hasPlaceholdersNearby,
        hasVisiblePlaceholders,
        placeholdersCount: leftPlaceholders.length,
        triggerPercent: '20%'
      });

      // Simple trigger: just check if we're close to the left edge
      const shouldTriggerBackfill = range.from < triggerThreshold;

      console.log('Simple trigger decision:', {
        shouldTriggerBackfill,
        rangeFrom: range.from,
        triggerThreshold,
        difference: triggerThreshold - range.from, // How close we are to trigger
        windowWidth: range.to - range.from,
        remainingPercent: ((triggerThreshold - range.from) / (range.to - range.from)) * 100,
        hasVisiblePlaceholders,
        distanceFromOldest: oldestCandleTime ? oldestCandleTime - visibleStartTime : null
      });

      if (!shouldTriggerBackfill) {
        console.log('❌ Backfill not triggered - not close enough to edge');
        return;
      }

      // Prevent too many concurrent backfill requests
      if (activeBackfillCount >= MAX_CONCURRENT_BACKFILLS) {
        console.log('❌ Backfill limit reached, skipping request. Active:', activeBackfillCount, 'Max:', MAX_CONCURRENT_BACKFILLS);
        return;
      }

      // Prevent overlapping with existing requests
      if (isLoadingMore || pendingBackfill) {
        console.log('❌ Backfill already in progress, skipping request');
        return;
      }

      console.log('✅ All checks passed, proceeding with backfill request');

      const now = Date.now();
      const timeSinceLastTrigger = now - lastTriggerTime;

      console.log('🎯 TRIGGER ACTIVATED! Starting backfill request...', {
        timeSinceLastTrigger,
        lastTriggerTime: new Date(lastTriggerTime).toLocaleTimeString()
      });

      // Prevent triggers too close together (minimum 500ms between triggers)
      if (timeSinceLastTrigger < 500) {
        console.log('⏳ Trigger too soon, skipping...');
        return;
      }

      lastTriggerTime = now;

      // Execute backfill immediately without debounce for testing
      console.log('🚀 EXECUTING BACKFILL IMMEDIATELY...');
      
      (async () => {
        console.log('⏰ Debounce timer fired, executing backfill...');
        console.log('Backfill conditions:', {
          isLoadingMore,
          pendingBackfill: !!pendingBackfill,
          activeBackfillCount,
          candlesLength: candles?.length || 0,
          MAX_CONCURRENT_BACKFILLS
        });

        try {
          if (isLoadingMore || pendingBackfill) {
            console.log('❌ Skipping backfill due to active request');
            console.log('Resetting debounce timer for next attempt...');
            // Reset timer to try again later
            debounceTimer = setTimeout(() => {
              console.log('🔄 Retrying backfill after skip...');
              // Recursive call to retry
              if (!isLoadingMore && !pendingBackfill) {
                performAutomaticBackfill(1);
              }
            }, 1000);
            return;
          }
          console.log('✅ Backfill conditions passed, proceeding...');

          const cursor = backfillCursor || (candles.length ? candles[0].timestamp : null);
          console.log('Cursor check:', {
            cursor,
            backfillCursor,
            oldestCandleTimestamp: candles?.[0]?.timestamp,
            lastRequestedCursor
          });

          if (!cursor) {
            console.log('No cursor available, skipping backfill');
            return;
          }

          // don't duplicate request for same cursor
          if (lastRequestedCursor === cursor) {
            console.log('Duplicate cursor detected, skipping backfill');
            return;
          }

          console.log('🚀 About to start backfill request...');
          isLoadingMore = true;
          lastRequestedCursor = cursor;
          activeBackfillCount++;
          console.log(`✅ Starting backfill request ${activeBackfillCount}/${MAX_CONCURRENT_BACKFILLS} for cursor:`, cursor);

          // before requesting, ensure we already have a left buffer so viewport doesn't move
          ensureLeftBuffer(500);
          updateChart({ preserveViewport: true });

          // fetch older data using end_time (get data BEFORE cursor)
          console.log('🚀 Making backfill API request:', {
            symbol,
            interval,
            end_time: cursor,
            limit: 1000
          });

          pendingBackfill = apiClient.getCandles({
            symbol,
            interval,
            end_time: cursor,
            limit: 1000
          });

          console.log('📡 API call initiated, waiting for response...');

          const older = await pendingBackfill;
          pendingBackfill = null;

          console.log('📥 API response received:', {
            received: older?.length || 0,
            cursor: cursor,
            oldestCurrent: candles?.[0]?.timestamp,
            newestCurrent: candles?.[candles.length - 1]?.timestamp
          });

          if (older && older.length) {
            // replace matching placeholders by time
            const olderTimes = new Set(older.map(c => Math.floor(new Date(c.timestamp).getTime() / 1000)));
            leftPlaceholders = leftPlaceholders.filter(p => !olderTimes.has(p.time));

            // prepend new real candles (filter out duplicates)
            const existing = new Set((candles || []).map(c => new Date(c.timestamp).getTime()));
            const onlyNew = older.filter(c => !existing.has(new Date(c.timestamp).getTime()));

            if (onlyNew.length) {
              candles = [...onlyNew, ...(candles || [])].sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
              backfillCursor = candles[0].timestamp;
              updateChart({ preserveViewport: true });
            } else {
              // nothing new, move cursor one interval back for next attempt
              const ts = new Date(cursor).getTime() - (intervalToSec[interval] || 900) * 1000;
              backfillCursor = new Date(ts).toISOString();
            }
          } else {
            reachedHistoryStart = true;
          }
        } catch (e) {
          console.warn('Backfill error:', e);
        } finally {
          console.log('🏁 Backfill request finishing, resetting flags...');
          isLoadingMore = false;
          activeBackfillCount = Math.max(0, activeBackfillCount - 1);
          console.log(`✅ Backfill request completed. Active requests: ${activeBackfillCount}/${MAX_CONCURRENT_BACKFILLS}`);
        }
      })();
    });
  }

  // React to interval change: reset buffers and reload
  $: if (chart && interval) {
    // whenever interval changes externally, reload data
    // (simple heuristic: if candles exist and their spacing mismatches selected interval)
    activeBackfillCount = 0; // Reset backfill counter on interval change
    reachedHistoryStart = false;
    lastRequestedCursor = null;
    backfillCursor = null; // Reset backfill cursor too
    pendingBackfill = null;
    initialLoadComplete = false;
    lastTriggerTime = 0; // Reset trigger timing
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
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
        <span class="loading-indicator">
          <div class="spinner"></div>
          Loading chart data...
        </span>
      {:else if isBackfilling}
        <span class="loading-indicator backfilling">
          <div class="spinner"></div>
          Loading historical data...
        </span>
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
    {#if !candles.length && loading}
      <div class="chart-loading-overlay">
        <div class="loading-content">
          <div class="spinner-large"></div>
          <h4>Loading Chart Data</h4>
          <p>Fetching latest candles from exchange...</p>
        </div>
      </div>
    {:else if !candles.length && !loading}
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

    <!-- Backfilling indicator overlay -->
    {#if isBackfilling && candles.length > 0}
      <div class="backfill-indicator">
        <div class="backfill-content">
          <div class="spinner-small"></div>
          <span>Loading more historical data...</span>
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
    max-height: 100vh;
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
    height: 100%;
    overflow: hidden;
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

  /* Loading indicators */
  .loading-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #3498db;
    font-size: 0.875rem;
    font-weight: 500;
    margin-left: 1rem;
  }

  .loading-indicator.backfilling {
    color: #f39c12;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid #e0e0e0;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  /* Chart loading overlay */
  .chart-loading-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(255, 255, 255, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }

  .loading-content {
    text-align: center;
    color: #666;
  }

  .loading-content h4 {
    margin: 1rem 0 0.5rem;
    color: #333;
    font-weight: 600;
  }

  .loading-content p {
    margin: 0;
    color: #999;
    font-size: 0.875rem;
  }

  .spinner-large {
    width: 48px;
    height: 48px;
    border: 4px solid #e0e0e0;
    border-top: 4px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }

  /* Backfilling indicator */
  .backfill-indicator {
    position: absolute;
    top: 10px;
    right: 10px;
    background: rgba(255, 255, 255, 0.95);
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 0.5rem 1rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    z-index: 20;
    backdrop-filter: blur(4px);
  }

  .backfill-content {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #f39c12;
    font-weight: 500;
  }

  .spinner-small {
    width: 14px;
    height: 14px;
    border: 2px solid #e0e0e0;
    border-top: 2px solid #f39c12;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  /* Placeholder candles styling */
  .placeholder-candle {
    opacity: 0.6;
    border-style: dashed !important;
    border-width: 1px !important;
  }

  .placeholder-candle.loading {
    opacity: 0.4;
    animation: placeholder-pulse 2s ease-in-out infinite;
  }

  @keyframes placeholder-pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.6; }
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

    .backfill-indicator {
      top: 5px;
      right: 5px;
      padding: 0.25rem 0.5rem;
    }

    .backfill-content {
      font-size: 0.75rem;
    }
  }
</style>
