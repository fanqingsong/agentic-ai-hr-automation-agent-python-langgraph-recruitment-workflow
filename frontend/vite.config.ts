import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true, // listen on 0.0.0.0 for Docker / network access
    strictPort: true,
    // HMR: so browser can connect to WebSocket when dev server runs in Docker.
    // clientPort must match the HOST-facing port (may differ from container port).
    hmr: {
      clientPort: Number(process.env.VITE_HMR_CLIENT_PORT) || 5173,
      host: 'localhost',
      protocol: 'ws',
    },
    // Detect file changes on mounted volumes (e.g. Docker); use polling if native events miss updates
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
        // In Docker Compose, set VITE_API_PROXY_TARGET=http://hr-automation:8000
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        // Batch CV import holds the connection open while LLM extraction runs.
        timeout: 7_200_000,
        proxyTimeout: 7_200_000,
      },
    },
  },
})
