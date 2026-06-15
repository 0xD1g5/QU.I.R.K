import { describe, it, expect, beforeAll, afterAll, afterEach, beforeEach, vi } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { setupServer } from "msw/node"
import { http, HttpResponse } from "msw"
import type { ReactNode } from "react"
import { AuthProvider } from "../AuthProvider"
import { useAuth } from "../auth-context"

// AuthProvider calls setUnauthorizedHandler on mount — stub to a no-op.
vi.mock("@/lib/api", () => ({
  setUnauthorizedHandler: vi.fn(),
  fetchApi: (path: string, options?: RequestInit) => fetch(path, options),
}))

// AuthProvider's mount probe hits GET /api/scans — return 200 so tests
// land in "authenticated" state after mount.
const server = setupServer(
  http.get("/api/scans", () => HttpResponse.json([], { status: 200 })),
)

beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
})
afterAll(() => server.close())

const wrapper = ({ children }: { children: ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
)

describe("AuthProvider — sessionStorage migration (AUDIT-14 / D-01)", () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
  })

  it("setToken writes to sessionStorage, NOT localStorage", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper })

    // Wait for mount probe to settle (status transitions away from "loading")
    await waitFor(() => expect(result.current.status).not.toBe("loading"))

    act(() => {
      result.current.setToken("tok")
    })

    expect(sessionStorage.getItem("quirk_api_token")).toBe("tok")
    expect(localStorage.getItem("quirk_api_token")).toBeNull()
  })

  it("logout removes token from sessionStorage", async () => {
    // Seed sessionStorage to simulate the post-migration state
    sessionStorage.setItem("quirk_api_token", "tok")

    const { result } = renderHook(() => useAuth(), { wrapper })

    // Wait for mount probe to settle (status transitions away from "loading")
    await waitFor(() => expect(result.current.status).not.toBe("loading"))

    act(() => {
      result.current.logout()
    })

    expect(sessionStorage.getItem("quirk_api_token")).toBeNull()
  })
})
