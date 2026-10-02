/**
 * baseline-diff.mjs — pure count-budget comparison for the dashboard a11y gate.
 *
 * Phase 165 / A11Y-01, A11Y-02, A11Y-04 / 165-CONTEXT.md D-01, D-02, D-06, D-13, D-14
 *
 * This module performs NO filesystem I/O and has NO browser dependency — all reads and
 * writes stay in run-a11y.mjs. Every export here is a pure function of its arguments, which
 * is what makes the D-01 (churn-resistant key), D-02 (capped evidence samples), D-06
 * (never-synthesized justification), D-13 (ratchet) and D-14 (critical refusal) guarantees
 * verifiable by fast synthetic unit tests instead of a live browser sweep.
 */

// D-02: evidence samples per baseline entry are capped so a 190-node violation does not
// produce an unreviewable file.
export const SAMPLE_CAP = 3

// D-06/D-11: a justification matching one of these (case-insensitive, trimmed) is never
// accepted as a real reason for baselining debt. "pre-existing" is explicitly named in D-11.
export const PLACEHOLDER_JUSTIFICATIONS = Object.freeze([
  'tbd',
  'todo',
  'pre-existing',
  'n/a',
  'na',
  'none',
  '-',
  'accepted',
  'see above',
])

const PLACEHOLDER_SET = new Set(PLACEHOLDER_JUSTIFICATIONS)
const JUSTIFICATION_MIN_LENGTH = 20

/**
 * Returns true when `value` cannot stand as a real, human-written justification:
 * not a string, empty after trimming, shorter than the 20-character mechanical floor, or a
 * known placeholder phrase. The 20-character floor is a mechanical floor on filler only —
 * judging whether a justification is *defensible* stays a human-only verification.
 */
export function isPlaceholderJustification(value) {
  if (typeof value !== 'string') return true
  const trimmed = value.trim()
  if (trimmed.length === 0) return true
  if (trimmed.length < JUSTIFICATION_MIN_LENGTH) return true
  if (PLACEHOLDER_SET.has(trimmed.toLowerCase())) return true
  return false
}

// D-15/D-16: baseline filenames are variant-aware so the empty and loading fixture variants
// each hold their own baseline data instead of silently sharing the happy-path fixture's
// file. `resolveVariant` normalizes an unset or empty-string variant to "default" so the
// unsuffixed run never collides with a literal "" segment in the filename.
// 221 D-02/T-221-03: the variant allowlist, symmetric with THEMES. An unknown variant throws
// instead of silently selecting a baseline set that does not exist.
export const VARIANTS = Object.freeze(['default', 'empty', 'loading'])

export function resolveVariant(env) {
  const value = (env && env.VITE_A11Y_FIXTURE_VARIANT) || 'default'
  if (!VARIANTS.includes(value)) {
    throw new Error(
      `resolveVariant: unsupported VITE_A11Y_FIXTURE_VARIANT "${value}" — must be one of: ${VARIANTS.join(', ')}`,
    )
  }
  return value
}

// 216 D-01/D-02: the harness-side theme allowlist. Deliberately NARROWER than the app's own
// `VALID_THEMES` (`src/components/theme-context.ts`), which also allows `"system"`. A swept
// `"system"` theme resolves via `matchMedia` and is non-deterministic per runner/OS — the
// opposite of what a committed baseline needs — so it is excluded here on purpose, not by
// omission.
export const THEMES = Object.freeze(['dark', 'light'])

// 216 D-01/D-02: resolves the sweep theme from the harness-only `A11Y_THEME` env var (NOT
// `VITE_A11Y_THEME` — unlike `VITE_A11Y_FIXTURE_VARIANT`, which the Vite fixture middleware
// reads inside the bundle, the theme is applied entirely harness-side by seeding
// `localStorage` before `page.goto` (D-01), so a `VITE_` prefix would falsely imply the
// bundle itself consumes it). Unset resolves to the historical default `'dark'`, named
// explicitly rather than left implicit. Anything outside `THEMES` — including the app-valid
// `'system'` and simple typos — THROWS rather than silently falling back: a mistyped
// `A11Y_THEME=ligth` silently sweeping dark and overwriting the dark baseline is the exact
// unnamed-dimension defect class this phase repairs.
export function resolveTheme(env) {
  const value = (env && env.A11Y_THEME) || 'dark'
  if (!THEMES.includes(value)) {
    throw new Error(
      `resolveTheme: unsupported A11Y_THEME "${value}" — must be one of: ${THEMES.join(', ')}`,
    )
  }
  return value
}

// 216 D-02: `theme` is REQUIRED, not optional-with-a-default. A 2-arg call would previously
// have silently produced `baseline-{slug}-{variant}-undefined.json` — a plausible-looking
// filename that is actually a distinct, un-reviewed baseline. Throwing here is what makes
// the theme dimension impossible to omit by accident (216-RESEARCH.md § Code Examples).
export function baselineFilename(slug, variant, theme) {
  if (typeof theme !== 'string' || theme.length === 0 || !THEMES.includes(theme)) {
    throw new Error(
      `baselineFilename: missing/invalid theme for slug "${slug}" (received ${JSON.stringify(theme)}) — ` +
        `a 2-arg call would silently produce "baseline-${slug}-${variant}-undefined.json"; ` +
        `theme must be one of: ${THEMES.join(', ')}`,
    )
  }
  return `baseline-${slug}-${variant}-${theme}.json`
}

