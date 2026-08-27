import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// Phase 161 HWLC-19 / D-07 layer 1 precedent (Phase 156 HWLC-11) —
// mechanical firewall between the advisory-only vendor PQC trend section
// and the app's scored-finding visual language.
//
// Ten forbidden hsl() literals — every hardcoded badge color already in use
// on /hardware and /compare (TIER_STYLES, PQC_STYLES, CONF_STYLES,
// SEVERITY_STYLES, Modbus/BACnet badges, and the compare.tsx score-delta
// badges). Declared as an array so a future added forbidden hue is a
// one-line change. This is a deliberate duplicate of the lifecycle guard
// test's own copy — the two guard files each keep their own, no shared
// module extraction.
const FORBIDDEN_PALETTE = [
  "hsl(0 72% 51%)",
  "hsl(24 95% 53%)",
  "hsl(38 92% 50%)",
  "hsl(142 71% 45%)",
  "hsl(199 89% 48%)",
  "hsl(213 94% 68%)",
  "hsl(240 5% 46%)",
  "hsl(271 81% 56%)",
  "hsl(var(--ds-ok, 142 46% 46%))",
  "hsl(var(--destructive))",
  // Phase 165 D-09: executive.tsx/cbom.tsx now consume these two literals via new design
  // tokens instead of the raw hsl() values above. Additive coverage so the guard keeps
  // preventing this advisory-only component from adopting the token-referenced form too.
  "hsl(var(--risk-badge-high))",
  "hsl(var(--qs-node-safe))",
]

function stripComments(src: string): string {
  return src
    .split("\n")
    .filter((line) => !line.trim().startsWith("//"))
    .join("\n")
}

const LIST_SRC = stripComments(
  readFileSync(path.resolve(__dirname, "../VendorTrendList.tsx"), "utf-8"),
)
const ROW_SRC = stripComments(
  readFileSync(path.resolve(__dirname, "../VendorTrendRow.tsx"), "utf-8"),
)

describe("vendor trend advisory guard (HWLC-19)", () => {
  it("does not import the score-regression alert chip in VendorTrendList", () => {
    expect(LIST_SRC).not.toContain("RegressionAlertChip")
  })

  it("does not import the score-regression alert chip in VendorTrendRow", () => {
    expect(ROW_SRC).not.toContain("RegressionAlertChip")
  })

  it.each(FORBIDDEN_PALETTE)(
    "does not use forbidden severity literal %s in VendorTrendList",
    (literal) => {
      expect(LIST_SRC).not.toContain(literal)
    },
  )

  it.each(FORBIDDEN_PALETTE)(
    "does not use forbidden severity literal %s in VendorTrendRow",
    (literal) => {
      expect(ROW_SRC).not.toContain(literal)
    },
  )

  it("renders the verbatim advisory caption somewhere in the two components", () => {
    const combined = `${LIST_SRC}\n${ROW_SRC}`
    expect(combined).toContain(
      "Advisory — vendor PQC status trends do not affect the readiness score.",
    )
  })

  it("does not import the filled pill component in VendorTrendList", () => {
    expect(LIST_SRC).not.toContain("@/components/ui/badge")
  })

  it("does not import the filled pill component in VendorTrendRow", () => {
    expect(ROW_SRC).not.toContain("@/components/ui/badge")
  })
})
