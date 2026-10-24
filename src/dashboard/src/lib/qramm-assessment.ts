// QRAMM assessment-state vocabulary — Phase 231 D-05/D-07/D-09; the one definition every QRAMM surface imports. Python twin: quirk/qramm/assessment_state.py.

import type { QRAMMRowCoverageStatus } from "@/types/api"

export type AssessmentState = "scanner-measured" | "self-assessed" | "not-assessed"

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
    default:
      return "not-assessed"
  }
}

// Live-answers derivation used by the scorecard: same mapping as the server's row_coverage_status.
export function dimensionStateFromAnswered(dimension: string, answered: number): AssessmentState {
  if (!isDimensionAssessed(answered)) return "not-assessed"
  return (SCANNER_MEASURED_DIMENSIONS as readonly string[]).includes(dimension)
    ? "scanner-measured"
    : "self-assessed"
}

export const ASSESSMENT_LABEL: Record<AssessmentState, string> = {
  "scanner-measured": "Scanner-measured",
  "self-assessed": "Self-assessed",
  "not-assessed": "Not assessed",
}

export const ASSESSMENT_BADGE_VARIANT: Record<AssessmentState, "default" | "outline" | "secondary"> = {
  "scanner-measured": "default",
  "self-assessed": "outline",
  "not-assessed": "secondary",
}

export const ASSESSMENT_PRINT_CLASS: Record<AssessmentState, "tier-scanner" | "tier-self" | "tier-none"> = {
  "scanner-measured": "tier-scanner",
  "self-assessed": "tier-self",
  "not-assessed": "tier-none",
}

export const QRAMM_COVERAGE_SENTENCE =
  'CVI rows are measured from QUIRK scanner evidence; SGRM, DPE and ITR rows show self-assessed answers; any dimension with no answered question reads "Not assessed".'

export function notAssessedCountLabel(n: number): string {
  return n === 1 ? "1 dimension not assessed" : `${n} dimensions not assessed`
}
