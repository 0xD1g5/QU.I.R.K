// Phase 206 Plan 02 (COV-04) — UAT-7-03: Executive Page — Score Gauge.
//
// Pass Criteria under test (docs/UAT-SERIES.md UAT-7-03):
//   - Score gauge renders with a numeric value 0-100
//   - Score label visible (EXCELLENT/GOOD/MODERATE/FAIR/POOR)
//   - Confidence badge present with value
// ("Score color-coded" is a presentation detail delegated to ScoreGauge's
//  own `_gaugeColor()` — already covered structurally by ScoreGauge's own
//  render, not re-asserted pixel-for-pixel here.)
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

const FIXTURE = {
  meta: { scan_id: "scan-1", scanned_at: "2026-09-01T00:00:00Z", total_endpoints: 4, total_findings: 6 },
  score: {
    score: 72,
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
  findings: [],
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

describe("ExecutivePage — UAT-7-03", () => {
  it("renders the executive score gauge with the fixture score, its rating label, and the confidence badge", async () => {
    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    // Numeric score value 0-100, taken from the fixture. The score renders
    // twice on this page (the ScoreGauge SVG text, and ExecutiveVerdict's
    // headline number) — assert at least one occurrence exists.
    expect(screen.getAllByText(String(FIXTURE.score.score)).length).toBeGreaterThanOrEqual(1)

    // Rating label. This page does NOT render the raw EXCELLENT/GOOD/
    // MODERATE/FAIR/POOR words verbatim (that literal 5-word vocabulary was
    // superseded by VERDICT-01/D-07's 3-tone collapse). What it DOES render,
    // derived exclusively from the same `score.rating` field the Pass
    // Criterion is about, is ExecutiveVerdict's tone label — "QUANTUM-READY"
    // for a GOOD/EXCELLENT rating (ratingToTone -> "safe" ->
    // TONE_LABEL.safe). This is the qualitative score label this build
    // actually ships; asserting it is the honest current-product equivalent
    // of the case's "score label visible" bullet.
    expect(screen.getByText("QUANTUM-READY")).toBeInTheDocument()

    // Confidence badge — rendered as "High Confidence" for HIGH rating.
    expect(screen.getByText("High Confidence")).toBeInTheDocument()
  })
})
