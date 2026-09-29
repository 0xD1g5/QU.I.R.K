#!/usr/bin/env node
/**
 * regenerate-ledger.mjs — browser-free CLI entry point for `npm run a11y:ledger`.
 *
 * Phase 216 / HARNESS-01 / 216-CONTEXT.md D-17
 *
 * Renders ACCEPTED-VIOLATIONS.md from the committed `baseline-*.json` files already on disk,
 * via the shared `loadLedgerInput()` (ledger-input.mjs) and the existing pure
 * `generateMarkdown()` (generate-accepted-violations.mjs, unchanged by this plan). This process
 * opens no browser, spawns no preview server, and touches no network — the ledger is a
 * rendering of already-committed JSON, so regenerating it locally does NOT violate D-15's
 * Linux-provenance rule, which governs baseline COUNTS (produced by an actual axe sweep, a
 * fundamentally different operation with real cross-platform render risk). Rendering
 * already-committed counts into markdown carries none of that risk.
 *
 * This replaces the old in-process ledger write in run-a11y.mjs (guarded
 * `UPDATE_BASELINES && VARIANT === 'default'`), which could only ever see the ONE theme that
 * process happened to sweep and was therefore structurally incapable of producing a
 * theme-complete ledger (D-17). Run this after any `npm run a11y:baseline*` invocation, or as
 * the dedicated CI step in the `a11y-regenerate-baselines` job, positioned after every
 * `a11y:baseline*` step and before the artifact upload so the uploaded ledger covers every
 * theme that run produced.
 */

import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { loadLedgerInput } from './ledger-input.mjs'
import { generateMarkdown } from './generate-accepted-violations.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const A11Y_DIR = __dirname
const LEDGER_PATH = resolve(A11Y_DIR, 'ACCEPTED-VIOLATIONS.md')

const routes = JSON.parse(readFileSync(resolve(A11Y_DIR, 'routes.json'), 'utf-8'))
const { input, missing } = loadLedgerInput(A11Y_DIR, routes)

// Every missing (slug, theme) pair is logged — never silent — mirroring the harness's own
// "a missing baseline is a hard error, never a silent empty-violations fallback" idiom
// (run-a11y.mjs D-15 comment). A missing `light` file is expected pre-216-08 and logged as a
// warning; a missing `dark` file is unconditional and fails this command.
let hasMissingDark = false
for (const { theme, path: missingPath } of missing) {
  console.warn(`[a11y] WARN missing baseline: ${missingPath}`)
  if (theme === 'dark') hasMissingDark = true
}

const markdown = generateMarkdown(input, 'default')
writeFileSync(LEDGER_PATH, markdown)
console.log(`[a11y] Regenerated ${LEDGER_PATH}`)

if (hasMissingDark) {
  console.error(
    '[a11y] ERROR: at least one dark default baseline is missing — the ledger just written is incomplete',
  )
  process.exit(1)
}
