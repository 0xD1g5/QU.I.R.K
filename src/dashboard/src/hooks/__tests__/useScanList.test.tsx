import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest"
import { renderHook, render, screen, waitFor } from "@testing-library/react"
import { setupServer } from "msw/node"
import { http, HttpResponse } from "msw"
import { MemoryRouter } from "react-router-dom"
import { useScanList } from "../useScanList"

// Mock fetchApi to call native fetch so MSW intercepts.
vi.mock("@/lib/api", () => ({
  fetchApi: (path: string, options?: RequestInit) => fetch(path, options),
}))

const server = setupServer()
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe("useScanList — D-01 hook surface (WR-02 evidence)", () => {
  it("exposes { sessions, loading, error } keys", () => {
    server.use(
      http.get("/api/scans", () => HttpResponse.json([])),
    )
    const { result } = renderHook(() => useScanList())
    expect(result.current).toHaveProperty("sessions")
    expect(result.current).toHaveProperty("loading")
    expect(result.current).toHaveProperty("error")
  })

  it("sets error to non-empty string AND sessions to [] on 500 response", async () => {
    server.use(
      http.get("/api/scans", () =>
        new HttpResponse(JSON.stringify({}), { status: 500, statusText: "Internal Server Error" }),
      ),
    )
    const { result } = renderHook(() => useScanList())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBeTruthy()
    expect(typeof result.current.error).toBe("string")
    expect(result.current.error!.length).toBeGreaterThan(0)
    expect(result.current.sessions).toEqual([])
  })

  it("sets error to 'Authentication required' on 401", async () => {
    server.use(
      http.get("/api/scans", () => new HttpResponse(null, { status: 401 })),
    )
    const { result } = renderHook(() => useScanList())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe("Authentication required")
  })
})

describe("ScanHistoryPage — D-01 consumer renders error banner (WR-02 audit evidence)", () => {
  it("renders the destructive-text error card when useScanList yields error", async () => {
    // Stub the hook to force the error branch in the consumer.
    vi.doMock("@/hooks/useScanList", () => ({
      useScanList: () => ({ sessions: [], loading: false, error: "boom" }),
    }))
    // Re-import after mock applied
    const mod = await import("@/pages/scan-history")
    const ScanHistoryPage = mod.ScanHistoryPage
    render(
      <MemoryRouter>
        <ScanHistoryPage />
      </MemoryRouter>,
    )
    expect(screen.getByText(/Could not load scan history/i)).toBeInTheDocument()
    vi.doUnmock("@/hooks/useScanList")
  })
})
