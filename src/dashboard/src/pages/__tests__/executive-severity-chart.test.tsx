// Phase 206 Plan 02 (COV-04) — UAT-7-04: Executive Page — Severity Chart.
//
// Pass Criteria under test (docs/UAT-SERIES.md UAT-7-04):
//   - Chart renders with at least 2 severity levels  <- covered
//   - Severity counts match findings in the real scan-output JSON file  <- PARTIAL,
//     see the coverage note at the end of this file
//   - Chart is interactive (hover shows count)  <- UNCOVERED, see below
import { describe, it, expect, vi, beforeAll, afterAll } from "vitest"
import { render, within } from "@testing-library/react"

// MEASURED (this task): the global test-setup.ts ResizeObserver stub never
// fires a callback, and Recharts' <ResponsiveContainer> also reads its
// initial size synchronously via `containerRef.current.getBoundingClientRect()`
// (node_modules/recharts/es6/component/ResponsiveContainer.js) on mount.
// jsdom's default getBoundingClientRect() returns an all-zero rect, so
// `calculatedWidth` resolves to 0 and the chart renders a genuinely EMPTY
// `<div class="recharts-responsive-container">` — confirmed live: with no
// override, `screen.debug()` shows a self-closing responsive-container div
// with zero children (not just 0-height bars — nothing at all, not even
// axis tick text).
//
// A NAIVE fixed-size override (same rect for every element) was tried first
// and made things WORSE, not better: Recharts also measures each axis tick
// LABEL's own size via `getStringSize()` (node_modules/recharts/es6/util/
// DOMUtils.js:60), which appends an off-screen `<span id=
// "recharts_measurement_span">` and reads ITS getBoundingClientRect(). A
// single fixed rect for every element made every tick label appear 400px
// wide, which fed Recharts' internal tick-collision/interval logic and
// collapsed the y-axis down to rendering only ONE category tick (confirmed
// live). The fix distinguishes the measurement span (approximate its size
// from its own text length) from the container (a fixed, realistic pixel
// size) — this reproduces what a real browser's layout engine would report
// for each, rather than stubbing away the very sizing behavior under test.
const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect
beforeAll(() => {
  Element.prototype.getBoundingClientRect = function (this: Element) {
    if (this.id === "recharts_measurement_span") {
      const text = this.textContent ?? ""
      return {
        width: text.length * 7,
        height: 14,
        top: 0,
        left: 0,
        bottom: 14,
        right: text.length * 7,
        x: 0,
        y: 0,
        toJSON() {
          return {}
        },
      } as DOMRect
    }
    return {
      width: 400,
      height: 180,
      top: 0,
      left: 0,
      bottom: 180,
      right: 400,
      x: 0,
      y: 0,
      toJSON() {
        return {}
      },
    } as DOMRect
  }
})
afterAll(() => {
  Element.prototype.getBoundingClientRect = originalGetBoundingClientRect
})

const FIXTURE = {
  meta: { scan_id: "scan-1", scanned_at: "2026-09-01T00:00:00Z", total_endpoints: 4, total_findings: 6 },
  score: {
    score: 65,
    rating: "GOOD",
    subscores: {
      hygiene: 20,
      modern_tls: 18,
      identity_trust: 15,
      agility_signals: 12,
      data_at_rest: null,
      data_in_motion: null,
    },
    drivers: [],
  },
  confidence: { confidence_score: 0.8, confidence_rating: "HIGH", factor_breakdown: {} },
  findings: [
    { id: 1, host: "a.example.com", port: 443, severity: "CRITICAL", title: "f1" },
    { id: 2, host: "b.example.com", port: 443, severity: "CRITICAL", title: "f2" },
    { id: 3, host: "c.example.com", port: 22, severity: "HIGH", title: "f3" },
    { id: 4, host: "d.example.com", port: 443, severity: "MEDIUM", title: "f4" },
    { id: 5, host: "e.example.com", port: 443, severity: "MEDIUM", title: "f5" },
    { id: 6, host: "f.example.com", port: 443, severity: "MEDIUM", title: "f6" },
  ],
  certificates: [],
  cbom_components: [],
  roadmap: { nodes: [], edges: [] },
  identity_findings: [],
  motion_findings: [],
  dar_findings: [],
  hardware_findings: [],
  hardware_devices: [],
  partial_failures: [],
  excluded_cert_count: 0,
  projected_score: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => ({ data: FIXTURE, loading: false, error: null }),
}))

