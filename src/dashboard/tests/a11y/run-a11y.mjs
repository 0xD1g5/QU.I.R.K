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
 * Chrome-pinning status (Phase 185 D-06/D-07/D-08/D-09; supersedes Phase 165 D-04's
 * jitter-tolerance justification, named here rather than hidden):
 *   - In CI, the Chrome binary used for the a11y gate and baseline regeneration is PINNED
 *     to a concrete version (`chrome-version: '152.0.7977.82'`) in
 *     `.github/workflows/dashboard-quality.yml` per Phase 185 D-07, mechanically guarded
 *     by `pinned-deps.test.ts` per D-09 so it cannot silently drift back to a floating
 *     channel or disagree between jobs.
 *   - Locally, this harness still resolves Chrome via
 *     `puppeteer.launch({ channel: 'chrome' })`, falling back to
 *     `PUPPETEER_EXECUTABLE_PATH`, and remains DELIBERATELY unpinned per D-08 — local runs
 *     are diagnostic-only after Phase 185 and are never the source of a committed
 *     baseline, so contributors are not required to obtain a specific Chrome build.
 *   - AMENDED by Phase 216 HARNESS-03 (216-CONTEXT.md D-11), narrowing rather than
 *     reversing the claim above: exact-integer counts remain the DEFAULT for every baseline
 *     entry — this paragraph's zero-tolerance claim still holds for any entry without a
 *     declared range. Tolerance is now OPT-IN and PER-ENTRY via a `countRange: [floor,
 *     ceiling]` field on a baseline entry (see `baseline-diff.mjs`'s `compareToBaseline`).
 *   - Reason: `scrollable-region-focusable` on `/data-at-rest` is render-dependent (font
 *     metrics / overflow resolution differ between macOS and the pinned Linux Chrome), which
 *     produced a real recorded disagreement — baseline `1` locally vs `2` on CI, hand-bumped
 *     in Phase 177-07 (see `.planning/todos/completed/a11y-baseline-environment-mismatch.md`).
 *     The CI pin above makes a zero-tolerance comparison sound BETWEEN CI RUNS; it does not
 *     make a local run agree with CI, which is what this one entry needed.
 *   - A global tolerance band was REJECTED (D-10): the resolved todo above warns in writing
 *     that "a loose tolerance could hide a real regression", and a global band would apply
 *     that risk to every baseline to fix one entry. The range stays opt-in and per-entry.
 *   - The stale-entry leg ("count is BELOW baseline — Baseline is stale") still fires against
 *     a declared range's LOWER bound (D-12) — a range is not a one-way ratchet in the wrong
 *     direction.
 *   - RETIRED by Phase 219 (KBD-01, 219-03, CI run 36795176372): `components/ui/table.tsx`
 *     gained conditional `tabIndex`/`role`/`aria-label` on its scroll wrapper (applied only
 *     while actually overflowing), and `scrollable-region-focusable` withdrew outright across
 *     every route and fixture variant — the render-dependence this range existed to absorb no
 *     longer produces any violation to range. The `countRange` field itself (the opt-in,
 *     per-entry mechanism in `baseline-diff.mjs`'s `compareToBaseline`) remains available for a
 *     future render-dependent entry; no committed baseline currently declares one.
 *   - 221 D-02 (preview lifecycle): the `npm -> sh -> vite` chain orphans the vite grandchild on
 *     Linux when only the npm pid is signalled, so every sweep after the first measured sweep
 *     1's default-variant server (CI run 36881093817: "Preview ready" 15-19 ms after the
 *     previous sweep's). The preview is therefore spawned detached in its own process group
 *     and the whole group is killed (SIGTERM, escalating to SIGKILL); `--strictPort` refuses a
 *     silent port hop; a pre-spawn free-port check, a post-shutdown free-port assertion and the
 *     /__a11y-variant identity sentinel together make "the server this sweep measured is the
 *     server it spawned" checkable rather than assumed.
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
import { buildBaselineEntries, compareToBaseline, resolveVariant, resolveTheme, baselineFilename } from './baseline-diff.mjs'
import { renderStateViolations, DEFAULT_LOADING_SELECTOR } from './variant-guard.mjs'
import { matchHandler } from './fixture-handlers.mjs'

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
// 216 D-01/D-02: the theme dimension, named explicitly at the choke point rather than left
// implicit. No sweep-behaviour change here — THEME resolves to 'dark' with no env set, so an
// unset A11Y_THEME run stays byte-equivalent to before this plan apart from filenames.
const THEME = resolveTheme(process.env)
console.log(`[a11y] Theme: ${THEME}`)

// 216 D-03: light is swept for the default fixture variant only. `empty` renders
// EmptyStateCard and `loading` renders skeletons — neither emits a badge variant, so a light
// sweep there would carry no signal (the existing VARIANT !== 'default' interaction skip
// below is the same rationale, applied here to the whole run rather than one section of it).
// A silent skip here would be indistinguishable from a broken invocation — this harness's own
// idiom is that skips are logged, never silent — so this refuses loudly and exits before the
// preview server or browser are even started.
if (THEME !== 'dark' && VARIANT !== 'default') {
  console.error(
    `[a11y] REFUSED: theme=${THEME} is only swept for the default fixture variant (216 D-03) — ` +
      `the empty variant renders EmptyStateCard and loading renders skeletons, neither of which ` +
      `emits a badge variant`,
  )
  process.exit(1)
}

// 216 D-01: the harness-side literal copy of the app's localStorage theme key
// (src/components/theme-context.ts's THEME_STORAGE_KEY). This file is `.mjs` and cannot
// import from the app's `.ts` module, so the literal is duplicated deliberately;
// theme-sweep-contract.test.ts mechanically asserts the two copies stay equal (D-01).
const THEME_STORAGE_KEY = 'quirk-ui-theme'

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

// 221 D-02: refuse to sweep when something already answers on the port. A stale preview left
// by a previous sweep would otherwise be measured instead of the server this run spawns.
function assertPortFree(host, port) {
  return new Promise(resolveP => {
    const socket = createConnection({ host, port })
    socket.on('connect', () => { socket.destroy(); resolveP(false) })
    socket.on('error', () => { socket.destroy(); resolveP(true) })
  })
}
if (!(await assertPortFree(PREVIEW_HOST, PREVIEW_PORT))) {
  console.error(
    `[a11y] FAIL: port ${PREVIEW_PORT} already answers before this sweep spawned its own preview — stale server from a previous sweep? (221 D-02)`,
  )
  process.exit(1)
}

console.log('[a11y] Starting vite preview with VITE_A11Y_FIXTURE=1...')
const previewProc = spawn('npm', ['run', 'preview', '--', '--port', String(PREVIEW_PORT), '--strictPort'], {
  cwd: DASHBOARD_DIR,
  stdio: ['ignore', 'pipe', 'pipe'],
  env: previewEnv,
  detached: true,
})
previewProc.stderr.on('data', d => process.stderr.write(d))
// 221: stdout carries vite's "Port 4173 is in use, trying another one" notice.
previewProc.stdout.on('data', d => process.stdout.write(d))

// Ensure preview is killed on exit
// 221 D-02: signal the whole process group (negative pid), not just the npm wrapper.
// Synchronous so it is safe inside process.on('exit').
function cleanup() {
  if (previewProc.pid) {
    try { process.kill(-previewProc.pid, 'SIGTERM') } catch {}
  }
}

// 221 D-02: normal-end shutdown that proves the port was actually released.
async function waitForPortFree(timeoutMs) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await assertPortFree(PREVIEW_HOST, PREVIEW_PORT)) return true
    await new Promise(r => setTimeout(r, 100))
  }
  return await assertPortFree(PREVIEW_HOST, PREVIEW_PORT)
}
async function shutdownPreview() {
  cleanup()
  if (!(await waitForPortFree(3_000))) {
    if (previewProc.pid) {
      try { process.kill(-previewProc.pid, 'SIGKILL') } catch {}
    }
    await waitForPortFree(2_000)
  }
  if (!(await assertPortFree(PREVIEW_HOST, PREVIEW_PORT))) {
    console.error(
      `[a11y] FAIL: preview server still listening on ${PREVIEW_PORT} after group SIGKILL — next sweep would measure a stale server (221 D-02)`,
    )
    exitCode = 1
  } else {
    console.log(`[a11y] Preview shut down; port ${PREVIEW_PORT} free`)
  }
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

// 221 D-02: identity assertion — the server on the port must be the one this sweep spawned,
// serving the variant this sweep asked for.
let identity = null
try {
  const resp = await fetch(`http://${PREVIEW_HOST}:${PREVIEW_PORT}/__a11y-variant`)
  identity = await resp.json()
} catch {
  identity = null
}
if (!identity || identity.variant !== VARIANT) {
  console.error(
    `[a11y] FAIL: preview server reports variant ${identity ? identity.variant : '(no sentinel response)'}, expected ${VARIANT} — not the server this sweep spawned (221 D-02)`,
  )
  cleanup()
  process.exit(1)
}
console.log(`[a11y] Preview identity confirmed: variant=${identity.variant} pid=${identity.pid}`)

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

for (const { slug, path: routePath, contentMarker, interaction, variantMarkers, unmarkedEndpoints, variantInsensitive, loadingSelector } of ROUTES) {
  const url = `http://${PREVIEW_HOST}:${PREVIEW_PORT}${routePath}`
  console.log(`[a11y] Scanning ${slug} [${THEME}] (${url})...`)

  const page = await browser.newPage()
  // 216 D-01: seed the app's real theme-provider path by writing its localStorage key
  // BEFORE any page script runs — exercising `getStoredTheme`'s useState initializer exactly
  // as a real user visit would, rather than diverging from it. Rejected: forcing
  // `documentElement.classList` after load (diverges from the app path and races the
  // provider's effect); CDP `Emulation.setEmulatedMedia` (a silent no-op, because
  // `theme-provider.tsx` only consults `matchMedia` when `theme === 'system'`, which the
  // harness never sweeps). Registered once per page — this loop already opens a fresh page
  // per route, so hoisting this call out of the loop would leave two registrations firing on
  // the same page and silently reintroduce single-theme sweeping one layer down.
  await page.evaluateOnNewDocument(
    (key, value) => { localStorage.setItem(key, value) },
    THEME_STORAGE_KEY,
    THEME,
  )
  const consoleMsgs = []
  page.on('console', m => {
    if (m.type() === 'warn' || m.type() === 'error') consoleMsgs.push(m.text())
  })
  page.on('pageerror', e => consoleMsgs.push(String(e)))
  // 221 D-06: record every /api/ request so consumption is derived at run time.
  const apiRequests = []
  page.on('request', r => {
    try {
      const u = new URL(r.url())
      if (u.pathname.startsWith('/api/')) apiRequests.push(u.pathname + u.search)
    } catch {}
  })

  // 221 D-08: under `loading` the held request never settles, so networkidle2 would time out.
  // Navigate on 'load', then wait for the skeleton as positive proof of the loading state.
  const waitUntil = VARIANT === 'loading' ? 'load' : 'networkidle2'
  try {
    await page.goto(url, { waitUntil, timeout: 30_000 })
  } catch (err) {
    console.error(`[a11y] ERROR: Navigation to ${url} failed: ${err.message}`)
    exitCode = 1
    // Record the route so it appears in the summary table. Without this the
    // run still fails (exitCode is 1), but the route vanishes from the summary
    // and a maintainer has to scroll the raw log to find which one broke.
    summary.push({ slug, violations: 0, console: consoleMsgs.length, incomplete: 0, status: 'NAV_ERR' })
    await page.close()
    continue
  }

  // D-14 content-marker check — a route can declare an optional `contentMarker` CSS
  // selector in routes.json. This is checked here, AFTER navigation and BEFORE both the
  // axe scan and (in --update-baselines mode) any writeFileSync, so a route that renders
  // empty under the fixture harness fails loudly instead of producing a hollow baseline
  // or a hollow-but-passing diff. Restricted to the DEFAULT variant only (skipped for
  // VARIANT === 'empty'/'loading'): D-13's `empty` variant is intentionally empty and
  // `loading` intentionally shows a skeleton, so enforcing a content marker there would
  // contradict the fixture's own purpose — D-14 only asks that the DEFAULT variant render
  // real content. Uses a plain CSS selector via Puppeteer's standard `page.$()` support
  // (RESEARCH.md Assumption A3 flags `text=` pseudo-selector support as unconfirmed for
  // the pinned puppeteer-core 24.43.1 — a CSS selector is always available).
  if (contentMarker && VARIANT === 'default') {
    const found = await page.waitForSelector(contentMarker, { timeout: 5_000 }).catch(() => null)
    if (!found) {
      console.error(
        `[a11y] FAIL [${slug}]: content marker "${contentMarker}" not found — route rendered empty`,
      )
      exitCode = 1
      summary.push({ slug, violations: 0, console: consoleMsgs.length, incomplete: 0, status: 'FAIL' })
      await page.close()
      continue
    }
  }

  // 221 D-05: render-state guard. BEFORE the axe scan and any baseline write. Under default
  // every declared marker must be present; under empty/loading every one must be absent (and
  // under loading the skeleton must be present). A sweep that measured the wrong server or a
  // fixture that did not take effect fails here instead of baselining a hollow page.
  if (variantMarkers) {
    const present = {}
    let skeleton
    if (VARIANT === 'loading') {
      skeleton = !!(await page.waitForSelector(loadingSelector ?? DEFAULT_LOADING_SELECTOR, { timeout: 5_000 }).catch(() => null))
    }
    // 221 D-06: any honouring, non-chrome handler this page actually requested must be declared.
    const hitIds = [...new Set(apiRequests.map(u => matchHandler(u)).filter(Boolean)
      .filter(h => h.scope !== 'chrome' && (h.empty.body !== undefined || h.empty.emptyFrom) && h.loading.hold === true)
      .map(h => h.id))]
    const declared = new Set([...Object.keys(variantMarkers), ...Object.keys(unmarkedEndpoints ?? {})])
    const undeclared = hitIds.filter(id => !declared.has(id))
    for (const id of undeclared) {
      console.error(
        `[a11y] FAIL [${slug}]: page requested honouring endpoint '${id}' that routes.json does not declare — add a marker or an unmarkedEndpoints reason (221 D-06)`,
      )
    }
    if (undeclared.length > 0) {
      exitCode = 1
      summary.push({ slug, violations: 0, console: consoleMsgs.length, incomplete: 0, status: 'FAIL' })
      await page.close()
      continue
    }
    for (const selector of Object.values(variantMarkers)) {
      if (VARIANT === 'default') {
        present[selector] = !!(await page.waitForSelector(selector, { timeout: 5_000 }).catch(() => null))
      } else {
        present[selector] = !!(await page.$(selector))
      }
    }
    const rsViolations = renderStateViolations({
      variant: VARIANT,
      slug,
      markers: variantMarkers,
      present,
      skeleton,
      loadingSelector: loadingSelector ?? DEFAULT_LOADING_SELECTOR,
    })
    if (rsViolations.length > 0) {
      for (const line of rsViolations) console.error(`[a11y] FAIL [${slug}]: ${line}`)
      exitCode = 1
      summary.push({ slug, violations: 0, console: consoleMsgs.length, incomplete: 0, status: 'FAIL' })
      await page.close()
      continue
    }
  } else if (variantInsensitive) {
    console.log(`[a11y] NOTE [${slug}]: variant-insensitive — ${variantInsensitive}`)
    const hit = [...new Set(apiRequests.map(u => matchHandler(u)).filter(Boolean)
      .filter(h => h.scope !== 'chrome' && (h.empty.body !== undefined || h.empty.emptyFrom) && h.loading.hold === true)
      .map(h => h.id))]
    console.log(`[a11y] NOTE [${slug}]: honouring endpoints hit: ${hit.join(', ') || '(none)'}`)
  }

  // Run axe with WCAG 2A/2AA tags
  const results = await new AxePuppeteer(page).withTags(['wcag2a', 'wcag2aa']).analyze()
  // RESEARCH Pitfall 3 / Assumption A2: axe's `incomplete` array holds rules it could not
  // resolve either way (e.g. a `color-contrast` check it cannot compute) — never gated on
  // this phase, but logged so a needs-manual-review result is visible rather than invisible.
  const incompleteCount = results.incomplete.length
  console.log(`[a11y] ${slug} [${THEME}]: violations=${results.violations.length} incomplete=${incompleteCount}`)

  let newViolationsCount = 0
  let routeStatus = 'PASS'

  const baselinePath = resolve(A11Y_DIR, baselineFilename(slug, VARIANT, THEME))

  if (UPDATE_BASELINES) {
    // Write baseline snapshot: per-(route, rule) count budget (D-01), no selectors stored
    // (D-02), justifications carried forward from the previous file (165-CONTEXT.md D-06,
    // and — for the merge-not-rewrite property this carry-forward implements — Phase 185 D-05).
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
      // 216 D-15: the remediation command names the theme too, not just the variant — a
      // missing light baseline must point at `a11y:baseline:light`, never the dark command.
      const generateCmd =
        THEME === 'light'
          ? 'npm run a11y:baseline:light'
          : VARIANT === 'default'
            ? 'npm run a11y:baseline'
            : `npm run a11y:baseline:${VARIANT}`
      console.error(
        `[a11y] FAIL [${slug}]: missing baseline file ${baselinePath} — run \`${generateCmd}\` to generate it`,
      )
      exitCode = 1
      routeStatus = 'FAIL'
      summary.push({ slug, violations: 0, console: 0, incomplete: 0, status: routeStatus })
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

  // Phase 202-07 — optional per-route interaction step (F10a/F10b/F10c). Declared via
  // routes.json's `interaction: { slug, trigger, awaitSelector }` on the EXISTING route
  // entry — never a routes.json ROUTE entry of its own, so the base route above is always
  // scanned with the drawer closed and this is the only place the opened state is
  // captured. Runs AFTER the primary route's axe scan/baseline handling and BEFORE the
  // console-allowlist check below, so `consoleMsgs` (collected by the page-lifetime
  // listener registered above) picks up any console output the interaction itself
  // produces — F8 is specifically about that post-open console state.
  if (interaction) {
    const { slug: interactionSlug, trigger, awaitSelector } = interaction

    if (VARIANT !== 'default') {
      // F10c: the `empty` variant renders EmptyStateCard and `loading` renders
      // FindingsSkeleton — neither has table rows, so there is no trigger and no drawer
      // to open. This skip is a LOGGED line, never a silent continue: a silent failure to
      // find the selector would be indistinguishable from the trigger being broken.
      console.log(
        `[a11y] SKIP [${interactionSlug}] (route: ${slug}, variant: ${VARIANT}): interaction skipped by design — no table rows in this variant`,
      )
    } else {
      const triggerHandle = await page.waitForSelector(trigger, { timeout: 5_000 }).catch(() => null)
      if (!triggerHandle) {
        console.error(`[a11y] FAIL [${interactionSlug}]: trigger "${trigger}" not found`)
        exitCode = 1
        summary.push({ slug: interactionSlug, violations: 0, console: 0, incomplete: 0, status: 'FAIL' })
      } else {
        await triggerHandle.click()
        const opened = await page.waitForSelector(awaitSelector, { timeout: 5_000 }).catch(() => null)
        if (!opened) {
          console.error(
            `[a11y] FAIL [${interactionSlug}]: awaitSelector "${awaitSelector}" never appeared after clicking trigger — drawer did not open`,
          )
          exitCode = 1
          summary.push({ slug: interactionSlug, violations: 0, console: 0, incomplete: 0, status: 'FAIL' })
        } else {
          // Second, independent axe scan of the opened state — reuses the exact same
          // helpers the primary route scan above uses (buildBaselineEntries /
          // compareToBaseline / baselineFilename); no parallel baseline code path.
          const interactionResults = await new AxePuppeteer(page).withTags(['wcag2a', 'wcag2aa']).analyze()
          const interactionIncompleteCount = interactionResults.incomplete.length
          console.log(`[a11y] ${interactionSlug} [${THEME}]: violations=${interactionResults.violations.length} incomplete=${interactionIncompleteCount}`)

          let interactionViolationsCount = 0
          let interactionStatus = 'PASS'
          const interactionBaselinePath = resolve(A11Y_DIR, baselineFilename(interactionSlug, VARIANT, THEME))

          if (UPDATE_BASELINES) {
            const previous = existsSync(interactionBaselinePath)
              ? JSON.parse(readFileSync(interactionBaselinePath, 'utf8'))
              : null
            const previousEntries = previous?.entries ?? []

            const { entries, refusedCritical } = buildBaselineEntries(
              interactionSlug,
              interactionResults.violations,
              { previousEntries },
            )

            const baseline = {
              route: interactionSlug,
              generated: new Date().toISOString(),
              entries,
            }
            writeFileSync(interactionBaselinePath, JSON.stringify(baseline, null, 2) + '\n')
            console.log(`[a11y] Wrote baseline for ${interactionSlug}: ${entries.length} rule(s)`)

            if (refusedCritical.length > 0) {
              exitCode = 1
              interactionStatus = 'FAIL'
              for (const entry of refusedCritical) {
                console.error(
                  `[a11y] REFUSED [${interactionSlug}]: ${entry.rule} is impact:critical and cannot be baselined — fix it in the UI`,
                )
              }
            }
          } else {
            if (!existsSync(interactionBaselinePath)) {
              const generateCmd =
                THEME === 'light'
                  ? 'npm run a11y:baseline:light'
                  : VARIANT === 'default'
                    ? 'npm run a11y:baseline'
                    : `npm run a11y:baseline:${VARIANT}`
              console.error(
                `[a11y] FAIL [${interactionSlug}]: missing baseline file ${interactionBaselinePath} — run \`${generateCmd}\` to generate it`,
              )
              exitCode = 1
              interactionStatus = 'FAIL'
            } else {
              const baseline = JSON.parse(readFileSync(interactionBaselinePath, 'utf8'))
              const { regressions, staleEntries, criticalViolations, missingJustifications } =
                compareToBaseline(interactionSlug, interactionResults.violations, baseline.entries ?? [])

              interactionViolationsCount = regressions.length

              for (const r of regressions) {
                exitCode = 1
                interactionStatus = 'FAIL'
                console.error(
                  `[a11y] FAIL [${interactionSlug}]: ${r.rule} count ${r.observedCount} exceeds baseline ${r.baselineCount}`,
                )
                if (r.samples[0]) {
                  console.error(`    sample: ${r.samples[0]}`)
                }
              }

              for (const s of staleEntries) {
                exitCode = 1
                interactionStatus = 'FAIL'
                console.error(
                  `[a11y] FAIL [${interactionSlug}]: ${s.rule} count ${s.observedCount} is BELOW baseline ${s.baselineCount} — Baseline is stale — run npm run a11y:baseline to tighten`,
                )
              }

              for (const c of criticalViolations) {
                exitCode = 1
                interactionStatus = 'FAIL'
                console.error(`[a11y] FAIL [${interactionSlug}]: ${c.rule} is impact:critical — never baselineable`)
              }

              for (const m of missingJustifications) {
                exitCode = 1
                interactionStatus = 'FAIL'
                console.error(`[a11y] FAIL [${interactionSlug}]: ${m.rule} has no written justification`)
              }

              if (
                regressions.length === 0 &&
                staleEntries.length === 0 &&
                criticalViolations.length === 0 &&
                missingJustifications.length === 0
              ) {
                console.log(
                  `[a11y] PASS [${interactionSlug}]: no regressions (${interactionResults.violations.length} live)`,
                )
              }
            }
          }

          if (UPDATE_BASELINES && interactionStatus !== 'FAIL') {
            interactionStatus = 'WRITTEN'
          }

          summary.push({
            slug: interactionSlug,
            violations: interactionViolationsCount,
            console: 0,
            incomplete: interactionIncompleteCount,
            status: interactionStatus,
          })
        }
      }
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

  summary.push({ slug, violations: newViolationsCount, console: unallowlisted.length, incomplete: incompleteCount, status: routeStatus })
  await page.close()
}

await browser.close()
await shutdownPreview()

// 216 D-17: in-process ledger collection is gone. Theme is now a per-process dimension
// (D-01/D-02), so a single `--update-baselines` invocation can only ever see ONE theme — it
// was structurally incapable of producing a theme-complete ACCEPTED-VIOLATIONS.md, and left
// alone would silently narrow the ledger to whichever theme's process ran last. Regeneration
// now reads every committed baseline file from disk across every theme
// (`tests/a11y/ledger-input.mjs`), so it cannot be partial by construction. Run the dedicated
// command afterward instead of writing here.
if (UPDATE_BASELINES) {
  console.log(
    '[a11y] Baselines written. Run `npm run a11y:ledger` to regenerate ACCEPTED-VIOLATIONS.md across all themes.',
  )
}

console.log('\n[a11y] Summary:')
for (const { slug, violations, console: consoleCount, incomplete, status } of summary) {
  console.log(`  ${status.padEnd(7)} ${slug} — violations: ${violations}, console: ${consoleCount}, incomplete: ${incomplete ?? 0}`)
}

process.exit(exitCode)
