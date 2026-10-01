// Phase 221 / HARNESS-03 / D-03, D-08. Declarative a11y fixture-handler table.
//
// PURE data module: no fs, no process.env at import time (WR-05 laziness is preserved
// because the vite middleware reads the fixture files lazily). Every handler carries an
// explicit `empty` decision ({body} | {emptyFrom} | {na: reason}) and an explicit
// `loading` decision ({hold: true} | {na: reason}). Silence counts as a defect (D-03):
// tests/a11y/variant-contract.test.ts enumerates this table at run time.
//
// Matching (221 WR-01): FIRST MATCH WINS, so table order is precedence. A `prefix` matches the
// exact path, optionally followed by a query string (`/api/scans`, `/api/scans?x=1`), and NOT
// `/api/scansX` or a sub-path like `/api/scans/1/coverage`. A handler that deliberately serves
// sub-paths declares `subpaths: "<reason>"`, so a parent prefix can never silently answer a
// child endpoint with the wrong shape. A `regex` is anchored by its author (end-anchor it).
// fixture-coverage.test.ts asserts no entry is shadowed by an earlier one.

const NA_QRAMM =
  "questionnaire/session content, not scan-driven; the qramm and qramm-assessment routes are declared variantInsensitive in routes.json (221-01, D-03/D-06)"

const NA_FINDINGS =
  "only requested by the storyline drawer, which opens from a findings table row; empty/loading render no rows, so the interaction is skipped by design (run-a11y.mjs F10c)"

export const FIXTURE_HANDLERS = Object.freeze([
  {
    id: "scan-latest",
    match: { prefix: "/api/scan/latest" },
    default: { file: "fixture-scan.json" },
    empty: { body: {} },
    loading: { hold: true },
  },
  {
    id: "scans",
    match: { prefix: "/api/scans" },
    default: { file: "fixture-scans.json" },
    empty: { body: [] },
    loading: {
      na: "AuthProvider.tsx:77 probes GET /api/scans on mount and renders a blank shell until it resolves (App.tsx AppShell status=loading); holding it would blank EVERY route and no page skeleton could ever be proven (221-05 finding)",
    },
    scope: "chrome",
    scopeReason:
      "sidebar.tsx:191,194 (ScanSelector/ScanDateBadge) fetch it on every route; 221-06: default is fixture-scans.json with exactly ONE session, so ScanSelector (sessions.length <= 1 returns null) stays hidden on every route and only ScanDateBadge's label changes",
  },
  {
    id: "sensor-registry",
    match: { prefix: "/api/sensor/registry" },
    default: { file: "fixture-sensor-registry.json" },
    empty: { body: { sensors: [] } },
    loading: { hold: true },
  },
  {
    id: "trends",
    match: {
      prefix: "/api/trends",
      subpaths:
        "useTimelineData.ts:23 requests /api/trends/timeline?n=30 and has always been answered with this trends body (pre-221 behaviour, kept so the trends baselines do not shift); the timeline chart therefore renders its 'Run two or more scans' fallback, a fabricated state recorded for a dedicated timeline fixture (221 WR-01, 999.118)",
    },
    default: { file: "fixture-trends.json" },
    empty: { body: {} },
    loading: { hold: true },
  },
  {
    id: "vendor-trends",
    match: { prefix: "/api/hardware/vendor-trends" },
    default: { file: "fixture-vendor-trends.json" },
    empty: { body: { events: [], truncated: false } },
    loading: { hold: true },
  },
  {
    id: "hardware-drift",
    match: { prefix: "/api/hardware/drift" },
    default: { file: "fixture-hardware-drift.json" },
    empty: {
      body: {
        has_prior_scan: false,
        latest_scan_at: null,
        latest_events: [],
        historical_events: [],
        historical_truncated: false,
      },
    },
    loading: { hold: true },
  },
  {
    id: "compare",
    match: { prefix: "/api/compare" },
    default: { file: "fixture-compare.json" },
    empty: { emptyFrom: "compare-zero-diff" },
    loading: { hold: true },
  },
  {
    id: "findings",
    match: {
      prefix: "/api/findings",
      subpaths: "useFindingStoryline.ts:68 requests /api/findings/{id}/storyline; this handler exists only to serve that sub-path (fixture-storyline.json)",
    },
    default: { file: "fixture-storyline.json" },
    empty: { na: NA_FINDINGS },
    loading: { na: NA_FINDINGS },
  },
  {
    id: "qramm-answers",
    match: { regex: "^/api/qramm/sessions/\\d+/answers(?:\\?|$)", example: "/api/qramm/sessions/1/answers" },
    default: { qrammKey: "GET /api/qramm/sessions/1/answers", fallback: [] },
    empty: { na: NA_QRAMM },
    loading: { na: NA_QRAMM },
  },
  {
    id: "qramm-session",
    match: { regex: "^/api/qramm/sessions/\\d+(?:\\?|$)", example: "/api/qramm/sessions/1" },
    default: { qrammKey: "GET /api/qramm/sessions/1", fallback: {} },
    empty: { na: NA_QRAMM },
    loading: { na: NA_QRAMM },
  },
  {
    id: "qramm-sessions",
    match: { prefix: "/api/qramm/sessions" },
    default: { qrammKey: "GET /api/qramm/sessions", fallback: [] },
    empty: { na: NA_QRAMM },
    loading: { na: NA_QRAMM },
  },
  {
    id: "qramm-questions",
    match: { prefix: "/api/qramm/questions" },
    default: { qrammKey: "GET /api/qramm/questions", fallback: [] },
    empty: { na: NA_QRAMM },
    loading: { na: NA_QRAMM },
  },
  {
    id: "qramm-profiles",
    match: { prefix: "/api/qramm/profiles" },
    default: { json: { profile_id: 1, session_id: 1, multiplier: 1.0 } },
    empty: { na: NA_QRAMM },
    loading: { na: NA_QRAMM },
  },
])

