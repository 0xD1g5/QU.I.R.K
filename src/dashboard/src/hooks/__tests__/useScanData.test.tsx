import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { setupServer } from "msw/node"
import { http, HttpResponse, delay } from "msw"
import { useScanData } from "../useScanData"

// Mock useSelectedScan so we can drive selectedScanId from the test
let currentScanId: string | null = null
vi.mock("@/hooks/useSelectedScan", () => ({
  useSelectedScan: () => ({ selectedScanId: currentScanId, setSelectedScanId: (id: string | null) => { currentScanId = id } }),
}))

// Mock fetchApi to call native fetch so MSW intercepts.
vi.mock("@/lib/api", () => ({
  fetchApi: (path: string, options?: RequestInit) => fetch(path, options),
}))

// Minimal fixture factory matching ScanLatestResponse shape
function makeScanResponse(scanId: string) {
  return {
    meta: {
      scan_id: scanId,
      total_endpoints: 0,
      total_findings: 0,
    },
    score: {
      score: 0,
      rating: "Unknown",
      subscores: {
        hygiene: 0,
        modern_tls: 0,
        identity_trust: 0,
        agility_signals: 0,
        data_at_rest: 0,
        data_in_motion: 0,
      },
      drivers: [],
    },
    confidence: {
      confidence_score: 0,
      confidence_rating: "Low",
      factor_breakdown: {},
    },
    findings: [],
    certificates: [],
    cbom_components: [],
    roadmap: { nodes: [], edges: [] },
    identity_findings: [],
    motion_findings: [],
    dar_findings: [],
  }
}

const server = setupServer(
  http.get("/api/scan/latest", async ({ request }) => {
    const url = new URL(request.url)
    const id = url.searchParams.get("scan_id")
    if (id === "1") {
      await delay(50)  // slow first response
      return HttpResponse.json(makeScanResponse("1"))
    }
    if (id === "2") {
      return HttpResponse.json(makeScanResponse("2"))
    }
    return HttpResponse.json({ error: "not found" }, { status: 404 })
  }),
)

beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
  currentScanId = null
})
afterAll(() => server.close())

describe("useScanData — HOOK-01 scan-switch stale data", () => {
  it("displays the most recently selected scan_id, not the slow earlier one", async () => {
    currentScanId = "1"
    const { result, rerender } = renderHook(() => useScanData())

    // Switch to scan_id=2 before the slow first response can resolve
    currentScanId = "2"
    rerender()

    // After both fetches settle, the displayed data must match scan_id=2
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
      expect(result.current.data?.meta.scan_id).toBe("2")
    }, { timeout: 1000 })

    // Even after waiting longer than the 50ms delay, the stale scan_id=1 must not overwrite
    await new Promise((r) => setTimeout(r, 100))
    expect(result.current.data?.meta.scan_id).toBe("2")
  })
})
