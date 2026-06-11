/**
 * run-e2e.mjs — Browser smoke test against the REAL FastAPI server + built bundle.
 *
 * Unlike tests/a11y (vite preview + fixture JSON), this boots `quirk serve`
 * in an isolated temp workspace and drives the committed bundle in headless
 * Chrome, end to end. It validates the seam the unit suites cannot see:
 * API-contract drift, SPA deep-link routing through the FastAPI catch-all,
 * runtime JS errors, and the scan-submission lifecycle.
 *
 * Usage:
 *   npm run e2e:smoke
 *
 * Environment:
 *   E2E_PYTHON                  — python interpreter (default: repo .venv/bin/python)
 *   E2E_PORT                    — server port (default: 8517)
 *   PUPPETEER_EXECUTABLE_PATH   — fallback Chrome path if system Chrome not found
 *
 * Failure policy: ANY console error, page error, or >=400 API response that
 * is not explicitly allowlisted fails the run. Empty-DB phase allows exactly
 * one pattern: GET /api/scan/latest -> 404 (UI renders the empty state from
 * it). After a scan exists, nothing is allowed.
 */

import { mkdtempSync, rmSync, readFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve, dirname } from 'node:path'
import { spawn } from 'node:child_process'
import { createConnection } from 'node:net'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DASHBOARD_DIR = resolve(__dirname, '../..')
const REPO_ROOT = resolve(DASHBOARD_DIR, '../..')

const PORT = Number(process.env.E2E_PORT || 8517)
const HOST = '127.0.0.1'
const BASE = `http://${HOST}:${PORT}`
const PYTHON = process.env.E2E_PYTHON || resolve(REPO_ROOT, '.venv/bin/python')
const SCAN_TIMEOUT_MS = 120_000
const CONNECT_TIMEOUT_MS = 30_000
const CONNECT_POLL_MS = 250

// Every SPA route the sidebar exposes. Hard-navigated (page.goto), which also
// exercises the FastAPI catch-all that serves index.html for deep links.
const ROUTES = [
  '/', '/findings', '/identity', '/motion', '/data-at-rest', '/certificates',
  '/cbom', '/roadmap', '/trends', '/scans', '/sensors', '/schedules', '/qramm',
]

// Shared third-party console allowlist (same file the a11y harness uses).
const sharedAllow = JSON.parse(
  readFileSync(resolve(DASHBOARD_DIR, 'tests/console-allowlist.json'), 'utf8'),
).entries.map((e) => new RegExp(e.pattern))

const findings = []
function report(phase, kind, detail) {
  findings.push({ phase, kind, detail })
  console.error(`  ✗ [${phase}] ${kind}: ${detail}`)
}

function waitForPort(host, port, timeoutMs) {
  return new Promise((resolveP, rejectP) => {
    const deadline = Date.now() + timeoutMs
    function attempt() {
      const socket = createConnection({ host, port })
      socket.on('connect', () => { socket.destroy(); resolveP() })
      socket.on('error', () => {
        socket.destroy()
        if (Date.now() >= deadline) {
          rejectP(new Error(`Timed out waiting for ${host}:${port} after ${timeoutMs}ms`))
        } else {
          setTimeout(attempt, CONNECT_POLL_MS)
        }
      })
    }
    attempt()
  })
}

// --- Isolated workspace: the server must not touch the repo's DB or output/ ---
const workspace = mkdtempSync(join(tmpdir(), 'quirk-e2e-'))
console.log(`[e2e] Workspace: ${workspace}`)

const serverProc = spawn(
  PYTHON, ['-m', 'run_scan', 'serve', '--port', String(PORT), '--no-open'],
  {
    cwd: workspace,
    stdio: 'pipe',
    env: {
      ...process.env,
      QUIRK_DB_PATH: join(workspace, 'quirk.db'),
      PYTHONPATH: REPO_ROOT,
    },
  },
)
let serverLog = ''
serverProc.stdout.on('data', (d) => { serverLog += d })
serverProc.stderr.on('data', (d) => { serverLog += d })

function cleanup() {
  if (!serverProc.killed) serverProc.kill('SIGTERM')
  rmSync(workspace, { recursive: true, force: true })
}
process.on('exit', cleanup)
process.on('SIGINT', () => { cleanup(); process.exit(130) })
process.on('SIGTERM', () => { cleanup(); process.exit(143) })

try {
  await waitForPort(HOST, PORT, CONNECT_TIMEOUT_MS)
} catch (err) {
  console.error('[e2e] ERROR: server did not start:', err.message)
  console.error(serverLog)
  process.exit(1)
}
console.log(`[e2e] Server ready at ${BASE}`)

