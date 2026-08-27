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
export function resolveVariant(env) {
  return (env && env.VITE_A11Y_FIXTURE_VARIANT) || 'default'
}

export function baselineFilename(slug, variant) {
  return `baseline-${slug}-${variant}.json`
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
    const baselineCount = baseline ? baseline.count : 0
    if (live.count > baselineCount) {
      regressions.push({
        rule,
        baselineCount,
        observedCount: live.count,
        impact: live.impact,
        samples: live.samples,
      })
    } else if (live.count < baselineCount) {
      staleEntries.push({
        rule,
        baselineCount,
        observedCount: live.count,
      })
    }
  }

  // Rules baselined but not observed live at all are also stale (observed count 0).
  for (const [rule, baseline] of baselineByRule) {
    if (!liveByRule.has(rule) && baseline.count > 0) {
      staleEntries.push({
        rule,
        baselineCount: baseline.count,
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
