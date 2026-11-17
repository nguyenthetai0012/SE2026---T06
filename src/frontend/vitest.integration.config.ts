import { defineConfig } from 'vitest/config'
import frontendConfig from './vite.config'

const root = decodeURIComponent(new URL('../../', import.meta.url).pathname).replace(/^\/([A-Za-z]:\/)/, '$1')
export default defineConfig({
  ...frontendConfig,
  root,
  server: { fs: { allow: [root] } },
  test: {
    ...frontendConfig.test,
    include: ['tests/integration/frontend/**/*.test.{ts,tsx}'],
    setupFiles: ['src/frontend/src/test/setup.ts'],
  },
})
