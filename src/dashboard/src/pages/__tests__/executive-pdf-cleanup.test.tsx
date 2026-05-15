import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react"

// D-06 (WR-05): executive.tsx PDF download must store the revoke setTimeout
// id in a ref and the blob URL in a ref so a useEffect cleanup releases both
// on unmount. If the user navigates away mid-download the timer must not fire
// after unmount and the blob URL must be revoked.

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => ({
    data: {
      meta: { scan_id: "1", scanned_at: "2026-05-15T00:00:00Z", total_endpoints: 0, total_findings: 0 },
      score: {
        score: 50, rating: "Moderate",
        subscores: { hygiene: 0, modern_tls: 0, identity_trust: 0, agility_signals: 0, data_at_rest: 0, data_in_motion: 0 },
        drivers: [],
      },
      confidence: { confidence_score: 0, confidence_rating: "LOW", factor_breakdown: {} },
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

const revokeSpy = vi.fn()
const createSpy = vi.fn(() => "blob:fake-url")

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  fetchApiMock.mockReset()
  revokeSpy.mockReset()
  createSpy.mockClear()
  vi.stubGlobal("URL", {
    createObjectURL: createSpy,
    revokeObjectURL: revokeSpy,
  })
  vi.stubGlobal("ResizeObserver", ResizeObserverStub)
  vi.useFakeTimers({ shouldAdvanceTime: true })
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe("ExecutivePage — D-06 (WR-05) PDF cleanup", () => {
  it("revokes the blob URL on unmount before the scheduled timer fires", async () => {
    fetchApiMock.mockResolvedValue({
      ok: true,
      blob: async () => new Blob(["%PDF-1.4"], { type: "application/pdf" }),
    })
    const { ExecutivePage } = await import("@/pages/executive")
    const { unmount } = render(<ExecutivePage />)

    fireEvent.click(screen.getByRole("button", { name: /export pdf/i }))

    await waitFor(() => expect(createSpy).toHaveBeenCalled())

    // Unmount BEFORE the 100ms revoke timer fires.
    unmount()

    expect(revokeSpy).toHaveBeenCalledWith("blob:fake-url")
    const callsAfterUnmount = revokeSpy.mock.calls.length

    // Advance past the original 100ms timer; cleanup must have cleared it
    // so no additional revoke call should occur.
    vi.advanceTimersByTime(500)
    expect(revokeSpy.mock.calls.length).toBe(callsAfterUnmount)
  })

  it("revokes once via scheduled timer when component remains mounted, idempotent on later unmount", async () => {
    fetchApiMock.mockResolvedValue({
      ok: true,
      blob: async () => new Blob(["%PDF-1.4"], { type: "application/pdf" }),
    })
    const { ExecutivePage } = await import("@/pages/executive")
    const { unmount } = render(<ExecutivePage />)

    fireEvent.click(screen.getByRole("button", { name: /export pdf/i }))
    await waitFor(() => expect(createSpy).toHaveBeenCalled())

    vi.advanceTimersByTime(150)
    expect(revokeSpy).toHaveBeenCalledTimes(1)
    expect(revokeSpy).toHaveBeenCalledWith("blob:fake-url")

    // Unmount afterwards — blob URL ref already cleared, so no second call.
    unmount()
    expect(revokeSpy).toHaveBeenCalledTimes(1)
  })
})
