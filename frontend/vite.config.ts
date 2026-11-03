import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // On Vercel the API is reached through the same-origin /api rewrite in vercel.json: a cross-site API host would
  // drop the login cookie (SameSite=Lax), so every signed-in request would count as a guest.
  ...(process.env.VERCEL ? {define: {'import.meta.env.VITE_API_BASE': JSON.stringify('')}} : {}),
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
