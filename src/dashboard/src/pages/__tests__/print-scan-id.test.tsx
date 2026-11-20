import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup } from "@testing-library/react"

// 261120-export-pdf-ignores-selected-scan: the server-side PDF render opens /print?scan_id=...
// in a fresh browser with no dashboard state, so /print must load the scan named in its URL
// on its FIRST fetch (setting context after mount would render the latest scan first).

const useScanDataMock = vi.fn<(scanId?: string | null) => { data: null; loading: boolean; error: null }>(
  () => ({ data: null, loading: true, error: null }),
)
vi.mock("@/hooks/useScanData", () => ({
  useScanData: (scanId?: string | null) => useScanDataMock(scanId),
}))
vi.mock("@/hooks/useQRAMMPrintData", () => ({
  useQRAMMPrintData: () => ({ scoreResult: null, complianceRows: null, loading: false, error: null }),
}))

afterEach(() => {
  cleanup()
  useScanDataMock.mockClear()
  window.history.pushState({}, "", "/")
})

describe("PrintPage — scan named in the URL", () => {
  it("loads the scan_id from the /print URL", async () => {
    window.history.pushState({}, "", "/print?scan_id=2026-11-19%2022%3A59%3A41.123456")
    const { PrintPage } = await import("@/pages/print")
    render(<PrintPage />)
    expect(useScanDataMock.mock.calls[0][0]).toBe("2026-11-19 22:59:41.123456")
  })

  it("loads the latest scan when the URL names none", async () => {
    window.history.pushState({}, "", "/print")
    const { PrintPage } = await import("@/pages/print")
    render(<PrintPage />)
    expect(useScanDataMock.mock.calls[0][0] ?? null).toBeNull()
  })
})
