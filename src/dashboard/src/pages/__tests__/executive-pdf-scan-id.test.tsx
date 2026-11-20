import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react"

// 261120-export-pdf-ignores-selected-scan: the scan picked in the dashboard is in-tab
// React state, so Export PDF must send it to the server or the PDF prints the latest scan.

let selectedScanId: string | null = null
vi.mock("@/hooks/useSelectedScan", () => ({
  useSelectedScan: () => ({ selectedScanId, setSelectedScanId: () => {} }),
}))

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => ({
    data: {
      meta: { scan_id: "1", scanned_at: "2026-11-19T22:59:00Z", total_endpoints: 0, total_findings: 0 },
      score: {
        score: 19, rating: "POOR",
        subscores: { hygiene: 0, modern_tls: 0, identity_trust: 0, agility_signals: 0, data_at_rest: 0, data_in_motion: 0 },
        drivers: [],
      },
      confidence: { confidence_score: 89, confidence_rating: "HIGH", factor_breakdown: {} },
      findings: [],
      partial_failures: [],
    },
    loading: false,
    error: null,
  }),
}))

const fetchApiMock = vi.fn()
vi.mock("@/lib/api", () => ({
  fetchApi: (...args: unknown[]) => fetchApiMock(...args),
}))

vi.mock("@/components/RegressionAlertChip", () => ({
  RegressionAlertChip: () => null,
}))

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  fetchApiMock.mockReset()
  // The page also fetches the report manifest on mount; give it a well-formed (empty) one so
  // the render does not throw an unhandled error that fails the whole vitest run.
  fetchApiMock.mockImplementation(async (url: string) => ({
    ok: true,
    json: async () => (url === "/api/reports/latest/manifest" ? { formats: {} } : {}),
    blob: async () => new Blob(["%PDF-1.4"], { type: "application/pdf" }),
  }))
  vi.stubGlobal("URL", { createObjectURL: () => "blob:fake", revokeObjectURL: () => {} })
  vi.stubGlobal("ResizeObserver", ResizeObserverStub)
})

afterEach(() => {
  cleanup()
  selectedScanId = null
  vi.unstubAllGlobals()
})

async function exportBody(): Promise<Record<string, unknown>> {
  const { ExecutivePage } = await import("@/pages/executive")
  render(<ExecutivePage />)
  fireEvent.click(screen.getByRole("button", { name: /export pdf/i }))
  let call: unknown[] | undefined
  await waitFor(() => {
    call = fetchApiMock.mock.calls.find((c) => c[0] === "/api/export/pdf")
    expect(call).toBeDefined()
  })
  const options = call![1] as RequestInit
  expect(options.method).toBe("POST")
  return JSON.parse(String(options.body ?? "{}"))
}

describe("ExecutivePage — Export PDF carries the selected scan", () => {
  it("sends the selected scan id with the export request", async () => {
    selectedScanId = "2026-11-19 22:59:41.123456"
    expect(await exportBody()).toEqual({ scan_id: "2026-11-19 22:59:41.123456" })
  })

  it("sends no scan id when the latest scan is selected", async () => {
    selectedScanId = null
    expect(await exportBody()).toEqual({})
  })
})
