import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/app/',
  server: {
    proxy: {
      // Forward all API paths to the FastAPI backend
      '/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/users': { target: 'http://localhost:8000', changeOrigin: true },
      '/bill': { target: 'http://localhost:8000', changeOrigin: true },
      '/overview': { target: 'http://localhost:8000', changeOrigin: true },
      '/forecast': { target: 'http://localhost:8000', changeOrigin: true },
      '/plans': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
      '/metrics': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
