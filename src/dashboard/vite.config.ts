import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { readFileSync } from 'node:fs'
import type { Plugin, Connect } from 'vite'
import type { ServerResponse } from 'node:http'
import { FIXTURE_HANDLERS, matchHandler, compareZeroDiff } from './tests/a11y/fixture-handlers.mjs'

function a11yFixture(): Plugin {
  // Fixture files are loaded lazily inside configureServer/configurePreviewServer,
  // after the VITE_A11Y_FIXTURE guard, so a fresh clone without fixture files
  // does not crash vite dev/build when the env-var is not set (WR-05).
  //
  // 221 D-03: the per-endpoint decisions live in tests/a11y/fixture-handlers.mjs (a pure,
  // contract-tested table). This function is only an interpreter over that table.
  function buildHandler(held: Set<ServerResponse>) {
    const fileCache = new Map<string, string>()
    for (const h of FIXTURE_HANDLERS) {
      if ('file' in h.default && !fileCache.has(h.default.file)) {
        fileCache.set(h.default.file, readFileSync(path.resolve(__dirname, './tests/a11y', h.default.file), 'utf8'))
      }
    }
    const qrammFixtureRaw = JSON.parse(readFileSync(path.resolve(__dirname, './tests/a11y/fixture-qramm.json'), 'utf8')) as Record<string, unknown>
    const noCache = (r: ServerResponse) => r.setHeader('Cache-Control', 'no-store')
    const sendJson = (r: ServerResponse, body: string) => {
      noCache(r); r.setHeader('Content-Type', 'application/json')
      r.end(body)
    }
    const defaultBody = (h: (typeof FIXTURE_HANDLERS)[number]): string => {
      const src = h.default
      if ('file' in src) return fileCache.get(src.file) as string
      if ('qrammKey' in src) return JSON.stringify(qrammFixtureRaw[src.qrammKey] ?? src.fallback)
      return JSON.stringify(src.json)
    }
    return (req: Connect.IncomingMessage, res: ServerResponse, next: Connect.NextFunction) => {
      const variant = process.env.VITE_A11Y_FIXTURE_VARIANT
      // 221 D-02: identity sentinel. Lets the harness prove the server answering the port is
      // the one it spawned, with the variant it asked for. Lives inside buildHandler, so it is
      // only mounted behind the VITE_A11Y_FIXTURE guard below (never in a normal dev/preview).
      if (req.url === '/__a11y-variant') {
        sendJson(res, JSON.stringify({ variant: variant ?? 'default', pid: process.pid }))
        return
      }
      const h = matchHandler(req.url)
      if (!h) { next(); return }
      if (variant === 'empty') {
        if ('body' in h.empty) {
          const b = h.empty.body
          sendJson(res, typeof b === 'string' ? b : JSON.stringify(b))
          return
        }
        if ('emptyFrom' in h.empty) {
          sendJson(res, JSON.stringify(compareZeroDiff(JSON.parse(defaultBody(h)))))
          return
        }
        // {na}: declared non-applicability (reason enforced by variant-contract.test.ts)
      }
      if (variant === 'loading' && 'hold' in h.loading) {
        // 221 D-08: hold the request open for the whole sweep. res.end is NEVER called;
        // held responses are destroyed when the HTTP server closes.
        noCache(res); res.setHeader('Content-Type', 'application/json')
        held.add(res)
        res.on('close', () => { held.delete(res) })
        return
      }
      sendJson(res, defaultBody(h))
    }
  }

  const releaseOnClose = (server: { httpServer?: { on: (e: 'close', cb: () => void) => unknown } | null }, held: Set<ServerResponse>) => {
    server.httpServer?.on('close', () => { for (const r of held) r.destroy() })
  }

  return {
    name: 'a11y-fixture',
    configureServer(server) {
      if (!process.env.VITE_A11Y_FIXTURE) return
      const held = new Set<ServerResponse>()
      releaseOnClose(server, held)
      server.middlewares.use(buildHandler(held))
    },
    configurePreviewServer(server) {
      if (!process.env.VITE_A11Y_FIXTURE) return
      const held = new Set<ServerResponse>()
      releaseOnClose(server, held)
      server.middlewares.use(buildHandler(held))
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
