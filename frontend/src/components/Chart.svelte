<!-- Trading Chart Component with TradingView Lightweight Charts -->
<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { chartUtils } from '../utils/chart.js';
  import { apiClient } from '../utils/api.js';
  import { liquidityStore, liquidityVisible, currentOrderBook } from '../stores/liquidity.js';
  import { liveCandle } from '../stores/liveCandle.js';
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
  
  // 🚀 Liquidity overlay state
  let bidSeries = null;
  let askSeries = null;
  let liquidityOverlayActive = false;
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
  let lastLogicalRange = null;
  let prevRangeBeforeBackfill = null;

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
      const wasLiquidityActive = liquidityOverlayActive || $liquidityVisible;
      
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
      liquidityPriceLines = [];
      liquidityOverlayActive = false;
      
      // Force a small delay then reinitialize
      setTimeout(() => {
        if (chartContainer) {
          initializeChart();
          // Restore liquidity overlay after chart is recreated
          if (wasLiquidityActive) {
            setTimeout(() => initializeLiquidityOverlay(), 120);
          }
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

  // 🚀 Liquidity Overlay Functions
  let liquidityPriceLines = []; // Store price lines for cleanup
  
  function initializeLiquidityOverlay() {
    if (!chart) return;
    
    try {
      liquidityOverlayActive = true;
      console.log('✅ Liquidity overlay initialized');
      
      // Load initial liquidity data
      updateLiquidityData();
      
    } catch (error) {
      console.error('❌ Failed to initialize liquidity overlay:', error);
    }
  }

  function destroyLiquidityOverlay() {
    // Remove all price lines
    liquidityPriceLines.forEach(priceLine => {
      try {
        if (candlestickSeries && priceLine) {
          candlestickSeries.removePriceLine(priceLine);
        }
      } catch (e) {}
    });
    liquidityPriceLines = [];
    
    liquidityOverlayActive = false;
    console.log('🗑️ Liquidity overlay destroyed');
  }

  async function loadLiquidityData() {
    if (!liquidityOverlayActive || !bidSeries || !askSeries) return;
    
    try {
      // Load current order book data
      await liquidityStore.loadCurrentOrderBook(symbol.replace('/', ''));
      
      // Get the order book from store
      const orderBook = $currentOrderBook;
      if (!orderBook) return;
      
      updateLiquidityOverlay(orderBook);
      
    } catch (error) {
      console.error('❌ Failed to load liquidity data:', error);
    }
  }

  // Alias function for compatibility
  async function updateLiquidityData() {
    await loadLiquidityData();
  }

  function updateLiquidityOverlay(orderBook) {
    if (!liquidityOverlayActive || !candlestickSeries || !orderBook) return;
    
    try {
      // Clear existing price lines
      liquidityPriceLines.forEach(priceLine => {
        try {
          candlestickSeries.removePriceLine(priceLine);
        } catch (e) {}
      });
      liquidityPriceLines = [];
      
      // Process bid levels (green horizontal lines below current price)
      const cap = Math.min(50, (orderBook.bid_levels?.length || 0));
      const bidLevels = orderBook.bid_levels?.slice(0, cap) || [];
      const askCap = Math.min(50, (orderBook.ask_levels?.length || 0));
      const askLevels = orderBook.ask_levels?.slice(0, askCap) || [];
      
             // Compute max volume among shown levels for relative styling
       const maxOverlayVolume = Math.max(1, ...[...bidLevels, ...askLevels].map(l => Number(l.volume) || 0));

       // Add significant bid levels as horizontal price lines
       bidLevels.forEach((level) => {
         const vol = Number(level.volume) || 0;
         if (vol > 0) {
           const rel = Math.min(1, vol / maxOverlayVolume);
           const alpha = (0.2 + 0.8 * rel).toFixed(3); // 0.2..1.0
           const lw = Math.max(1, Math.round(1 + rel * 4)); // 1..5
           try {
             const priceLine = candlestickSeries.createPriceLine({
               price: level.price,
               color: `rgba(76, 175, 80, ${alpha})`,
               lineWidth: lw,
               lineStyle: 0,
               axisLabelVisible: false,
               title: '',
             });
             liquidityPriceLines.push(priceLine);
           } catch (e) {}
         }
       });
      
             // Add significant ask levels as horizontal price lines  
       askLevels.forEach((level) => {
         const vol = Number(level.volume) || 0;
         if (vol > 0) {
           const rel = Math.min(1, vol / maxOverlayVolume);
           const alpha = (0.2 + 0.8 * rel).toFixed(3);
           const lw = Math.max(1, Math.round(1 + rel * 4));
           try {
             const priceLine = candlestickSeries.createPriceLine({
               price: level.price,
               color: `rgba(244, 67, 54, ${alpha})`,
               lineWidth: lw,
               lineStyle: 0,
               axisLabelVisible: false,
               title: '',
             });
             liquidityPriceLines.push(priceLine);
           } catch (e) {}
         }
       });
      
      console.log(`📊 Updated liquidity overlay: ${bidLevels.length} bids, ${askLevels.length} asks, ${liquidityPriceLines.length} lines`);
      
    } catch (error) {
      console.error('❌ Failed to update liquidity overlay:', error);
    }
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

  // Reactive statement for liquidity visibility
  $: if (chart && $liquidityVisible !== liquidityOverlayActive) {
    if ($liquidityVisible && !liquidityOverlayActive) {
      console.log('🚀 Enabling liquidity overlay');
      initializeLiquidityOverlay();
    } else if (!$liquidityVisible && liquidityOverlayActive) {
      console.log('🚀 Disabling liquidity overlay');
      destroyLiquidityOverlay();
    }
  }

  // Reactive statement for liquidity data updates
  $: if (liquidityOverlayActive && $currentOrderBook) {
    updateLiquidityOverlay($currentOrderBook);
  }
  
  // Separate reactive block for candle updates
  $: if (chart && candles.length > 0) {
    console.log('Reactive updateChart triggered, candles:', candles.length, 'symbol:', symbol, 'activeBackfillCount:', activeBackfillCount);
    
    // Mark initial load completed once real candles are in
    if (!initialLoadComplete) initialLoadComplete = true;
    
    // Set backfill cursor if not set yet
    if (!backfillCursor) {
      backfillCursor = candles[0].timestamp;
      console.log('Setting backfill cursor from reactive data:', backfillCursor);
    }
    
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

      // initial load handled by App.svelte via backtest
      console.log('Chart init: waiting for App to provide candles');
      initialLoadComplete = true;

      // Connect live kline stream
      try {
        if (liveConnected) liveCandle.disconnect();
        liveCandle.connect(symbol, interval, (k) => {
          try {
            const barSec = Math.floor(k.timestamp / 1000);
            const last = candles && candles[candles.length - 1];
            if (last && Math.floor(new Date(last.timestamp).getTime() / 1000) === barSec) {
              last.open = k.open;
              last.high = Math.max(last.high, k.high);
              last.low = Math.min(last.low, k.low);
              last.close = k.close;
            } else if (k.isClosed) {
              candles = [...(candles || []), {
                timestamp: k.timestamp,
                open: k.open, high: k.high, low: k.low, close: k.close,
                volume: k.volume,
              }];
            }
            updateChart({ preserveViewport: true });
          } catch (_) {}
        });
        liveConnected = true;
      } catch (_) {}
    } catch (e) {
      console.error('Chart init failed:', e);
    }
  });

  // Reconnect live stream on symbol/interval change
  $: if (chart && (symbol !== lastSymbol || interval !== lastInterval)) {
    (async () => {
      try {
        if (liveConnected) liveCandle.disconnect();
        liveCandle.connect(symbol, interval, (k) => {
          try {
            const barSec = Math.floor(k.timestamp / 1000);
            const last = candles && candles[candles.length - 1];
            if (last && Math.floor(new Date(last.timestamp).getTime() / 1000) === barSec) {
              last.open = k.open;
              last.high = Math.max(last.high, k.high);
              last.low = Math.min(last.low, k.low);
              last.close = k.close;
            } else if (k.isClosed) {
              candles = [...(candles || []), {
                timestamp: k.timestamp,
                open: k.open, high: k.high, low: k.low, close: k.close,
                volume: k.volume,
              }];
            }
            updateChart({ preserveViewport: true });
          } catch (_) {}
        });
        liveConnected = true;
      } catch (_) {}
    })();
  }

  onDestroy(async () => {
    try { const { liveCandle } = await import('../stores/liveCandle.js'); liveCandle.disconnect(); } catch (_) {}
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
        background: { type: 'Solid', color: '#ffffff' },
        textColor: '#333',
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
        // 4 decimal digits on axis
        entireTextOnly: false,
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
      priceFormat: {
        type: 'price',
        precision: 4,
        minMove: 0.0001,
      },
    });

    // 🚀 Initialize liquidity overlay if needed
    if ($liquidityVisible) {
      initializeLiquidityOverlay();
    }

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
        // Use whitespace bars (time only), they don't affect autoscale
        needed.push({ time });
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

    // Convert candles to chart format (real data only)
    const realData = (candles || []).map(candle => ({
      time: Math.floor(new Date(candle.timestamp).getTime() / 1000),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    })).sort((a,b) => a.time - b.time);

    // Update backfill cursor to oldest candle
    backfillCursor = candles && candles.length ? candles[0].timestamp : backfillCursor;

    // Strictly increasing time with only real candles
    const seen = new Set();
    const chartData = realData.filter(d => {
      if (seen.has(d.time)) return false;
      seen.add(d.time);
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
            
            // Store current viewport before adding new candles
            const currentRange = chart.timeScale().getVisibleLogicalRange();
            
            // Add new candles and sort, then find where they were inserted
            const oldCandlesCount = (candles || []).length;
            const oldCandles = [...(candles || [])];
            candles = [...onlyNew, ...(candles || [])].sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
            const newCandlesCount = candles.length;
            const actuallyAdded = newCandlesCount - oldCandlesCount;
            
            // Find how many candles were added to the left of the current view
            let addedToLeft = 0;
            if (oldCandles.length > 0 && candles.length > 0) {
              const firstOldTime = new Date(oldCandles[0].timestamp).getTime();
              const firstNewTime = new Date(candles[0].timestamp).getTime();
              
              // If the first candle is older than the first old candle, we added to the left
              if (firstNewTime < firstOldTime) {
                addedToLeft = actuallyAdded;
              } else {
                // Check if we added to the right (which shouldn't happen in backfill)
                const lastOldTime = new Date(oldCandles[oldCandles.length - 1].timestamp).getTime();
                const lastNewTime = new Date(candles[candles.length - 1].timestamp).getTime();
                if (lastNewTime > lastOldTime) {
                  console.warn('New candles added to the right instead of left - this is not historical backfill');
                  addedToLeft = 0;
                } else {
                  // Candles were added in the middle, which is also wrong for backfill
                  console.warn('New candles added in the middle instead of left - this is not historical backfill');
                  addedToLeft = 0;
                }
              }
            }
            
            console.log(`Backfill: added ${actuallyAdded} candles (expected ${onlyNew.length}), total: ${oldCandlesCount} -> ${newCandlesCount}`);
            console.log(`Added to left: ${addedToLeft} candles`);
            
            // Verify that new candles are at the beginning
            if (candles.length > 0) {
              const oldestCandle = candles[0];
              const newestCandle = candles[candles.length - 1];
              console.log(`Candles range: ${oldestCandle.timestamp} (oldest) to ${newestCandle.timestamp} (newest)`);
              
              // Show first few and last few candles for debugging
              console.log(`First 3 candles:`, candles.slice(0, 3).map(c => c.timestamp));
              console.log(`Last 3 candles:`, candles.slice(-3).map(c => c.timestamp));
            }
            
            const prevCursor = backfillCursor;
            
            // Only update backfillCursor if we actually added candles to the left
            if (addedToLeft > 0) {
              backfillCursor = candles[0].timestamp;
              console.log(`Updated backfillCursor to: ${backfillCursor}`);
            } else {
              console.warn('Not updating backfillCursor - no candles added to the left');
            }
            
            // Reset request guard if cursor changed
            if (prevCursor !== backfillCursor) {
              lastRequestedCursor = null;
            }
            ensureLeftBuffer(500);
            
            // Update chart data first
            updateChart({ preserveViewport: true });

            // Shift viewport to the right by the number of candles added to the left
            if (currentRange && addedToLeft > 0 && chart) {
              try {
                const newRange = {
                  from: currentRange.from + addedToLeft,
                  to: currentRange.to + addedToLeft,
                };
                console.log(`Shifting viewport: ${currentRange.from}-${currentRange.to} -> ${newRange.from}-${newRange.to} (added ${addedToLeft} candles to left)`);
                chart.timeScale().setVisibleLogicalRange(newRange);
              } catch (e) {
                console.warn('Failed to shift viewport:', e);
              }
            } else if (addedToLeft === 0 && actuallyAdded > 0) {
              console.warn('Not shifting viewport - no candles added to the left, but viewport shift would be needed');
            }
          } else {
            // Nothing new, move cursor one interval back
            const ts = new Date(cursor).getTime() - (intervalToSec[interval] || 900) * 1000;
            backfillCursor = new Date(ts).toISOString();
            // Reset request guard to allow retry with shifted cursor
            lastRequestedCursor = null;
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

      // Improved trigger: operate purely in logical indexes (bars)
      const windowWidth = range.to - range.from;
      const visibleStartIdx = range.from;
      const totalBars = (candles?.length || 0) + (leftPlaceholders?.length || 0);
      const oldestBarIdx = (leftPlaceholders?.length || 0); // index of first REAL candle
      const latestBarIdx = totalBars > 0 ? totalBars - 1 : null;

      // Only trigger if user moved viewport further left than before (avoid triggering on zoom-in place)
      const movedLeft = lastLogicalRange ? range.from < lastLogicalRange.from : false;
      
      // Add minimum movement threshold to prevent micro-movements from triggering backfill
      const significantMovement = lastLogicalRange ? Math.abs(range.from - lastLogicalRange.from) > (windowWidth * 0.05) : true;

      // "Near left edge" if start is within 50% of current window width from the oldest loaded bar
      const nearLeftEdge = (visibleStartIdx - oldestBarIdx) < (windowWidth * 0.5);
      const veryCloseLeft = (visibleStartIdx - oldestBarIdx) < (windowWidth * 0.1);

      // Avoid backfill when we're near the latest bars (zooming at the right edge)
      const nearRightEdge = false; // do not block by right edge
      
      // Cooldowns
      const currentTime = Date.now();
      const timeSinceLastBackfill = currentTime - lastTriggerTime;
      const backfillCooldownPassed = timeSinceLastBackfill > 750; // 0.75s min gap

      // Save last range for next comparison
      lastLogicalRange = range;

      // Final decision (allow trigger if user is very close to left edge even without clear movedLeft)
      const shouldTriggerBackfill = initialLoadComplete && nearLeftEdge && (movedLeft || veryCloseLeft || significantMovement) && backfillCooldownPassed;

      console.log('Trigger check:', {
        rangeFrom: range.from,
        movedLeft,
        significantMovement,
        nearLeftEdge,
        nearRightEdge
      });

      if (!shouldTriggerBackfill) {
        console.log('❌ Backfill not triggered - conditions not met');
        return;
      }

      lastTriggerTime = currentTime;
      prevRangeBeforeBackfill = chart.timeScale().getVisibleLogicalRange();
      performAutomaticBackfill(1);
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

  // 🚀 Liquidity Overlay Functions
  function initializeLiquidityOverlay_OLD() {
    if (!chart || liquidityOverlayActive) return;

    try {
      // Create bid series (green, negative values for left side)
      bidSeries = chart.addHistogramSeries({
        color: 'rgba(38, 166, 154, 0.4)',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: 'liquidity', // Use separate price scale
      });

      // Create ask series (red, positive values for right side)  
      askSeries = chart.addHistogramSeries({
        color: 'rgba(239, 83, 80, 0.4)',
        priceFormat: {
          type: 'volume',
        },
        priceScaleId: 'liquidity', // Use separate price scale
      });

      // Configure liquidity price scale
      chart.priceScale('liquidity').applyOptions({
        position: 'left',
        scaleMargins: {
          top: 0.7,
          bottom: 0.1,
        },
        borderVisible: false,
      });

      liquidityOverlayActive = true;
      console.log('✅ Liquidity overlay initialized');

      // Load initial data
      updateLiquidityData();

    } catch (error) {
      console.error('❌ Failed to initialize liquidity overlay:', error);
    }
  }

  function removeLiquidityOverlay_OLD() {
    if (!chart || !liquidityOverlayActive) return;

    try {
      if (bidSeries) {
        chart.removeSeries(bidSeries);
        bidSeries = null;
      }
      if (askSeries) {
        chart.removeSeries(askSeries);
        askSeries = null;
      }

      liquidityOverlayActive = false;
      console.log('✅ Liquidity overlay removed');

    } catch (error) {
      console.error('❌ Failed to remove liquidity overlay:', error);
    }
  }

  async function updateLiquidityData_OLD() {
    if (!liquidityOverlayActive || !bidSeries || !askSeries) return;

    try {
      // Load current order book data
      const { liquidityStore } = await import('../stores/liquidity.js');
      await liquidityStore.loadCurrentOrderBook(symbol);
      
      // Get current order book data from store
      const orderBook = $currentOrderBook;
      if (!orderBook || !orderBook.bid_levels || !orderBook.ask_levels) {
        console.log('⚠️ No order book data available');
        return;
      }

      const currentTime = Math.floor(Date.now() / 1000);

      // Create single data point for each series (TradingView format)
      const bidData = [{
        time: currentTime,
        value: orderBook.total_bid_volume * 100, // Scale for visibility
        color: 'rgba(38, 166, 154, 0.6)'
      }];

      const askData = [{
        time: currentTime,
        value: orderBook.total_ask_volume * 100, // Scale for visibility  
        color: 'rgba(239, 83, 80, 0.6)'
      }];

      // Update series data
      bidSeries.setData(bidData);
      askSeries.setData(askData);

      console.log('✅ Liquidity data updated', {
        bidVolume: orderBook.total_bid_volume,
        askVolume: orderBook.total_ask_volume,
        spread: orderBook.spread,
        timestamp: currentTime
      });

    } catch (error) {
      console.error('❌ Failed to update liquidity data:', error);
    }
  }

  // React to liquidity visibility changes
  $: if (chart) {
    if ($liquidityVisible && !liquidityOverlayActive) {
      initializeLiquidityOverlay();
    } else if (!$liquidityVisible && liquidityOverlayActive) {
      removeLiquidityOverlay();
    }
  }

  // React to order book data changes
  $: if ($currentOrderBook && liquidityOverlayActive) {
    updateLiquidityData();
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
          Loading more data...
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



  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
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

  }
</style>
