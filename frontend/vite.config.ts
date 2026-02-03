import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: ['5173.app.cloudstudio.work'],
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://47.117.126.60:8000',
        changeOrigin: true,
      },
    },
  },
})
