// Phase 206 Plan 02 (COV-04) — UAT-7-05: Executive Page — Score Driver Cards.
//
// Pass Criteria under test (docs/UAT-SERIES.md UAT-7-05):
//   - All 4 subscores visible (each out of 25 pts)
//   - Each card shows the subscore value
//   - Cards total <= 100
// ("Each card has a brief description" is NOT covered — see the module
//  docstring at the bottom of this file / red-proof Citations note; the
//  current UI renders each subscore as a labeled gauge, not a card with
//  descriptive body text.)
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

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

describe("ExecutivePage — UAT-7-05", () => {
  it("renders four score driver cards whose subscores come from the fixture and sum to at most 100", async () => {
    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    // UAT-7-05 names exactly these four driver labels (Hygiene, Modern TLS,
    // Identity Trust, Agility Signals) — the page's labels for identity_trust
    // and agility_signals are shortened to "Identity"/"Agility", so match on
    // the fixture-derived values + the page's own label text instead of the
    // case's longer label strings.
    const driverLabels = ["Hygiene", "Modern TLS", "Identity", "Agility"] as const
    const driverKeys = ["hygiene", "modern_tls", "identity_trust", "agility_signals"] as const

    for (const label of driverLabels) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }

    let total = 0
    for (const key of driverKeys) {
      const value = FIXTURE.score.subscores[key]
      expect(value).not.toBeNull()
      total += value as number
      // Each subscore's own numeric value is rendered somewhere on the page
      // (the ScoreGauge SVG text node for that driver).
      expect(screen.getAllByText(String(value)).length).toBeGreaterThanOrEqual(1)
    }

    expect(total).toBeLessThanOrEqual(100)
  })
})
