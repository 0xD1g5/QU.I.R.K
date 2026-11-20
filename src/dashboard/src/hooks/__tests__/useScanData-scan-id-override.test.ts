import { describe, it, expect, vi, afterEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useScanData } from "../useScanData"

// 261120-export-pdf-ignores-selected-scan: /print passes the URL's scan id straight into
// useScanData so the first and only fetch targets that scan, whatever the context holds.

let contextScanId: string | null = null
vi.mock("@/hooks/useSelectedScan", () => ({
  useSelectedScan: () => ({ selectedScanId: contextScanId, setSelectedScanId: () => {} }),
}))

const fetchApiMock = vi.fn<(url: string) => Promise<{ ok: boolean; json: () => Promise<unknown> }>>(
  async () => ({ ok: true, json: async () => ({}) }),
)
vi.mock("@/lib/api", () => ({ fetchApi: (url: string) => fetchApiMock(url) }))

afterEach(() => {
  fetchApiMock.mockClear()
  contextScanId = null
})

describe("useScanData — explicit scan id", () => {
  it("fetches only the explicit scan id, ignoring the context selection", async () => {
    contextScanId = "context-scan"
    const { result } = renderHook(() => useScanData("2026-11-19 22:59:41.123456"))
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(fetchApiMock.mock.calls.map((c) => c[0])).toEqual([
      "/api/scan/latest?scan_id=2026-11-19%2022%3A59%3A41.123456",
    ])
  })

  it("falls back to the context selection when no explicit id is given", async () => {
    contextScanId = "context-scan"
    const { result } = renderHook(() => useScanData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(fetchApiMock.mock.calls.map((c) => c[0])).toEqual(["/api/scan/latest?scan_id=context-scan"])
  })
})
