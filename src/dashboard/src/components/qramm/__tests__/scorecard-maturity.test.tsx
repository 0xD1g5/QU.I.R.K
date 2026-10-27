import { describe, it, expect, afterEach } from "vitest"
import { render, cleanup, screen } from "@testing-library/react"
import { ScorecardTab } from "@/components/qramm/ScorecardTab"
import { QRAMMContext } from "@/context/QRAMMContext"
import type { ScoreResult } from "@/context/QRAMMContext"
import {
  MATURITY_BAR_CLASS,
  MATURITY_BADGE_CLASS,
  MATURITY_LABEL,
  DIMENSION_COUNT,
  DIMENSIONS,
} from "@/lib/qramm-constants"
import type { Dimension } from "@/lib/qramm-constants"
import { buildAnswers, buildCatalog, buildCtx, withAnsweredCounts } from "./scorecard-fixtures"

// D-10 (WR-11, WR-12):
//  - Bar width = (count / DIMENSION_COUNT) * 100 (NOT hardcoded /4)
//  - Bar fill className = MATURITY_BAR_CLASS[level] (solid bg-*, no text-/border-)
//  - Badge at the Dimension Summary table preserves MATURITY_BADGE_CLASS tokens
//  - Indeterminate (all-null dimension scores) renders em-dash row, no bar div
// Covers QRAMM-11 (Dimension Scorecard maturity-band rendering).

afterEach(() => cleanup())

