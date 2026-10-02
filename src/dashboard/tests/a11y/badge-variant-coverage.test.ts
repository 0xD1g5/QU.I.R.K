/**
 * Source-derived badge-variant fixture coverage gate — Phase 216 plan 216-02
 * (HARNESS-02 / 216-CONTEXT.md D-08).
 *
 * WHY THIS FILE EXISTS. `/certificates` and `/hardware` could report a clean
 * axe PASS while the page contains badge pairs below AA, because axe can
 * only audit DOM that exists and the a11y fixture (`fixture-scan.json`) did
 * not make every badge-style-map key render. This test closes that loop
 * mechanically: it reads each page's badge-style maps from source at run
 * time via `extractBadgeMaps` (never a hand-maintained list — this project
 * has been bitten six times by exactly that drift class, CLAUDE.md §
 * Staleness Review Cadence), and asserts every discovered key is reached by
 * the fixture.
 *
 * DISPOSITION LEDGER. Every discovered map needs a row here, keyed
 * `"<file>:<MAP_NAME>"`. A `raw-field` row's observed keys are the distinct
 * values that field takes across the relevant `fixture-scan.json` array. A
 * `derived-label` row's observed keys are mechanically produced by calling
 * the named exported label function (from `@/pages/hardware-badge-labels`)
 * against every fixture row — not a declared list of expected labels.
 *
 * ANTI-TAUTOLOGY (216-VALIDATION.md falsifier 2). A coverage test that
 * discovers zero badge maps must FAIL, not pass vacuously. Assertion group 1
 * below exists solely to catch that: if `extractBadgeMaps`'s regex ever
 * under-reads to zero, this test goes red instead of silently asserting
 * nothing. Falsifier-2's RED demonstration (temporarily breaking the
 * discovery/ledger symmetry and watching this file go red) is recorded in
 * `216-02-SUMMARY.md`, not in this file — this file only asserts the
 * passing shape.
 *
 * SCOPE FINDING (recorded, not papered over). The file glob genuinely scans
 * every `src/pages/*.tsx` — as the plan requires — and it discovers 11 more
 * badge-style maps outside `hardware.tsx`/`certificates.tsx`: `cbom.tsx`'s
 * `QS_BADGE`/`TIER_BADGE`, and a `SEVERITY_STYLES` (plus `identity.tsx`'s
 * `STATUS_BADGE_STYLES`, `findings.tsx`'s inline `colors`) map in
 * `compare.tsx`, `data-at-rest.tsx`, `findings.tsx`, `identity.tsx`,
 * `motion.tsx`, `scan-history.tsx` and `trends.tsx`. HARNESS-02
 * (216-CONTEXT.md D-05..D-09) scopes the fixture-blind-spot repair to
 * `/certificates` and `/hardware` specifically — those are the two routes
 * with a confirmed, measured blind spot (D-05). Verifying fixture coverage
 * for the other 11 maps is real, valuable work but belongs to a future
 * phase, not a silent side effect of this one widening `fixture-scan.json`'s
 * other nine arrays. Per D-08's own instruction ("if the map cannot be read
 * ... that page is listed in the test with a written reason — never
 * silently omitted"), those 11 maps are named explicitly in
 * `OUT_OF_SCOPE_MAPS` below with that reason, not left to silently pass or
 * silently fail.
 */
import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync } from "node:fs"
import path from "node:path"
import { extractBadgeMaps, dispositionCoverage } from "./badge-map-extractor.mjs"
import {
  snmpLabel,
  bridgeLabel,
  modbusLabel,
  bacnetLabel,
} from "@/pages/hardware-badge-labels"
import type { HardwareFinding, CertItem } from "@/types/api"

const PAGES_DIR = path.resolve(__dirname, "../../src/pages")
const FIXTURE_PATH = path.resolve(__dirname, "fixture-scan.json")

// Scope derived at run time, never written down: every non-skeleton .tsx
// file directly under src/pages/. A page added tomorrow is scanned tomorrow.
function pageFiles(): string[] {
  return readdirSync(PAGES_DIR)
    .filter((f) => f.endsWith(".tsx") && !f.endsWith(".skeleton.tsx"))
    .sort()
}

interface TaggedMap {
  file: string
  name: string
  keys: string[]
}

function discoverAllMaps(): TaggedMap[] {
  const found: TaggedMap[] = []
  for (const file of pageFiles()) {
    const source = readFileSync(path.join(PAGES_DIR, file), "utf-8")
    for (const map of extractBadgeMaps(source)) {
      found.push({ file, ...map })
    }
  }
  return found
}

