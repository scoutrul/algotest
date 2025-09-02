<!-- Data Manager Component for Database Synchronization -->
<script>
  import { onMount } from 'svelte';
  import { apiClient } from '../utils/api.js';

  let dataStatus = null;
  let loading = false;
  let syncLoading = false;
  let error = null;

  // Load data status on mount
  onMount(async () => {
    await loadDataStatus();
  });

  async function loadDataStatus() {
    try {
      loading = true;
      error = null;
      const response = await apiClient.request('/api/v1/data/status');
      dataStatus = response;
    } catch (err) {
      error = err.message;
      console.error('Error loading data status:', err);
    } finally {
      loading = false;
    }
  }

  async function syncSymbolInterval(symbol, interval) {
    try {
      syncLoading = true;
      error = null;

      const response = await apiClient.request(`/api/v1/data/sync/${symbol}/${interval}`, {
        method: 'POST',
        body: JSON.stringify({ limit: 5000 })
      });

      // Reload status after sync starts
      setTimeout(() => loadDataStatus(), 2000);

      return response;
    } catch (err) {
      error = err.message;
      console.error('Error syncing data:', err);
    } finally {
      syncLoading = false;
    }
  }

  async function syncAllData() {
    try {
      syncLoading = true;
      error = null;

      const response = await apiClient.request('/api/v1/data/sync-all', {
        method: 'POST',
        body: JSON.stringify({ limit_per_symbol: 3000 })
      });

      // Reload status after sync starts
      setTimeout(() => loadDataStatus(), 5000);

      return response;
    } catch (err) {
      error = err.message;
      console.error('Error syncing all data:', err);
    } finally {
      syncLoading = false;
    }
  }

  function formatTimestamp(timestamp) {
    if (!timestamp) return 'Never';
    return new Date(timestamp).toLocaleString();
  }

  function formatNumber(num) {
    if (!num) return '0';
    return num.toLocaleString();
  }
</script>

<div class="data-manager">
  <div class="data-header">
    <h3>Data Synchronization</h3>
    <div class="data-controls">
      <button
        class="btn btn-primary"
        on:click={loadDataStatus}
        disabled={loading}
      >
        {#if loading}
          <div class="spinner-small"></div>
          Loading...
        {:else}
          Refresh Status
        {/if}
      </button>

      <button
        class="btn btn-success"
        on:click={syncAllData}
        disabled={syncLoading}
      >
        {#if syncLoading}
          <div class="spinner-small"></div>
          Syncing...
        {:else}
          Sync All Data
        {/if}
      </button>
    </div>
  </div>

  {#if error}
    <div class="error-message">
      <strong>Error:</strong> {error}
    </div>
  {/if}

  {#if dataStatus}
    <div class="data-overview">
      <div class="overview-card">
        <h4>Database Status</h4>
        <p class="status-{dataStatus.database_status}">{dataStatus.database_status}</p>
      </div>

      <div class="overview-card">
        <h4>Total Symbols</h4>
        <p>{dataStatus.supported_symbols.length}</p>
      </div>

      <div class="overview-card">
        <h4>Total Intervals</h4>
        <p>{dataStatus.supported_intervals.length}</p>
      </div>
    </div>

    <div class="data-table">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Interval</th>
            <th>Candles</th>
            <th>Last Updated</th>
            <th>Date Range</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {#each dataStatus.supported_symbols as symbol}
            {#each dataStatus.supported_intervals as interval}
              {@const statusKey = `${symbol}_${interval}`}
              {@const status = dataStatus.data_status[statusKey]}
              <tr>
                <td>{symbol}</td>
                <td>{interval}</td>
                <td>{formatNumber(status?.total_candles || 0)}</td>
                <td>{formatTimestamp(status?.last_updated)}</td>
                <td>
                  {#if status?.oldest_timestamp && status?.newest_timestamp}
                    {new Date(status.oldest_timestamp).toLocaleDateString()} -
                    {new Date(status.newest_timestamp).toLocaleDateString()}
                  {:else}
                    No data
                  {/if}
                </td>
                <td>
                  <button
                    class="btn btn-sm btn-outline"
                    on:click={() => syncSymbolInterval(symbol, interval)}
                    disabled={syncLoading}
                  >
                    {#if syncLoading}
                      <div class="spinner-tiny"></div>
                    {:else}
                      Sync
                    {/if}
                  </button>
                </td>
              </tr>
            {/each}
          {/each}
        </tbody>
      </table>
    </div>
  {:else if !loading}
    <div class="no-data">
      <p>Unable to load data synchronization status.</p>
      <button class="btn btn-primary" on:click={loadDataStatus}>
        Try Again
      </button>
    </div>
  {/if}
</div>

<style>
  .data-manager {
    padding: 1.5rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .data-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #e0e0e0;
  }

  .data-header h3 {
    margin: 0;
    color: #2c3e50;
  }

  .data-controls {
    display: flex;
    gap: 0.5rem;
  }

  .error-message {
    background: #fee;
    color: #c33;
    padding: 1rem;
    border-radius: 4px;
    border: 1px solid #fcc;
    margin-bottom: 1rem;
  }

  .data-overview {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .overview-card {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 6px;
    text-align: center;
  }

  .overview-card h4 {
    margin: 0 0 0.5rem;
    color: #666;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .overview-card p {
    margin: 0;
    font-size: 1.5rem;
    font-weight: bold;
    color: #2c3e50;
  }

  .status-connected {
    color: #27ae60;
  }

  .status-error {
    color: #e74c3c;
  }

  .data-table {
    overflow-x: auto;
  }

  .data-table table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }

  .data-table th,
  .data-table td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid #e0e0e0;
  }

  .data-table th {
    background: #f8f9fa;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 0.8rem;
  }

  .data-table tr:hover {
    background: #f8f9fa;
  }

  .btn-sm {
    padding: 0.25rem 0.5rem;
    font-size: 0.8rem;
  }

  .btn-outline {
    border: 1px solid #3498db;
    background: transparent;
    color: #3498db;
  }

  .btn-outline:hover {
    background: #3498db;
    color: white;
  }

  .spinner-small {
    width: 14px;
    height: 14px;
    border: 2px solid #e0e0e0;
    border-top: 2px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 0.25rem;
  }

  .spinner-tiny {
    width: 10px;
    height: 10px;
    border: 1px solid #e0e0e0;
    border-top: 1px solid currentColor;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 0.25rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .no-data {
    text-align: center;
    padding: 2rem;
    color: #666;
  }

  /* Responsive adjustments */
  @media (max-width: 768px) {
    .data-manager {
      padding: 1rem;
    }

    .data-header {
      flex-direction: column;
      gap: 1rem;
      align-items: stretch;
    }

    .data-controls {
      justify-content: center;
    }

    .data-overview {
      grid-template-columns: 1fr;
    }

    .data-table {
      font-size: 0.8rem;
    }
  }
</style>

