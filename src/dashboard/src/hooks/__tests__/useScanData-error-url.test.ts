import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { setupServer } from "msw/node"
import { http, HttpResponse } from "msw"
import { useScanData } from "../useScanData"

// D-29 (IN-07): useScanData must include the actual fetch URL in
// non-OK error messages so operators can triage which endpoint failed.
// Per RESEARCH Pitfall 8: URL hoisted out of try-block for catch-block reuse.

let currentScanId: string | null = null
vi.mock("@/hooks/useSelectedScan", () => ({
  useSelectedScan: () => ({
    selectedScanId: currentScanId,
    setSelectedScanId: (id: string | null) => {
      currentScanId = id
    },
  }),
}))

vi.mock("@/lib/api", () => ({
  fetchApi: (path: string, options?: RequestInit) => fetch(path, options),
}))

const server = setupServer(
  http.get("/api/scan/latest", () =>
    HttpResponse.json({ error: "boom" }, { status: 500 }),
  ),
)

beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
  currentScanId = null
})
afterAll(() => server.close())

describe("useScanData — D-29 (IN-07) fetch URL in error message", () => {
  it("error message includes the actual fetch URL when response is not OK", async () => {
    currentScanId = "scan-xyz-123"
    const { result } = renderHook(() => useScanData())

    await waitFor(
      () => {
        expect(result.current.loading).toBe(false)
        expect(result.current.error).not.toBeNull()
      },
      { timeout: 1000 },
    )

    expect(result.current.error).toMatch(/Failed to fetch/i)
    // URL must be interpolated — should mention the path including the scan_id
    expect(result.current.error).toMatch(/scan-xyz-123/)
    expect(result.current.error).toMatch(/\/api\/scan\/latest/)
  })
})
