<script>
  import { createEventDispatcher } from 'svelte';
  import { configStore } from '../stores/config.js';

  export let selectedSymbol = 'BTC/USDT';
  export let loading = false;

  const dispatch = createEventDispatcher();

  $: availableSymbols = $configStore.availableSymbols;

  function selectSymbol(sym) {
    // Only emit; parent decides what to do (update store, reload, etc.)
    dispatch('symbolSelect', sym);
  }
</script>

<div class="symbol-badges">
  <div class="badge-container" id="symbol-badges" role="group" aria-label="Select trading symbol">
    {#if availableSymbols && availableSymbols.length}
      {#each availableSymbols as sym}
        <button
          class="badge {selectedSymbol === sym ? 'badge-active' : 'badge-inactive'}"
          on:click={() => selectSymbol(sym)}
          disabled={loading}
          aria-pressed={selectedSymbol === sym}
        >
          {sym}
        </button>
      {/each}
    {:else}
      <span class="empty">No symbols</span>
    {/if}
  </div>
</div>

<style>
  .symbol-badges {
    display: flex;
    flex-direction: column;
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .badge-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.25rem;
  }

  .badge {
    padding: 0.375rem 0.75rem;
    border: 1px solid #ddd;
    border-radius: 20px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    background: white;
    color: #333;
    min-width: auto;
    white-space: nowrap;
  }

  .badge:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .badge-active {
    background: #3498db;
    color: white;
    border-color: #3498db;
    box-shadow: 0 2px 4px rgba(52, 152, 219, 0.3);
  }

  .badge-active:hover:not(:disabled) {
    background: #2980b9;
    border-color: #2980b9;
    box-shadow: 0 4px 8px rgba(52, 152, 219, 0.4);
  }

  .badge-inactive {
    background: white;
    color: #666;
    border-color: #ddd;
  }

  .badge-inactive:hover:not(:disabled) {
    background: #f8f9fa;
    border-color: #bbb;
    color: #333;
  }

  .badge:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }

  .badge:focus {
    outline: none;
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
  }

  .empty {
    color: #999;
    font-size: 0.85rem;
  }
</style>
