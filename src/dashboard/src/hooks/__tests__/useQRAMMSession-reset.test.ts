import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// D-26 (IN-04): useQRAMMSession must expose a resetSession() callback
// that nulls seededRef.current so the next session load re-seeds answers
// after a "New Assessment" flow trigger.
describe("useQRAMMSession.ts — D-26 (IN-04) resetSession callback", () => {
  const HOOK = readFileSync(
    path.resolve(__dirname, "../useQRAMMSession.ts"),
    "utf-8",
  )
  const CALLER = readFileSync(
    path.resolve(__dirname, "../../pages/qramm-assessment.tsx"),
    "utf-8",
  )

  it("hook defines resetSession via useCallback that nulls seededRef.current", () => {
    expect(HOOK).toMatch(/resetSession/)
    // Must set seededRef.current = null (or false)
    expect(HOOK).toMatch(/seededRef\.current\s*=\s*null/)
  })

  it("hook exports resetSession in the returned object", () => {
    // returned via the `return { ... }` block
    const returnBlock = HOOK.match(/return\s*\{[\s\S]*?\}\s*\}\s*$/m)
    expect(returnBlock).not.toBeNull()
    expect(returnBlock?.[0] ?? "").toMatch(/resetSession/)
  })

  it("qramm-assessment.tsx wires resetSession into the New Assessment flow", () => {
    expect(CALLER).toMatch(/resetSession/)
    // Called inside or alongside handleNewAssessment
    expect(CALLER).toMatch(/resetSession\s*\(\s*\)/)
  })
})
