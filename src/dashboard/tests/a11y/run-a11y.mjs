/**
 * run-a11y.mjs — A11y + console-capture test harness for QU.I.R.K. dashboard
 *
 * Usage:
 *   npm run a11y:check           — diff mode (exits 1 on new violations or unallowlisted console)
 *   npm run a11y:baseline        — update-baselines mode (writes baseline JSON for each route)
 *   npm run a11y:check:empty     — run against empty-state fixture variant
 *   npm run a11y:check:loading   — run against loading-state fixture variant
 *
 * Environment:
 *   VITE_A11Y_FIXTURE=1          — activates the Vite middleware that serves fixture JSON
 *   VITE_A11Y_FIXTURE_VARIANT    — optional: "empty" or "loading"
 *   PUPPETEER_EXECUTABLE_PATH    — fallback Chrome path if system Chrome not found
 */

import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { createConnection } from 'node:net'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import puppeteer from 'puppeteer-core'
import { AxePuppeteer } from '@axe-core/puppeteer'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
// Harness runs from src/dashboard/, so resolve relative to tests/a11y/
const DASHBOARD_DIR = resolve(__dirname, '../..')
const A11Y_DIR = __dirname

const UPDATE_BASELINES = process.argv.includes('--update-baselines')
const PREVIEW_PORT = 4173
const PREVIEW_HOST = 'localhost'
const CONNECT_TIMEOUT_MS = 30_000
const CONNECT_POLL_MS = 250

// Read config files
const ROUTES = JSON.parse(readFileSync(resolve(A11Y_DIR, 'routes.json'), 'utf8'))
const allowlistRaw = JSON.parse(readFileSync(resolve(DASHBOARD_DIR, 'tests/console-allowlist.json'), 'utf8'))
const ALLOWLIST_REGEXES = allowlistRaw.entries.map(e => new RegExp(e.pattern))

// --- Helper: wait for TCP port to accept connections ---
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

// --- Spawn vite preview with fixture env ---
const previewEnv = {
  ...process.env,
  VITE_A11Y_FIXTURE: '1',
}

// Build first if dist is missing
const distIndex = resolve(DASHBOARD_DIR, '../../quirk/dashboard/static/index.html')
if (!existsSync(distIndex)) {
  console.log('[a11y] Build artifacts missing — running npm run build...')
  const buildProc = spawn('npm', ['run', 'build'], {
    cwd: DASHBOARD_DIR,
    stdio: 'inherit',
    env: process.env,
  })
  await new Promise((res, rej) => {
    buildProc.on('close', code => code === 0 ? res() : rej(new Error(`Build failed (exit ${code})`)))
  })
}

console.log('[a11y] Starting vite preview with VITE_A11Y_FIXTURE=1...')
const previewProc = spawn('npm', ['run', 'preview', '--', '--port', String(PREVIEW_PORT)], {
  cwd: DASHBOARD_DIR,
  stdio: 'pipe',
  env: previewEnv,
})
previewProc.stderr.on('data', d => process.stderr.write(d))

// Ensure preview is killed on exit
function cleanup() {
  if (!previewProc.killed) previewProc.kill('SIGTERM')
}
process.on('exit', cleanup)
process.on('SIGINT', () => { cleanup(); process.exit(130) })
process.on('SIGTERM', () => { cleanup(); process.exit(143) })

// Wait for preview to be ready
try {
  await waitForPort(PREVIEW_HOST, PREVIEW_PORT, CONNECT_TIMEOUT_MS)
} catch (err) {
  console.error('[a11y] ERROR: Preview server did not start:', err.message)
  cleanup()
  process.exit(1)
}
console.log(`[a11y] Preview ready at http://${PREVIEW_HOST}:${PREVIEW_PORT}`)

// --- Launch headless Chrome ---
let browser
try {
  browser = await puppeteer.launch({ channel: 'chrome', headless: true, args: ['--no-sandbox'] })
} catch {
  const execPath = process.env.PUPPETEER_EXECUTABLE_PATH
  if (!execPath) {
    console.error('[a11y] ERROR: System Chrome not found. Set PUPPETEER_EXECUTABLE_PATH to a Chrome binary.')
    cleanup()
    process.exit(1)
  }
  browser = await puppeteer.launch({ executablePath: execPath, headless: true, args: ['--no-sandbox'] })
}

