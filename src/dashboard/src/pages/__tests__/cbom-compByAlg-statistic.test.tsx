import { describe, it, expect } from "vitest"
import { firstNonZeroComp } from "../cbom-utils"

// D-27 (IN-05): cbom.tsx must expose a firstNonZeroComp helper that
// returns the first component with count > 0, falling back to the [0]
// representative (preserves existing "any representative" semantic per
// Discretion D-27 — Researcher recommendation).
describe("cbom.tsx — D-27 (IN-05) firstNonZeroComp helper", () => {
  it("returns the first component with count > 0", () => {
    const comps = [
      { count: 0, algorithm: "a" },
      { count: 5, algorithm: "b" },
      { count: 3, algorithm: "c" },
    ]
    expect(firstNonZeroComp(comps)).toEqual({ count: 5, algorithm: "b" })
  })

  it("falls back to [0] when all counts are zero", () => {
    const comps = [
      { count: 0, algorithm: "a" },
      { count: 0, algorithm: "b" },
    ]
    expect(firstNonZeroComp(comps)).toEqual({ count: 0, algorithm: "a" })
  })

  it("returns undefined for undefined input", () => {
    expect(firstNonZeroComp(undefined)).toBeUndefined()
  })

  it("returns undefined for empty array", () => {
    expect(firstNonZeroComp([])).toBeUndefined()
  })

  it("returns first when only one element has count > 0", () => {
    const comps = [{ count: 7, algorithm: "only" }]
    expect(firstNonZeroComp(comps)).toEqual({ count: 7, algorithm: "only" })
  })
})
