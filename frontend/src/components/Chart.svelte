<!-- Trading Chart Component with TradingView Lightweight Charts -->
<script>
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
 
  import { apiClient } from '../utils/api.js';
  import { liquidityStore, liquidityVisible, currentOrderBook } from '../stores/liquidity.js';
  import { liveCandle } from '../stores/liveCandle.js';
  import { configStore } from '../stores/config.js';
  import SymbolBadges from './SymbolBadges.svelte';
  import IntervalSwitcher from './IntervalSwitcher.svelte';
  import ChartHeader from './ChartHeader.svelte';
  let createChartFn = null;

  // Format price with spaces between thousands
  function formatPrice(price) {
    if (price === null || price === undefined) return '';
    return price.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  // Props
  export let candles = [];
  export let trades = [];
  export let symbol = 'BTC/USDT';
  export let interval = '15m';
  export let fullscreen = false;
  export let loading = false;

  // Export loading states for parent components
  export let isBackfilling = false;

  // Liquidity props
  export let liquidityFeatureAvailable = true;
  export let selectedSymbol = 'BTC/USDT';
  
  // Interval switcher props
  export let availableIntervals = [];
  export let selectedInterval = '15m';

  // Component state
  let chartContainer;
  let chart;
  let candlestickSeries;
  let tradeMarkers = [];
  let resizeObserver;
  
  // 🚀 Liquidity overlay state
  let liquidityOverlayActive = false;
  let initialHeight = 0;
  let lastWidth = 0;
  let isLoadingMore = false;
  
  // Current timeframe for liquidity scaling
  let currentInterval = interval;

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
  
  // Live candle connection state
  let liveConnected = false;
  let livePrice = null;
  let livePriceChange = null;
  
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
      reachedHistoryStart = false; // Always reset history start flag
      liquidityPriceLines = [];
      liquidityOverlayActive = false;
      
      // Reset live price
      livePrice = null;
      livePriceChange = null;
      
      // Disconnect and reset live candle WebSocket
      if (liveConnected) {
        console.log('🔌 Disconnecting live candle WebSocket for symbol change');
        liveCandle.disconnect();
        liveConnected = false;
      }
      
      // Reset all backfill-related state
      activeBackfillCount = 0;
      lastRequestedCursor = null;
      pendingBackfill = null;
      isLoadingMore = false;
      lastTriggerTime = 0;
      lastLogicalRange = null;
      initialLoadComplete = false; // Reset this too for fresh start
      
      // Clear any pending timers
      if (debounceTimer) {
        clearTimeout(debounceTimer);
        debounceTimer = null;
      }
      
      // Reset tracking variables to prevent immediate re-trigger
      prevInterval = null;
      prevSymbol = null;
      
      // Force a small delay then reinitialize
      setTimeout(() => {
        if (chartContainer) {
          initializeChart();
          
          // Set tracking variables after chart is created
          prevInterval = interval;
          prevSymbol = symbol;
          lastSymbol = symbol;
          lastInterval = interval;
          
          // Setup backfill after chart is created
          setupBackfill();
          
          // Restore liquidity overlay after chart is recreated
          if (wasLiquidityActive) {
            setTimeout(() => initializeLiquidityOverlay(), 120);
          }
          
          // Reconnect live candle WebSocket for new symbol
          setTimeout(() => {
            console.log('🔌 Reconnecting live candle WebSocket for new symbol:', symbol, interval);
            liveCandle.connect(symbol, interval, (k) => {
              try {
                console.log('🕯️ Live candle update:', k);
                
                // Update live price for legend
                const previousPrice = livePrice;
                livePrice = k.close;
                if (previousPrice !== null) {
                  livePriceChange = k.close - previousPrice;
                }
                
                const barSec = Math.floor(k.timestamp / 1000);
                const last = candles && candles[candles.length - 1];
                
                if (last && Math.floor(new Date(last.timestamp).getTime() / 1000) === barSec) {
                  // Update existing candle
                  console.log('📈 Updating existing candle');
                  last.open = k.open;
                  last.high = Math.max(last.high, k.high);
                  last.low = Math.min(last.low, k.low);
                  last.close = k.close;
                  last.volume = k.volume;
                } else if (k.isClosed) {
                  // Add new closed candle
                  console.log('🆕 Adding new closed candle');
                  candles = [...(candles || []), {
                    timestamp: k.timestamp,
                    open: k.open, high: k.high, low: k.low, close: k.close,
                    volume: k.volume,
                  }];
                } else {
                  // Add new live candle
                  console.log('🆕 Adding new live candle');
                  candles = [...(candles || []), {
                    timestamp: k.timestamp,
                    open: k.open, high: k.high, low: k.low, close: k.close,
                    volume: k.volume,
                  }];
                }
                updateChart({ preserveViewport: true });
              } catch (e) {
                console.error('Error processing live candle:', e);
              }
            });
            liveConnected = true;
          }, 200);
          
          // After reinit, trigger data reload from App.svelte
          // This will cause App.svelte to call updateChartData with new symbol/interval
          setTimeout(() => {
            // Set initialLoadComplete to true after reinitialization
            initialLoadComplete = true;
            console.log('Chart reinitialized, initialLoadComplete set to true');
            
            // Dispatch event to trigger data reload in App.svelte
            dispatch('reloadData', { symbol, interval });
          }, 100);
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

  // Map timeframe to number of levels to create visually
  function getLevelsForTimeframe(interval) {
    const map = {
      '1m': 100,
      '5m': 300,
      '15m': 1000,
      '30m': 1500,
      '1h': 2000,
      '2h': 2500,
      '4h': 3000,
      '6h': 3500,
      '8h': 4000,
      '12h': 4500,
      '1d': 5000,
      '1w': 7000,
      '1M': 10000
    };
    return map[interval] || 100;
  }

  async function loadLiquidityData() {
    if (!liquidityOverlayActive) return;
    
    try {
      // Always request maximum from API (100), will expand visually later
      const maxLevels = 100;
      const targetLevels = getLevelsForTimeframe(currentInterval);
      
      console.log(`🚀 Loading liquidity data for ${currentInterval}: requesting ${maxLevels} levels from API, will expand to ${targetLevels} visual lines, filter by ±10% price range`);
      
      // Load current order book data with maximum available limit
      await liquidityStore.loadCurrentOrderBook(symbol.replace('/', ''), maxLevels);
      
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

  // Fixed 10% range for all timeframes and all coins
  function calculateFixedLiquidityRange(currentPrice) {
    const percentage = 10.0; // ±10% от текущей цены для всех монет и таймфреймов
    const range = currentPrice * (percentage / 100);
    
    console.log(`📊 Fixed range calculation: price=${currentPrice.toFixed(4)}, ±${percentage}%, range=±${range.toFixed(4)}`);
    
    return range;
  }

  // Expand existing levels to create more visual lines by interpolation
  function expandLevels(originalLevels, targetCount, minPrice, maxPrice) {
    if (originalLevels.length === 0) return [];
    if (originalLevels.length >= targetCount) return originalLevels.slice(0, targetCount);
    
    const expanded = [...originalLevels];
    const priceStep = (maxPrice - minPrice) / targetCount;
    
    // Fill gaps with interpolated levels
    for (let i = expanded.length; i < targetCount; i++) {
      const price = minPrice + (i * priceStep);
      
      // Find nearest existing levels for volume interpolation
      const nearestLevel = originalLevels.reduce((prev, curr) => 
        Math.abs(curr.price - price) < Math.abs(prev.price - price) ? curr : prev
      );
      
      // Create synthetic level with interpolated volume (add some randomness)
      const volumeVariation = 0.5 + Math.random() * 0.5; // 50%-100% of nearest level
      expanded.push({
        price: price,
        volume: nearestLevel.volume * volumeVariation
      });
    }
    
    // Sort by price and return
    return expanded.sort((a, b) => a.price - b.price).slice(0, targetCount);
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
      
      // Get current price reference (best bid/ask midpoint)
      const currentPrice = (orderBook.best_bid + orderBook.best_ask) / 2;
      if (!currentPrice || currentPrice <= 0) return;
      
      // Calculate fixed 10% range for all timeframes and coins
      const fixedRange = calculateFixedLiquidityRange(currentPrice);
      const priceRangeLow = currentPrice - fixedRange;
      const priceRangeHigh = currentPrice + fixedRange;
      
      console.log(`🎯 Filtering liquidity for ${currentInterval}: price=${currentPrice.toFixed(4)}, ±10% range=±${fixedRange.toFixed(4)} (${priceRangeLow.toFixed(4)} - ${priceRangeHigh.toFixed(4)})`);
      
      // Filter bid levels within 10% range
      let bidLevels = (orderBook.bid_levels || [])
        .filter(level => level.price >= priceRangeLow && level.price <= currentPrice);
      
      // Filter ask levels within 10% range  
      let askLevels = (orderBook.ask_levels || [])
        .filter(level => level.price <= priceRangeHigh && level.price >= currentPrice);

      // Expand levels based on timeframe to create more visual lines
      const targetLevels = getLevelsForTimeframe(currentInterval);
      const levelsPerSide = Math.floor(targetLevels / 2); // Split target equally between bid/ask
      bidLevels = expandLevels(bidLevels, Math.min(levelsPerSide, 1000), priceRangeLow, currentPrice);
      askLevels = expandLevels(askLevels, Math.min(levelsPerSide, 1000), currentPrice, priceRangeHigh);
      
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
      
      console.log(`📊 Updated liquidity overlay (${currentInterval}): ${bidLevels.length} bids, ${askLevels.length} asks, ${liquidityPriceLines.length} lines, fixed ±10% range`);
      
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

  // Update current interval and refresh liquidity when interval changes
  $: if (interval !== currentInterval) {
    currentInterval = interval;
    if (liquidityOverlayActive) {
      console.log(`🚀 Interval changed to ${interval}, reloading liquidity data with new range`);
      loadLiquidityData(); // Reload data with new effectiveCap, don't just update overlay
    }
  }
  
  // Separate reactive block for candle updates
  $: if (chart && candles.length > 0) {
    console.log('Reactive updateChart triggered, candles:', candles.length, 'symbol:', symbol, 'activeBackfillCount:', activeBackfillCount);
    
    // Mark initial load completed once real candles are in
    if (!initialLoadComplete) initialLoadComplete = true;
    
    // Set backfill cursor if not set yet - use the OLDEST candle timestamp for backfill
    if (!backfillCursor) {
      // For backfill, we need to request data BEFORE the oldest candle
      // So we set cursor to the oldest candle timestamp
      backfillCursor = candles[0].timestamp; // candles[0] is the oldest candle
      console.log('Setting backfill cursor from reactive data (oldest candle):', backfillCursor);
      console.log('Candles range:', {
        oldest: candles[0]?.timestamp,
        newest: candles[candles.length - 1]?.timestamp,
        count: candles.length
      });
    }
    
    // If symbol/interval matches current, it's new data for current symbol
    if (symbol === lastSymbol && interval === lastInterval) {
      updateChart({ preserveViewport: true });
    } else {
      // This is new data for a different symbol - reset viewport
      updateChart({ preserveViewport: true }); // TEMPORARILY CHANGED: was false
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
            console.log('🕯️ Live candle update:', k);
            
            // Update live price for legend
            const previousPrice = livePrice;
            livePrice = k.close;
            if (previousPrice !== null) {
              livePriceChange = k.close - previousPrice;
            }
            
            const barSec = Math.floor(k.timestamp / 1000);
            const last = candles && candles[candles.length - 1];
            
            if (last && Math.floor(new Date(last.timestamp).getTime() / 1000) === barSec) {
              // Update existing candle
              console.log('📈 Updating existing candle');
              last.open = k.open;
              last.high = Math.max(last.high, k.high);
              last.low = Math.min(last.low, k.low);
              last.close = k.close;
              last.volume = k.volume;
            } else if (k.isClosed) {
              // Add new closed candle
              console.log('🆕 Adding new closed candle');
              candles = [...(candles || []), {
                timestamp: k.timestamp,
                open: k.open, high: k.high, low: k.low, close: k.close,
                volume: k.volume,
              }];
            } else {
              // Add new live candle
              console.log('🆕 Adding new live candle');
              candles = [...(candles || []), {
                timestamp: k.timestamp,
                open: k.open, high: k.high, low: k.low, close: k.close,
                volume: k.volume,
              }];
            }
            updateChart({ preserveViewport: true });
          } catch (e) {
            console.error('Error processing live candle:', e);
          }
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
        console.log('🔄 Symbol/interval changed, reconnecting live stream:', symbol, interval, 'lastSymbol:', lastSymbol, 'lastInterval:', lastInterval);
        
        // Update tracking variables first
        lastSymbol = symbol;
        lastInterval = interval;
        
        // Reset live price
        livePrice = null;
        livePriceChange = null;
        
        if (liveConnected) liveCandle.disconnect();
        liveCandle.connect(symbol, interval, (k) => {
          try {
            console.log('🕯️ Live candle update:', k);
            
            // Update live price for legend
            const previousPrice = livePrice;
            livePrice = k.close;
            if (previousPrice !== null) {
              livePriceChange = k.close - previousPrice;
            }
            
            const barSec = Math.floor(k.timestamp / 1000);
            const last = candles && candles[candles.length - 1];
            
            if (last && Math.floor(new Date(last.timestamp).getTime() / 1000) === barSec) {
              // Update existing candle
              console.log('📈 Updating existing candle');
              last.open = k.open;
              last.high = Math.max(last.high, k.high);
              last.low = Math.min(last.low, k.low);
              last.close = k.close;
              last.volume = k.volume;
            } else if (k.isClosed) {
              // Add new closed candle
              console.log('🆕 Adding new closed candle');
              candles = [...(candles || []), {
                timestamp: k.timestamp,
                open: k.open, high: k.high, low: k.low, close: k.close,
                volume: k.volume,
              }];
            } else {
              // Add new live candle
              console.log('🆕 Adding new live candle');
              candles = [...(candles || []), {
                timestamp: k.timestamp,
                open: k.open, high: k.high, low: k.low, close: k.close,
                volume: k.volume,
              }];
            }
            updateChart({ preserveViewport: true });
          } catch (e) {
            console.error('Error processing live candle:', e);
          }
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
    
    // Reset backfill state when initializing new chart
    console.log('🔄 Initializing new chart, resetting backfill state');
    reachedHistoryStart = false;
    backfillCursor = null;
    lastRequestedCursor = null;
    isLoadingMore = false;
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
        // Change mode from default 'magnet' to 'normal'.
        // Allows the crosshair to move freely without snapping to datapoints
        mode: 0, // LightweightCharts.CrosshairMode.Normal

        // Vertical crosshair line (showing Date in Label)
        vertLine: {
          width: 8,
          color: '#C3BCDB44',
          style: 0, // LightweightCharts.LineStyle.Solid
          labelBackgroundColor: '#9B7DFF',
        },

        // Horizontal crosshair line (showing Price in Label)
        horzLine: {
          color: '#9B7DFF',
          labelBackgroundColor: '#9B7DFF',
        },
      },
      rightPriceScale: {
        borderColor: '#cccccc',
        autoScale: false,
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
        // 4 decimal digits on axis
        entireTextOnly: false,
        // Enable panning on price scale
        handleScale: {
          mouseWheel: true,
          pinch: true,
          axisPressedMouseMove: true,
        },
      },
      timeScale: {
        borderColor: '#cccccc',
        timeVisible: true,
        secondsVisible: false,
        // Enable panning (drag) in any zoom level
        handleScroll: {
          mouseWheel: true,
          pressedMouseMove: true,
          horzTouchDrag: true,
          vertTouchDrag: true,
        },
        handleScale: {
          mouseWheel: true,
          pinch: true,
          axisPressedMouseMove: {
            time: true,
            price: true,
          },
        },
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

    // Subscribe to crosshair movement for legend updates
    chart.subscribeCrosshairMove((param) => {
      if (param.time && param.seriesPrices) {
        const price = param.seriesPrices.get(candlestickSeries);
        if (price !== undefined) {
          // Update live price for legend
          const previousPrice = livePrice;
          livePrice = price;
          if (previousPrice !== null) {
            livePriceChange = price - previousPrice;
          }
        }
      }
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
    
    // Set tracking variables after chart is created
    prevInterval = interval;
    prevSymbol = symbol;
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

  function updateChart({ preserveViewport = true } = {}) { // TEMPORARILY CHANGED: was false
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

    // Combine real data with placeholders for seamless chart display
    // Use the oldest real candle's open price for placeholders to maintain visual continuity
    const oldestPrice = realData.length > 0 ? realData[0].open : 0;
    const placeholderData = (leftPlaceholders || []).map(p => ({
      time: p.time,
      open: oldestPrice,
      high: oldestPrice,
      low: oldestPrice,
      close: oldestPrice,
    }));

    // Combine and sort all data (placeholders + real candles)
    const allData = [...placeholderData, ...realData].sort((a,b) => a.time - b.time);

    // Strictly increasing time with all data
    const seen = new Set();
    const chartData = allData.filter(d => {
      if (seen.has(d.time)) return false;
      seen.add(d.time);
      return true;
    });

    // Update candlestick series without changing viewport
    candlestickSeries.setData(chartData);

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
    // For 1-minute intervals, allow more requests to get more data
    const actualMaxRequests = interval === '1m' ? 5 : maxRequests;
    
    console.log('performAutomaticBackfill called with:', {
      chart: !!chart,
      initialLoadComplete,
      reachedHistoryStart,
      candlesLength: candles?.length || 0,
      backfillCursor,
      maxRequests: actualMaxRequests,
      interval
    });

    if (!chart || reachedHistoryStart) {
      console.log('performAutomaticBackfill: early return due to conditions');
      return;
    }

    console.log(`Starting automatic backfill with max ${actualMaxRequests} requests`);
    
    let failedAttempts = 0;
    const maxFailedAttempts = 3;

    for (let i = 0; i < actualMaxRequests; i++) {
      if (activeBackfillCount >= MAX_CONCURRENT_BACKFILLS || reachedHistoryStart) {
        console.log(`Automatic backfill stopped at request ${i + 1}/${actualMaxRequests}`);
        break;
      }

      const cursor = backfillCursor || (candles.length ? candles[0].timestamp : null);
      if (!cursor) break;

      // Don't duplicate request for same cursor
      if (lastRequestedCursor === cursor) break;

      try {
        console.log(`Automatic backfill request ${i + 1}/${actualMaxRequests} for cursor:`, cursor);

        activeBackfillCount++;
        isLoadingMore = true;
        lastRequestedCursor = cursor;

        // Fetch older data using only end_time (get data BEFORE a much earlier time)
        // Calculate a time that's much earlier than cursor to ensure we get historical data
        const cursorTime = new Date(cursor);
        // For 1-minute intervals, go back much further to get more data
        // Need to go back far enough to bridge the gap between backtest and historical data
        const stepBack = interval === '1m' ? 50000 : 10; // 50000 intervals for 1m (~34.7 days), 10 for others
        const olderTime = new Date(cursorTime.getTime() - (intervalToSec[interval] || 900) * 1000 * stepBack);
        
        console.log(`Requesting historical data for ${symbol} ${interval} before ${cursor}`);
        console.log(`Going back ${stepBack} intervals to ${olderTime.toISOString()}`);
        
        // Request historical data using end_time (data before this time)
        const older = await apiClient.getCandles({
          symbol,
          interval,
          end_time: olderTime.toISOString(), // Use much earlier time as end_time
          limit: 1000
        });

        if (older && older.length) {
          // Convert datetime timestamps to ISO strings for consistency
          const processedOlder = older.map(candle => ({
            ...candle,
            timestamp: typeof candle.timestamp === 'string' ? candle.timestamp : candle.timestamp.toISOString()
          }))
          .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp)); // Sort by timestamp to ensure chronological order
          
          // Debug: Log what we got from API
          console.log(`API returned ${processedOlder.length} candles:`, {
            first: processedOlder[0]?.timestamp,
            last: processedOlder[processedOlder.length - 1]?.timestamp,
            cursor: cursor
          });
          
          // Filter out any data that's not older than the cursor (API might return future data)
          const historicalData = processedOlder.filter(candle => new Date(candle.timestamp) < new Date(cursor));
          
          // Check if we have any data after filtering
          let finalData;
          if (historicalData.length === 0) {
            console.warn(`No historical data found after filtering. API returned ${processedOlder.length} candles, but none were older than cursor ${cursor}`);
            console.log(`First API candle: ${processedOlder[0]?.timestamp}, Last API candle: ${processedOlder[processedOlder.length - 1]?.timestamp}`);
            
            // Try with an even older time for all intervals
            const ts = new Date(cursor).getTime() - (intervalToSec[interval] || 900) * 1000 * 2000; // Go back 2000 intervals
            backfillCursor = new Date(ts).toISOString();
            lastRequestedCursor = backfillCursor;
            console.log(`Trying with much older time: ${backfillCursor}`);
            continue;
          } else {
            finalData = historicalData;
          }
          
          // Replace matching placeholders by time
          const olderTimes = new Set(finalData.map(c => Math.floor(new Date(c.timestamp).getTime() / 1000)));
          leftPlaceholders = leftPlaceholders.filter(p => !olderTimes.has(p.time));

          // Prepend new real candles (filter out duplicates)
          const existing = new Set((candles || []).map(c => new Date(c.timestamp).getTime()));
          const onlyNew = finalData.filter(c => !existing.has(new Date(c.timestamp).getTime()));

          // Additional check: ensure new candles are actually older than existing ones
          if (onlyNew.length && candles && candles.length > 0) {
            const oldestExisting = new Date(candles[0].timestamp).getTime();
            const newestNew = new Date(onlyNew[onlyNew.length - 1].timestamp).getTime();
            const intervalMs = (intervalToSec[interval] || 900) * 1000;
            
            // Check if there's a reasonable gap (not too large)
            const gap = oldestExisting - newestNew;
            // For 1-minute intervals, allow much larger gaps (up to 30 days)
            const maxGap = interval === '1m' ? intervalMs * 43200 : intervalMs * 50; // 50 intervals for others, 43200 for 1m (30 days)
            
            if (newestNew >= oldestExisting) {
              console.warn(`New candles are not older than existing! Newest new: ${onlyNew[onlyNew.length - 1].timestamp}, Oldest existing: ${candles[0].timestamp}`);
              // For 1-minute intervals, try with a much older time to get truly historical data
              const stepBackMultiplier = interval === '1m' ? 2000 : 20; // Go back much further for 1m
              const ts = new Date(cursor).getTime() - (intervalToSec[interval] || 900) * 1000 * stepBackMultiplier;
              backfillCursor = new Date(ts).toISOString();
              lastRequestedCursor = backfillCursor; // Set to new cursor to prevent immediate retry
              console.log(`Trying with much older time: ${backfillCursor}`);
              continue;
            } else if (gap > maxGap) {
              console.warn(`Gap too large between new and existing data! Gap: ${gap}ms (${Math.round(gap / intervalMs)} intervals), max allowed: ${maxGap}ms`);
              // Skip this batch and try with a closer time
              const ts = new Date(cursor).getTime() - (intervalToSec[interval] || 900) * 1000 * 5; // Go back only 5 intervals
              backfillCursor = new Date(ts).toISOString();
              lastRequestedCursor = backfillCursor; // Set to new cursor to prevent immediate retry
              // Don't mark as reached history start - just try with closer time
              console.log('Trying with closer time due to large gap');
              continue;
            }
          }

          if (onlyNew.length) {
            console.log(`Automatic backfill: adding ${onlyNew.length} candles from batch ${i + 1}`);
            
            // Reset failed attempts counter on successful data retrieval
            failedAttempts = 0;
            
            // Log the range of new candles
            const newCandles = onlyNew.sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
            console.log(`New candles range: ${newCandles[0].timestamp} to ${newCandles[newCandles.length - 1].timestamp}`);
            
            // Log current candles range before adding
            if (candles && candles.length > 0) {
              console.log(`Current candles range: ${candles[0].timestamp} to ${candles[candles.length - 1].timestamp}`);
            }
            
            candles = [...newCandles, ...(candles || [])].sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
            
            // Log final candles range after adding
            console.log(`Final candles range: ${candles[0].timestamp} to ${candles[candles.length - 1].timestamp}`);
            
            // Check for gaps in the data
            if (candles.length > 1) {
              const intervalMs = (intervalToSec[interval] || 900) * 1000;
              for (let i = 1; i < Math.min(candles.length, 10); i++) {
                const prevTime = new Date(candles[i-1].timestamp).getTime();
                const currTime = new Date(candles[i].timestamp).getTime();
                const expectedTime = prevTime + intervalMs;
                const gap = currTime - expectedTime;
                if (Math.abs(gap) > intervalMs * 0.1) { // 10% tolerance
                  console.warn(`Gap detected at index ${i}: expected ${new Date(expectedTime).toISOString()}, got ${candles[i].timestamp}, gap: ${gap}ms`);
                }
              }
            }
            
            // Set backfill cursor to the oldest candle (first in sorted array)
            backfillCursor = candles[0].timestamp;
            ensureLeftBuffer(500);
            updateChart({ preserveViewport: true });
          } else {
            // Nothing new, move cursor one interval back
            const ts = new Date(cursor).getTime() - (intervalToSec[interval] || 900) * 1000;
            backfillCursor = new Date(ts).toISOString();
            console.log(`No new data found, moving cursor back to: ${backfillCursor}`);
            // Set request guard to prevent immediate retry with same cursor
            lastRequestedCursor = backfillCursor;
          }
        } else {
          // No data returned - increment failed attempts
          failedAttempts++;
          console.log(`No data returned, failed attempts: ${failedAttempts}/${maxFailedAttempts}`);
          
          if (failedAttempts >= maxFailedAttempts) {
            reachedHistoryStart = true;
            console.log('Reached max failed attempts, marking as reached history start');
            isLoadingMore = false;
            activeBackfillCount = Math.max(0, activeBackfillCount - 1);
            break;
          }
          
          // Try with a much older time
          const ts = new Date(cursor).getTime() - (intervalToSec[interval] || 900) * 1000 * 100; // Go back 100 intervals
          backfillCursor = new Date(ts).toISOString();
          lastRequestedCursor = backfillCursor; // Set to new cursor to prevent immediate retry
          console.log('Trying with much older time');
          continue;
        }

        // Small delay between requests to prevent overwhelming the server
        await new Promise(resolve => setTimeout(resolve, 100));

      } catch (e) {
        console.warn(`Automatic backfill error on request ${i + 1}:`, e);
        // Reset loading state on error
        isLoadingMore = false;
        activeBackfillCount = Math.max(0, activeBackfillCount - 1);
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

    console.log('Setting up backfill for', symbol, interval, 'initialLoadComplete:', initialLoadComplete);

    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      // Guard against null/undefined range or missing properties
      if (!range || range.from == null || range.to == null) {
        console.log('Viewport change ignored:', { 
          noRange: !range, 
          invalidFrom: range?.from == null,
          invalidTo: range?.to == null
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
        // For backfill, we want to trigger when user scrolls close to the left edge of the data
        const nearLeftEdge = visibleStartIdx < (windowWidth * 0.5);
        const veryCloseLeft = visibleStartIdx < (windowWidth * 0.1);
      
      // Debug logging for edge detection
      console.log('Edge detection:', {
        visibleStartIdx,
        oldestBarIdx,
        windowWidth,
        nearLeftEdge,
        veryCloseLeft,
        distanceFromLeft: visibleStartIdx - oldestBarIdx,
        threshold: windowWidth * 0.3
      });

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
        nearRightEdge,
        initialLoadComplete,
        backfillCooldownPassed,
        timeSinceLastBackfill: currentTime - lastTriggerTime,
        shouldTrigger: initialLoadComplete && nearLeftEdge && (movedLeft || veryCloseLeft || significantMovement) && backfillCooldownPassed
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

  // Track previous values to detect changes
  let prevInterval = null;
  let prevSymbol = null;
  
  // React to interval/symbol change: reset buffers and reload
  $: if (chart && ((interval !== prevInterval) || (symbol !== prevSymbol))) {
    // Only reinitialize if values actually changed
    if (prevInterval !== null || prevSymbol !== null) {
      console.log('🔄 Interval/symbol change detected, forcing chart reinitialization');
      console.log(`Previous: interval=${prevInterval}, symbol=${prevSymbol}`);
      console.log(`Current: interval=${interval}, symbol=${symbol}`);
      
      // Force complete chart reinitialization like tab switching
      reinitializeChart();
    }
    
    // Update previous values
    prevInterval = interval;
    prevSymbol = symbol;
  }

  function toggleFullscreen() {
    fullscreen = !fullscreen;
    dispatch('toggleFullscreen', { fullscreen });
  }

  // 🚀 Liquidity toggle function
  function handleLiquidityToggle() {
    if ($liquidityVisible) {
      liquidityStore.hide();
    } else {
      liquidityStore.show();
      // Load liquidity data for current symbol
      const symbolForLiquidity = selectedSymbol && selectedSymbol !== 'undefined' ? selectedSymbol : 'BTC/USDT';
      liquidityStore.loadCurrentOrderBook(symbolForLiquidity.replace('/', ''));
    }
    
    // Dispatch event to notify parent about liquidity toggle
    dispatch('liquidityToggled', { 
      visible: !$liquidityVisible,
      symbol: selectedSymbol 
    });
  }

  // 📊 Interval switcher function
  function handleIntervalChange(newInterval) {
    selectedInterval = newInterval;
    // Dispatch event to update chart data
    dispatch('intervalChanged', { symbol: selectedSymbol, interval: selectedInterval });
  }

  // Symbol badges: available symbols from config store
  $: availableSymbols = $configStore.availableSymbols;

  // Handle symbol change from in-chart badges
  function handleSymbolChange(newSymbol) {
    selectedSymbol = newSymbol;
    configStore.setSelectedSymbol(selectedSymbol);
    dispatch('symbolChanged', { symbol: selectedSymbol, interval: selectedInterval });
  }


  // 🚀 Liquidity Overlay Functions



  // React to liquidity visibility changes
  $: if (chart) {
    if ($liquidityVisible && !liquidityOverlayActive) {
      initializeLiquidityOverlay();
    } else if (!$liquidityVisible && liquidityOverlayActive) {
      destroyLiquidityOverlay();
    }
  }

  // React to order book data changes
  $: if ($currentOrderBook && liquidityOverlayActive) {
    updateLiquidityData();
  }
</script>

<div class="chart-container">
  <SymbolBadges
    selectedSymbol={selectedSymbol}
    loading={loading}
    on:symbolSelect={(e) => handleSymbolChange(e.detail)}
  />

  
  <!-- 📊 Interval Switcher - отдельная строка -->
  <IntervalSwitcher
    {availableIntervals}
    {selectedInterval}
    on:intervalSelect={(e) => handleIntervalChange(e.detail)}
  />


  <!-- Chart header -->
  <ChartHeader
    {symbol}
    {interval}
    {livePrice}
    {livePriceChange}
    {loading}
    {isBackfilling}
  >
    {#if liquidityFeatureAvailable}
      <button 
        class="btn {$liquidityVisible ? 'btn-liquidity-active' : 'btn-liquidity'}"
        on:click={handleLiquidityToggle}
        title={$liquidityVisible ? 'Hide liquidity overlay' : 'Show liquidity overlay'}
      >
        <span class="icon">💧</span>
        {$liquidityVisible ? 'Hide Liquidity' : 'Show Liquidity'}
      </button>
    {/if}
    
    <button class="btn btn-primary" on:click={toggleFullscreen} title="Toggle Fullscreen">
      {fullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
    </button>
  </ChartHeader>

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

  <!-- Trading signals legend -->
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
    padding: 0.5rem;
    gap: 0.5rem;
    height: 100%;
    max-height: max-content;
    background: white;
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
    min-height: 500px;
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

  /* 📊 Interval switcher styles */


  /* Responsive adjustments */
</style>
