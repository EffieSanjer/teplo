import { readFileSync } from 'node:fs'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

const appVersion = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8'))
  .version as string

// Locally these defaults keep the usual `npm run dev` workflow unchanged.
// The Docker dev service overrides them so Vite can reach the API container
// and still send the Host/Origin the API expects from the public URL.
const apiTarget = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000'
const publicOrigin = process.env.PUBLIC_ORIGIN || ''
const publicHost = publicOrigin ? new URL(publicOrigin).host : ''
const usePolling = process.env.VITE_WATCH_POLLING === 'true'
// Pin the dev container's HMR socket to the published host/port. Otherwise
// some browsers try to reconnect to 0.0.0.0 and reload the page in a loop.
const dockerHmr = process.env.API_PROXY_TARGET
  ? {
      host: process.env.VITE_HMR_HOST || 'localhost',
      port: Number(process.env.VITE_HMR_PORT || 5173),
      clientPort: Number(process.env.VITE_HMR_CLIENT_PORT || process.env.VITE_HMR_PORT || 5173),
      // Keep the socket warm: some proxies/Docker forwarders drop it after ~10s
      // of idle time, which makes Vite reload the page on every reconnect.
      timeout: Number(process.env.VITE_HMR_TIMEOUT || 5000),
    }
  : undefined

export default defineConfig({
  plugins: [
    vue({
      template: {
        // Keep absolute public URLs as literals so Vitest does not try to import /…jpg.
        transformAssetUrls: { includeAbsolute: false },
      },
    }),
    tailwindcss(),
  ],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(appVersion),
  },
  server: {
    port: Number(process.env.VITE_PORT || 3000),
    strictPort: true,
    host: process.env.VITE_HOST || undefined,
    hmr: dockerHmr,
    watch: {
      // Docker Desktop on Windows does not reliably deliver bind-mount events.
      usePolling,
      interval: 1000,
      // Generated/editor files can change often and cause full page reloads.
      ignored: [
        '**/node_modules/**',
        '**/dist/**',
        '**/.git/**',
        '**/*.tsbuildinfo',
        '**/coverage/**',
        '**/test-results/**',
        '**/playwright-report/**',
      ],
    },
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: false,
        configure: (proxy) => {
          if (!publicOrigin) return
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('origin', publicOrigin)
            if (publicHost) proxyReq.setHeader('host', publicHost)
          })
        },
      },
    },
  },
  test: { environment: 'jsdom', include: ['tests/unit/**/*.test.ts'] },
})