const WCAG_TAG_RE = /^wcag(\d)(\d)(\d+)$/

/**
 * Derives dotted WCAG success-criterion strings (e.g. "1.4.3", "1.4.11") from an axe
 * `violation.tags` array. The final capture group is greedy — NOT a fixed three-character
 * split — so multi-digit criteria (wcag1411 -> "1.4.11") derive correctly. Returns all
 * matches, sorted and de-duplicated, since a rule can carry both a WCAG 2.0 and 2.1 tag.
 */
export function deriveWcagCriteria(tags) {
  if (!Array.isArray(tags)) return []
  const criteria = new Set()
  for (const tag of tags) {
    const m = typeof tag === 'string' ? tag.match(WCAG_TAG_RE) : null
    if (m) {
      criteria.add(`${m[1]}.${m[2]}.${m[3]}`)
    }
  }
  return [...criteria].sort()
}

function sumNodes(violation) {
  return Array.isArray(violation.nodes) ? violation.nodes.length : 0
}

// 216-CONTEXT.md D-10: a declared `countRange` is opt-in and, when present, must be a
// two-integer `[floor, ceiling]` tuple with `floor <= ceiling` and `floor >= 0`. Returns
// `false` for `undefined`/`null` (the "no range declared" case is valid and handled by the
// caller, not here) but `false` for any other malformed shape too — the caller distinguishes
// "absent" from "malformed" itself.
//
// 216-CONTEXT.md D-14 — countRange is TRANSITIONAL, not permanent. The one live use was
// `data-at-rest`'s `scrollable-region-focusable`, whose count was render-dependent (it fired
// on whether a container actually overflowed at render time, a function of viewport/font
// metrics). RETIRED by Phase 219 (KBD-01, 219-03, CI run 36795176372): `src/components/ui/
// table.tsx` gained conditional `tabIndex`/`role` on its scroll wrapper and the rule withdrew
// outright across every route and fixture variant, removing the render-dependence this band
// existed to absorb. No committed baseline currently declares a `countRange`; the mechanism
// itself stays available for a future render-dependent entry. The same pointer is in
// run-a11y.mjs's header; it is repeated here because this is the file a future reader
// changing the comparison will open.
function isValidCountRange(value) {
  if (value === undefined || value === null) return false
  if (!Array.isArray(value) || value.length !== 2) return false
  const [floor, ceiling] = value
  if (!Number.isInteger(floor) || !Number.isInteger(ceiling)) return false
  if (floor < 0) return false
  if (floor > ceiling) return false
  return true
}

/**
 * Builds the D-01 per-(route, rule) baseline entry array from a live axe `violations` array.
 *
 * Returns `{ entries, refusedCritical }`. `entries` excludes any rule whose impact is
 * "critical" (D-14, per-entry not whole-route refusal); those are returned separately in
 * `refusedCritical` so the caller can report and fail loudly instead of silently dropping them.
 */
export function buildBaselineEntries(route, violations, { previousEntries } = {}) {
  const previousByRule = new Map()
  for (const entry of previousEntries ?? []) {
    if (entry && typeof entry.rule === 'string') {
      previousByRule.set(entry.rule, entry)
    }
  }

  // Group live violations by rule id (a rule can theoretically appear more than once).
  const byRule = new Map()
  for (const violation of violations ?? []) {
    const rule = violation.id
    if (!byRule.has(rule)) {
      byRule.set(rule, [])
    }
    byRule.get(rule).push(violation)
  }

  const entries = []
  const refusedCritical = []

  for (const [rule, ruleViolations] of byRule) {
    const count = ruleViolations.reduce((sum, v) => sum + sumNodes(v), 0)
    const first = ruleViolations[0]
    const impact = first.impact ?? 'unknown'

    // Merge tags/samples/helpUrl across all violations grouped under this rule.
    const allTags = ruleViolations.flatMap(v => (Array.isArray(v.tags) ? v.tags : []))
    const allNodes = ruleViolations.flatMap(v => (Array.isArray(v.nodes) ? v.nodes : []))

    const previous = previousByRule.get(rule)
    const carriedJustification =
      previous && !isPlaceholderJustification(previous.justification)
        ? previous.justification
        : ''

    const entry = {
      rule,
      count,
      impact,
      wcag: deriveWcagCriteria(allTags),
      helpUrl: first.helpUrl,
      justification: carriedJustification,
      samples: allNodes.slice(0, SAMPLE_CAP).map(n => n.html),
    }

    // 216-CONTEXT.md D-10/D-12: carry a declared countRange forward across a regeneration,
    // mirroring the Phase 185 D-05 justification carry-forward above. Only carried when the
    // previous entry declared a VALID range — an entry that never had one must not gain a
    // `countRange: undefined` key, which would change the JSON byte output and redden the
    // ACCEPTED-VIOLATIONS.md drift gate. Validity is re-checked here rather than trusted from
    // the prior file, since that file could have been hand-edited.
    if (previous && isValidCountRange(previous.countRange)) {
      entry.countRange = previous.countRange
    }

    if (impact === 'critical') {
      refusedCritical.push(entry)
    } else {
      entries.push(entry)
    }
  }

  entries.sort((a, b) => a.rule.localeCompare(b.rule))

  return { entries, refusedCritical }
}

