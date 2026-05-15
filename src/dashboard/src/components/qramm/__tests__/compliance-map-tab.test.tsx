import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { render, cleanup, waitFor } from "@testing-library/react"
import { ComplianceMapTab } from "@/components/qramm/ComplianceMapTab"
import { QRAMMContext } from "@/context/QRAMMContext"
import type { ScoreResult } from "@/context/QRAMMContext"

// D-07 (WR-13): ComplianceMapTab useEffect must depend only on
// [ctx.sessionId]. Mutating ctx.scoreResult while sessionId is stable must
// NOT trigger a re-fetch. RESEARCH C-4: ctx.sessionId is the stable field
// (ctx.scoreResult.session_id does not exist on the ScoreResult type).

const fetchSpy = vi.fn()

beforeEach(() => {
  fetchSpy.mockReset()
  fetchSpy.mockResolvedValue({
    ok: true,
    json: async () => [],
  })
  vi.stubGlobal("fetch", fetchSpy)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

function ctxValue(overrides: { sessionId: number | null; scoreResult?: ScoreResult | null }) {
  return {
    sessionId: overrides.sessionId,
    setSessionId: () => {},
    answers: new Map(),
    setAnswer: () => {},
    resetAnswers: () => {},
    profile: null,
    setProfile: () => {},
    scoreResult: overrides.scoreResult ?? null,
    setScoreResult: () => {},
    confirmAnswer: () => {},
    clearPendingDebounces: () => {},
  }
}

describe("ComplianceMapTab — D-07 (WR-13) narrowed deps", () => {
  it("fetches once on initial mount with sessionId", async () => {
    const value = ctxValue({ sessionId: 1 })
    render(
      <QRAMMContext.Provider value={value}>
        <ComplianceMapTab />
      </QRAMMContext.Provider>
    )
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1))
    expect(fetchSpy.mock.calls[0][0]).toMatch(/\/api\/qramm\/sessions\/1\/compliance-map/)
  })

  it("does not refetch when scoreResult mutates but sessionId is stable", async () => {
    const value1 = ctxValue({ sessionId: 1, scoreResult: null })
    const { rerender } = render(
      <QRAMMContext.Provider value={value1}>
        <ComplianceMapTab />
      </QRAMMContext.Provider>
    )
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1))

    const newScore: ScoreResult = {
      overall: 75,
      maturity: "Intermediate",
      dimensions: { CVI: { score: 3, weighted: 0.75 } },
      profile_multiplier: 1.0,
    }
    const value2 = ctxValue({ sessionId: 1, scoreResult: newScore })
    rerender(
      <QRAMMContext.Provider value={value2}>
        <ComplianceMapTab />
      </QRAMMContext.Provider>
    )

    // Allow a tick for any spurious effect to fire.
    await new Promise((r) => setTimeout(r, 10))
    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  it("refetches when sessionId changes", async () => {
    const value1 = ctxValue({ sessionId: 1 })
    const { rerender } = render(
      <QRAMMContext.Provider value={value1}>
        <ComplianceMapTab />
      </QRAMMContext.Provider>
    )
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1))

    const value2 = ctxValue({ sessionId: 2 })
    rerender(
      <QRAMMContext.Provider value={value2}>
        <ComplianceMapTab />
      </QRAMMContext.Provider>
    )
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2))
    expect(fetchSpy.mock.calls[1][0]).toMatch(/\/api\/qramm\/sessions\/2\/compliance-map/)
  })
})
