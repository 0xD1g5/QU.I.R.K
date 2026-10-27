// QRAMM assessment-state vocabulary — Phase 231 D-05/D-07/D-09; the one definition every QRAMM surface imports. Python twin: quirk/qramm/assessment_state.py.

import type { QRAMMRowCoverageStatus } from "@/types/api"

// Phase 234 D-15: "stale" = answers changed after the saved score; never counted as self-assessed or toward a maturity level.
export type AssessmentState = "scanner-measured" | "self-assessed" | "not-assessed" | "stale"

// Mirrors SCANNER_COVERAGE_STATUS 'covered' (quirk/qramm/compliance_map.py); the parity tests catch drift.
export const SCANNER_MEASURED_DIMENSIONS = ["CVI"] as const

// Assessed means at least one answered question (D-07, D-08). Never a score test, never a rounded percentage.
export function isDimensionAssessed(answered: number): boolean {
  return answered >= 1
}

// Row coverage_status -> display state. Anything not explicitly scanner or self-assessed fails closed (T-231-02).
export function stateFromCoverageStatus(
  status: QRAMMRowCoverageStatus | null | undefined,
): AssessmentState {
  switch (status) {
    case "covered":
    case "partial":
      return "scanner-measured"
    case "self-assessed":
      return "self-assessed"
    case "stale":
      return "stale"
    default:
      return "not-assessed"
  }
}

// Live-answers derivation used by the scorecard: same mapping and precedence as the server's
// row_coverage_status (Phase 234 D-15/D-25): unanswered -> not-assessed FIRST; then a score with
// no persisted count for this dimension (legacy, or a count missing from the blob) -> stale; then a
// persisted count that differs from the live one -> stale; then today's mapping.
export function dimensionStateFromAnswered(
  dimension: string,
  answered: number,
  scoredAnswered?: number,
  scoreHasCounts = true,
): AssessmentState {
  if (!isDimensionAssessed(answered)) return "not-assessed"
  if (!scoreHasCounts) return "stale"
  if (scoredAnswered !== undefined && scoredAnswered !== answered) return "stale"
  return (SCANNER_MEASURED_DIMENSIONS as readonly string[]).includes(dimension)
    ? "scanner-measured"
    : "self-assessed"
}

export const ASSESSMENT_LABEL: Record<AssessmentState, string> = {
  "scanner-measured": "Scanner-measured",
  "self-assessed": "Self-assessed",
  "not-assessed": "Not assessed",
  stale: "Stale — recalculate",
}

export const ASSESSMENT_BADGE_VARIANT: Record<AssessmentState, "default" | "outline" | "secondary" | "destructive"> = {
  "scanner-measured": "default",
  "self-assessed": "outline",
  "not-assessed": "secondary",
  // The one existing variant distinct from scanner (default), self-assessed (outline) and not-assessed (secondary): it asks for action.
  stale: "destructive",
}

export const ASSESSMENT_PRINT_CLASS: Record<AssessmentState, "tier-scanner" | "tier-self" | "tier-none"> = {
  "scanner-measured": "tier-scanner",
  "self-assessed": "tier-self",
  "not-assessed": "tier-none",
  stale: "tier-none",
}

export const QRAMM_COVERAGE_SENTENCE =
  'CVI rows are measured from QUIRK scanner evidence; SGRM, DPE and ITR rows show self-assessed answers; any dimension with no answered question reads "Not assessed".'

export function notAssessedCountLabel(n: number): string {
  return n === 1 ? "1 dimension not assessed" : `${n} dimensions not assessed`
}

// Phase 234 D-25: a score saved before answered_by_dimension existed still averages a Not-assessed
// dimension in as 0, so its overall is never shown as a maturity level. TS twin of Python overall_state.
export const RECALCULATE_OVERALL_LABEL = "Recalculate to apply the updated overall"

export function overallDisplayState(
  score: { answered_by_dimension?: Record<string, number> | null } | null | undefined,
): "current" | "recalculate" | null {
  if (score == null) return null
  const counts = score.answered_by_dimension
  return counts != null && typeof counts === "object" ? "current" : "recalculate"
}

// Phase 234 D-23 / D-14: "N of 4 dimensions assessed".
export function dimensionsAssessedLabel(n: number, total: number): string {
  return `${n} of ${total} dimensions assessed`
}
