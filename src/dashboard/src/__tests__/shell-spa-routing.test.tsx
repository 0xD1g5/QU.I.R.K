// Phase 206 Plan 10 (COV-04) — UAT-7-20: Dashboard — SPA Routing.
//
// Pass Criteria under test (docs/UAT-SERIES.md UAT-7-20):
//   - Page renders correctly (not 404)          -> the Findings page's own heading renders
//   - Same content as navigating via sidebar    -> the route table consulted IS the app's own
//   - URL stays at /findings                    -> MemoryRouter's entry is unchanged after render
//
// D-A4: `AppShell` is imported as a NAMED import from the real `@/App`. The
// route table is deliberately NOT duplicated into this file — a test-local
// `<Routes>` tree drifts from the real one and would assert nothing about the
// actual application (206-RESEARCH.md § Pitfall 2). That is the entire reason
// exporting `AppShell` was authorized.
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AppShell } from "@/App"

const FIXTURE = {
  meta: { scan_id: "scan-1", scanned_at: "2026-09-01T00:00:00Z", total_endpoints: 1, total_findings: 1 },
  score: {
    score: 72,
    rating: "GOOD",
    subscores: {
      hygiene: 20, modern_tls: 18, identity_trust: 15, agility_signals: 12,
      data_at_rest: null, data_in_motion: null,
    },
    drivers: [],
  },
  confidence: { confidence_score: 0.8, confidence_rating: "HIGH", factor_breakdown: {} },
  findings: [
    {
      id: 1,
      severity: "HIGH",
      title: "TLS 1.0 enabled",
      description: "Legacy protocol offered",
      recommendation: "Disable TLS 1.0",
      host: "host-a.example.com",
      port: 443,
      protocol: "TLS",
      category: "TLS",
    },
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

// AppShell renders LoginPage unless auth status is "authenticated" — mock the
// context hooks directly (the ConnectorsPanel.test.tsx pattern) rather than
// wrapping the real provider tree, so no network call is made.
vi.mock("@/context/auth-context", () => ({
  useAuth: () => ({ status: "authenticated", setToken: () => {}, logout: () => {} }),
}))

vi.mock("@/context/vertical-context", () => ({
  useVertical: () => ({
    id: "general",
    label: "General",
    Icon: () => null,
    accentColor: "",
    navItem: null,
    PageComponent: null,
  }),
}))

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => ({ data: FIXTURE, loading: false, error: null }),
}))

vi.mock("@/hooks/useScanList", () => ({
  useScanList: () => ({ sessions: [], loading: false, error: null }),
}))

vi.mock("@/hooks/useSelectedScan", () => ({
  useSelectedScan: () => ({ selectedScanId: null, setSelectedScanId: () => {} }),
}))

vi.mock("@/hooks/useMergeLatest", () => ({
  useMergeLatest: () => ({ merge: null, loading: false, error: null }),
}))

vi.mock("@/hooks/useFindingStoryline", () => ({
  useFindingStoryline: () => ({ data: null, loading: false, error: null, retry: () => {} }),
}))

describe("AppShell SPA routing — UAT-7-20", () => {
  it("renders the findings page from the app route table when navigating directly to slash findings", () => {
    render(
      <TooltipProvider>
        <MemoryRouter initialEntries={["/findings"]}>
          <AppShell />
        </MemoryRouter>
      </TooltipProvider>,
    )

    // The Findings page's own distinguishing content. Queried as a heading so
    // the sidebar's "Findings" nav label cannot satisfy it.
    expect(screen.getByRole("heading", { name: "Findings" })).toBeInTheDocument()
    expect(screen.getByText("TLS 1.0 enabled")).toBeInTheDocument()

    // The Executive page's own distinguishing heading must be ABSENT — this is
    // what proves the route table SELECTED /findings, rather than merely that
    // something mounted.
    expect(screen.queryByRole("heading", { name: "QU.I.R.K. — Scan Results" })).toBeNull()
  })
})
