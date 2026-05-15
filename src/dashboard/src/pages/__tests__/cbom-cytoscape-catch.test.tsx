import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// D-24 (IN-02): cbom.tsx and roadmap.tsx cytoscape registration must
// log via console.error AND re-throw non-"already registered" errors
// (HMR-safe per RESEARCH C-12 Pattern 8).
describe("cbom.tsx / roadmap.tsx — D-24 (IN-02) cytoscape catch is loud + HMR-safe", () => {
  const CBOM = readFileSync(path.resolve(__dirname, "../cbom.tsx"), "utf-8")
  const ROADMAP = readFileSync(path.resolve(__dirname, "../roadmap.tsx"), "utf-8")

  it("cbom.tsx logs cytoscape.use failures via console.error", () => {
    expect(CBOM).toMatch(/console\.error\([^)]*cytoscape/i)
  })

  it("cbom.tsx re-throws non-'already' errors via /already/i message guard", () => {
    // RESEARCH Pattern 8: regex-guarded re-throw so HMR re-registration is swallowed
    // but genuine failures propagate.
    expect(CBOM).toMatch(/\/already\/i/)
    expect(CBOM).toMatch(/throw\s+e/)
  })

  it("roadmap.tsx logs cytoscape.use failures via console.error", () => {
    expect(ROADMAP).toMatch(/console\.error\([^)]*cytoscape/i)
  })

  it("roadmap.tsx re-throws non-'already' errors via /already/i message guard", () => {
    expect(ROADMAP).toMatch(/\/already\/i/)
    expect(ROADMAP).toMatch(/throw\s+e/)
  })
})
