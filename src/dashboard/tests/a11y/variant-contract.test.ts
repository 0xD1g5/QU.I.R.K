import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { VARIANTS, isPlaceholderJustification } from "./baseline-diff.mjs"

// Phase 221 / HARNESS-03 / 221-CONTEXT.md D-05, D-06. Run-time enumeration contract:
// every route in routes.json must carry exactly one variant decision (per-endpoint
// `variantMarkers`, or a written `variantInsensitive` reason), and the VARIANTS allowlist,
// npm scripts, CI steps and harness guards must not drift apart. Occurrence sets are derived
// at test time, never from a hand-listed array (mutation M5 targets the route decision).

const PACKAGE_JSON = JSON.parse(readFileSync(path.resolve(__dirname, "../../package.json"), "utf-8"))
const WORKFLOW_TEXT = readFileSync(
  path.resolve(__dirname, "../../../../.github/workflows/dashboard-quality.yml"),
  "utf-8",
)
const RUN_A11Y_SOURCE = readFileSync(path.resolve(__dirname, "run-a11y.mjs"), "utf-8")
const ROUTES: Array<Record<string, unknown> & { slug: string }> = JSON.parse(
  readFileSync(path.resolve(__dirname, "routes.json"), "utf-8"),
)
const NON_DEFAULT = VARIANTS.filter((v: string) => v !== "default")

describe("variant-contract (221-01)", () => {
  it("VARIANTS carries at least three entries (vacuity guard)", () => {
    expect(Array.isArray(VARIANTS)).toBe(true)
    expect(VARIANTS.length).toBeGreaterThanOrEqual(3)
  })

  it("routes.json carries at least 13 routes (vacuity guard)", () => {
    expect(ROUTES.length).toBeGreaterThanOrEqual(13)
  })

  it.each(NON_DEFAULT)("package.json declares a11y:check:%s and a11y:baseline:%s, each setting VITE_A11Y_FIXTURE_VARIANT=%s", (v) => {
    for (const kind of ["check", "baseline"]) {
      const script = PACKAGE_JSON.scripts[`a11y:${kind}:${v}`]
      expect(script, `missing npm script a11y:${kind}:${v}`).toBeTruthy()
      expect(script).toContain(`VITE_A11Y_FIXTURE_VARIANT=${v}`)
    }
  })

  it.each(NON_DEFAULT)("dashboard-quality.yml names both npm run a11y:check:%s and npm run a11y:baseline:%s", (v) => {
    expect(WORKFLOW_TEXT, `no "npm run a11y:check:${v}" step`).toContain(`npm run a11y:check:${v}`)
    expect(WORKFLOW_TEXT, `no "npm run a11y:baseline:${v}" step`).toContain(`npm run a11y:baseline:${v}`)
  })

  it.each(ROUTES.map((r) => r.slug))("route %s carries exactly one variant decision", (slug) => {
    const route = ROUTES.find((r) => r.slug === slug)!
    const markers = route.variantMarkers as Record<string, unknown> | undefined
    const insensitive = route.variantInsensitive
    const hasMarkers = markers !== undefined
    const hasInsensitive = insensitive !== undefined
    expect(
      hasMarkers !== hasInsensitive,
      `route "${slug}" must have exactly one of variantMarkers or variantInsensitive (D-06)`,
    ).toBe(true)
    if (hasMarkers) {
      expect(typeof markers).toBe("object")
      const entries = Object.entries(markers!)
      expect(entries.length, `route "${slug}" variantMarkers is empty`).toBeGreaterThan(0)
      for (const [handler, sel] of entries) {
        expect(typeof sel === "string" && sel.length > 0, `route "${slug}" marker for ${handler} is not a non-empty string`).toBe(true)
      }
    } else {
      expect(typeof insensitive).toBe("string")
      expect(
        isPlaceholderJustification(insensitive),
        `route "${slug}" variantInsensitive reason is a placeholder`,
      ).toBe(false)
    }
  })

  it("run-a11y.mjs refuses a pre-existing server on the port (221 D-02)", () => {
    expect(RUN_A11Y_SOURCE).toContain("already answers before this sweep")
  })

  it("run-a11y.mjs checks the /__a11y-variant sentinel (221 D-02)", () => {
    expect(RUN_A11Y_SOURCE).toContain("__a11y-variant")
  })

  it("run-a11y.mjs applies renderStateViolations before the axe scan (221 D-05)", () => {
    const guard = RUN_A11Y_SOURCE.indexOf("renderStateViolations(")
    const axe = RUN_A11Y_SOURCE.indexOf("new AxePuppeteer(")
    expect(guard).toBeGreaterThan(-1)
    expect(axe).toBeGreaterThan(-1)
    expect(guard).toBeLessThan(axe)
  })
})