let exitCode = 0
const summary = []

for (const { slug, path: routePath } of ROUTES) {
  const url = `http://${PREVIEW_HOST}:${PREVIEW_PORT}${routePath}`
  console.log(`[a11y] Scanning ${slug} (${url})...`)

  const page = await browser.newPage()
  const consoleMsgs = []
  page.on('console', m => {
    if (m.type() === 'warn' || m.type() === 'error') consoleMsgs.push(m.text())
  })
  page.on('pageerror', e => consoleMsgs.push(String(e)))

  try {
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 30_000 })
  } catch (err) {
    console.error(`[a11y] ERROR: Navigation to ${url} failed: ${err.message}`)
    exitCode = 1
    await page.close()
    continue
  }

  // Run axe with WCAG 2A/2AA tags
  const results = await new AxePuppeteer(page).withTags(['wcag2a', 'wcag2aa']).analyze()

  let newViolationsCount = 0

  if (UPDATE_BASELINES) {
    // Write baseline snapshot
    const baseline = {
      violations: results.violations.map(v => ({
        id: v.id,
        nodes: v.nodes.map(n => ({ target: n.target })),
      })),
    }
    const baselinePath = resolve(A11Y_DIR, `baseline-${slug}.json`)
    writeFileSync(baselinePath, JSON.stringify(baseline, null, 2) + '\n')
    console.log(`[a11y] Wrote baseline for ${slug}: ${results.violations.length} violation(s)`)
  } else {
    // Diff mode: compare against saved baseline
    // NOTE: The baseline filename is not variant-aware. When VITE_A11Y_FIXTURE_VARIANT=empty
    // (i.e. npm run a11y:check:empty), the harness falls back to { violations: [] } for
    // every route because no baseline-<slug>-empty.json files exist. This means empty-state
    // a11y regressions are silently swallowed and will not cause CI to fail.
    // TODO: Make baselines variant-aware by writing/reading baseline-${slug}-${variant || 'default'}.json
    const baselinePath = resolve(A11Y_DIR, `baseline-${slug}.json`)
    const baseline = existsSync(baselinePath)
      ? JSON.parse(readFileSync(baselinePath, 'utf8'))
      : { violations: [] }

    // Build a set of (id, sortedTargets) keys from baseline
    const baselineKeys = new Set()
    for (const v of baseline.violations) {
      for (const n of v.nodes) {
        baselineKeys.add(`${v.id}::${[...n.target].sort().join('|')}`)
      }
    }

    const newViolations = results.violations.filter(v =>
      v.nodes.some(n => !baselineKeys.has(`${v.id}::${[...n.target].sort().join('|')}`))
    )
    newViolationsCount = newViolations.length

    if (newViolations.length > 0) {
      exitCode = 1
      console.error(`[a11y] FAIL [${slug}]: ${newViolations.length} new violation(s)`)
      for (const v of newViolations) {
        console.error(`  - ${v.id}: ${v.help}`)
        for (const n of v.nodes) {
          console.error(`    targets: ${JSON.stringify(n.target)}`)
        }
      }
    } else {
      console.log(`[a11y] PASS [${slug}]: no new violations (${results.violations.length} baseline)`)
    }
  }

  // Console allowlist check
  const unallowlisted = consoleMsgs.filter(msg => !ALLOWLIST_REGEXES.some(re => re.test(msg)))
  if (unallowlisted.length > 0) {
    exitCode = 1
    console.error(`[a11y] FAIL [${slug}]: ${unallowlisted.length} unallowlisted console message(s)`)
    for (const msg of unallowlisted) {
      console.error(`  - ${msg}`)
    }
  }

  summary.push({ slug, violations: newViolationsCount, console: unallowlisted.length })
  await page.close()
}

await browser.close()
cleanup()

console.log('\n[a11y] Summary:')
for (const { slug, violations, console: consoleCount } of summary) {
  const status = violations === 0 && consoleCount === 0 ? 'PASS' : UPDATE_BASELINES ? 'WRITTEN' : 'FAIL'
  console.log(`  ${status.padEnd(7)} ${slug} — violations: ${violations}, console: ${consoleCount}`)
}

process.exit(exitCode)
