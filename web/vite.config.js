import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5199,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8799', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8799', changeOrigin: true },
    },
  },
  build: { outDir: 'dist' },
})