/** True when `url` is `prefix` exactly, `prefix?query`, or (only with `subpaths`) `prefix/...`. */
export function prefixMatches(match, url) {
  const p = match.prefix
  if (p === undefined) return false
  if (url === p || url.startsWith(p + "?")) return true
  return match.subpaths !== undefined && url.startsWith(p + "/")
}

/** First entry (table order) whose prefix matches on a segment boundary, or whose regex tests true. */
export function matchHandler(url) {
  if (typeof url !== "string") return undefined
  for (const h of FIXTURE_HANDLERS) {
    if (prefixMatches(h.match, url)) return h
    if (h.match.regex !== undefined && new RegExp(h.match.regex).test(url)) return h
  }
  return undefined
}

/**
 * Zero-diff CompareResponse derived from the default compare fixture (221 RESEARCH
 * Finding 3): never `{}`, which crashes ComparePage with a TypeError.
 *
 * 221 WR-09: a TRUE zero diff, never an impossible one. scan_b is scan_a's score and
 * subscores under scan_b's own identity (scan_id, scanned_at), so the rendered "a -> b"
 * values agree with score_delta = 0 and every subscore delta = 0. Every list key is
 * emptied; a null/absent subscore_deltas cannot throw inside the middleware.
 */
export function compareZeroDiff(fixture) {
  const a = fixture.scan_a ?? {}
  const b = fixture.scan_b ?? {}
  const out = {}
  for (const [key, value] of Object.entries(fixture)) {
    if (key === "scan_a") out[key] = structuredClone(a)
    else if (key === "scan_b") {
      out[key] = { ...structuredClone(a), scan_id: b.scan_id, scanned_at: b.scanned_at }
    } else if (key === "score_delta") out[key] = 0
    else if (key === "subscore_deltas") {
      out[key] = Object.fromEntries(Object.keys(value ?? {}).map((k) => [k, 0]))
    } else if (Array.isArray(value)) out[key] = []
    else out[key] = value
  }
  return out
}
