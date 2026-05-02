import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { readFileSync } from 'node:fs'
import type { Plugin } from 'vite'

function a11yFixture(): Plugin {
  // Cache fixture contents at plugin init time to avoid blocking reads on every request
  const scanFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-scan.json'), 'utf8')
  const trendsFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-trends.json'), 'utf8')
  const noCache = (r: any) => r.setHeader('Cache-Control', 'no-store')
  const handler = (req: any, res: any, next: any) => {
    if (!process.env.VITE_A11Y_FIXTURE) return next()
    const variant = process.env.VITE_A11Y_FIXTURE_VARIANT
    if (req.url?.startsWith('/api/scan/latest')) {
      if (variant === 'empty') {
        noCache(res); res.setHeader('Content-Type', 'application/json')
        res.end('{}')
        return
      }
      if (variant === 'loading') {
        // Delay response so first-paint shows the loading skeleton/spinner
        setTimeout(() => {
          noCache(res); res.setHeader('Content-Type', 'application/json')
          res.end(scanFixture)
        }, 3000)
        return
      }
      noCache(res); res.setHeader('Content-Type', 'application/json')
      res.end(scanFixture)
      return
    }
    if (req.url?.startsWith('/api/scans')) {
      noCache(res); res.setHeader('Content-Type', 'application/json')
      res.end('[]')
      return
    }
    if (req.url?.startsWith('/api/trends')) {
      if (variant === 'empty') {
        noCache(res); res.setHeader('Content-Type', 'application/json')
        res.end('{}')
        return
      }
      if (variant === 'loading') {
        setTimeout(() => {
          noCache(res); res.setHeader('Content-Type', 'application/json')
          res.end(trendsFixture)
        }, 3000)
        return
      }
      noCache(res); res.setHeader('Content-Type', 'application/json')
      res.end(trendsFixture)
      return
    }
    next()
  }
  return {
    name: 'a11y-fixture',
    configureServer(server) {
      if (!process.env.VITE_A11Y_FIXTURE) return
      server.middlewares.use(handler)
    },
    configurePreviewServer(server) {
      if (!process.env.VITE_A11Y_FIXTURE) return
      server.middlewares.use(handler)
    },
  }
}

export default defineConfig({
  plugins: [react(), a11yFixture()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: '../../quirk/dashboard/static',
    emptyOutDir: true,
    chunkSizeWarningLimit: 600,
    rolldownOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/') || id.includes('node_modules/react-router')) return 'vendor-react'
          if (id.includes('node_modules/recharts') || id.includes('node_modules/d3-')) return 'vendor-charts'
          if (id.includes('node_modules/cytoscape')) return 'vendor-graph'
          if (id.includes('node_modules/@tanstack')) return 'vendor-table'
        },
      },
    },
  },
})
