// Phase 231 QRAMM-19 (D-01, D-05, D-06a): the compliance map tab shows
// answered SGRM/DPE/ITR practice areas as Self-assessed, with their scores,
// and marks every row's assessment state in text. The tier comes from the
// row's coverage_status (never scanner_informed, which is true for an
// unanswered CVI too). Rows are the real D-09 contract fixture: CVI covered,
// SGRM and DPE self-assessed, ITR pending.
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { render, cleanup, screen, within } from "@testing-library/react"
import { ComplianceMapTab } from "@/components/qramm/ComplianceMapTab"
import { QRAMMContext } from "@/context/QRAMMContext"
import { QRAMM_COVERAGE_SENTENCE } from "@/lib/qramm-assessment"
import contract from "@/lib/__fixtures__/qramm-assessment-contract.json"
import type { QRAMMComplianceMapRow } from "@/types/api"

const CONTRACT_ROWS = contract.rows as QRAMMComplianceMapRow[]
const FRAMEWORKS = [
  "NIST_PQC", "NSM10", "CNSA2", "ISO27001",
  "ETSI_QS", "PCI_DSS", "CC", "BSI_TR",
] as const

const fetchSpy = vi.fn()

function serveRows(rows: QRAMMComplianceMapRow[]) {
  fetchSpy.mockResolvedValue({ ok: true, status: 200, json: async () => rows })
}

beforeEach(() => {
  fetchSpy.mockReset()
  serveRows(CONTRACT_ROWS)
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

async function renderTab() {
  render(
    <QRAMMContext.Provider value={ctxValue()}>
      <ComplianceMapTab />
    </QRAMMContext.Provider>
  )
  await screen.findByText("Executive Leadership")
}

// The table row for one practice area: [practice area, dimension, assessment, 8 framework cells].
function practiceCells(practiceArea: string): HTMLElement[] {
  const table = screen.getByRole("table", {
    name: "QRAMM compliance framework coverage by practice area",
  })
  const row = within(table)
    .getAllByRole("row")
    .find((r) => within(r).queryAllByRole("cell")[0]?.textContent?.startsWith(practiceArea))
  if (!row) throw new Error(`no table row for practice area ${practiceArea}`)
  return within(row).getAllByRole("cell")
}

function expectedScores(rows: QRAMMComplianceMapRow[], practiceArea: string): string[] {
  return FRAMEWORKS.map((fw) => {
    const r = rows.find((x) => x.practice_area === practiceArea && x.framework === fw)
    if (!r || r.relevance_score === null) throw new Error(`fixture lacks a score for ${practiceArea} ${fw}`)
    return r.relevance_score.toFixed(2)
  })
}

function practiceAreasOf(dimension: string): string[] {
  return [...new Set(CONTRACT_ROWS.filter((r) => r.dimension === dimension).map((r) => r.practice_area))]
}

describe("ComplianceMapTab — Phase 231 QRAMM-19 assessment states", () => {
  it("labels self-assessed rows with text and shows their scores", async () => {
    await renderTab()
    const sgrm = practiceAreasOf("SGRM")
    expect(sgrm).toHaveLength(3)
    for (const pa of sgrm) {
      const cells = practiceCells(pa)
      expect(cells).toHaveLength(11)
      expect(cells[2].textContent).toBe("Self-assessed")
      const badge = within(cells[2]).getByText("Self-assessed")
      expect(badge.className).toContain("text-foreground")
      expect(badge.className).not.toContain("bg-primary")
      expect(cells.slice(3).map((c) => c.textContent)).toEqual(expectedScores(CONTRACT_ROWS, pa))
    }
    // At least one self-assessed score is non-zero, so "shows the score" is not a 0.00 coincidence.
    expect(practiceCells("2.1")[3].textContent).toBe("0.20")
  })

  it("labels scanner-measured CVI rows and shows their scores", async () => {
    await renderTab()
    for (const pa of practiceAreasOf("CVI")) {
      const cells = practiceCells(pa)
      expect(cells[2].textContent).toBe("Scanner-measured")
      expect(within(cells[2]).getByText("Scanner-measured").className).toContain("bg-primary")
      expect(cells.slice(3).map((c) => c.textContent)).toEqual(expectedScores(CONTRACT_ROWS, pa))
    }
  })

  it("labels unanswered rows Not assessed and shows em dashes", async () => {
    await renderTab()
    const itr = practiceAreasOf("ITR")
    expect(itr).toHaveLength(3)
    for (const pa of itr) {
      const cells = practiceCells(pa)
      expect(cells[2].textContent).toBe("Not assessed")
      expect(within(cells[2]).getByText("Not assessed").className).toContain("bg-secondary")
      expect(cells.slice(3).map((c) => c.textContent)).toEqual(Array(8).fill("—"))
    }
  })

  it("maps a null coverage_status to Not assessed", async () => {
    const firstIdx = CONTRACT_ROWS.findIndex((r) => r.practice_area === "2.1")
    const rows = CONTRACT_ROWS.map((r, i) => (i === firstIdx ? { ...r, coverage_status: null } : r))
    serveRows(rows)
    await renderTab()
    const cells = practiceCells("2.1")
    expect(cells[2].textContent).toBe("Not assessed")
    expect(cells.slice(3).map((c) => c.textContent)).toEqual(Array(8).fill("—"))
  })

  it("renders the shared coverage sentence as the footnote", async () => {
    await renderTab()
    const footnote = screen.getByText(QRAMM_COVERAGE_SENTENCE)
    expect(footnote.textContent).toBe(QRAMM_COVERAGE_SENTENCE)
    expect(footnote.tagName).toBe("P")
  })

  it("renders three Coverage Tiers legend rows", async () => {
    await renderTab()
    expect(screen.getByText("Coverage Tiers")).toBeTruthy()
    // Only the legend badges carry a title attribute; the table badges do not.
    const card = screen
    const expected: Array<[string, string]> = [
      ["Scanner-measured", "CVI practice areas, scored with QUIRK scanner evidence."],
      [
        "Self-assessed",
        "SGRM, DPE and ITR practice areas scored from answers entered by hand. No scanner evidence backs these scores.",
      ],
      [
        "Not assessed",
        "No question in this dimension has been answered yet, so its practice areas have no score.",
      ],
    ]
    const badges = card.getAllByTitle(/^(Scanner-measured|Self-assessed|Not assessed)$/)
    expect(badges.map((b) => b.textContent)).toEqual(expected.map(([label]) => label))
    for (const [label, description] of expected) {
      const badge = card.getByTitle(label)
      expect(badge.textContent).toBe(label)
      expect(badge.parentElement!.textContent).toBe(label + description)
    }
  })

  it("does not render retired labels", async () => {
    await renderTab()
    const text = document.body.textContent ?? ""
    for (const retired of [
      "Scanner-informed",
      "Scanner-Informed",
      "Manual only",
      "All relevant dimensions require manual assessment",
      "At least one relevant dimension is scanner-informed",
      "Coverage reflects QUIRK scanner findings for CVI only",
      "require manual assessment",
    ]) {
      expect(text).not.toContain(retired)
    }
  })

  it("places the Assessment column between Dimension and the first framework column", async () => {
    await renderTab()
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent)
    expect(headers.slice(0, 4)).toEqual(["Practice Area", "Dimension", "Assessment", "NIST PQC"])
    expect(headers).toHaveLength(11)
  })
})