// Phase 231 D-07a: a dimension with no answered question reads "Not assessed",
// so every fixture renders a real catalog (30 questions per dimension) and, by
// default, one answered question in every dimension it scores.
function renderWith(
  scoreResult: ScoreResult | null,
  answeredPerDim: Partial<Record<Dimension, number>> = { CVI: 1, SGRM: 1, DPE: 1, ITR: 1 },
  perDim = 30,
) {
  const qnToDim = buildCatalog(perDim)
  const answers = buildAnswers(qnToDim, answeredPerDim)
  return render(
    <QRAMMContext.Provider value={buildCtx(withAnsweredCounts(scoreResult, qnToDim, answers), answers)}>
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

// Phase 231 QRAMM-18 (D-07, D-08, D-21a): an unanswered dimension is "Not
// assessed", not maturity level 1. The predicate is the live answered count.

function score(dims: Record<Dimension, number>): ScoreResult {
  return {
    overall: 40,
    maturity: "Basic",
    dimensions: Object.fromEntries(
      DIMENSIONS.map((d) => [d, { score: dims[d], weighted: dims[d] / 4 }]),
    ),
    profile_multiplier: 1.0,
  }
}

function summaryRow(dim: Dimension): HTMLTableRowElement {
  const rows = Array.from(document.querySelectorAll("tbody tr")) as HTMLTableRowElement[]
  const row = rows.find((r) => r.cells[0]?.textContent === dim)
  if (!row) throw new Error(`no Dimension Summary row for ${dim}`)
  return row
}

function levelCount(level: number): string | null {
  const bar = document.querySelector(`[data-testid="maturity-bar-${level}"]`)
  const levelRow = bar?.parentElement?.parentElement
  return levelRow?.querySelector(".font-data")?.textContent ?? null
}

describe("ScorecardTab — Phase 231 QRAMM-18 Not assessed dimensions", () => {
  it("renders Not assessed for a dimension with no answered question", () => {
    renderWith(score({ CVI: 2, SGRM: 3, DPE: 3, ITR: 0 }), { CVI: 1, SGRM: 1, DPE: 1, ITR: 0 })
    const row = summaryRow("ITR")
    const badge = row.cells[4].firstElementChild as HTMLElement
    expect(row.cells[4].textContent).toBe("Not assessed")
    // Colour tokens only: the base Badge class itself carries a bare `border`.
    const maturityTokens = Object.values(MATURITY_BADGE_CLASS)
      .join(" ")
      .split(" ")
      .filter((t) => /quantum-|severity-/.test(t))
    expect(maturityTokens.length).toBeGreaterThan(0)
    for (const token of maturityTokens) {
      expect(badge.className.split(" ")).not.toContain(token)
    }
    expect(badge.className).toContain("bg-secondary")
    expect(row.cells[1].textContent).toBe("—")
    expect(row.cells[2].textContent).toBe("—")
  })

  it("excludes a not-assessed dimension from the Maturity Distribution", () => {
    renderWith(score({ CVI: 1, SGRM: 0, DPE: 0, ITR: 0 }), { CVI: 1 })
    expect(levelCount(1)).toBe("1")
    const bar1 = document.querySelector('[data-testid="maturity-bar-1"]') as HTMLElement
    expect(bar1.style.width).toBe(`${(1 / DIMENSION_COUNT) * 100}%`)
    expect(screen.getByTestId("maturity-not-assessed").textContent).toBe("3 dimensions not assessed")
  })

  it("buckets a partially answered dimension by its score", () => {
    renderWith(score({ CVI: 0, SGRM: 0, DPE: 3.2, ITR: 0 }), { DPE: 1 })
    expect(levelCount(3)).toBe("1")
    expect(levelCount(1)).toBe("0")
    expect(summaryRow("DPE").cells[4].textContent).toBe(MATURITY_LABEL[3])
    expect(summaryRow("DPE").cells[1].textContent).toBe("3.20")
  })

  it("decides assessment from the live answered count, never from the stored score", () => {
    // SGRM answered but its stored score is the 0.0 placeholder (scored before
    // the answer); ITR unanswered but carries a stale non-zero score.
    renderWith(score({ CVI: 2, SGRM: 0, DPE: 2, ITR: 2 }), { CVI: 1, SGRM: 1, DPE: 1 })
    expect(summaryRow("SGRM").cells[4].textContent).toBe(MATURITY_LABEL[1])
    expect(summaryRow("SGRM").cells[1].textContent).toBe("0.00")
    expect(summaryRow("ITR").cells[4].textContent).toBe("Not assessed")
    expect(levelCount(1)).toBe("1")
    expect(levelCount(2)).toBe("2")
    expect(screen.getByTestId("maturity-not-assessed").textContent).toBe("1 dimension not assessed")
  })

  it("treats one answered question as assessed even when completion rounds to 0%", () => {
    renderWith(score({ CVI: 2, SGRM: 2, DPE: 2, ITR: 2 }), { CVI: 1, SGRM: 1, DPE: 1, ITR: 1 }, 300)
    expect(summaryRow("ITR").cells[5].textContent).toBe("0%")
    expect(summaryRow("ITR").cells[4].textContent).toBe(MATURITY_LABEL[2])
    expect(screen.queryByTestId("maturity-not-assessed")).toBeNull()
  })

  it("shows no not-assessed line when every dimension is answered", () => {
    renderWith(score({ CVI: 2, SGRM: 3, DPE: 3, ITR: 4 }))
    expect(screen.queryByTestId("maturity-not-assessed")).toBeNull()
    expect(screen.queryByText("Not assessed")).toBeNull()
  })

  it("shows no not-assessed line before a score exists", () => {
    renderWith(null, {})
    expect(screen.queryByTestId("maturity-not-assessed")).toBeNull()
    expect(screen.queryByText("Not assessed")).toBeNull()
    expect(summaryRow("CVI").cells[4].textContent).toBe("—")
  })

  it("keeps the 0% completion cell for a not-assessed dimension", () => {
    renderWith(score({ CVI: 2, SGRM: 0, DPE: 2, ITR: 2 }), { CVI: 1, DPE: 1, ITR: 1 })
    expect(summaryRow("SGRM").cells[5].textContent).toBe("0%")
    expect(summaryRow("CVI").cells[5].textContent).toBe("3%")
  })

  it("renders the not-assessed line under the Indeterminate em-dash state", () => {
    const indeterminate: ScoreResult = {
      overall: 0,
      maturity: "Indeterminate",
      dimensions: Object.fromEntries(
        DIMENSIONS.map((d) => [d, { score: null as unknown as number, weighted: 0 }]),
      ),
      profile_multiplier: 1.0,
    }
    renderWith(indeterminate, { CVI: 1, SGRM: 1 })
    expect(document.querySelector('[data-testid="maturity-bar-1"]')).toBeNull()
    expect(screen.getByTestId("maturity-not-assessed").textContent).toBe("2 dimensions not assessed")
  })
})
