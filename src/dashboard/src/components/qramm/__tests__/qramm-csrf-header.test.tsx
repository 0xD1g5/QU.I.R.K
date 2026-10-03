import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { render, cleanup, waitFor, fireEvent, screen } from "@testing-library/react"
import { ScorecardTab } from "@/components/qramm/ScorecardTab"
import { ComplianceMapTab } from "@/components/qramm/ComplianceMapTab"
import { QRAMMContext } from "@/context/QRAMMContext"

// Phase 222.1 UAT finding: the QRAMM router requires X-Quirk-Request: 1 on
// every mutating call (require_csrf, wired in 58-04), but ScorecardTab and
// ComplianceMapTab POSTed /score with a raw fetch() that never sent it, so
// "Calculate Score" got a 403 from a live server since Phase 58. A stubbed
// fetch returns 200 whatever the headers are, so these tests assert the
// REQUEST: every QRAMM call must carry the header fetchApi() injects.

const fetchSpy = vi.fn()

beforeEach(() => {
  fetchSpy.mockReset()
  fetchSpy.mockResolvedValue({ ok: true, status: 200, json: async () => [] })
  vi.stubGlobal("fetch", fetchSpy)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function ctxValue() {
  return {
    sessionId: 1 as number | null,
    setSessionId: () => {},
    answers: new Map(),
    setAnswer: () => {},
    resetAnswers: () => {},
    profile: null,
    setProfile: () => {},
    scoreResult: null,
    setScoreResult: () => {},
    confirmAnswer: () => {},
    clearPendingDebounces: () => {},
  }
}

function headerOf(call: unknown[], name: string): string | undefined {
  const init = (call[1] ?? {}) as RequestInit
  const h = init.headers
  if (h instanceof Headers) return h.get(name) ?? undefined
  return (h as Record<string, string> | undefined)?.[name]
}

function scoreCalls() {
  return fetchSpy.mock.calls.filter((c) => String(c[0]).endsWith("/score"))
}

describe("QRAMM tabs send the CSRF header on every API call", () => {
  it("ScorecardTab Calculate Score POST carries X-Quirk-Request: 1", async () => {
    render(
      <QRAMMContext.Provider value={ctxValue()}>
        <ScorecardTab qnToDim={new Map<number, string>()} />
      </QRAMMContext.Provider>,
    )
    fireEvent.click(screen.getByRole("button", { name: "Calculate Score" }))
    await waitFor(() => expect(scoreCalls()).toHaveLength(1))
    const call = scoreCalls()[0]
    expect((call[1] as RequestInit).method).toBe("POST")
    expect(headerOf(call, "X-Quirk-Request")).toBe("1")
  })

  it("ComplianceMapTab Calculate Score POST carries X-Quirk-Request: 1", async () => {
    render(
      <QRAMMContext.Provider value={ctxValue()}>
        <ComplianceMapTab />
      </QRAMMContext.Provider>,
    )
    const button = await screen.findByRole("button", { name: "Calculate Score" })
    fireEvent.click(button)
    await waitFor(() => expect(scoreCalls()).toHaveLength(1))
    const call = scoreCalls()[0]
    expect((call[1] as RequestInit).method).toBe("POST")
    expect(headerOf(call, "X-Quirk-Request")).toBe("1")
  })

  it("ComplianceMapTab compliance-map GET goes through fetchApi (header present)", async () => {
    render(
      <QRAMMContext.Provider value={ctxValue()}>
        <ComplianceMapTab />
      </QRAMMContext.Provider>,
    )
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled())
    const mapCall = fetchSpy.mock.calls.find((c) => String(c[0]).endsWith("/compliance-map"))
    expect(mapCall).toBeDefined()
    expect(headerOf(mapCall!, "X-Quirk-Request")).toBe("1")
  })
})
