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
 *
 * Deliberately-unpinned and indirectly-pinned inputs (D-04, A11Y-05) — named here rather
 * than hidden, since both decide what axe reports on a given run:
 *   - The Chrome binary is resolved via `puppeteer.launch({ channel: 'chrome' })`, falling
 *     back to `PUPPETEER_EXECUTABLE_PATH`. It is NOT version pinned. This is a deliberate,
 *     named residual risk, mitigated (not eliminated) by D-01's count-budget key tolerating
 *     rendering jitter across Chrome versions.
 *   - The axe rule definitions come from `axe-core` 4.11.4, pinned only indirectly through
 *     `@axe-core/puppeteer`'s exact version pin in package.json.
 */

import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { createConnection } from 'node:net'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import puppeteer from 'puppeteer-core'
import { AxePuppeteer } from '@axe-core/puppeteer'
import { buildBaselineEntries, compareToBaseline, resolveVariant, baselineFilename } from './baseline-diff.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
// Harness runs from src/dashboard/, so resolve relative to tests/a11y/
const DASHBOARD_DIR = resolve(__dirname, '../..')
const A11Y_DIR = __dirname

const UPDATE_BASELINES = process.argv.includes('--update-baselines')
// D-15/D-16: baseline filenames are variant-aware (baseline-{slug}-{variant}.json), so the
// empty and loading fixture variants each hold their own baseline data. A missing baseline
// file is a deliberate hard error, not a silent empty-violations fallback — that silent
// fallback was the actual defect that made the empty-state CI gate a no-op.
const VARIANT = resolveVariant(process.env)
console.log(`[a11y] Fixture variant: ${VARIANT}`)
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
  let routeStatus = 'PASS'

  const baselinePath = resolve(A11Y_DIR, baselineFilename(slug, VARIANT))

  if (UPDATE_BASELINES) {
    // Write baseline snapshot: per-(route, rule) count budget (D-01), no selectors stored
    // (D-02), justifications carried forward from the previous file (D-06).
    const previous = existsSync(baselinePath)
      ? JSON.parse(readFileSync(baselinePath, 'utf8'))
      : null
    const previousEntries = previous?.entries ?? []

    const { entries, refusedCritical } = buildBaselineEntries(slug, results.violations, {
      previousEntries,
    })

    const baseline = {
      route: slug,
      generated: new Date().toISOString(),
      entries,
    }
    writeFileSync(baselinePath, JSON.stringify(baseline, null, 2) + '\n')
    console.log(`[a11y] Wrote baseline for ${slug}: ${entries.length} rule(s)`)

    if (refusedCritical.length > 0) {
      exitCode = 1
      routeStatus = 'FAIL'
      for (const entry of refusedCritical) {
        console.error(
          `[a11y] REFUSED [${slug}]: ${entry.rule} is impact:critical and cannot be baselined — fix it in the UI`,
        )
      }
    }
  } else {
    // Diff mode: compare live per-(route, rule) counts against the saved baseline (D-01/D-13),
    // refusing any critical-impact violation regardless of baseline state (D-14) and failing
    // on any missing/placeholder justification (D-06).
    //
    // A missing baseline file is a deliberate hard error, not a silent empty-violations
    // fallback (D-15) — that fallback was the actual defect that made the empty-state CI gate
    // a no-op: it made every route unconditionally pass regardless of live violations.
    if (!existsSync(baselinePath)) {
      const generateCmd =
        VARIANT === 'default'
          ? 'npm run a11y:baseline'
          : `npm run a11y:baseline:${VARIANT}`
      console.error(
        `[a11y] FAIL [${slug}]: missing baseline file ${baselinePath} — run \`${generateCmd}\` to generate it`,
      )
      exitCode = 1
      routeStatus = 'FAIL'
      summary.push({ slug, violations: 0, console: 0, status: routeStatus })
      await page.close()
      continue
    }

    const baseline = JSON.parse(readFileSync(baselinePath, 'utf8'))

    const { regressions, staleEntries, criticalViolations, missingJustifications } =
      compareToBaseline(slug, results.violations, baseline.entries ?? [])

    newViolationsCount = regressions.length

    for (const r of regressions) {
      exitCode = 1
      routeStatus = 'FAIL'
      console.error(
        `[a11y] FAIL [${slug}]: ${r.rule} count ${r.observedCount} exceeds baseline ${r.baselineCount}`,
      )
      if (r.samples[0]) {
        console.error(`    sample: ${r.samples[0]}`)
      }
    }

    for (const s of staleEntries) {
      exitCode = 1
      routeStatus = 'FAIL'
      console.error(
        `[a11y] FAIL [${slug}]: ${s.rule} count ${s.observedCount} is BELOW baseline ${s.baselineCount} — Baseline is stale — run npm run a11y:baseline to tighten`,
      )
    }

    for (const c of criticalViolations) {
      exitCode = 1
      routeStatus = 'FAIL'
      console.error(`[a11y] FAIL [${slug}]: ${c.rule} is impact:critical — never baselineable`)
    }

    for (const m of missingJustifications) {
      exitCode = 1
      routeStatus = 'FAIL'
      console.error(`[a11y] FAIL [${slug}]: ${m.rule} has no written justification`)
    }

    if (
      regressions.length === 0 &&
      staleEntries.length === 0 &&
      criticalViolations.length === 0 &&
      missingJustifications.length === 0
    ) {
      console.log(`[a11y] PASS [${slug}]: no regressions (${results.violations.length} live)`)
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
  if (unallowlisted.length > 0) {
    routeStatus = 'FAIL'
  }

  if (UPDATE_BASELINES && routeStatus !== 'FAIL') {
    routeStatus = 'WRITTEN'
  }

  summary.push({ slug, violations: newViolationsCount, console: unallowlisted.length, status: routeStatus })
  await page.close()
}

await browser.close()
cleanup()

console.log('\n[a11y] Summary:')
for (const { slug, violations, console: consoleCount, status } of summary) {
  console.log(`  ${status.padEnd(7)} ${slug} — violations: ${violations}, console: ${consoleCount}`)
}

process.exit(exitCode)
