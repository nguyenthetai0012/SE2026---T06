import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const packagePath = (path: string) => decodeURIComponent(new URL(`./node_modules/${path}`, import.meta.url).pathname).replace(/^\/([A-Za-z]:\/)/, '$1')

export default defineConfig({
  resolve: { alias: [
    { find: /^@testing-library\/react$/, replacement: packagePath('@testing-library/react/dist/index.js') },
    { find: /^vitest$/, replacement: packagePath('vitest/dist/index.js') },
    { find: /^react\/jsx-dev-runtime$/, replacement: packagePath('react/jsx-dev-runtime.js') },
    { find: /^react$/, replacement: packagePath('react/index.js') },
    { find: /^react\/jsx-runtime$/, replacement: packagePath('react/jsx-runtime.js') },
  ] },
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    clearMocks: true,
    pool: 'threads',
    maxWorkers: 1,
    minWorkers: 1,
  },
})
