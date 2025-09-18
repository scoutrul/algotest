<script>
  import { createEventDispatcher } from 'svelte';
  export let availableIntervals = [];
  export let selectedInterval = '15m';

  const dispatch = createEventDispatcher();

  function choose(interval) {
    dispatch('intervalSelect', interval);
  }
</script>

<div class="interval-switcher">
  {#each availableIntervals as interval}
    <button
      class="interval-btn {selectedInterval === interval ? 'interval-btn-active' : 'interval-btn-inactive'}"
      on:click={() => choose(interval)}
      title={`Select time interval: ${interval}`}
    >
      {interval}
    </button>
  {/each}
</div>

<style>
  .interval-switcher {
    display: flex;
    flex-direction: row;
    gap: 4px;
    margin-right: 0;
    margin-bottom: 0.5rem;
    width: 100%;
    justify-content: flex-start;
  }

  .interval-btn {
    all: initial;
    font-family: -apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif;
    font-size: 12px;
    font-style: normal;
    font-weight: 500;
    line-height: 16px;
    letter-spacing: -0.2px;
    padding: 4px 8px;
    color: rgba(19, 23, 34, 1);
    background-color: rgba(240, 243, 250, 1);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
    min-width: 32px;
    text-align: center;
  }

  .interval-btn:hover {
    background-color: rgba(224, 227, 235, 1);
  }

  .interval-btn:active {
    background-color: rgba(209, 212, 220, 1);
  }

  .interval-btn-active {
    background-color: rgba(52, 152, 219, 1) !important;
    color: white !important;
  }

  .interval-btn-active:hover {
    background-color: rgba(41, 128, 185, 1) !important;
  }

  .interval-btn-inactive {
    background-color: rgba(240, 243, 250, 1);
    color: rgba(19, 23, 34, 1);
  }

  @media (max-width: 768px) {
    .interval-switcher {
      flex-wrap: wrap;
      justify-content: center;
      margin-bottom: 0.75rem;
    }

    .interval-btn {
      font-size: 11px;
      padding: 3px 6px;
      min-width: 28px;
    }
  }
</style>
