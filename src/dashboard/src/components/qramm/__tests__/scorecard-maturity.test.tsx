import { describe, it, expect, afterEach } from "vitest"
import { render, cleanup, screen } from "@testing-library/react"
import { ScorecardTab } from "@/components/qramm/ScorecardTab"
import { QRAMMContext } from "@/context/QRAMMContext"
import type { ScoreResult } from "@/context/QRAMMContext"
import { MATURITY_BAR_CLASS, DIMENSION_COUNT } from "@/lib/qramm-constants"

// D-10 (WR-11, WR-12):
//  - Bar width = (count / DIMENSION_COUNT) * 100 (NOT hardcoded /4)
//  - Bar fill className = MATURITY_BAR_CLASS[level] (solid bg-*, no text-/border-)
//  - Badge at the Dimension Summary table preserves MATURITY_BADGE_CLASS tokens
//  - Indeterminate (all-null dimension scores) renders em-dash row, no bar div

afterEach(() => cleanup())

function buildCtx(scoreResult: ScoreResult | null) {
  return {
    sessionId: 1 as number | null,
    setSessionId: () => {},
    answers: new Map(),
    setAnswer: () => {},
    resetAnswers: () => {},
    profile: null,
    setProfile: () => {},
    scoreResult,
    setScoreResult: () => {},
    confirmAnswer: () => {},
    clearPendingDebounces: () => {},
  }
}

function renderWith(scoreResult: ScoreResult | null) {
  const qnToDim = new Map<number, string>()
  return render(
    <QRAMMContext.Provider value={buildCtx(scoreResult)}>
      <ScorecardTab qnToDim={qnToDim} />
    </QRAMMContext.Provider>,
  )
}

describe("ScorecardTab — D-10 (WR-11, WR-12) maturity bar math + class", () => {
  it("DIMENSION_COUNT constant equals 4 (CVI/SGRM/DPE/ITR)", () => {
    expect(DIMENSION_COUNT).toBe(4)
  })

  it("renders bar width as (count / DIMENSION_COUNT) — 2 of 4 dimensions at level 3 → 50%", () => {
    // 2 dimensions at level 3, 2 at level 2 → bucket 3 should show width 50%
    const scoreResult: ScoreResult = {
      overall: 60,
      maturity: "Intermediate",
      dimensions: {
        CVI: { score: 3, weighted: 0.75 },
        SGRM: { score: 3, weighted: 0.75 },
        DPE: { score: 2, weighted: 0.5 },
        ITR: { score: 2, weighted: 0.5 },
      },
      profile_multiplier: 1.0,
    }
    renderWith(scoreResult)
    const bar3 = document.querySelector('[data-testid="maturity-bar-3"]') as HTMLElement | null
    expect(bar3).not.toBeNull()
    expect(bar3!.style.width).toBe("50%")
  })

  it.each([
    [1, "bg-quantum-vulnerable"],
    [2, "bg-quantum-at-risk"],
    [3, "bg-severity-low"],
    [4, "bg-quantum-safe"],
  ])("applies %s bar fill class at level %i", (level, expectedClass) => {
    // Construct dimensions so that the bucket-for-this-level has count>=1.
    // Use one dimension at the target level, others at distinct other levels.
    const others = [1, 2, 3, 4].filter((l) => l !== level)
    const scoreResult: ScoreResult = {
      overall: 50,
      maturity: "Intermediate",
      dimensions: {
        CVI: { score: level as number, weighted: 0.5 },
        SGRM: { score: others[0], weighted: 0.5 },
        DPE: { score: others[1], weighted: 0.5 },
        ITR: { score: others[2], weighted: 0.5 },
      },
      profile_multiplier: 1.0,
    }
    renderWith(scoreResult)
    const bar = document.querySelector(`[data-testid="maturity-bar-${level}"]`) as HTMLElement | null
    expect(bar).not.toBeNull()
    expect(bar!.className).toContain(expectedClass)
    expect(MATURITY_BAR_CLASS[level]).toBe(expectedClass)
  })

  it("does not apply text-* or border-* tokens to bar fill", () => {
    const scoreResult: ScoreResult = {
      overall: 60,
      maturity: "Intermediate",
      dimensions: {
        CVI: { score: 3, weighted: 0.75 },
        SGRM: { score: 3, weighted: 0.75 },
        DPE: { score: 2, weighted: 0.5 },
        ITR: { score: 2, weighted: 0.5 },
      },
      profile_multiplier: 1.0,
    }
    renderWith(scoreResult)
    const bar3 = document.querySelector('[data-testid="maturity-bar-3"]') as HTMLElement | null
    expect(bar3).not.toBeNull()
    expect(bar3!.className).toMatch(/bg-/)
    expect(bar3!.className).not.toMatch(/\btext-/)
    expect(bar3!.className).not.toMatch(/\bborder-/)
  })

  it("renders em-dash row for Indeterminate (all-null dimension scores)", () => {
    const scoreResult: ScoreResult = {
      overall: 0,
      maturity: "Indeterminate",
      dimensions: {
        CVI: { score: null as unknown as number, weighted: 0 },
        SGRM: { score: null as unknown as number, weighted: 0 },
        DPE: { score: null as unknown as number, weighted: 0 },
        ITR: { score: null as unknown as number, weighted: 0 },
      },
      profile_multiplier: 1.0,
    }
    renderWith(scoreResult)
    // No bar divs should be rendered for any maturity level when Indeterminate.
    for (const level of [1, 2, 3, 4]) {
      const bar = document.querySelector(`[data-testid="maturity-bar-${level}"]`)
      expect(bar).toBeNull()
    }
    // Em-dash sentinel present somewhere in the Maturity Distribution card.
    expect(screen.getAllByText("—").length).toBeGreaterThan(0)
  })

  it("Badge in Dimension Summary table retains MATURITY_BADGE_CLASS tokens", () => {
    const scoreResult: ScoreResult = {
      overall: 75,
      maturity: "Advanced",
      dimensions: {
        CVI: { score: 4, weighted: 1.0 },
        SGRM: { score: 4, weighted: 1.0 },
        DPE: { score: 4, weighted: 1.0 },
        ITR: { score: 4, weighted: 1.0 },
      },
      profile_multiplier: 1.0,
    }
    renderWith(scoreResult)
    // The Badge at the Dimension Summary table (line 249) must still carry
    // text-* and border-* tokens (regression guard — Pitfall 5).
    const badges = document.querySelectorAll('[class*="text-quantum-"]')
    expect(badges.length).toBeGreaterThan(0)
    const hasBorder = Array.from(badges).some((el) =>
      /border-quantum-/.test((el as HTMLElement).className),
    )
    expect(hasBorder).toBe(true)
  })
})
