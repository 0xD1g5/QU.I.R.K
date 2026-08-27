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
import { baselineFilename, isPlaceholderJustification } from './baseline-diff.mjs'

const A11Y_DIR = __dirname
const ACCEPTED_VIOLATIONS_MD = path.resolve(A11Y_DIR, 'ACCEPTED-VIOLATIONS.md')
const REGEN_COMMAND = 'npm run a11y:baseline'
const routes: Array<{ slug: string; path: string }> = JSON.parse(
  readFileSync(path.resolve(A11Y_DIR, 'routes.json'), 'utf-8'),
)

function loadDefaultBaselines() {
  return routes.map(({ slug }) => {
    const baselinePath = path.resolve(A11Y_DIR, baselineFilename(slug, 'default'))
    const baseline = existsSync(baselinePath)
      ? JSON.parse(readFileSync(baselinePath, 'utf-8'))
      : { route: slug, entries: [] }
    return { route: slug, entries: baseline.entries ?? [] }
  })
}

function allEntries() {
  return loadDefaultBaselines().flatMap(({ route, entries }) =>
    entries.map(entry => ({ route, ...entry })),
  )
}

describe('ACCEPTED-VIOLATIONS.md freshness (A11Y-01 / D-05)', () => {
  it('exists', () => {
    expect(
      existsSync(ACCEPTED_VIOLATIONS_MD),
      `ACCEPTED-VIOLATIONS.md is missing. Generate with: ${REGEN_COMMAND}`,
    ).toBe(true)
  })

  it('is current — byte-matches generateMarkdown() called on the committed default baselines', () => {
    const generated = generateMarkdown(loadDefaultBaselines()).replace(/\n+$/, '')
    const current = existsSync(ACCEPTED_VIOLATIONS_MD)
      ? readFileSync(ACCEPTED_VIOLATIONS_MD, 'utf-8').replace(/\n+$/, '')
      : ''
    expect(generated, 'ACCEPTED-VIOLATIONS.md is stale. Regenerate with: npm run a11y:baseline').toBe(
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
    const generated = generateMarkdown(loadDefaultBaselines())
    const totalsLine = generated
      .split('\n')
      .find(line => line.startsWith('Totals:'))
    expect(totalsLine, 'ACCEPTED-VIOLATIONS.md must have a Totals: line').toBeDefined()
    expect(totalsLine).toContain(`${totalCount} accepted violation node(s)`)
  })

  it('no entry stores a selector — no key named "target" appears anywhere in any committed baseline (D-01, D-02)', () => {
    for (const { slug } of routes) {
      const baselinePath = path.resolve(A11Y_DIR, baselineFilename(slug, 'default'))
      if (!existsSync(baselinePath)) continue
      const raw = readFileSync(baselinePath, 'utf-8')
      expect(raw).not.toMatch(/"target"\s*:/)
    }
  })
})
