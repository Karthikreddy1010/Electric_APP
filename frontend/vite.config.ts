import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/app/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
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
      '/pjm': { target: 'http://localhost:8000', changeOrigin: true },
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/customers': { target: 'http://localhost:8000', changeOrigin: true },
      '/tariffs': { target: 'http://localhost:8000', changeOrigin: true },
      '/simulate': { target: 'http://localhost:8000', changeOrigin: true },
      '/geo': { target: 'http://localhost:8000', changeOrigin: true },
      '/recommendations': { target: 'http://localhost:8000', changeOrigin: true },
      '/bgs': { target: 'http://localhost:8000', changeOrigin: true },
      '/municipal': { target: 'http://localhost:8000', changeOrigin: true },
      '/eia861': { target: 'http://localhost:8000', changeOrigin: true },
      '/eia861m': { target: 'http://localhost:8000', changeOrigin: true },
      '/eia930': { target: 'http://localhost:8000', changeOrigin: true },
      '/report': { target: 'http://localhost:8000', changeOrigin: true },
      '/service-territory': { target: 'http://localhost:8000', changeOrigin: true },
      '/smart-meter': { target: 'http://localhost:8000', changeOrigin: true },
      '/tariff-optimization': { target: 'http://localhost:8000', changeOrigin: true },
      '/inflation': { target: 'http://localhost:8000', changeOrigin: true },
      '/cross-dataset': { target: 'http://localhost:8000', changeOrigin: true },
      '/eia-retail': { target: 'http://localhost:8000', changeOrigin: true },
      '/admin-analytics': { target: 'http://localhost:8000', changeOrigin: true },
      '/monitoring': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})

