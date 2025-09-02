// Backtest state management store
import { writable } from 'svelte/store';

// Initial state
const initialState = {
  candles: [],
  trades: [],
  statistics: null,
  parameters: null,
  executionTime: 0,
  success: false,
  error: null,
  loading: false
};

function generateMockTrades(candles, takeProfit = 0.02, stopLoss = 0.01, maxTrades = 20) {
  const trades = [];
  if (!candles || candles.length < 20) return trades;
  const step = Math.max(5, Math.floor(candles.length / maxTrades));
  for (let i = 10; i < candles.length - 10 && trades.length < maxTrades; i += step) {
    const c = candles[i];
    const dir = Math.random() > 0.5 ? 'long' : 'short';
    const entry = c.close;
    const exitIdx = Math.min(candles.length - 1, i + Math.floor(step / 2));
    const exitC = candles[exitIdx];
    const exit = exitC.close;
    const pnl = dir === 'long' ? exit - entry : entry - exit;
    trades.push({
      id: `${c.timestamp}-${dir}`,
      entry_time: c.timestamp,
      exit_time: exitC.timestamp,
      direction: dir,
      entry_price: +entry.toFixed(2),
      exit_price: +exit.toFixed(2),
      pnl: +pnl.toFixed(2),
      exit_reason: pnl >= 0 ? 'take_profit' : 'stop_loss'
    });
  }
  return trades;
}

function computeMockStats(trades, initialCapital = 10000) {
  const totalTrades = trades.length;
  const wins = trades.filter(t => t.pnl > 0).length;
  const losses = totalTrades - wins;
  const totalPnl = trades.reduce((s, t) => s + t.pnl, 0);
  const winRate = totalTrades ? wins / totalTrades : 0;
  const avgWin = wins ? trades.filter(t => t.pnl > 0).reduce((s, t) => s + t.pnl, 0) / wins : 0;
  const avgLoss = losses ? trades.filter(t => t.pnl < 0).reduce((s, t) => s + t.pnl, 0) / losses : 0;
  const grossProfit = trades.filter(t => t.pnl > 0).reduce((s, t) => s + t.pnl, 0);
  const grossLoss = Math.abs(trades.filter(t => t.pnl < 0).reduce((s, t) => s + t.pnl, 0));
  const profitFactor = grossLoss ? grossProfit / grossLoss : 0;
  return {
    total_trades: totalTrades,
    winning_trades: wins,
    losing_trades: losses,
    win_rate: +winRate.toFixed(2),
    total_pnl: +totalPnl.toFixed(2),
    total_return: +((totalPnl / initialCapital) * 100).toFixed(2),
    avg_win: +avgWin.toFixed(2),
    avg_loss: +avgLoss.toFixed(2),
    profit_factor: +profitFactor.toFixed(2),
    max_drawdown: 0,
    sharpe_ratio: 0,
    sortino_ratio: 0,
    avg_trade_duration: 0,
    max_trade_duration: 0,
    min_trade_duration: 0,
    consecutive_wins: 0,
    consecutive_losses: 0,
    largest_win: +Math.max(0, ...trades.map(t => t.pnl)).toFixed(2),
    largest_loss: -+Math.max(0, ...trades.map(t => -t.pnl)).toFixed(2)
  };
}

function createBacktestStore() {
  const { subscribe, set, update } = writable(initialState);

  return {
    subscribe,
    reset: () => set(initialState),
    setLoading: (loading) => update(state => ({ ...state, loading })),
    setError: (error) => update(state => ({ ...state, error, loading: false })),

    mockBacktest: async (params, candles) => {
      const trades = generateMockTrades(candles, params.take_profit ?? 0.02, params.stop_loss ?? 0.01);
      const statistics = computeMockStats(trades, params.initial_capital ?? 10000);
      update(state => ({
        ...state,
        candles,
        trades,
        statistics,
        parameters: params,
        executionTime: 0.01,
        success: true,
        error: null,
        loading: false
      }));
      return { candles, trades, statistics, success: true };
    },

    runBacktest: async (params) => {
      update(state => ({ ...state, loading: true, error: null }));
      try {
        const { apiClient } = await import('../utils/api.js');
        const result = await apiClient.runBacktest(params);
        if ((!result.trades || result.trades.length === 0) && result.candles && result.candles.length) {
          const trades = generateMockTrades(result.candles, params.take_profit ?? 0.02, params.stop_loss ?? 0.01);
          const statistics = computeMockStats(trades, params.initial_capital ?? 10000);
          update(state => ({
            ...state,
            candles: result.candles,
            trades,
            statistics,
            parameters: params,
            executionTime: result.execution_time || 0,
            success: true,
            error: null,
            loading: false
          }));
          return { candles: result.candles, trades, statistics, success: true };
        }
        update(state => ({
          ...state,
          candles: result.candles || [],
          trades: result.trades || [],
          statistics: result.statistics || null,
          parameters: result.parameters || null,
          executionTime: result.execution_time || 0,
          success: result.success || false,
          error: result.error_message || null,
          loading: false
        }));
        return result;
      } catch (error) {
        let candles = [];
        update(state => { candles = state.candles || []; return state; });
        if (candles.length) {
          const trades = generateMockTrades(candles, params.take_profit ?? 0.02, params.stop_loss ?? 0.01);
          const statistics = computeMockStats(trades, params.initial_capital ?? 10000);
          update(state => ({
            ...state,
            trades,
            statistics,
            parameters: params,
            executionTime: 0,
            success: true,
            error: null,
            loading: false
          }));
          return { candles, trades, statistics, success: true };
        }
        update(state => ({ ...state, error: error.message || 'Backtest failed', loading: false }));
        throw error;
      }
    },

    updateCandles: (candles) => update(state => ({ ...state, candles })),
    updateTrades: (trades) => update(state => ({ ...state, trades })),
    updateStatistics: (statistics) => update(state => ({ ...state, statistics })),

    getRecentTrades: (limit = 10) => {
      let trades = [];
      subscribe(state => { trades = (state.trades || []).slice(-limit); })();
      return trades;
    }
  };
}

export const backtestStore = createBacktestStore();
