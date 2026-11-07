/**
 * Phase 235.3 review fixes for the New Scan internal-target warning
 * (C-WR-02 / C-WR-03 / C-WR-05). Rendered directly so each case controls the
 * connectors prop and the preflight answer.
 */
import { describe, it, expect, afterEach, beforeEach, vi } from "vitest"
import { render, screen, act } from "@testing-library/react"
import { InternalTargetWarning } from "@/components/InternalTargetWarning"

const mockFetchApi = vi.fn()

vi.mock("@/lib/api", () => ({
  fetchApi: (...args: unknown[]) => mockFetchApi(...args),
}))

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: async () => body }
}

function checkCalls() {
  return mockFetchApi.mock.calls.filter((c) =>
    String(c[0]).includes("/api/config/internal-target-check"),
  )
}

/** Every key the component sent to the preflight, whatever the transport. */
function sentText(): string {
  const call = checkCalls()[0]
  return decodeURIComponent(String(call[0])) + " " + String(call[1]?.body ?? "")
}

async function renderAndWait(connectors: Record<string, unknown>) {
  render(<InternalTargetWarning connectors={connectors as never} />)
  await act(async () => {
    await vi.advanceTimersByTimeAsync(600)
  })
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  mockFetchApi.mockReset()
})

describe("InternalTargetWarning", () => {
  it("internal target warning names only the connector that produced an entry", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse({
      allow_internal_targets: false, config_error: null, truncated: false,
      internal: [{ field: "jwt_targets", preview: "http://localhost:20001/", reason: "loopback" }],
    }))
    await renderAndWait({ jwt_targets: ["http://localhost:20001"] })

    const banner = screen.getByRole("status")
    expect(banner).toHaveTextContent("JWT")
    expect(banner).not.toHaveTextContent("OpenAPI")
    expect(banner).not.toHaveTextContent("SAML")
  })

  it("internal target warning posts the connector values with fetchApi", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse({
      allow_internal_targets: false, config_error: null, truncated: false, internal: [],
    }))
    await renderAndWait({ jwt_targets: ["http://localhost:20001"] })

    expect(checkCalls().length).toBe(1)
    const [path, init] = checkCalls()[0]
    expect(path).toBe("/api/config/internal-target-check")
    expect(init?.method).toBe("POST")
    expect(JSON.parse(String(init?.body))).toEqual({ connectors: { jwt_targets: ["http://localhost:20001"] } })
  })

  it("internal target warning never sends openapi_spec_path", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse({
      allow_internal_targets: false, config_error: null, truncated: false, internal: [],
    }))
    await renderAndWait({ jwt_targets: ["http://localhost:20001"], openapi_spec_path: "http://localhost/spec.json" })

    expect(checkCalls().length).toBe(1)
    expect(sentText()).not.toContain("openapi_spec_path")
  })
})
