import { defineConfig } from 'vite';
import { svelte } from '@vitejs/plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'lightweight-charts': ['lightweight-charts']
        }
      }
    }
  },
  optimizeDeps: {
    include: ['lightweight-charts']
  }
});