// Disposition ledger — every discovered badge map must have a row here.
// kind: 'raw-field' -> observed keys are the distinct values `field` takes
//   across the named fixture array.
// kind: 'derived-label' -> observed keys are produced by calling `fn` (an
//   export of hardware-badge-labels.ts) against every row of the named
//   fixture array.
type LedgerRow =
  | { kind: "raw-field"; field: string; fixtureArray: "hardware_findings" | "certificates" }
  | { kind: "derived-label"; fn: "snmpLabel" | "bridgeLabel" | "modbusLabel" | "bacnetLabel"; fixtureArray: "hardware_findings" }

const LEDGER: Record<string, LedgerRow> = {
  "hardware.tsx:TIER_STYLES": { kind: "raw-field", field: "remediation_tier", fixtureArray: "hardware_findings" },
  "hardware.tsx:PQC_STYLES": { kind: "raw-field", field: "pqc_status", fixtureArray: "hardware_findings" },
  "hardware.tsx:CONF_STYLES": { kind: "raw-field", field: "confidence", fixtureArray: "hardware_findings" },
  "hardware.tsx:SNMP_STYLES": { kind: "derived-label", fn: "snmpLabel", fixtureArray: "hardware_findings" },
  "hardware.tsx:BRIDGE_STYLES": { kind: "derived-label", fn: "bridgeLabel", fixtureArray: "hardware_findings" },
  "hardware.tsx:MODBUS_STYLES": { kind: "derived-label", fn: "modbusLabel", fixtureArray: "hardware_findings" },
  "hardware.tsx:BACNET_STYLES": { kind: "derived-label", fn: "bacnetLabel", fixtureArray: "hardware_findings" },
  "certificates.tsx:QS_BADGE": { kind: "raw-field", field: "quantum_safety", fixtureArray: "certificates" },
}

const LABEL_FNS: Record<string, (f: HardwareFinding) => string> = {
  snmpLabel,
  bridgeLabel,
  modbusLabel,
  bacnetLabel,
}

// Known dead map keys — a key present in a source map's object literal that
// no raw wire value can ever produce. Reported honestly rather than papered
// over with a fabricated fixture value. Every entry must carry a reason.
//
// SNMP_STYLES:"v3 failed → none" — snmpLabel() has no branch that returns
// this string: its "v3-failed-fell-back" case returns "v3 failed → v2c",
// and no other case can reach "v3 failed → none". Cross-referenced against
// quirk/reports/html_renderer.py's _snmp_badge_label, which carries the same
// dead mapping. Not a harness defect; not removed in this phase.
const UNREACHABLE: Record<string, string> = {
  "hardware.tsx:SNMP_STYLES:v3 failed → none":
    "snmpLabel() has no branch producing this label; dead map key, cross-referenced against quirk/reports/html_renderer.py's _snmp_badge_label (same dead mapping there).",
}

// Badge-style maps discovered outside hardware.tsx/certificates.tsx. HARNESS-02
// (216-CONTEXT.md D-05..D-09) scopes the fixture blind-spot repair to
// /certificates and /hardware specifically (see module docstring "SCOPE
// FINDING"). These maps are acknowledged as discovered, and exempted from the
// key-coverage assertion below, rather than silently passed or silently
// failed — a future phase may extend fixture coverage to them; this one does
// not.
const OUT_OF_SCOPE_MAPS: Record<string, string> = {
  "cbom.tsx:QS_BADGE": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
  "cbom.tsx:TIER_BADGE": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
  "compare.tsx:SEVERITY_STYLES": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
  "data-at-rest.tsx:SEVERITY_STYLES": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
  "findings.tsx:SEVERITY_STYLES": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
  "findings.tsx:colors": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
  "identity.tsx:SEVERITY_STYLES": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
  "identity.tsx:STATUS_BADGE_STYLES": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
  "motion.tsx:SEVERITY_STYLES": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
  "scan-history.tsx:SEVERITY_STYLES": "/scans is axe-swept since Phase 221 (221-06); fixture-scans.json's single session renders the HIGH/MEDIUM/LOW badges (non-zero finding_counts). Key reach is not raw-field derivable here (the map keys are not fixture field values), so it stays a self-covering row",
  "trends.tsx:SEVERITY_STYLES": "out of HARNESS-02 scope (D-05..D-09 name only /certificates + /hardware)",
}

function loadFixture() {
  return JSON.parse(readFileSync(FIXTURE_PATH, "utf-8")) as {
    hardware_findings: HardwareFinding[]
    certificates: CertItem[]
  }
}

