import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 3000,
      host: true,
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:3005',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
      rollupOptions: {
        output: {
          manualChunks: {
            'chakra-ui': ['@chakra-ui/react'],
            'thirdweb': ['@thirdweb-dev/react', '@thirdweb-dev/sdk'],
            'urql': ['urql', 'graphql', 'graphql-ws'],
          },
        },
      },
    },
    optimizeDeps: {
      include: ['@chakra-ui/react', '@emotion/react', '@emotion/styled'],
      exclude: ['@thirdweb-dev/react', '@thirdweb-dev/sdk'],
    },
    define: {
      // Telegram Web App global
      'window.Telegram': 'window.Telegram',
    },
  }
})
