import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { isPlaceholderJustification } from "./baseline-diff.mjs"
import { matchHandler } from "./fixture-handlers.mjs"

// Phase 221 / 221-06 / D-12. UNMEASURED-EXCLUSIONS.md is HAND-maintained, so this test derives the
// REQUIRED row set from source at run time (App.tsx, routes.json, FIXTURE_HANDLERS). A blind spot
// cannot be silently omitted (missing key) and a swept page cannot keep a stale row (orphan key).
// Same discipline as badge-variant-coverage.test.ts: never a hand-listed set of expected keys,
// except the conceptual blind spots that have no source artefact (CONCEPTUAL below).

const A11Y_DIR = __dirname
const APP_TSX = readFileSync(path.resolve(A11Y_DIR, "../../src/App.tsx"), "utf-8")
const HORIZON = readFileSync(path.resolve(A11Y_DIR, "../../../../.planning/HORIZON.md"), "utf-8")
const LEDGER = readFileSync(path.resolve(A11Y_DIR, "UNMEASURED-EXCLUSIONS.md"), "utf-8")

interface Route {
  slug: string
  path: string
  variantInsensitive?: string
  insensitiveEndpoints?: Record<string, string>
  unmarkedEndpoints?: Record<string, string>
  loadingRetired?: string
}
const ROUTES: Route[] = JSON.parse(readFileSync(path.resolve(A11Y_DIR, "routes.json"), "utf-8"))

// Blind spots with no source artefact to derive from.
const CONCEPTUAL = ["tailwind-shorthand-badges", "cytoscape-rendered-canvas"]

function deriveRequired(): Map<string, string> {
  const req = new Map<string, string>()
  const swept = new Set(ROUTES.map((r) => r.path.split("?")[0]))
  // (A) literal <Route path="..."> in App.tsx that no routes.json entry sweeps
  for (const m of APP_TSX.matchAll(/<Route\s+path="([^"]+)"/g)) {
    if (!swept.has(m[1])) req.set(m[1], `App.tsx route ${m[1]} is not in routes.json`)
  }
  // (B) a dynamic path={...} expression (the vertical page)
  if (/path=\{/.test(APP_TSX)) req.set("vertical", "App.tsx registers a path={...} expression")
  // (C) chrome-free /print and the LoginPage
  if (APP_TSX.includes('"/print"')) req.set("/print", 'App.tsx special-cases "/print"')
  if (/import\s*\{\s*LoginPage\s*\}/.test(APP_TSX)) req.set("/login", "App.tsx imports LoginPage")
  for (const r of ROUTES) {
    // (D) variantInsensitive routes
    if (r.variantInsensitive) req.set(r.slug, `routes.json ${r.slug} is variantInsensitive`)
    // (E) unmarked endpoints
    for (const id of Object.keys(r.unmarkedEndpoints ?? {})) {
      req.set(`${r.slug}:${id}`, `routes.json ${r.slug} leaves endpoint ${id} unmarked`)
    }
    // (E2) 221 WR-03: each honouring endpoint a variantInsensitive route consumes
    for (const id of Object.keys(r.insensitiveEndpoints ?? {})) {
      req.set(`${r.slug}:${id}`, `routes.json ${r.slug} is variantInsensitive yet consumes endpoint ${id}`)
    }
    // (F) retired loading legs
    if (r.loadingRetired) req.set(`${r.slug}:loading`, `routes.json ${r.slug} retires its loading leg`)
  }
  // (G) conceptual keys, plus the expanded-row blind spot when no coverage handler exists
  for (const k of CONCEPTUAL) req.set(k, "conceptual blind spot with no source artefact")
  // 221 WR-01: keyed on REACHABILITY, not on a handler id merely existing. A scan-coverage entry
  // shadowed by an earlier one would be dead, and must not retire this row.
  if (matchHandler("/api/scans/1/coverage")?.id !== "scan-coverage") {
    req.set("scan-history-expanded-row", "no FIXTURE_HANDLERS entry reachably serves /api/scans/{id}/coverage")
  }
  return req
}

interface Row {
  id: string
  key: string
  blind: string
  why: string
  owner: string
  date: string
  evidence: string
}