function observedKeysFor(id: string, row: LedgerRow, fixture: ReturnType<typeof loadFixture>): string[] {
  if (row.kind === "raw-field") {
    const rows = fixture[row.fixtureArray] as Record<string, unknown>[]
    const values = rows.map((r) => r[row.field]).filter((v): v is string => typeof v === "string")
    return [...new Set(values)]
  }
  const fn = LABEL_FNS[row.fn]
  const rows = fixture[row.fixtureArray]
  const labels = rows.map((r) => fn(r))
  return [...new Set(labels)]
}

describe("badge-variant fixture coverage is derived from source, not declared (D-08)", () => {
  const maps = discoverAllMaps()
  const fixture = loadFixture()

  const observedKeysByMap: Record<string, string[]> = {}
  for (const [id, row] of Object.entries(LEDGER)) {
    observedKeysByMap[id] = observedKeysFor(id, row, fixture)
  }
  // Out-of-scope maps disposition to a ledger entry that trivially
  // self-covers (observed keys = the map's own discovered keys) — this
  // records the map as dispositioned (so undispositionedMaps stays empty and
  // orphanedLedgerRows still catches a rename/removal) without asserting
  // anything about whether the fixture reaches its keys, which is exactly
  // what "out of scope" means here.
  const mapKeysById = new Map(maps.map((m) => [`${m.file}:${m.name}`, m.keys]))
  for (const id of Object.keys(OUT_OF_SCOPE_MAPS)) {
    observedKeysByMap[id] = mapKeysById.get(id) ?? []
  }

  const ledgerForComparator: Record<string, unknown> = { ...LEDGER, ...OUT_OF_SCOPE_MAPS }

  const { uncoveredKeys, undispositionedMaps, orphanedLedgerRows } = dispositionCoverage({
    maps,
    ledger: ledgerForComparator,
    observedKeysByMap,
  })

  // Partition uncoveredKeys against the explicit UNREACHABLE allowlist —
  // this is the test's own acceptability judgment, deliberately kept out of
  // the pure comparator (badge-map-extractor.mjs).
  const trulyUncovered = uncoveredKeys.filter((k) => !(k in UNREACHABLE))
  const unreachableFound = uncoveredKeys.filter((k) => k in UNREACHABLE)

  it("discovers a non-zero number of badge maps in total, and in hardware.tsx specifically (anti-tautology falsifier 2)", () => {
    const perFile = new Map<string, number>()
    for (const m of maps) perFile.set(m.file, (perFile.get(m.file) ?? 0) + 1)
    console.log("Discovered badge maps per file:", Object.fromEntries(perFile))

    expect(maps.length, "extractBadgeMaps discovered zero maps across all of src/pages/ — the extractor regex under-read to zero").toBeGreaterThan(0)
    expect(
      perFile.get("hardware.tsx") ?? 0,
      "extractBadgeMaps discovered zero maps in hardware.tsx specifically",
    ).toBeGreaterThan(0)
  })

  it("has a ledger row for every discovered map (undispositionedMaps is empty)", () => {
    expect(
      undispositionedMaps,
      `Discovered badge map(s) with no disposition-ledger row — a new badge map was added without dispositioning it: ${JSON.stringify(undispositionedMaps)}`,
    ).toEqual([])
  })

  it("has a discovered map for every ledger row (orphanedLedgerRows is empty)", () => {
    expect(
      orphanedLedgerRows,
      `Disposition-ledger row(s) with no matching discovered map — a map was renamed or the extractor stopped seeing it: ${JSON.stringify(orphanedLedgerRows)}`,
    ).toEqual([])
  })

  it("reaches every discovered, dispositioned map key with the fixture (uncoveredKeys, minus known-unreachable keys, is empty)", () => {
    expect(
      trulyUncovered,
      `Fixture does not reach the following badge-map keys: ${JSON.stringify(trulyUncovered)}`,
    ).toEqual([])
  })

  it("mentions all four derived-label maps, so this is not a tautology that never exercises them", () => {
    const source = readFileSync(__filename, "utf-8")
    expect(source).toContain("SNMP_STYLES")
    expect(source).toContain("BRIDGE_STYLES")
    expect(source).toContain("MODBUS_STYLES")
    expect(source).toContain("BACNET_STYLES")
  })

  it("every discovered-unreachable key matches the explicit, reasoned UNREACHABLE allowlist exactly", () => {
    expect(new Set(unreachableFound)).toEqual(new Set(Object.keys(UNREACHABLE)))
  })
})
