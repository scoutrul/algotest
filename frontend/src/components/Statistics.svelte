<!-- Statistics Component for Backtest Results -->
<script>
  import { formatTime, formatPrice, formatPercentage, getValueColor } from '../utils/chart.js';

  // Props
  export let statistics = null;
  export let trades = [];
  export let collapsed = false;
  export let loading = false;

  // Reactive statements
  $: recentTrades = trades.slice(-10).reverse();
  $: hasData = statistics && trades.length > 0;


  function getStatValue(stat, formatter = (v) => v) {
    if (!statistics || statistics[stat] === undefined) return 'N/A';
    return formatter(statistics[stat]);
  }

  function getStatColor(stat, neutral = 0) {
    if (!statistics || statistics[stat] === undefined) return '#95a5a6';
    return getValueColor(statistics[stat], neutral);
  }
</script>

<div class="statistics-panel">
  <!-- Statistics header removed - now handled by App.svelte -->

  {#if !collapsed}
    {#if loading}
      <div class="loading-state">
        <div class="loading-spinner"></div>
        <p>Calculating statistics...</p>
      </div>
    {:else if !hasData}
      <div class="no-data">
        <div class="no-data-content">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="currentColor" opacity="0.3">
            <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
          </svg>
          <h4>No Results</h4>
          <p>Run a backtest to see statistics</p>
        </div>
      </div>
    {:else}
      <!-- Statistics grid -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{getStatValue('total_trades')}</div>
          <div class="stat-label">Total Trades</div>
        </div>

        <div class="stat-card">
          <div class="stat-value" style="color: {getStatColor('win_rate', 0.5)}">
            {getStatValue('win_rate', formatPercentage)}
          </div>
          <div class="stat-label">Win Rate</div>
        </div>

        <div class="stat-card">
          <div class="stat-value" style="color: {getStatColor('total_pnl')}">
            {getStatValue('total_pnl', (v) => (v > 0 ? '+' : '') + formatPrice(v))}
          </div>
          <div class="stat-label">Total PnL</div>
        </div>

        <div class="stat-card">
          <div class="stat-value" style="color: {getStatColor('total_return')}">
            {getStatValue('total_return', formatPercentage)}
          </div>
          <div class="stat-label">Total Return</div>
        </div>

        <div class="stat-card">
          <div class="stat-value" style="color: {getStatColor('max_drawdown')}">
            {getStatValue('max_drawdown', formatPercentage)}
          </div>
          <div class="stat-label">Max Drawdown</div>
        </div>

        <div class="stat-card">
          <div class="stat-value" style="color: {getStatColor('sharpe_ratio', 1)}">
            {getStatValue('sharpe_ratio', (v) => v.toFixed(2))}
          </div>
          <div class="stat-label">Sharpe Ratio</div>
        </div>

        <div class="stat-card">
          <div class="stat-value">{getStatValue('winning_trades')}</div>
          <div class="stat-label">Winning Trades</div>
        </div>

        <div class="stat-card">
          <div class="stat-value">{getStatValue('losing_trades')}</div>
          <div class="stat-label">Losing Trades</div>
        </div>

        <div class="stat-card">
          <div class="stat-value" style="color: {getStatColor('avg_win')}">
            {getStatValue('avg_win', formatPrice)}
          </div>
          <div class="stat-label">Avg Win</div>
        </div>

        <div class="stat-card">
          <div class="stat-value" style="color: {getStatColor('avg_loss')}">
            {getStatValue('avg_loss', formatPrice)}
          </div>
          <div class="stat-label">Avg Loss</div>
        </div>

        <div class="stat-card">
          <div class="stat-value" style="color: {getStatColor('profit_factor', 1)}">
            {getStatValue('profit_factor', (v) => v.toFixed(2))}
          </div>
          <div class="stat-label">Profit Factor</div>
        </div>

        <div class="stat-card">
          <div class="stat-value">
            {getStatValue('avg_trade_duration', (v) => `${Math.round(v)}m`)}
          </div>
          <div class="stat-label">Avg Duration</div>
        </div>
      </div>

      <!-- Recent trades table -->
      {#if recentTrades.length > 0}
        <div class="trades-table">
          <h4>Recent Trades</h4>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Direction</th>
                  <th>Entry</th>
                  <th>Exit</th>
                  <th>PnL</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                {#each recentTrades as trade}
                  <tr>
                    <td>{formatTime(trade.entry_time)}</td>
                    <td>
                      <span class="direction-badge" class:long={trade.direction === 'long'} class:short={trade.direction === 'short'}>
                        {trade.direction.toUpperCase()}
                      </span>
                    </td>
                    <td>{formatPrice(trade.entry_price)}</td>
                    <td>{trade.exit_price ? formatPrice(trade.exit_price) : 'Open'}</td>
                    <td class="pnl-cell" class:positive={trade.pnl > 0} class:negative={trade.pnl < 0}>
                      {trade.pnl ? (trade.pnl > 0 ? '+' : '') + formatPrice(trade.pnl) : 'N/A'}
                    </td>
                    <td>
                      <span class="exit-reason" class:profit={trade.exit_reason === 'take_profit'} class:loss={trade.exit_reason === 'stop_loss'}>
                        {trade.exit_reason ? trade.exit_reason.replace('_', ' ').toUpperCase() : 'Open'}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
    {/if}
  {/if}
</div>

<style>
  .statistics-panel {
    background: white;
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.3s ease;
  }

  .stats-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    background: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
  }

  .stats-header h3 {
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
    color: #2c3e50;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    color: #7f8c8d;
  }

  .loading-spinner {
    width: 32px;
    height: 32px;
    border: 3px solid #f3f3f3;
    border-top: 3px solid #3498db;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .no-data {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3rem;
    color: #7f8c8d;
  }

  .no-data-content {
    text-align: center;
  }

  .no-data-content h4 {
    margin: 1rem 0 0.5rem;
    color: #95a5a6;
  }

  .no-data-content p {
    margin: 0;
    color: #bdc3c7;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1rem;
    padding: 1.5rem;
  }

  .stat-card {
    text-align: center;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 6px;
    border: 1px solid #e9ecef;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
    color: #2c3e50;
  }

  .stat-label {
    font-size: 0.75rem;
    color: #7f8c8d;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .trades-table {
    padding: 0 1.5rem 1.5rem;
  }

  .trades-table h4 {
    margin: 0 0 1rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: #2c3e50;
  }

  .table-container {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  th, td {
    padding: 0.75rem 0.5rem;
    text-align: left;
    border-bottom: 1px solid #e9ecef;
  }

  th {
    background: #f8f9fa;
    font-weight: 600;
    color: #495057;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  td {
    color: #495057;
  }

  .direction-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .direction-badge.long {
    background: #d4edda;
    color: #155724;
  }

  .direction-badge.short {
    background: #f8d7da;
    color: #721c24;
  }

  .pnl-cell.positive {
    color: #28a745;
    font-weight: 600;
  }

  .pnl-cell.negative {
    color: #dc3545;
    font-weight: 600;
  }

  .exit-reason {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .exit-reason.profit {
    background: #d4edda;
    color: #155724;
  }

  .exit-reason.loss {
    background: #f8d7da;
    color: #721c24;
  }

  .btn {
    display: inline-flex;
    align-items: center;
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

  .btn-secondary {
    background: #95a5a6;
    color: white;
    border-color: #95a5a6;
  }

  .btn-secondary:hover {
    background: #7f8c8d;
    border-color: #7f8c8d;
  }

  /* Responsive design */
  @media (max-width: 768px) {
    .stats-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: 0.75rem;
      padding: 1rem;
    }

    .stat-card {
      padding: 0.75rem;
    }

    .stat-value {
      font-size: 1.25rem;
    }

    .trades-table {
      padding: 0 1rem 1rem;
    }

    table {
      font-size: 0.75rem;
    }

    th, td {
      padding: 0.5rem 0.25rem;
    }
  }
</style>
