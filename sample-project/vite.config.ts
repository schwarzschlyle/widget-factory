import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@widget": path.resolve(__dirname, "widget-generator/widget-component")
    }
  },
  server: {
    proxy: {
      '/api': 'http://localhost:3001'
    }
  }
})
