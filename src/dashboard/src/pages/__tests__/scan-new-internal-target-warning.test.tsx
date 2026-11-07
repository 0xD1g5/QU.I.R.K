/**
 * Phase 235.3 Plan 16 (D-11 / COVTRUTH-05) - New Scan pre-submit warning when
 * the server's internal-target policy will refuse a target or connector URL.
 * Non-blocking: the submit button is never disabled by the warning.
 */
import { describe, it, expect, afterEach, beforeEach, vi } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

const mockFetchApi = vi.fn()

vi.mock("@/lib/api", () => ({
  fetchApi: (...args: unknown[]) => mockFetchApi(...args),
}))

vi.mock("@/context/vertical-context", () => ({
  useVertical: () => ({ id: "general", label: "General", preset: null }),
}))

import { ScanNewPage } from "@/pages/scan-new"

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: async () => body }
}

const INTERNAL_BODY = {
  allow_internal_targets: false,
  config_error: null,
  internal: [{ field: "jwt_targets", preview: "http://localhost:20001", reason: "loopback" }],
  truncated: false,
}

function checkCalls() {
  return mockFetchApi.mock.calls.filter((c) =>
    String(c[0]).includes("/api/config/internal-target-check"),
  )
}

async function typeTargetsAndWait(value: string) {
  fireEvent.change(screen.getByLabelText("Targets"), { target: { value } })
  await act(async () => {
    await vi.advanceTimersByTimeAsync(600)
  })
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ScanNewPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  mockFetchApi.mockReset()
})

describe("ScanNewPage - internal target warning (D-11)", () => {
  it("new scan warns when server policy refuses an internal jwt url", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(INTERNAL_BODY))
    renderPage()
    await typeTargetsAndWait("localhost")

    const banner = screen.getByRole("status")
    expect(banner).toHaveTextContent("http://localhost:20001")
    expect(banner).toHaveTextContent("jwt_targets")
    expect(banner).toHaveTextContent("security.allow_internal_targets")
    expect(banner).toHaveTextContent("config.yaml")
    expect(banner).toHaveTextContent("TLS and SSH scanning is not affected")
  })

  it("new scan keeps run scan enabled while the internal target warning shows", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(INTERNAL_BODY))
    renderPage()
    await typeTargetsAndWait("localhost")

    expect(screen.getByRole("status")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /run scan/i })).toBeEnabled()
  })

  it("new scan shows no internal target warning when policy allows internal targets", async () => {
    mockFetchApi.mockResolvedValue(
      jsonResponse({ allow_internal_targets: true, config_error: null, internal: [], truncated: false }),
    )
    renderPage()
    await typeTargetsAndWait("localhost")

    expect(checkCalls().length).toBe(1)
    expect(screen.queryByRole("status")).not.toBeInTheDocument()
  })

  it("new scan says server policy could not be read on config error", async () => {
    mockFetchApi.mockResolvedValue(
      jsonResponse({ allow_internal_targets: false, config_error: "bad yaml", internal: [], truncated: false }),
    )
    renderPage()
    await typeTargetsAndWait("localhost")

    expect(screen.getByRole("status")).toHaveTextContent("Server policy could not be read")
  })

  it("new scan shows nothing when the internal target check fails", async () => {
    mockFetchApi.mockRejectedValue(new Error("network down"))
    renderPage()
    await typeTargetsAndWait("localhost")

    expect(checkCalls().length).toBe(1)
    expect(screen.queryByRole("status")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /run scan/i })).toBeEnabled()
  })

  it("new scan debounces the internal target check", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse(INTERNAL_BODY))
    renderPage()

    fireEvent.change(screen.getByLabelText("Targets"), { target: { value: "a.example.com" } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200)
    })
    fireEvent.change(screen.getByLabelText("Targets"), { target: { value: "ab.example.com" } })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(200)
    })
    expect(checkCalls().length).toBe(0)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(400)
    })
    expect(checkCalls().length).toBe(1)
    expect(String(checkCalls()[0][0])).toContain("targets=ab.example.com")
  })
})
