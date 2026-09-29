/**
 * ledger-input.mjs — disk-based, theme-complete input loader for the accepted-violations
 * ledger generator and its freshness gate.
 *
 * Phase 216 / HARNESS-01 / 216-CONTEXT.md D-17
 *
 * Problem this exists to fix: `generateMarkdown()` (generate-accepted-violations.mjs) is a
 * PURE function with no I/O, and was previously fed by `run-a11y.mjs`'s in-process
 * `writtenBaselinesByRoute` array — populated only when `UPDATE_BASELINES && VARIANT ===
 * 'default'` during a SINGLE process's sweep. Since theme is now a per-process dimension
 * (216 D-01/D-02), one process can only ever see ONE theme, so in-process collection was
 * structurally incapable of producing a theme-complete ledger — left alone, it would silently
 * narrow to whichever theme last ran `--update-baselines` (216-CONTEXT.md D-17's named risk).
 * This module replaces in-process collection with a disk read across every theme, shared
 * verbatim by both the generator's caller (`regenerate-ledger.mjs`) and the freshness gate
 * (`accepted-violations-freshness.test.ts`), so the two consume byte-identical input by
 * construction rather than by two hand-synced copies — the defect class CLAUDE.md's Staleness
 * Review Cadence section documents six prior instances of in this project.
 *
 * No filesystem writes happen here — only `regenerate-ledger.mjs` writes.
 */

import { readFileSync, existsSync } from 'node:fs'
import path from 'node:path'
import { baselineFilename, THEMES } from './baseline-diff.mjs'

/**
 * Derives every baseline slug from routes.json — each route's own `slug`, plus its optional
 * `interaction.slug` (e.g. `findings-storyline`, which is an interaction capture, not a
 * routes.json route entry of its own, and therefore has no route entry of its own). Moved
 * verbatim from accepted-violations-freshness.test.ts (Phase 202-07 / T-202-29) so the
 * derivation has ONE home shared by the generator and the gate, rather than two hand-synced
 * copies.
 */
export function allBaselineSlugs(routes) {
  return routes.flatMap((route) => [route.slug, ...(route.interaction ? [route.interaction.slug] : [])])
}

/**
 * Reads routes.json (passed in, not read here — callers already load it) plus every committed
 * `baseline-{slug}-default-{theme}.json` file for every theme in THEMES, and returns:
 *
 *   - `input`: the generateMarkdown-shaped array, one element per (slug, theme) pair that has a
 *     committed file, `{ route: "${slug} [${theme}]", entries }`. Theme-labelled route keys
 *     thread the theme axis through the EXISTING pure generator with zero generator change,
 *     and because each (slug, theme) pair is pushed at most once, there is no double-counting
 *     (D-17's second named risk).
 *   - `presentThemes`: the Set of themes for which at least one baseline file exists on disk.
 *   - `missing`: every (slug, theme) pair from THEMES x allBaselineSlugs(routes) whose file is
 *     absent, as `{ slug, theme, path }`. A missing file is never defaulted to `{ entries: [] }`
 *     here — the harness's own D-15 rule is that a missing baseline is never a silent
 *     empty-violations fallback, and silently substituting one in the ledger loader would
 *     reintroduce that same defect one layer up. Callers decide what a `missing` entry means
 *     for their purpose (a hard error in `regenerate-ledger.mjs` for `dark`; a completeness
 *     assertion in the freshness gate).
 */
export function loadLedgerInput(a11yDir, routes) {
  const slugs = allBaselineSlugs(routes)
  const input = []
  const presentThemes = new Set()
  const missing = []

  for (const theme of THEMES) {
    for (const slug of slugs) {
      const filename = baselineFilename(slug, 'default', theme)
      const baselinePath = path.resolve(a11yDir, filename)
      if (existsSync(baselinePath)) {
        presentThemes.add(theme)
        const baseline = JSON.parse(readFileSync(baselinePath, 'utf-8'))
        input.push({ route: `${slug} [${theme}]`, entries: baseline.entries ?? [] })
      } else {
        missing.push({ slug, theme, path: baselinePath })
      }
    }
  }

  return { input, presentThemes, missing }
}

/**
 * Completeness rule (216-CONTEXT.md D-17, sequencing note): a theme with at least one committed
 * default baseline must have one for EVERY slug — EXCEPT that `light` is not required to be
 * complete yet. Light baselines are generated on Linux CI in plan 216-08 (D-15's
 * Linux-provenance rule for baseline COUNTS), which is necessarily sequenced after this plan —
 * requiring THEMES-complete coverage here would leave the freshness gate red across two waves
 * for a reason unrelated to real drift, exactly what D-17 warns against. `dark` completeness IS
 * required unconditionally, in every wave, because 216-01 already produced a complete dark set.
 *
 * Returns the subset of `missing` that DOES count as a real completeness failure under this
 * rule: every `dark` miss, plus — for any OTHER theme that has at least one baseline present —
 * every miss within that theme. This is what turns a half-committed light rollout (some slugs
 * present, others not) into a caught failure once light baselining begins, without demanding
 * light-completeness before it has started.
 */
export function incompleteThemeMisses(missing, presentThemes) {
  return missing.filter(({ theme }) => theme === 'dark' || presentThemes.has(theme))
}
