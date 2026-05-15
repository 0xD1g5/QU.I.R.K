import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// D-25 (IN-03): findings.tsx and identity.tsx columns arrays must be
// wrapped in useMemo<ColumnDef<...>[]>(() => [...], [...]) for stable
// reference identity across renders (TanStack Table column stability).
describe("findings.tsx / identity.tsx — D-25 (IN-03) columns memoization", () => {
  const FINDINGS = readFileSync(path.resolve(__dirname, "../findings.tsx"), "utf-8")
  const IDENTITY = readFileSync(path.resolve(__dirname, "../identity.tsx"), "utf-8")

  it("findings.tsx wraps columns in useMemo<ColumnDef<FindingItem>[]>", () => {
    // Match useMemo with ColumnDef generic — tolerates whitespace
    expect(FINDINGS).toMatch(/useMemo\s*<\s*ColumnDef\s*<\s*FindingItem\s*>\s*\[\s*\]\s*>/)
  })

  it("identity.tsx wraps columns in useMemo<ColumnDef<IdentityFinding>[]>", () => {
    expect(IDENTITY).toMatch(/useMemo\s*<\s*ColumnDef\s*<\s*IdentityFinding\s*>\s*\[\s*\]\s*>/)
  })
})
