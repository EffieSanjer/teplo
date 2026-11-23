import { defineConfig, devices } from '@playwright/test'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

// nginx only accepts the public Host from PUBLIC_BASE_URL, so a plain
// http://localhost:3000 run against the Docker container is rejected. Prefer
// the tunnel URL from the repo .env unless the caller overrides it.
function defaultBaseURL() {
  if (process.env.PLAYWRIGHT_BASE_URL) return process.env.PLAYWRIGHT_BASE_URL
  const envPath = resolve(process.cwd(), '../.env')
  if (existsSync(envPath)) {
    const match = readFileSync(envPath, 'utf8').match(/^PUBLIC_BASE_URL=(.+)$/m)
    if (match?.[1]) return match[1].trim().replace(/\/+$/, '')
  }
  return 'http://localhost:3000'
}

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: {
    baseURL: defaultBaseURL(),
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
