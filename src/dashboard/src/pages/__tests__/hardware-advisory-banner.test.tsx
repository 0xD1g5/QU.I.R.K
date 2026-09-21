import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

// UAT-7-40 — Hardware Tab — Page Loads with Advisory Banner (HWCOMPAT-07).
//
// Model: pages/__tests__/certificates-inventory-table.test.tsx (module-level FIXTURE, vi.mock of
// the data hooks, real render() of the page component). hardware.tsx reads THREE hooks —
// useScanData, useHardwareDrift, useVendorPqcTrends (RESEARCH § Q2) — so all three are mocked;
// leaving any one live would let the page attempt a real fetch.
//
// Scope note (206-09 Task 1): the plan anticipated that the advisory banner's text would be served
// by the drift hook's fixture. Reading hardware.tsx in full shows it is NOT — the banner is static
// product copy rendered unconditionally (`role="note"`), and UAT-7-40's Pass Criteria quotes that
// copy verbatim. The honest assertion is therefore against the verbatim UAT string (declared once,
// in ADVISORY_BANNER below), not against a fixture field that does not exist. The drift and
// vendor-trend fixtures below still carry realistic data so the page's LifecycleEventList /
// VendorTrendList subtrees render their real populated path rather than an empty-state shortcut.
//
// Two of UAT-7-40's four Pass Criteria bullets are NOT covered here and are named explicitly in
// .planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-hardware.md:
//   - the sidebar "Hardware" nav-entry ordering bullet (not reachable from a bare HardwarePage
//     render — sidebar.tsx is a sibling component, not a child of this page)
//   - the Executive score-gauge lock bullet (a different page entirely)

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))
vi.mock("@/hooks/useHardwareDrift", () => ({
  useHardwareDrift: () => driftReturn,
}))
vi.mock("@/hooks/useVendorPqcTrends", () => ({
  useVendorPqcTrends: () => vendorTrendsReturn,
}))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null }
let driftReturn: { data: unknown; loading: boolean; error: string | null }
let vendorTrendsReturn: { data: unknown; loading: boolean; error: string | null }

// UAT-7-40 Pass Criteria, quoted verbatim from docs/UAT-SERIES.md.
const PAGE_TITLE = "Hardware Compatibility"
const PAGE_SUBHEADER = "PQC readiness of identified network devices"
const ADVISORY_BANNER =
  "Hardware findings are advisory-only and do not affect the readiness score."

const SCAN_FIXTURE = {
  hardware_findings: [
    {
      host: "10.10.0.22",
      port: 20222,
      severity: "HIGH",
      title: "HPE iLO5 management interface",
      vendor: "HPE",
      model: "iLO5",
      pqc_status: "unsupported",
      remediation_tier: "Tier 1",
      confidence: "high",
      fingerprint_method: "http_mgmt",
      eol_date: null,
    },
  ],
}

const DRIFT_FIXTURE = {
  has_prior_scan: true,
  latest_scan_at: "2026-09-01T12:00:00Z",
  latest_events: [
    {
      host: "10.10.0.22",
      port: 20222,
      vendor: "HPE",
      model: "iLO5",
      event_type: "tier_crossing",
      old_value: "Tier 2",
      new_value: "Tier 1",
      direction: "worsened",
      detected_at: "2026-09-01T12:00:00Z",
      is_partial_scan: false,
    },
  ],
  historical_events: [],
  historical_truncated: false,
}

const VENDOR_TRENDS_FIXTURE = {
  events: [
    {
      vendor: "HPE",
      event_type: "pqc_status_change",
      old_value: "partial",
      new_value: "unsupported",
      detected_at: "2026-09-01T12:00:00Z",
      confirmed_at: null,
    },
  ],
  truncated: false,
}

afterEach(() => {
  cleanup()
})

describe("HardwarePage — advisory banner (UAT-7-40)", () => {
  it("renders the hardware advisory banner text from the fixture drift data", async () => {
    scanDataReturn = { data: SCAN_FIXTURE, loading: false, error: null }
    driftReturn = { data: DRIFT_FIXTURE, loading: false, error: null }
    vendorTrendsReturn = { data: VENDOR_TRENDS_FIXTURE, loading: false, error: null }

    const { HardwarePage } = await import("@/pages/hardware")
    render(<HardwarePage />)

    // Pass Criteria bullet 1: page title + sub-header.
    expect(screen.getByRole("heading", { name: PAGE_TITLE })).toBeInTheDocument()
    expect(screen.getByText(PAGE_SUBHEADER)).toBeInTheDocument()

    // Pass Criteria bullet 2: the advisory banner renders, as a note landmark, with the verbatim
    // copy the case quotes. Asserted on the note element specifically (not a loose document-wide
    // text match) so a banner deleted from the page cannot be satisfied by the same words
    // appearing anywhere else in the subtree.
    const notes = screen.getAllByRole("note")
    const advisory = notes.find((n) => n.textContent?.trim() === ADVISORY_BANNER)
    expect(advisory).toBeDefined()
    expect(advisory).toHaveTextContent(ADVISORY_BANNER)

    // Negative half: the advisory note is the page's unconditional banner, and the fixture has no
    // bridge-confirmed device, so exactly one note renders. A page that rendered the banner twice,
    // or that leaked the bridge caveat banner on non-bridge data, would fail here.
    expect(notes).toHaveLength(1)
  })
})
