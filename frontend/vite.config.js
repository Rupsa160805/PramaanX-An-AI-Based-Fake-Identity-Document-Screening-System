import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backendUrl = env.VITE_BACKEND_URL || 'http://127.0.0.1:5001'

  return {
    // Base public path. Local dev/build stay at '/'; the GitHub Pages workflow
    // sets VITE_BASE to '/<repo-name>/' so built asset URLs resolve on the
    // project site (https://<owner>.github.io/<repo-name>/).
    base: env.VITE_BASE || '/',
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      proxy: {
        '/api': backendUrl,
      },
    },
  }
})