// --- Launch headless Chrome (system install; no browser download) ---
let browser
try {
  browser = await puppeteer.launch({ channel: 'chrome', headless: true, args: ['--no-sandbox'] })
} catch {
  const execPath = process.env.PUPPETEER_EXECUTABLE_PATH || '/opt/google/chrome/chrome'
  browser = await puppeteer.launch({ executablePath: execPath, headless: true, args: ['--no-sandbox'] })
}

const page = await browser.newPage()

// Console / page-error / failed-API capture. `apiAllow` is swapped per phase.
let currentPhase = 'init'
let apiAllow = []
page.on('console', (msg) => {
  if (msg.type() !== 'error') return
  const text = msg.text()
  if (sharedAllow.some((re) => re.test(text))) return
  // Chromium's "Failed to load resource" console text omits the URL — it is
  // only in msg.location(). The response hook already reports failed API
  // calls with full method/URL/status, so match the location URL against the
  // same allowlist here to avoid double-reporting allowed 404s.
  const locUrl = msg.location()?.url || ''
  if (apiAllow.some((a) => a.urlRe.test(text) || a.urlRe.test(locUrl))) return
  report(currentPhase, 'console.error', `${text} (${locUrl})`)
})
page.on('pageerror', (err) => report(currentPhase, 'pageerror', err.message))
page.on('response', (resp) => {
  const url = resp.url()
  if (!url.includes('/api/')) return
  if (resp.status() < 400) return
  if (apiAllow.some((a) => a.urlRe.test(url) && a.status === resp.status())) return
  report(currentPhase, 'api-failure', `${resp.request().method()} ${url} -> ${resp.status()}`)
})

async function walkRoutes(phase) {
  currentPhase = phase
  for (const route of ROUTES) {
    await page.goto(BASE + route, { waitUntil: 'networkidle0', timeout: 30_000 })
    const rendered = await page.evaluate(() => {
      const main = document.querySelector('main')
      return main !== null && main.innerText.trim().length > 0
    })
    if (!rendered) report(phase, 'blank-page', `${route} rendered no <main> content`)
  }
}

// --- Phase 1: every route renders on an empty DB ---
console.log('[e2e] Phase 1: route walk (empty DB)')
apiAllow = [{ urlRe: /\/api\/scan\/latest/, status: 404 }]
await walkRoutes('empty-db')

// --- Phase 2: submit a loopback scan from the form and watch it complete ---
console.log('[e2e] Phase 2: scan submission lifecycle')
currentPhase = 'scan-flow'
apiAllow = [{ urlRe: /\/api\/scan\/latest/, status: 404 }]
await page.goto(`${BASE}/scan/new`, { waitUntil: 'networkidle0' })
await page.type('input[placeholder*="api.example.com"], textarea[placeholder*="api.example.com"]', '127.0.0.1')
await page.evaluate(() => {
  const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.trim() === 'Run Scan')
  if (!btn) throw new Error('Run Scan button not found')
  btn.click()
})
try {
  await page.waitForFunction(
    () => window.location.pathname.startsWith('/scan/job/'),
    { timeout: 15_000 },
  )
} catch {
  report('scan-flow', 'no-job-page', 'submitting the form never navigated to /scan/job/{id}')
}
try {
  // On completion the job page redirects to the executive summary.
  await page.waitForFunction(
    () => window.location.pathname === '/',
    { timeout: SCAN_TIMEOUT_MS },
  )
  // The redirect lands before the summary data fetch resolves — wait for the
  // populated heading rather than sampling the body immediately.
  try {
    await page.waitForFunction(
      () => document.body.innerText.includes('Scan Results'),
      { timeout: 30_000 },
    )
    console.log('[e2e] Scan completed and dashboard populated')
  } catch {
    const snippet = await page.evaluate(() => document.body.innerText.replace(/\s+/g, ' ').slice(0, 300))
    report('scan-flow', 'no-results', `redirected to / but "Scan Results" never rendered; page shows: ${snippet}`)
  }
} catch {
  const jobState = await page.evaluate(() => document.body.innerText.slice(0, 500))
  report('scan-flow', 'scan-timeout', `scan did not complete within ${SCAN_TIMEOUT_MS}ms; page shows: ${jobState}`)
}

// --- Phase 3: route walk again — populated DB, nothing is allowed to fail ---
console.log('[e2e] Phase 3: route walk (populated DB, zero-tolerance)')
apiAllow = []
await walkRoutes('populated-db')

await browser.close()
serverProc.kill('SIGTERM')

if (findings.length > 0) {
  console.error(`\n[e2e] FAIL — ${findings.length} finding(s):`)
  for (const f of findings) console.error(`  - [${f.phase}] ${f.kind}: ${f.detail}`)
  process.exit(1)
}
console.log('\n[e2e] PASS — all routes clean, scan lifecycle verified.')
process.exit(0)
