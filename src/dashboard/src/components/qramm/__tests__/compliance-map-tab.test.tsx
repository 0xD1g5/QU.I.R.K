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

// Phase 231 QRAMM-17 (D-10, D-21c): after a successful Calculate Score the tab
// refetches the compliance map through an explicit reloadKey trigger (never via
// scoreResult in the deps, which is the WR-13 loop above), and a polite status
// region announces the refreshed table. Rows come from the real D-09 contract.
import { fireEvent, screen } from "@testing-library/react"
import contract from "@/lib/__fixtures__/qramm-assessment-contract.json"
import type { QRAMMComplianceMapRow, QRAMMScoreResponse } from "@/types/api"

const CONTRACT_ROWS = contract.rows as QRAMMComplianceMapRow[]
const UNSCORED_CONTRACT_ROWS: QRAMMComplianceMapRow[] = CONTRACT_ROWS.map((r) => ({
  ...r,
  relevance_score: null,
}))

const SCORE_RESPONSE: QRAMMScoreResponse = {
  overall: 50,
  maturity: "Intermediate",
  dimensions: { CVI: { score: 0, weighted: 0 }, SGRM: { score: 2, weighted: 0.5 } },
  profile_multiplier: 1.0,
}

type ScoreMode = "ok" | "fail" | "throw"

// Route-aware stub: /score answers per mode; /compliance-map serves the given
// responses in order, repeating the last one.
function routeStub(scoreMode: ScoreMode, mapResponses: QRAMMComplianceMapRow[][]) {
  let mapIndex = 0
  fetchSpy.mockImplementation(async (url: string) => {
    if (String(url).endsWith("/score")) {
      if (scoreMode === "throw") throw new Error("network down")
      if (scoreMode === "fail") return { ok: false, status: 500, json: async () => ({}) }
      return { ok: true, status: 200, json: async () => SCORE_RESPONSE }
    }
    const body = mapResponses[Math.min(mapIndex, mapResponses.length - 1)]
    mapIndex += 1
    return { ok: true, status: 200, json: async () => body }
  })
}

function mapCalls() {
  return fetchSpy.mock.calls.filter((c) => String(c[0]).endsWith("/compliance-map"))
}

function renderTab(sessionId: number | null = 1) {
  return render(
    <QRAMMContext.Provider value={ctxValue({ sessionId })}>
      <ComplianceMapTab />
    </QRAMMContext.Provider>
  )
}

function clickCalculate() {
  fireEvent.click(screen.getByRole("button", { name: "Calculate Score" }))
}

const CALC_ERROR = "Could not calculate score — check your connection and try again."

describe("ComplianceMapTab — Phase 231 QRAMM-17 refetch after Calculate Score", () => {
  it("refetches the compliance map after a successful Calculate Score", async () => {
    routeStub("ok", [[], CONTRACT_ROWS])
    renderTab()
    await waitFor(() => expect(mapCalls()).toHaveLength(1))
    expect(screen.queryByText("Cryptographic Discovery & Inventory Management")).toBeNull()

    clickCalculate()
    await waitFor(() => expect(mapCalls()).toHaveLength(2))
    expect(String(mapCalls()[1][0])).toMatch(/\/api\/qramm\/sessions\/1\/compliance-map$/)
    expect(
      await screen.findByText("Cryptographic Discovery & Inventory Management")
    ).toBeTruthy()
  })

  it("does not refetch the compliance map after a failed Calculate Score", async () => {
    routeStub("fail", [[]])
    renderTab()
    await waitFor(() => expect(mapCalls()).toHaveLength(1))
    clickCalculate()
    expect(await screen.findByText(CALC_ERROR)).toBeTruthy()
    await new Promise((r) => setTimeout(r, 10))
    expect(mapCalls()).toHaveLength(1)
  })

  it("does not refetch the compliance map when Calculate Score throws", async () => {
    routeStub("throw", [[]])
    renderTab()
    await waitFor(() => expect(mapCalls()).toHaveLength(1))
    clickCalculate()
    expect(await screen.findByText(CALC_ERROR)).toBeTruthy()
    await new Promise((r) => setTimeout(r, 10))
    expect(mapCalls()).toHaveLength(1)
  })

  it("announces Compliance map updated after the refetch resolves", async () => {
    routeStub("ok", [UNSCORED_CONTRACT_ROWS])
    renderTab()
    await waitFor(() => expect(mapCalls()).toHaveLength(1))
    await screen.findByText("Cryptographic Discovery & Inventory Management")
    const status = screen.getByRole("status")
    expect(status.textContent).toBe("")

    clickCalculate()
    await waitFor(() => expect(mapCalls()).toHaveLength(2))
    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toBe("Compliance map updated.")
    )

    clickCalculate()
    expect(screen.getByRole("status").textContent).toBe("")
    await waitFor(() => expect(mapCalls()).toHaveLength(3))
    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toBe("Compliance map updated.")
    )
  })

  it("keeps the status region empty after a failed Calculate Score", async () => {
    routeStub("fail", [UNSCORED_CONTRACT_ROWS])
    renderTab()
    await waitFor(() => expect(mapCalls()).toHaveLength(1))
    clickCalculate()
    expect(await screen.findByText(CALC_ERROR)).toBeTruthy()
    await new Promise((r) => setTimeout(r, 10))
    expect(screen.getByRole("status").textContent).toBe("")
  })

  it("keeps the status region mounted while the refetch is loading", async () => {
    let releaseSecond: (() => void) | null = null
    let mapIndex = 0
    fetchSpy.mockImplementation(async (url: string) => {
      if (String(url).endsWith("/score")) {
        return { ok: true, status: 200, json: async () => SCORE_RESPONSE }
      }
      mapIndex += 1
      if (mapIndex === 2) {
        await new Promise<void>((resolve) => { releaseSecond = resolve })
      }
      return { ok: true, status: 200, json: async () => UNSCORED_CONTRACT_ROWS }
    })
    renderTab()
    await waitFor(() => expect(mapCalls()).toHaveLength(1))
    await screen.findByText("Cryptographic Discovery & Inventory Management")
    clickCalculate()
    await waitFor(() => expect(mapCalls()).toHaveLength(2))
    expect(screen.getByLabelText("Loading compliance map")).toBeTruthy()
    expect(screen.getByRole("status").textContent).toBe("")
    releaseSecond!()
    await waitFor(() =>
      expect(screen.getByRole("status").textContent).toBe("Compliance map updated.")
    )
  })

  it("does not announce on a sessionId change", async () => {
    routeStub("ok", [UNSCORED_CONTRACT_ROWS])
    const { rerender } = renderTab(1)
    await waitFor(() => expect(mapCalls()).toHaveLength(1))
    rerender(
      <QRAMMContext.Provider value={ctxValue({ sessionId: 2 })}>
        <ComplianceMapTab />
      </QRAMMContext.Provider>
    )
    await waitFor(() => expect(mapCalls()).toHaveLength(2))
    await screen.findByText("Cryptographic Discovery & Inventory Management")
    await new Promise((r) => setTimeout(r, 10))
    expect(screen.getByRole("status").textContent).toBe("")
  })
})
