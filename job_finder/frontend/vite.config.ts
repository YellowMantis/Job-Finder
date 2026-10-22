import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // While developing, this page runs on Vite's own server (port 5173) and the
    // Python back end on port 5000. Requests to /api/... are passed on to it,
    // so the page talks to the back end exactly as it will when built.
    // API_URL can point elsewhere, e.g. a second copy of the back end for testing.
    proxy: {
      '/api': process.env.API_URL ?? 'http://127.0.0.1:5000',
    },
  },
})
