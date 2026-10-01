/**
 * Shrink-only contrast ratchet shared by the Phase 221 token guards
 * (ds-severity-chip-contrast-guard, cytoscape-label-contrast-guard).
 * Pure module: no fs, no test-runner import.
 *
 * measured: every pair's ratio (key -> ratio). baseline: failing pairs only.
 * Returns human-readable violations; empty means the ratchet holds.
 */
export function ratchetViolations(
  measured: Record<string, number>,
  baseline: Record<string, number>,
  floor = 4.5,
): string[] {
  const out: string[] = []
  for (const [key, ratio] of Object.entries(measured)) {
    const base = baseline[key]
    if (base === undefined) {
      if (ratio < floor) out.push(`new failing pair ${key}: ${ratio} < ${floor}`)
      continue
    }
    if (ratio >= floor) {
      out.push(`${key} now measures ${ratio} >= ${floor}: fixed, delete it from the baseline`)
    } else if (ratio < base - 0.01) {
      out.push(`${key} worsened: ${ratio} < baseline ${base}`)
    }
  }
  for (const key of Object.keys(baseline)) {
    if (!(key in measured)) out.push(`orphan baseline key ${key}: no measured pair`)
  }
  return out
}
