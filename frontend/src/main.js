// Main entry point for the Svelte application
import App from './App.svelte';

const app = new App({
  target: document.body,
  props: {
    name: 'BackTest Trading Bot'
  }
});

export default app;
