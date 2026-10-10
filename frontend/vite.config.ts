import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: Number(process.env.SOLAROPT_WEB_PORT || 5174),
    proxy: {
      '/api': {
        target: process.env.SOLAROPT_API_URL || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
    proxy: { '/api': { target: process.env.SOLAROPT_API_URL || 'http://127.0.0.1:8001', changeOrigin: true } },
  },
})
