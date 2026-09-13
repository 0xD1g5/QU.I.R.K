import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { setupServer } from "msw/node"
import { http, HttpResponse, delay } from "msw"
import { useFindingStoryline } from "../useFindingStoryline"
import type { FindingStoryline } from "@/types/api"

// Mock fetchApi to call native fetch so MSW intercepts (idiom from useScanData.test.tsx).
vi.mock("@/lib/api", () => ({
  fetchApi: (path: string, options?: RequestInit) => fetch(path, options),
}))

function makeStoryline(overrides: Partial<FindingStoryline> = {}): FindingStoryline {
  return {
    finding_id: 7,
    narrative: "RSA key sizes below 2048 bits are vulnerable to Shor's algorithm.",
    quantum_impact: "High — private key recovery becomes feasible with a CRQC.",
    remediation_guidance: "Reissue with a 3072-bit RSA key or migrate to ECDSA.",
    theme_slug: "undersized-rsa-keys",
    theme_title: "Replace undersized RSA keys",
    theme_score_lift: 4,
    theme_finding_count: 8,
    theme_closed_count: 6,
    finding_position: 1,
    ...overrides,
  }
}

let requestedUrls: string[] = []

const server = setupServer(
  http.get("/api/findings/:id/storyline", async ({ request, params }) => {
    requestedUrls.push(request.url)
    const url = new URL(request.url)
    const title = url.searchParams.get("title")
    if (params.id === "500") {
      return HttpResponse.json({ detail: "boom" }, { status: 500 })
    }
    if (params.id === "999") {
      await delay(50)
      return HttpResponse.json(makeStoryline())
    }
    return HttpResponse.json(makeStoryline({ finding_id: Number(params.id) }), {
      status: title ? 200 : 200,
    })
  }),
)

beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
  requestedUrls = []
})
afterAll(() => server.close())

describe("useFindingStoryline", () => {
  it("fetches and returns data on a 200 response", async () => {
    const { result } = renderHook(() =>
      useFindingStoryline({ id: 7, title: "Certificate expired" }),
    )

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).not.toBeNull()
    expect(result.current.data?.finding_id).toBe(7)
    expect(result.current.error).toBeNull()
  })

  it("URL-encodes the title, round-tripping &, ?, #, and non-ASCII characters", async () => {
    const trickyTitle = "Weak & Broken? Cipher #1 — café"
    const { result } = renderHook(() =>
      useFindingStoryline({ id: 7, title: trickyTitle }),
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(requestedUrls).toHaveLength(1)
    const requested = new URL(requestedUrls[0])
    expect(requested.pathname).toBe("/api/findings/7/storyline")
    // Decoding what was actually sent must round-trip to the original title.
    expect(requested.searchParams.get("title")).toBe(trickyTitle)
    // And the raw query string must actually be percent-encoded, not raw.
    expect(requestedUrls[0]).toContain("Weak%20%26%20Broken%3F%20Cipher%20%231")
  })

  it("on a non-ok response, sets error and leaves data null — never a null-filled payload", async () => {
    const { result } = renderHook(() =>
      useFindingStoryline({ id: 500, title: "Server explodes" }),
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBeTruthy()
    expect(typeof result.current.error).toBe("string")
    expect(result.current.data).toBeNull()
  })

  it("issues no request when id is null (A6 guard)", async () => {
    const { result } = renderHook(() =>
      useFindingStoryline({ id: null, title: "No stable id" }),
    )

    // Give any accidental async fetch a chance to fire.
    await new Promise((r) => setTimeout(r, 20))

    expect(requestedUrls).toHaveLength(0)
    expect(result.current.loading).toBe(false)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it("issues no request when finding is null (no finding selected)", async () => {
    const { result } = renderHook(() => useFindingStoryline(null))

    await new Promise((r) => setTimeout(r, 20))

    expect(requestedUrls).toHaveLength(0)
    expect(result.current.loading).toBe(false)
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBeNull()
  })

  it("unmounting mid-flight performs no state update on the unmounted component", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {})

    const { unmount } = renderHook(() =>
      useFindingStoryline({ id: 999, title: "Slow finding" }),
    )

    unmount()

    // Wait past the mocked 50ms server delay — if the hook were to call a
    // setter after unmount, React would log an "update on unmounted
    // component" warning here.
    await new Promise((r) => setTimeout(r, 100))

    expect(consoleError).not.toHaveBeenCalled()
    consoleError.mockRestore()
  })

  it("changing the selected finding re-issues the fetch and clears prior data synchronously", async () => {
    const { result, rerender } = renderHook(
      ({ finding }: { finding: { id: number; title: string } }) => useFindingStoryline(finding),
      { initialProps: { finding: { id: 1, title: "First finding" } } },
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(result.current.data?.finding_id).toBe(1)

    rerender({ finding: { id: 2, title: "Second finding" } })

    // Data must be cleared synchronously before the new fetch resolves —
    // the drawer must never show the prior finding's narrative under the
    // new finding's title.
    expect(result.current.data).toBeNull()
    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(result.current.data?.finding_id).toBe(2)
    expect(requestedUrls).toHaveLength(2)
  })

  it("retry() re-issues the same request, sets loading true again, and clears error on success", async () => {
    let failNext = true
    server.use(
      http.get("/api/findings/:id/storyline", async () => {
        if (failNext) {
          failNext = false
          return HttpResponse.json({ detail: "transient" }, { status: 500 })
        }
        return HttpResponse.json(makeStoryline())
      }),
    )

    const { result } = renderHook(() =>
      useFindingStoryline({ id: 7, title: "Flaky finding" }),
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(result.current.error).toBeTruthy()
    expect(result.current.data).toBeNull()

    act(() => {
      result.current.retry()
    })

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBeNull()
    expect(result.current.data).not.toBeNull()
  })

  it("retry() does not blank an already-rendered panel if the second attempt also fails", async () => {
    server.use(
      http.get("/api/findings/:id/storyline", () =>
        HttpResponse.json({ detail: "still broken" }, { status: 500 }),
      ),
    )

    const { result } = renderHook(() =>
      useFindingStoryline({ id: 7, title: "Always fails" }),
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    expect(result.current.error).toBeTruthy()
    const firstError = result.current.error

    act(() => {
      result.current.retry()
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Still an error, still null data, and the same fixed copy — not blanked.
    expect(result.current.error).toBe(firstError)
    expect(result.current.data).toBeNull()
  })
})
