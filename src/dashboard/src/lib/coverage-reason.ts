// Phase 235.3 COVTRUTH-04 / D-09 — exactly one place maps a phase record to empty-state text;
// pages never hand-write reason copy. Pure functions, no React: the returned strings are rendered
// by callers as React text children only (never as HTML).

import type { ScanCoverageResponse } from "@/types/api"

/**
 * Advisory (Skipped, not Failed) error categories. Mirrors
 * quirk/scanner/target_outcome.py COVERAGE_SKIP_ADVISORY_CATEGORIES, the source of truth.
 */
export const COVERAGE_SKIP_ADVISORY_CATEGORIES: readonly string[] = [
  "missing_extra",
  "missing_binary",
  "internal_target_refused",
  "auth_failed",
  "missing_credentials",
  "targets_unreachable",
]

const HUMAN_REASON: Record<string, string> = {
  "internal-target-refused": "internal targets refused by server policy",
  "missing-credentials": "missing credentials",
  "auth-failed": "credentials rejected",
  // C-WR-04: "failed" has two writers, so the bare wording claims no cause.
  failed: "failed or no target answered",
}

/**
 * C-WR-04: run_scan._classify_connector_outcomes writes reason "failed" with a
 * detail of this shape when every target was unreachable (D-03). Every other
 * "failed" row comes from PhaseRecorder.record_failed, written when the phase
 * itself raised, with the exception text as the detail. The Python side's
 * contract test (tests/test_scan_coverage_api.py) reads this regex from this
 * file and checks it against the real detail.
 */
export const NO_TARGET_ANSWERED_DETAIL = /^\d+ of \d+ targets did not answer\b/

/** True when a phase record is a phase that raised, not a skip. */
export function isPhaseError(p: { reason: string | null; detail: string | null }): boolean {
  return p.reason === "failed" && !(p.detail && NO_TARGET_ANSWERED_DETAIL.test(p.detail))
}

/** One phase record as empty-state text: "Failed: ..." for a phase error, else "Skipped: ...". */
export function phaseRecordText(p: { label: string; reason: string | null; detail: string | null }): string {
  const base = isPhaseError(p)
    ? `Failed: the scanner stopped with an error (${p.label})`
    : `Skipped: ${p.reason === "failed" ? "no target answered" : humanSkipReason(p.reason)} (${p.label})`
  return p.detail ? `${base} — ${p.detail}` : base
}

/** Human wording for a skip reason; reasons without a bespoke phrase keep their chip wording. */
export function humanSkipReason(reason: string | null | undefined): string {
  if (!reason) return "unclassified"
  return HUMAN_REASON[reason] ?? reason
}

/**
 * Honest empty-state text for a card fed by `phaseNames`. Returns `fallback` when no coverage is
 * recorded, a listed phase is absent, or every listed phase is disabled-by-config.
 */
export function emptyStateFor(
  coverage: ScanCoverageResponse | null | undefined,
  phaseNames: readonly string[],
  fallback: string,
): string {
  if (!coverage || !coverage.recorded) return fallback
  const listed = phaseNames.map(n => coverage.phases.find(p => p.phase_name === n))
  if (listed.length === 0 || listed.some(p => p === undefined)) return fallback
  const phases = listed as NonNullable<(typeof listed)[number]>[]

  const skipped = phases.filter(p => p.status !== "ran" && p.reason !== "disabled-by-config")
  if (skipped.length > 0) {
    return skipped.map(phaseRecordText).join("; ")
  }
  const ran = phases.filter(p => p.status === "ran")
  if (ran.length > 0) return `Ran, 0 results (${ran.map(p => p.label).join(", ")})`
  return fallback
}
