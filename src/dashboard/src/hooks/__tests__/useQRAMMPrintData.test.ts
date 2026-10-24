// Phase 231 D-20 (QRAMM-19): the print/PDF QRAMM page's data hook GET'd
// /api/qramm/sessions/{id}/score, a POST-only route. On a live server the SPA
// fallback answered that GET with 200 text/html, the hook's .json() threw, and
// the PDF export timed out waiting for data-ready. These tests run the REAL
// hook through the REAL fetchApi; only the global fetch is stubbed, and the
// stub answers any /score GET exactly like the live SPA fallback did.
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { useQRAMMPrintData } from "@/hooks/useQRAMMPrintData"
import contract from "@/lib/__fixtures__/qramm-assessment-contract.json"

const SPA_HTML = "<!doctype html><html></html>"

const SCORE = {
  overall: 1.25,
  maturity: "Developing",
  dimensions: contract.score,
  profile_multiplier: 1.0,
}

const SUMMARY = {
  session_id: 7,
  org_name: "Acme",
  created_at: "2026-10-24T00:00:00",
  status: "scored",
  answers_count: 33,
}

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  })
}

function html(): Response {
  return new Response(SPA_HTML, { status: 200, headers: { "content-type": "text/html" } })
}

interface Routes {
  session?: () => Response
}

const fetchSpy = vi.fn()

function install(routes: Routes = {}) {
  fetchSpy.mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith("/score")) return html()
    if (url === "/api/qramm/sessions") return json([SUMMARY])
    if (url === "/api/qramm/sessions/7/compliance-map") return json(contract.rows)
    if (url === "/api/qramm/sessions/7") {
      return routes.session
        ? routes.session()
        : json({ ...SUMMARY, updated_at: null, model_version: "1.0", score: SCORE })
    }
    return html()
  })
}

function urls(): string[] {
  return fetchSpy.mock.calls.map((c) => String(c[0]))
}

function headerOf(call: unknown[], name: string): string | undefined {
  const init = (call[1] ?? {}) as RequestInit
  const h = init.headers
  if (h instanceof Headers) return h.get(name) ?? undefined
  return (h as Record<string, string> | undefined)?.[name]
}

beforeEach(() => {
  fetchSpy.mockReset()
  vi.stubGlobal("fetch", fetchSpy)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("useQRAMMPrintData (Phase 231 D-20)", () => {
  it("reads the persisted score from the session endpoint", async () => {
    install()
    const { result } = renderHook(() => useQRAMMPrintData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBeNull()
    expect(result.current.scoreResult).toEqual(SCORE)
    expect(result.current.complianceRows).toEqual(contract.rows)
    expect(urls()).toContain("/api/qramm/sessions/7")
    expect(urls()).toContain("/api/qramm/sessions/7/compliance-map")
    expect(urls().filter((u) => u.endsWith("/score"))).toEqual([])
  })

  it("surfaces a non-JSON response as an error, not a crash", async () => {
    install({ session: html })
    const { result } = renderHook(() => useQRAMMPrintData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe("API error: unexpected response from /api/qramm/sessions/7")
    expect(result.current.scoreResult).toBeNull()
    expect(result.current.complianceRows).toBeNull()
  })

  it("treats a scored summary whose session score is null as no assessment", async () => {
    install({
      session: () => json({ ...SUMMARY, updated_at: null, model_version: "1.0", score: null }),
    })
    const { result } = renderHook(() => useQRAMMPrintData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBeNull()
    expect(result.current.scoreResult).toBeNull()
    expect(result.current.complianceRows).toBeNull()
  })

  it("sends the CSRF header on every request", async () => {
    install()
    const { result } = renderHook(() => useQRAMMPrintData())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(fetchSpy.mock.calls.length).toBeGreaterThanOrEqual(3)
    for (const call of fetchSpy.mock.calls) {
      expect(headerOf(call, "X-Quirk-Request")).toBe("1")
    }
  })
})
