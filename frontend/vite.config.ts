import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    // In development the API runs separately (uvicorn --reload on :8000).
    proxy: { '/api': 'http://localhost:8000' },
  },
})
