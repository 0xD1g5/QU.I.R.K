import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// Phase 156 HWLC-11 / D-07 layer 1 — mechanical firewall between the
// advisory-only hardware lifecycle section and the app's scored-finding
// visual language. See 156-UI-SPEC.md §Color for the source catalogue.
//
// Ten forbidden hsl() literals — every hardcoded badge color already in use
// on /hardware and /compare (TIER_STYLES, PQC_STYLES, CONF_STYLES,
// SEVERITY_STYLES, Modbus/BACnet badges, and the compare.tsx score-delta
// badges). Declared as an array so a future added forbidden hue is a
// one-line change.
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
]

function stripComments(src: string): string {
  return src
    .split("\n")
    .filter((line) => !line.trim().startsWith("//"))
    .join("\n")
}

const LIST_SRC = stripComments(
  readFileSync(path.resolve(__dirname, "../LifecycleEventList.tsx"), "utf-8"),
)
const ROW_SRC = stripComments(
  readFileSync(path.resolve(__dirname, "../LifecycleEventRow.tsx"), "utf-8"),
)

describe("lifecycle advisory guard (HWLC-11 / D-07 layer 1)", () => {
  it("does not import RegressionAlertChip in LifecycleEventList", () => {
    expect(LIST_SRC).not.toContain("RegressionAlertChip")
  })

  it("does not import RegressionAlertChip in LifecycleEventRow", () => {
    expect(ROW_SRC).not.toContain("RegressionAlertChip")
  })

  it.each(FORBIDDEN_PALETTE)(
    "does not use forbidden severity literal %s in LifecycleEventList",
    (literal) => {
      expect(LIST_SRC).not.toContain(literal)
    },
  )

  it.each(FORBIDDEN_PALETTE)(
    "does not use forbidden severity literal %s in LifecycleEventRow",
    (literal) => {
      expect(ROW_SRC).not.toContain(literal)
    },
  )

  it("renders the verbatim advisory caption somewhere in the two components", () => {
    const combined = `${LIST_SRC}\n${ROW_SRC}`
    expect(combined).toContain(
      "Advisory — hardware lifecycle changes do not affect the readiness score.",
    )
  })

  it("does not import the filled Badge pill component in LifecycleEventList", () => {
    expect(LIST_SRC).not.toContain("@/components/ui/badge")
  })

  it("does not import the filled Badge pill component in LifecycleEventRow", () => {
    expect(ROW_SRC).not.toContain("@/components/ui/badge")
  })
})