function parseRows(): Row[] {
  const rows: Row[] = []
  for (const line of LEDGER.split("\n")) {
    if (!line.startsWith("| UX-")) continue
    const c = line.split("|").slice(1, -1).map((s) => s.trim())
    rows.push({ id: c[0], key: c[1], blind: c[2], why: c[3], owner: c[4], date: c[5], evidence: c[6] })
  }
  return rows
}

const REQUIRED = deriveRequired()
const ROWS = parseRows()
const ROW_KEYS = new Set(ROWS.map((r) => r.key))

describe("UNMEASURED-EXCLUSIONS.md is enforced against a set derived from source (221-06 D-12)", () => {
  it("derives a non-trivial required set (vacuity floor of 8)", () => {
    expect(REQUIRED.size).toBeGreaterThanOrEqual(8)
  })

  it("has exactly one row per required key (row count equals required set size)", () => {
    expect(ROWS.length).toBe(REQUIRED.size)
    expect(ROW_KEYS.size, "duplicate Key in UNMEASURED-EXCLUSIONS.md").toBe(ROWS.length)
  })

  it.each([...REQUIRED.entries()])("required exclusion %s has a row (%s)", (key) => {
    expect(ROW_KEYS.has(key), `UNMEASURED-EXCLUSIONS.md has no row with Key "${key}"; a blind spot must be named, never implicit`).toBe(true)
  })

  it("has no orphan rows whose Key is not in the derived required set", () => {
    const orphans = ROWS.filter((r) => !REQUIRED.has(r.key)).map((r) => r.key)
    expect(orphans, `orphan exclusion row(s) naming something no longer unmeasured: ${JSON.stringify(orphans)}`).toEqual([])
  })

  it("every row fills every cell and the Why cell is not a placeholder", () => {
    for (const r of ROWS) {
      for (const [name, v] of Object.entries(r)) {
        expect(v.length, `${r.id} cell "${name}" is empty`).toBeGreaterThan(0)
      }
      expect(isPlaceholderJustification(r.why), `${r.id} Why cell is a placeholder`).toBe(false)
    }
  })

  it("every Owner is a 999.NNN id that is a row of the tracked HORIZON.md ledger", () => {
    for (const r of ROWS) {
      expect(/^999\.\d+$/.test(r.owner), `${r.id} Owner "${r.owner}" is not a 999.NNN id`).toBe(true)
      expect(HORIZON.includes(`| **${r.owner}** |`), `${r.id} Owner ${r.owner} has no HORIZON.md ledger row`).toBe(true)
    }
  })

  it("every Date is a real ISO date that is not in the future", () => {
    const tomorrow = Date.now() + 24 * 3600 * 1000
    for (const r of ROWS) {
      expect(/^\d{4}-\d{2}-\d{2}$/.test(r.date), `${r.id} Date "${r.date}" is not ISO`).toBe(true)
      const t = Date.parse(r.date)
      expect(Number.isNaN(t), `${r.id} Date "${r.date}" does not parse`).toBe(false)
      expect(t, `${r.id} Date ${r.date} is in the future`).toBeLessThanOrEqual(tomorrow)
    }
  })

  it("row IDs are unique UX-NN identifiers", () => {
    const ids = ROWS.map((r) => r.id)
    expect(new Set(ids).size).toBe(ids.length)
    for (const id of ids) expect(/^UX-\d{2}$/.test(id), `bad id ${id}`).toBe(true)
  })

  it("the cited cytoscape guard nodes exist in the repo test files", () => {
    const base = path.resolve(A11Y_DIR, "../../src/components/__tests__")
    const a = readFileSync(path.join(base, "cytoscape-label-contrast-guard.test.ts"), "utf-8")
    const b = readFileSync(path.join(base, "roadmap-graph-node-label-contrast-guard.test.ts"), "utf-8")
    expect(a).toContain("holds the shrink-only ratchet against cytoscape-label-contrast-baseline.json")
    expect(b).toContain("every phase's graph node label clears AA against that phase's own fill, in both themes")
  })

  it("every loadingRetired route is a swept route whose reason is not a placeholder", () => {
    for (const r of ROUTES.filter((x) => x.loadingRetired)) {
      expect(isPlaceholderJustification(r.loadingRetired), `${r.slug} loadingRetired reason is a placeholder`).toBe(false)
    }
  })
})
