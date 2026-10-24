// Phase 231-03 (QRAMM-18/19, D-05/D-07/D-09) — contract tests for lib/qramm-assessment.ts, the one
// assessment vocabulary ScorecardTab, ComplianceMapTab and the print page import. The coverage
// sentence is hard-coded here once, as the UI-SPEC contract; no other test should retype it.

import { describe, it, expect } from "vitest"
import {
  ASSESSMENT_BADGE_VARIANT,
  ASSESSMENT_LABEL,
  ASSESSMENT_PRINT_CLASS,
  QRAMM_COVERAGE_SENTENCE,
  SCANNER_MEASURED_DIMENSIONS,
  dimensionStateFromAnswered,
  isDimensionAssessed,
  notAssessedCountLabel,
  stateFromCoverageStatus,
} from "@/lib/qramm-assessment"

describe("isDimensionAssessed", () => {
  it("is false for zero answered questions", () => {
    expect(isDimensionAssessed(0)).toBe(false)
  })

  it("is true for exactly one answered question", () => {
    expect(isDimensionAssessed(1)).toBe(true)
  })

  it("is true for a fully answered dimension", () => {
    expect(isDimensionAssessed(30)).toBe(true)
  })
})

describe("stateFromCoverageStatus", () => {
  it("maps covered and partial to scanner-measured", () => {
    expect(stateFromCoverageStatus("covered")).toBe("scanner-measured")
    expect(stateFromCoverageStatus("partial")).toBe("scanner-measured")
  })

  it("maps self-assessed to self-assessed", () => {
    expect(stateFromCoverageStatus("self-assessed")).toBe("self-assessed")
  })

  it("maps pending, n/a, null and undefined to not-assessed", () => {
    expect(stateFromCoverageStatus("pending")).toBe("not-assessed")
    expect(stateFromCoverageStatus("n/a")).toBe("not-assessed")
    expect(stateFromCoverageStatus(null)).toBe("not-assessed")
    expect(stateFromCoverageStatus(undefined)).toBe("not-assessed")
  })

  it("fails closed on an unknown status string", () => {
    // T-231-02: a value the server should never send must not read as scanner-measured.
    expect(
      stateFromCoverageStatus("bogus" as unknown as Parameters<typeof stateFromCoverageStatus>[0]),
    ).toBe("not-assessed")
  })
})

describe("dimensionStateFromAnswered", () => {
  it("reads CVI as not-assessed with no answers and scanner-measured with one", () => {
    expect(dimensionStateFromAnswered("CVI", 0)).toBe("not-assessed")
    expect(dimensionStateFromAnswered("CVI", 1)).toBe("scanner-measured")
  })

  it("reads answered SGRM, DPE and ITR as self-assessed", () => {
    expect(dimensionStateFromAnswered("SGRM", 1)).toBe("self-assessed")
    expect(dimensionStateFromAnswered("DPE", 2)).toBe("self-assessed")
    expect(dimensionStateFromAnswered("ITR", 30)).toBe("self-assessed")
  })

  it("reads an unanswered ITR as not-assessed", () => {
    expect(dimensionStateFromAnswered("ITR", 0)).toBe("not-assessed")
  })

  it("treats CVI as the only scanner-measured dimension", () => {
    expect([...SCANNER_MEASURED_DIMENSIONS]).toEqual(["CVI"])
  })
})

describe("vocabulary maps", () => {
  it("labels the three states with the exact UI-SPEC copy", () => {
    expect(ASSESSMENT_LABEL).toEqual({
      "scanner-measured": "Scanner-measured",
      "self-assessed": "Self-assessed",
      "not-assessed": "Not assessed",
    })
  })

  it("maps the three states to Badge variants", () => {
    expect(ASSESSMENT_BADGE_VARIANT).toEqual({
      "scanner-measured": "default",
      "self-assessed": "outline",
      "not-assessed": "secondary",
    })
  })

  it("maps the three states to print chip classes", () => {
    expect(ASSESSMENT_PRINT_CLASS).toEqual({
      "scanner-measured": "tier-scanner",
      "self-assessed": "tier-self",
      "not-assessed": "tier-none",
    })
  })

  it("exports the coverage sentence verbatim", () => {
    expect(QRAMM_COVERAGE_SENTENCE).toBe(
      'CVI rows are measured from QUIRK scanner evidence; SGRM, DPE and ITR rows show self-assessed answers; any dimension with no answered question reads "Not assessed".',
    )
  })
})

describe("notAssessedCountLabel", () => {
  it("uses the singular for one dimension", () => {
    expect(notAssessedCountLabel(1)).toBe("1 dimension not assessed")
  })

  it("uses the plural for two to four dimensions", () => {
    expect(notAssessedCountLabel(2)).toBe("2 dimensions not assessed")
    expect(notAssessedCountLabel(4)).toBe("4 dimensions not assessed")
  })
})
