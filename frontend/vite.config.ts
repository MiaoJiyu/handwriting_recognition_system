import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: ['5173.app.cloudstudio.work'], //请根据实际情况修改
    proxy: {
      '/api': {
        target: 'http://localhost:8000', //请根据实际情况修改
        changeOrigin: true,
      },
    },
  },
})
