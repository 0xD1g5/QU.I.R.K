// Phase 165 / A11Y-01, A11Y-03 / 165-CONTEXT.md D-05, D-06, D-07
//
// Mirrors tests/test_error_codes_freshness.py — both prevent silent drift between a generator
// and its committed output. Here, ACCEPTED-VIOLATIONS.md is the committed, human-readable
// decision record; generateMarkdown(...) is its generator; the committed default-variant
// baseline-*.json files are the source of truth it is generated from. Called in-process
// (direct import) rather than spawning a separate process, since both sides already live in
// the same JS module graph — cheaper and strictly more reliable than the Python original's
// approach, which shells out to a separate CLI.
import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import path from 'node:path'
import { generateMarkdown } from './generate-accepted-violations.mjs'
import { baselineFilename, isPlaceholderJustification, THEMES } from './baseline-diff.mjs'
import { allBaselineSlugs, loadLedgerInput, incompleteThemeMisses } from './ledger-input.mjs'

const A11Y_DIR = __dirname
const ACCEPTED_VIOLATIONS_MD = path.resolve(A11Y_DIR, 'ACCEPTED-VIOLATIONS.md')
const REGEN_COMMAND = 'npm run a11y:ledger'
interface RouteEntry {
  slug: string
  path: string
  interaction?: { slug: string; trigger: string; awaitSelector: string }
}

const routes: RouteEntry[] = JSON.parse(
  readFileSync(path.resolve(A11Y_DIR, 'routes.json'), 'utf-8'),
)

// 216 D-17: the gate and the generator now consume the SAME disk-derived, theme-complete
// input (ledger-input.mjs's loadLedgerInput/allBaselineSlugs) by construction, rather than
// two hand-synced copies — the defect class CLAUDE.md's Staleness Review Cadence section
// documents six prior instances of in this project. `input` is the generateMarkdown-shaped,
// theme-labelled array (`route: "${slug} [${theme}]"`); `allEntries()` below flattens it for
// the per-entry assertions that don't care about theme grouping.
function ledgerInput() {
  return loadLedgerInput(A11Y_DIR, routes)
}

function allEntries() {
  const { input } = ledgerInput()
  return input.flatMap(({ route, entries }) => entries.map(entry => ({ route, ...entry })))
}

describe('ACCEPTED-VIOLATIONS.md freshness (A11Y-01 / D-05)', () => {
  it('exists', () => {
    expect(
      existsSync(ACCEPTED_VIOLATIONS_MD),
      `ACCEPTED-VIOLATIONS.md is missing. Generate with: ${REGEN_COMMAND}`,
    ).toBe(true)
  })

  it('is current — byte-matches generateMarkdown() called on the disk-derived, theme-complete input', () => {
    const { input } = ledgerInput()
    const generated = generateMarkdown(input).replace(/\n+$/, '')
    const current = existsSync(ACCEPTED_VIOLATIONS_MD)
      ? readFileSync(ACCEPTED_VIOLATIONS_MD, 'utf-8').replace(/\n+$/, '')
      : ''
    expect(generated, `ACCEPTED-VIOLATIONS.md is stale. Regenerate with: ${REGEN_COMMAND}`).toBe(
      current,
    )
  })

  it('every entry across every committed default baseline has a non-empty, non-placeholder justification (D-06)', () => {
    const entries = allEntries()
    expect(entries.length).toBeGreaterThan(0)
    for (const entry of entries) {
      expect(
        isPlaceholderJustification(entry.justification),
        `${entry.route}/${entry.rule} has no written justification: ${JSON.stringify(entry.justification)}`,
      ).toBe(false)
    }
  })

  it('every entry has a non-empty impact and at least one WCAG criterion (D-06)', () => {
    const entries = allEntries()
    expect(entries.length).toBeGreaterThan(0)
    for (const entry of entries) {
      expect(typeof entry.impact === 'string' && entry.impact.length > 0).toBe(true)
      expect(Array.isArray(entry.wcag) && entry.wcag.length > 0).toBe(true)
    }
  })

  it('no entry has impact === "critical" — a screen-reader blocker cannot be accepted (A11Y-02, D-14)', () => {
    const entries = allEntries()
    for (const entry of entries) {
      expect(entry.impact).not.toBe('critical')
    }
  })

  it('the sum of count across every entry equals the ledger totals line (D-07 reconstructibility)', () => {
    const entries = allEntries()
    const totalCount = entries.reduce((sum, e) => sum + (e.count ?? 0), 0)
    const { input } = ledgerInput()
    const generated = generateMarkdown(input)
    const totalsLine = generated
      .split('\n')
      .find(line => line.startsWith('Totals:'))
    expect(totalsLine, 'ACCEPTED-VIOLATIONS.md must have a Totals: line').toBeDefined()
    expect(totalsLine).toContain(`${totalCount} accepted violation node(s)`)
  })

  it('no entry stores a selector — no key named "target" appears anywhere in any committed baseline, for every theme (D-01, D-02)', () => {
    // 216 D-17: widened from dark-only to every (slug, theme) pair — the freshness gate must
    // not go blind to a `target` leak in a theme it doesn't happen to load by default.
    for (const slug of allBaselineSlugs(routes)) {
      for (const theme of THEMES) {
        const baselinePath = path.resolve(A11Y_DIR, baselineFilename(slug, 'default', theme))
        if (!existsSync(baselinePath)) continue
        const raw = readFileSync(baselinePath, 'utf-8')
        expect(raw).not.toMatch(/"target"\s*:/)
      }
    }
  })

  it('every slug has a committed dark default baseline (216 D-17)', () => {
    const { missing } = ledgerInput()
    const missingDark = missing.filter(m => m.theme === 'dark')
    expect(
      missingDark.map(m => m.slug),
      `Missing dark default baseline(s): ${missingDark.map(m => m.slug).join(', ')}. Generate the missing baseline file(s) (dark theme) for the affected route(s), then regenerate the ledger with: ${REGEN_COMMAND}`,
    ).toEqual([])
  })

  it('no theme is half-committed (216 D-17)', () => {
    // A theme with at least one committed default baseline must have one for EVERY slug.
    // `light` is exempt from this rule until at least one light baseline exists on disk
    // (216-08 generates those on Linux CI, sequenced after this plan) — see
    // incompleteThemeMisses's docstring for the full sequencing rationale.
    const { presentThemes, missing } = ledgerInput()
    const incomplete = incompleteThemeMisses(missing, presentThemes)
    expect(
      incomplete,
      `Half-committed theme(s) detected: ${JSON.stringify(incomplete)}`,
    ).toEqual([])
  })

  it('the ledger names every theme present on disk (216 D-17)', () => {
    const { input, presentThemes } = ledgerInput()
    const generated = generateMarkdown(input)
    for (const theme of presentThemes) {
      expect(generated, `ACCEPTED-VIOLATIONS.md is missing a [${theme}] heading despite ${theme} baselines existing on disk`).toContain(`[${theme}]`)
    }
  })

  it('no (slug, theme) pair appears twice in the ledger input (216 D-17)', () => {
    const { input } = ledgerInput()
    const routeKeys = input.map(({ route }) => route)
    expect(new Set(routeKeys).size, 'Duplicate (slug, theme) route keys found in ledger input').toBe(
      routeKeys.length,
    )
  })
})
