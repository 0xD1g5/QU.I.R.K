import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// D-23 (IN-01): Comment at qramm-assessment.tsx:246 must reflect the 6 tabs
// rendered at lines 248-254 (CVI, SGRM, DPE, ITR, Scorecard, Compliance Map).
describe("qramm-assessment.tsx — D-23 (IN-01) tab-count comment", () => {
  const SRC = readFileSync(
    path.resolve(__dirname, "../qramm-assessment.tsx"),
    "utf-8",
  )

  it("does not contain the stale '5-tab' comment", () => {
    expect(SRC).not.toContain("5-tab")
  })

  it("contains a 6-tab comment reflecting the actual rendered tabs", () => {
    expect(SRC).toMatch(/6[-\s]tab/i)
  })
})