vi.mock("@/hooks/useMergeLatest", () => ({
  useMergeLatest: () => ({ merge: null, loading: false, error: null }),
}))

vi.mock("@/context/vertical-context", () => ({
  useVertical: () => ({ id: "general", label: "General", Icon: () => null, accentColor: "", navItem: null }),
}))

vi.mock("@/components/RegressionAlertChip", () => ({
  RegressionAlertChip: () => null,
}))

describe("ExecutivePage — UAT-7-04", () => {
  it("renders one severity chart category label per severity present in the fixture with counts derived from the same fixture", async () => {
    const { ExecutivePage } = await import("@/pages/executive")
    const { container } = render(<ExecutivePage />)

    // Recharts appends an off-screen `#recharts_measurement_span` to
    // `document.body` for its own text-width measurement (DOMUtils.js) —
    // it is not part of the chart's visible output and would collide with
    // the same severity words on the y-axis. Scope every query to the
    // chart's own SVG so that stray element is never a match candidate.
    const chartSvg = container.querySelector(".recharts-surface")
    expect(chartSvg).not.toBeNull()
    const chart = within(chartSvg as HTMLElement)

    // Derive expected per-severity counts by filtering FIXTURE.findings — the
    // SAME object the mock served — never a hand-duplicated literal and
    // never a read of the real scan-output JSON from disk.
    const bySeverity = FIXTURE.findings.reduce<Record<string, number>>((acc, f) => {
      acc[f.severity] = (acc[f.severity] ?? 0) + 1
      return acc
    }, {})
    const present = Object.keys(bySeverity)
    expect(present.length).toBeGreaterThanOrEqual(2)

    // executive.tsx's YAxis renders one <text> tick per severity CATEGORY
    // present in `chartData` (all 5 — CRITICAL/HIGH/MEDIUM/LOW/INFO — are
    // always ticked, even at count 0, since chartData maps over the fixed
    // 5-severity list). Assert the severities actually present in the
    // fixture appear as y-axis tick labels.
    for (const severity of present) {
      expect(chart.getByText(severity)).toBeInTheDocument()
    }

    // MEASURED (this task, both with and without the getBoundingClientRect
    // patch above): executive.tsx's <Bar> uses only <Cell> for per-severity
    // FILL COLOR — it has no <LabelList> or other data-label child, so no
    // per-category count is ever rendered as its own text node in this
    // chart, in production or under test. The bar-rectangle <g> elements
    // themselves render as empty, attribute-less groups under jsdom (no
    // <path>/<rect> child at all), independent of container sizing — this
    // is Pitfall 1's Bar/rect-geometry hazard confirmed live and found to
    // be stronger than predicted (not just 0-height bars; no shape element
    // renders at all). A rendered numeric "count per category" readout to
    // assert against genuinely does not exist for this DOM.
    //
    // The one fixture-derived numeric value this chart's axis DOES
    // honestly expose is its x-axis (type="number") domain max tick, which
    // Recharts computes directly from chartData's count values — i.e. it
    // is driven by, and changes with, the same counts under test. Assert
    // that value, sourced from FIXTURE, per the acceptance criterion that
    // forbids a hand-duplicated literal.
    const maxCount = Math.max(...Object.values(bySeverity))
    expect(chart.getAllByText(String(maxCount)).length).toBeGreaterThanOrEqual(1)
  })
})

// ## Coverage note (206-12 reads this from the red-proof Citations section,
// not from here — duplicated in prose for a human reader of this file):
// two of the case's three Pass Criteria bullets are NOT fully exercised
// above:
//   - "Severity counts match findings in the real scan-output JSON file" — this
//     chart never renders a per-category numeric count as its own text
//     node (no <LabelList>, only <Cell> fill color), and Recharts' <Bar>
//     shape geometry does not render inside jsdom at all in this project's
//     setup (measured live, both with and without a getBoundingClientRect
//     patch) — only the axis structure (category ticks, numeric domain
//     ticks) renders. The test above asserts the fixture-derived x-axis
//     domain max as the closest honestly-renderable proxy; a true
//     per-category count comparison is not exerciseable.
//   - "Chart is interactive (hover shows count)" — jsdom has no layout
//     engine, so Recharts' Tooltip positioning (which activates on a real
//     pointer-move + measured bounding box) is not honestly driveable in
//     this environment.
// Both bullets are named as uncovered in
// red-proof/206-RED-PROOF-executive.md.
