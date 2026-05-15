import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

// Mutable hook stubs — tests assign values before render.
let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: true,
  error: null,
}
let qrammReturn: {
  scoreResult: unknown
  complianceRows: unknown
  loading: boolean
  error: string | null
} = { scoreResult: null, complianceRows: null, loading: true, error: null }

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))
vi.mock("@/hooks/useQRAMMPrintData", () => ({
  useQRAMMPrintData: () => qrammReturn,
}))

function makeScanFixture() {
  return {
    meta: { scan_id: "1", scanned_at: "2026-05-15T00:00:00Z", total_endpoints: 0, total_findings: 0 },
    score: {
      score: 50, rating: "Moderate",
      subscores: { hygiene: 0, modern_tls: 0, identity_trust: 0, agility_signals: 0, data_at_rest: 0, data_in_motion: 0 },
      drivers: [],
    },
    confidence: { confidence_score: 0, confidence_rating: "Low", factor_breakdown: {} },
    findings: [],
    certificates: [],
    cbom_components: [],
    roadmap: { nodes: [], edges: [] },
    identity_findings: [],
    motion_findings: [],
    dar_findings: [],
  }
}

beforeEach(() => {
  document.body.removeAttribute("data-ready")
})
afterEach(() => {
  cleanup()
  document.body.removeAttribute("data-ready")
})

describe("PrintPage — D-03 (WR-07) data-ready sentinel guards QRAMM error", () => {
  it("does not set data-ready when qrammError is present and renders QRAMM unavailable alert", async () => {
    scanDataReturn = { data: makeScanFixture(), loading: false, error: null }
    qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: "fetch failed" }
    const { PrintPage } = await import("@/pages/print")
    render(<PrintPage />)
    // Sentinel must NOT be set when QRAMM errored.
    expect(document.body.getAttribute("data-ready")).toBeNull()
    // Visible alert must be present so operator/PDF reviewer sees the omission.
    expect(screen.getByText(/QRAMM data unavailable/i)).toBeInTheDocument()
  })

  it("sets data-ready when QRAMM loaded successfully (happy path)", async () => {
    scanDataReturn = { data: makeScanFixture(), loading: false, error: null }
    qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: null }
    const { PrintPage } = await import("@/pages/print")
    render(<PrintPage />)
    // Wait a tick for the effect to flush.
    await new Promise(r => setTimeout(r, 0))
    expect(document.body.getAttribute("data-ready")).toBe("true")
  })

  it("BR-05 regression: cleanup effect removes data-ready on unmount", async () => {
    scanDataReturn = { data: makeScanFixture(), loading: false, error: null }
    qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: null }
    const { PrintPage } = await import("@/pages/print")
    const { unmount } = render(<PrintPage />)
    await new Promise(r => setTimeout(r, 0))
    expect(document.body.getAttribute("data-ready")).toBe("true")
    unmount()
    expect(document.body.getAttribute("data-ready")).toBeNull()
  })
})
