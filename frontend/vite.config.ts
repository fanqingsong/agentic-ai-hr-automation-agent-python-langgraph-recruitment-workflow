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
    // HMR: so browser (e.g. localhost:5173) can connect to WebSocket when dev server runs in Docker
    hmr: {
      clientPort: 5173,
      host: 'localhost',
      protocol: 'ws',
    },
    // Detect file changes on mounted volumes (e.g. Docker); use polling if native events miss updates
    watch: {
      usePolling: true,
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
