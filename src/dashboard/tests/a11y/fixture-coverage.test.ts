import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync } from "node:fs"
import { FIXTURE_HANDLERS, matchHandler, compareZeroDiff } from "./fixture-handlers.mjs"
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
      // 221 WR-01: keep a template literal's tail (`/api/scans/${id}/coverage` -> /api/scans/1/coverage)
      // instead of collapsing it to its parent prefix, so a child endpoint is a target of its own.
      for (const m of text.matchAll(/["'`](\/api\/(?:[^"'`$?:\s]|\$\{[^}]*\})*)/g)) {
        let t = m[1].replace(/\$\{[^}]*\}/g, "1")
        if (t.length > 1 && t.endsWith("/")) t = t.slice(0, -1)
        targets.add(t)
      }
    }
  }
  return targets
}

// 221 WR-01: a target is covered only if the table itself answers THAT url. No synthetic
// "/1/coverage" or "/1" probes: they let a parent prefix count as coverage for a child endpoint.
function covered(target: string): boolean {
  return matchHandler(target) !== undefined
}

// Fetch targets that no fixture handler serves, with the reason the sweep tolerates it.
const UNFIXTURED: Record<string, string> = {
  "/api/config": "fetched by VerticalProvider and EffectiveConfigPanel on every route; no handler serves it under the harness (default vertical behaviour not verified here). Chrome fetch, 221-06 decides whether to fixture it",
  "/api/config/effective": "only EffectiveConfigPanel requests it; that panel is not on any swept route in routes.json",
  "/api/connectors/availability": "only ConnectorsPanel requests it (scan-new page); /scan/new is not a swept route in routes.json",
  "/api/export/pdf": "download action in executive.tsx triggered by a button click; never fires during a page-load sweep",
  "/api/exposure-map": "pages/exposure-map.tsx; /exposure-map is not a swept route in routes.json (un-swept page)",
  "/api/jobs": "scan-job, scan-new and ScanCoverageChip job polling; those pages are not swept and the chip only fires for an active job",
  "/api/jobs/1": "useJobStatus.ts / scan-job.tsx job polling for /scan/job/:id, which is not a swept route in routes.json",
  "/api/jobs/1/coverage": "ScanCoverageChip.tsx:76 job-scoped coverage; the chip only renders inside an expanded scan-history row or an active job page, neither swept (UX-13)",
  "/api/jobs/1/result-summary": "useJobStatus.ts:72 result summary for /scan/job/:id, which is not a swept route in routes.json",
  "/api/merge/latest": "useMergeLatest, consumed by pages not in the sweep set of routes.json (un-swept page)",
  "/api/qramm/assessment/draft": "QRAMMProvider draft autosave; the qramm routes are variantInsensitive and the draft call is not scan data",
  "/api/reports/latest/1": "executive.tsx:260 report download link (/api/reports/latest/${fmt}); requested on click, not on page load",
  "/api/reports/latest/manifest": "executive.tsx requests it on load and no handler serves it under the harness (not verified which branch renders); candidate for 221-06 fixturing",
  "/api/qramm/sessions/1/compliance-map": "ComplianceMapTab.tsx:121 / useQRAMMPrintData.ts:66; fetched only when the compliance-map tab or the print view opens, neither on a swept page load (221 WR-01: previously answered by the qramm-session regex with the wrong shape)",
  "/api/qramm/sessions/1/score": "ScorecardTab.tsx:80 / ComplianceMapTab.tsx:95 / useQRAMMPrintData.ts:65; fetched only when a scorecard/compliance tab or the print view opens, not on a swept page load (221 WR-01: previously answered by the qramm-session regex with the wrong shape)",
  "/api/scans/1/coverage": "ScanCoverageChip.tsx:77 renders only inside an expanded scan-history row, which the sweep does not expand (UNMEASURED-EXCLUSIONS UX-13). 221 WR-01: previously shadowed by the /api/scans prefix, which answered it with a ScanSession[]",
  "/api/schedules": "useSchedules for /schedules, which is not a swept route in routes.json (un-swept page)",
  "/api/schedules/1": "useSchedules.ts:104,138 per-schedule update/delete for /schedules, which is not a swept route in routes.json",
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

  // 221 WR-01: first match wins, so an entry whose own canonical URL resolves to an EARLIER
  // entry is dead. Each handler's canonical URL is its prefix, or its regex's `example` (which
  // the regex must itself match), plus `<prefix>/x` for a handler that declares `subpaths`.
  it.each(FIXTURE_HANDLERS.map((h: { id: string }) => h.id))("handler %s is reachable (not shadowed by an earlier entry)", (id) => {
    const h = FIXTURE_HANDLERS.find((x: { id: string }) => x.id === id)!
    const probes: string[] = []
    if (h.match.prefix !== undefined) {
      probes.push(h.match.prefix, h.match.prefix + "?probe=1")
      if (h.match.subpaths !== undefined) probes.push(h.match.prefix + "/1/probe")
    }
    if (h.match.regex !== undefined) {
      expect(h.match.example, `regex handler "${id}" must declare match.example`).toBeTruthy()
      expect(new RegExp(h.match.regex).test(h.match.example!), `regex handler "${id}" does not match its own example`).toBe(true)
      probes.push(h.match.example!)
    }
    expect(probes.length, `handler "${id}" has no prefix or regex`).toBeGreaterThan(0)
    for (const u of probes) expect(matchHandler(u)?.id, `"${u}" should reach handler "${id}"`).toBe(id)
  })

  it.each(FIXTURE_HANDLERS.filter((h: { match: { subpaths?: string } }) => h.match.subpaths !== undefined).map((h: { id: string }) => h.id))(
    "handler %s declares a written reason for serving sub-paths",
    (id) => {
      const h = FIXTURE_HANDLERS.find((x: { id: string }) => x.id === id)!
      expect(typeof h.match.subpaths === "string" && h.match.subpaths.length >= 20, `handler "${id}" subpaths reason too short`).toBe(true)
    },
  )

  it("a prefix never matches a longer sibling segment or an undeclared sub-path (221 WR-01)", () => {
    expect(matchHandler("/api/scansX")).toBeUndefined()
    expect(matchHandler("/api/scans/1/coverage")).toBeUndefined()
    expect(matchHandler("/api/scans")?.id).toBe("scans")
  })

  it("fixture-scans.json holds exactly one ScanSession and fixture-sensor-registry.json one row per status (221-06)", () => {
    const scans = JSON.parse(readFileSync(path.resolve(__dirname, "fixture-scans.json"), "utf-8"))
    expect(Array.isArray(scans)).toBe(true)
    // exactly one keeps ScanSelector (sessions.length <= 1) hidden on every route
    expect(scans.length).toBe(1)
    for (const k of ["scan_id", "scanned_at", "total_endpoints", "score", "profile", "calibration", "target", "finding_counts", "rating"]) {
      expect(k in scans[0], `fixture-scans.json session is missing "${k}"`).toBe(true)
    }
    const fc = scans[0].finding_counts
    expect(fc.high).toBeGreaterThan(0)
    expect(fc.medium).toBeGreaterThan(0)
    expect(fc.low).toBeGreaterThan(0)

    const reg = JSON.parse(readFileSync(path.resolve(__dirname, "fixture-sensor-registry.json"), "utf-8"))
    expect(Array.isArray(reg.sensors)).toBe(true)
    expect(reg.sensors.map((s: { status: string }) => s.status).sort()).toEqual(["current", "stale", "unknown"])
  })

  it("FIXTURE_HANDLERS still carries the hardware-drift, vendor-trends, compare and findings handlers", () => {
    const ids = FIXTURE_HANDLERS.map((h: { id: string }) => h.id)
    for (const id of ["hardware-drift", "vendor-trends", "compare", "findings"]) {
      expect(ids, `handler "${id}" missing from FIXTURE_HANDLERS`).toContain(id)
    }
  })

  // 221 WR-09: the empty compare fixture must be a CompareResponse that can occur. ComparePage
  // renders scan_a/scan_b scores and per-subscore a/b values next to the deltas, so a/b must
  // agree with the zeroed deltas (no "55 -> 62, delta 0").
  it("compareZeroDiff yields a consistent zero diff (221 WR-09)", () => {
    const fixture = JSON.parse(readFileSync(path.resolve(__dirname, "fixture-compare.json"), "utf-8"))
    const out = compareZeroDiff(fixture) as {
      scan_a: { scan_id: string; scanned_at: string; score: number; subscores: Record<string, number> }
      scan_b: { scan_id: string; scanned_at: string; score: number; subscores: Record<string, number> }
      score_delta: number
      subscore_deltas: Record<string, number>
      [k: string]: unknown
    }
    expect(out.scan_b.score - out.scan_a.score).toBe(out.score_delta)
    expect(out.score_delta).toBe(0)
    const keys = Object.keys(out.subscore_deltas)
    expect(keys.length).toBeGreaterThan(0)
    for (const k of keys) {
      expect(out.scan_b.subscores[k] - out.scan_a.subscores[k], `subscore ${k}`).toBe(out.subscore_deltas[k])
    }
    expect(out.scan_b.scan_id).toBe(fixture.scan_b.scan_id)
    expect(out.scan_b.scanned_at).toBe(fixture.scan_b.scanned_at)
    for (const [k, v] of Object.entries(fixture)) {
      if (Array.isArray(v)) expect(out[k], `list ${k} not emptied`).toEqual([])
    }
    expect(() => compareZeroDiff({ ...fixture, subscore_deltas: null })).not.toThrow()
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