/**
 * D-13 ratchet + D-14 check-time critical refusal + D-06 justification enforcement.
 *
 * Compares live per-rule counts against a route's committed baseline entries. Returns
 * `{ regressions, staleEntries, criticalViolations, missingJustifications }` — never prints,
 * throws, or exits; the caller owns all reporting.
 */
export function compareToBaseline(route, liveViolations, baselineEntries) {
  const liveByRule = new Map()
  for (const violation of liveViolations ?? []) {
    const rule = violation.id
    const count = sumNodes(violation)
    const existing = liveByRule.get(rule)
    if (existing) {
      existing.count += count
      existing.impact = existing.impact ?? violation.impact
      existing.samples = existing.samples.length
        ? existing.samples
        : (violation.nodes ?? []).slice(0, SAMPLE_CAP).map(n => n.html)
    } else {
      liveByRule.set(rule, {
        count,
        impact: violation.impact ?? 'unknown',
        samples: (violation.nodes ?? []).slice(0, SAMPLE_CAP).map(n => n.html),
      })
    }
  }

  const baselineByRule = new Map()
  for (const entry of baselineEntries ?? []) {
    baselineByRule.set(entry.rule, entry)
  }

  const regressions = []
  const staleEntries = []

  for (const [rule, live] of liveByRule) {
    const baseline = baselineByRule.get(rule)

    // 216-CONTEXT.md D-10/D-12: an opt-in per-entry countRange widens the exact-count
    // comparison to a two-sided band. An entry with no countRange keeps today's exact-integer
    // semantics byte-unchanged (ceiling === floor === baseline.count). A malformed countRange
    // throws rather than silently degrading to "compare against undefined" — that silent
    // fallback would make every count pass, the same class run-a11y.mjs's D-15 comment
    // already forbids for a missing baseline file.
    if (baseline && baseline.countRange !== undefined && !isValidCountRange(baseline.countRange)) {
      throw new Error(
        `compareToBaseline: malformed countRange for route "${route}" rule "${rule}" — ` +
          `received ${JSON.stringify(baseline.countRange)}; expected [floor, ceiling] with ` +
          `two integers, floor >= 0 and floor <= ceiling`,
      )
    }
    const hasRange = baseline && isValidCountRange(baseline.countRange)
    const baselineCeiling = hasRange ? baseline.countRange[1] : baseline ? baseline.count : 0
    const baselineFloor = hasRange ? baseline.countRange[0] : baseline ? baseline.count : 0

    if (live.count > baselineCeiling) {
      regressions.push({
        rule,
        baselineCount: baselineCeiling,
        observedCount: live.count,
        impact: live.impact,
        samples: live.samples,
      })
    } else if (live.count < baselineFloor) {
      staleEntries.push({
        rule,
        baselineCount: baselineFloor,
        observedCount: live.count,
      })
    }
  }

  // Rules baselined but not observed live at all are also stale (observed count 0), checked
  // against the declared range's floor (D-12) so a range can never disable this leg.
  for (const [rule, baseline] of baselineByRule) {
    if (baseline.countRange !== undefined && !isValidCountRange(baseline.countRange)) {
      throw new Error(
        `compareToBaseline: malformed countRange for route "${route}" rule "${rule}" — ` +
          `received ${JSON.stringify(baseline.countRange)}; expected [floor, ceiling] with ` +
          `two integers, floor >= 0 and floor <= ceiling`,
      )
    }
    const baselineFloor = isValidCountRange(baseline.countRange)
      ? baseline.countRange[0]
      : baseline.count
    if (!liveByRule.has(rule) && baselineFloor > 0) {
      staleEntries.push({
        rule,
        baselineCount: baselineFloor,
        observedCount: 0,
      })
    }
  }

  // D-14: any live critical violation fails regardless of baseline state.
  const criticalViolations = (liveViolations ?? [])
    .filter(v => v.impact === 'critical')
    .map(v => ({
      rule: v.id,
      count: sumNodes(v),
      samples: (v.nodes ?? []).slice(0, SAMPLE_CAP).map(n => n.html),
    }))

  // D-06: every baseline entry must carry a real, non-placeholder justification.
  const missingJustifications = (baselineEntries ?? [])
    .filter(entry => isPlaceholderJustification(entry.justification))
    .map(entry => ({ rule: entry.rule, justification: entry.justification }))

  return { regressions, staleEntries, criticalViolations, missingJustifications }
}
