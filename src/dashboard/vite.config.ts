import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { readFileSync } from 'node:fs'
import type { Plugin, Connect } from 'vite'
import type { ServerResponse } from 'node:http'

function a11yFixture(): Plugin {
  // Fixture files are loaded lazily inside configureServer/configurePreviewServer,
  // after the VITE_A11Y_FIXTURE guard, so a fresh clone without fixture files
  // does not crash vite dev/build when the env-var is not set (WR-05).
  function buildHandler() {
    const scanFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-scan.json'), 'utf8')
    const trendsFixture = readFileSync(path.resolve(__dirname, './tests/a11y/fixture-trends.json'), 'utf8')
    const qrammFixtureRaw = JSON.parse(readFileSync(path.resolve(__dirname, './tests/a11y/fixture-qramm.json'), 'utf8')) as Record<string, unknown>
    const noCache = (r: ServerResponse) => r.setHeader('Cache-Control', 'no-store')
    return (req: Connect.IncomingMessage, res: ServerResponse, next: Connect.NextFunction) => {
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
      // QRAMM API fixtures — matched in specificity order (longest prefix first)
      if (req.url?.match(/^\/api\/qramm\/sessions\/\d+\/answers/)) {
        const key = 'GET /api/qramm/sessions/1/answers'
        noCache(res); res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(qrammFixtureRaw[key] ?? []))
        return
      }
      if (req.url?.match(/^\/api\/qramm\/sessions\/\d+/)) {
        const key = 'GET /api/qramm/sessions/1'
        noCache(res); res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(qrammFixtureRaw[key] ?? {}))
        return
      }
      if (req.url?.startsWith('/api/qramm/sessions')) {
        const key = 'GET /api/qramm/sessions'
        noCache(res); res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(qrammFixtureRaw[key] ?? []))
        return
      }
      if (req.url?.startsWith('/api/qramm/questions')) {
        const key = 'GET /api/qramm/questions'
        noCache(res); res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify(qrammFixtureRaw[key] ?? []))
        return
      }
      if (req.url?.startsWith('/api/qramm/profiles')) {
        noCache(res); res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ profile_id: 1, session_id: 1, multiplier: 1.0 }))
        return
      }
      next()
    }
  }

  return {
    name: 'a11y-fixture',
    configureServer(server) {
      if (!process.env.VITE_A11Y_FIXTURE) return
      server.middlewares.use(buildHandler())
    },
    configurePreviewServer(server) {
      if (!process.env.VITE_A11Y_FIXTURE) return
      server.middlewares.use(buildHandler())
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
