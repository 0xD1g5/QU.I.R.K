import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync } from "node:fs"
import { FIXTURE_HANDLERS, matchHandler } from "./fixture-handlers.mjs"
import path from "node:path"

// Phase 185 D-14 / 221-03 D-06: "covered but blind" guard, now enumerated at RUN TIME.
//
// Every "/api/..." string or template literal under src/{hooks,pages,components,context,lib}
// is collected by walking the source tree (no hand-listed hook array), normalised to its
// prefix, and must either be matched by a FIXTURE_HANDLERS entry or be named in UNFIXTURED
// with a written reason. A new fetch target, or a deleted handler, goes red by name.

const SRC_DIR = path.resolve(__dirname, "../../src")
const SCAN_DIRS = ["hooks", "pages", "components", "context", "lib"]

function walk(dir: string, out: string[] = []): string[] {
  let entries: import("node:fs").Dirent[]
  try {
    entries = readdirSync(dir, { withFileTypes: true })
  } catch {
    return out
  }
  for (const e of entries) {
    if (e.name === "__tests__" || e.name === "node_modules") continue
    const full = path.join(dir, e.name)
    if (e.isDirectory()) walk(full, out)
    else if (/\.(ts|tsx)$/.test(e.name) && !/\.test\./.test(e.name)) out.push(full)
  }
  return out
}

function enumerateApiTargets(): Set<string> {
  const targets = new Set<string>()
  for (const d of SCAN_DIRS) {
    for (const file of walk(path.join(SRC_DIR, d))) {
      const text = readFileSync(file, "utf-8")
      for (const m of text.matchAll(/["'`](\/api\/[^"'`$?\s]*)/g)) {
        let t = m[1]
        if (t.length > 1 && t.endsWith("/")) t = t.slice(0, -1)
        targets.add(t)
      }
    }
  }
  return targets
}

function covered(target: string): boolean {
  return [target, target + "/1/coverage", target + "/1"].some((u) => matchHandler(u) !== undefined)
}

// Fetch targets that no fixture handler serves, with the reason the sweep tolerates it.
const UNFIXTURED: Record<string, string> = {
  "/api/config": "fetched by VerticalProvider and EffectiveConfigPanel on every route; no handler serves it under the harness (default vertical behaviour not verified here). Chrome fetch, 221-06 decides whether to fixture it",
  "/api/config/effective": "only EffectiveConfigPanel requests it; that panel is not on any swept route in routes.json",
  "/api/connectors/availability": "only ConnectorsPanel requests it (scan-new page); /scan/new is not a swept route in routes.json",
  "/api/export/pdf": "download action in executive.tsx triggered by a button click; never fires during a page-load sweep",
  "/api/exposure-map": "pages/exposure-map.tsx; /exposure-map is not a swept route in routes.json (un-swept page)",
  "/api/jobs": "scan-job, scan-new and ScanCoverageChip job polling; those pages are not swept and the chip only fires for an active job",
  "/api/merge/latest": "useMergeLatest, consumed by pages not in the sweep set of routes.json (un-swept page)",
  "/api/qramm/assessment/draft": "QRAMMProvider draft autosave; the qramm routes are variantInsensitive and the draft call is not scan data",
  "/api/reports/latest": "executive.tsx report download link; requested on click, not on page load",
  "/api/reports/latest/manifest": "executive.tsx requests it on load and no handler serves it under the harness (not verified which branch renders); candidate for 221-06 fixturing",
  "/api/schedules": "useSchedules for /schedules, which is not a swept route in routes.json (un-swept page)",
  "/api/sensor/registry": "useSensorRegistry for /sensors, which is not a swept route in routes.json (un-swept page)",
}

const TARGETS = [...enumerateApiTargets()].sort()

describe("a11y fixture table covers every /api/ fetch target (D-14, 221 D-06)", () => {
  it("enumerates at least 15 distinct /api/ targets (vacuity floor)", () => {
    expect(TARGETS.length).toBeGreaterThanOrEqual(15)
  })

  it.each(TARGETS)("fetch target %s is handled by FIXTURE_HANDLERS or listed in UNFIXTURED", (target) => {
    const handled = covered(target)
    const reason = UNFIXTURED[target]
    expect(
      handled || (typeof reason === "string" && reason.length >= 20),
      `"${target}" is fetched under src/ but no FIXTURE_HANDLERS entry matches it and UNFIXTURED has no reason`,
    ).toBe(true)
  })

  it.each(Object.keys(UNFIXTURED))("UNFIXTURED key %s is still fetched and still unhandled", (key) => {
    expect(TARGETS.includes(key), `UNFIXTURED lists "${key}" but no source fetches it any more`).toBe(true)
    expect(covered(key), `UNFIXTURED lists "${key}" but a FIXTURE_HANDLERS entry now covers it`).toBe(false)
  })

  it("FIXTURE_HANDLERS still carries the hardware-drift, vendor-trends, compare and findings handlers", () => {
    const ids = FIXTURE_HANDLERS.map((h: { id: string }) => h.id)
    for (const id of ["hardware-drift", "vendor-trends", "compare", "findings"]) {
      expect(ids, `handler "${id}" missing from FIXTURE_HANDLERS`).toContain(id)
    }
  })

  it("fixture-storyline.json parses and carries all ten locked FindingStoryline keys", () => {
    const storyline = JSON.parse(
      readFileSync(path.resolve(__dirname, "fixture-storyline.json"), "utf-8"),
    )
    const lockedKeys = [
      "finding_id",
      "narrative",
      "quantum_impact",
      "remediation_guidance",
      "theme_slug",
      "theme_title",
      "theme_score_lift",
      "theme_finding_count",
      "theme_closed_count",
      "finding_position",
    ]
    for (const key of lockedKeys) {
      expect(key in storyline, `fixture-storyline.json is missing locked key "${key}"`).toBe(true)
    }
    // UI-SPEC Assumption A4: finding_position is always null in production — a fabricated
    // position would baseline a DOM that cannot occur.
    expect(storyline.finding_position).toBeNull()
  })

  it("fixture files referenced by the new handlers are non-empty and well-shaped", () => {
    const drift = JSON.parse(
      readFileSync(path.resolve(__dirname, "fixture-hardware-drift.json"), "utf-8"),
    )
    expect(Array.isArray(drift.latest_events)).toBe(true)
    expect(drift.latest_events.length).toBeGreaterThan(0)
    expect(Array.isArray(drift.historical_events)).toBe(true)
    expect(drift.historical_events.length).toBeGreaterThan(0)

    const vendorTrends = JSON.parse(
      readFileSync(path.resolve(__dirname, "fixture-vendor-trends.json"), "utf-8"),
    )
    expect(Array.isArray(vendorTrends.events)).toBe(true)
    expect(vendorTrends.events.length).toBeGreaterThan(0)

    const compare = JSON.parse(readFileSync(path.resolve(__dirname, "fixture-compare.json"), "utf-8"))
    expect(compare.scan_a).toBeTruthy()
    expect(compare.scan_b).toBeTruthy()
    expect(Array.isArray(compare.hardware_drift)).toBe(true)
    expect(compare.hardware_drift.length).toBeGreaterThan(0)

    const scan = JSON.parse(readFileSync(path.resolve(__dirname, "fixture-scan.json"), "utf-8"))
    expect(Array.isArray(scan.hardware_findings)).toBe(true)
    expect(scan.hardware_findings.length).toBeGreaterThanOrEqual(2)
  })
})
