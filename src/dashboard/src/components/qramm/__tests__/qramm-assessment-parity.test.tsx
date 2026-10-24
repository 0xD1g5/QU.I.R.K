// Phase 231 D-09 parity gate (vitest half). The pytest half is
// tests/test_qramm_assessment_parity.py; both read
// src/dashboard/src/lib/__fixtures__/qramm-assessment-contract.json, so the
// endpoint, ComplianceMapTab, ScorecardTab and the print page cannot drift
// apart without a red test.
//
// Scenario (frozen in the contract): CVI questions 1-3 answered
// (scanner-measured, score 0.0), all 30 SGRM (self-assessed, 2.0), DPE 61-65
// (self-assessed, 0.0), no ITR (not assessed). Two assessed dimensions score
// 0.0 on purpose (D-07): no surface may read "Not assessed" from a score.
//
// Selectors used to read each surface's per-dimension state:
//  - ComplianceMapTab: the table named "QRAMM compliance framework coverage by
//    practice area"; per body row, cell[1] = dimension, cell[2] = Assessment
//    badge text. A dimension's state is the set of its practice-area badges
//    (must be exactly one).
//  - Print: the .print-section whose h2 is "QRAMM Governance Assessment"; the
//    table after h3 "Dimension Scorecard"; per row cell[0] = dimension,
//    cell[1] span.badge = Assessment chip.
//  - ScorecardTab: the Dimension Summary tbody rows; cell[0] = dimension,
//    cell[4] = Maturity Level, which reads "Not assessed" for an unanswered
//    dimension. The scorecard has no scanner/self split, so it is compared on
//    the Not-assessed set only.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, cleanup, screen, within } from "@testing-library/react"
import { ComplianceMapTab } from "@/components/qramm/ComplianceMapTab"
import { ScorecardTab } from "@/components/qramm/ScorecardTab"
import { QRAMMContext } from "@/context/QRAMMContext"
import type { AnswerState, ScoreResult } from "@/context/QRAMMContext"
import contract from "@/lib/__fixtures__/qramm-assessment-contract.json"
import {
  ASSESSMENT_LABEL,
  QRAMM_COVERAGE_SENTENCE,
  stateFromCoverageStatus,
  type AssessmentState,
} from "@/lib/qramm-assessment"
import type { QRAMMComplianceMapRow, QRAMMRowCoverageStatus } from "@/types/api"
import { buildCtx } from "./scorecard-fixtures"

const DIMS = ["CVI", "SGRM", "DPE", "ITR"] as const
type Dim = (typeof DIMS)[number]
const FRAMEWORK_ORDER = ["NIST_PQC", "NSM10", "CNSA2", "ISO27001", "ETSI_QS", "PCI_DSS", "CC", "BSI_TR"]
const STATES: AssessmentState[] = ["scanner-measured", "self-assessed", "not-assessed"]

const ROWS = contract.rows as QRAMMComplianceMapRow[]
const EXPECTED_STATE = contract.expected_dimension_state as Record<Dim, AssessmentState>
const EXPECTED_STATUS = contract.expected_coverage_status as Record<Dim, QRAMMRowCoverageStatus>

// Neutral, recorded values for the fields the contract does not carry.
const SCORE: ScoreResult = {
  overall: 1.25,
  maturity: "Developing",
  dimensions: contract.score,
  profile_multiplier: 1.0,
}

// ---------------------------------------------------------------------------
// Print page mocks (231-06 pattern)
// ---------------------------------------------------------------------------
let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: true,
  error: null,
}
let qrammReturn: {
  scoreResult: unknown
  complianceRows: unknown
  loading: boolean
  error: string | null
} = { scoreResult: null, complianceRows: null, loading: true, error: null }

vi.mock("@/hooks/useScanData", () => ({ useScanData: () => scanDataReturn }))
vi.mock("@/hooks/useQRAMMPrintData", () => ({ useQRAMMPrintData: () => qrammReturn }))

const SCAN_FIXTURE = {
  meta: { scan_id: "42", scanned_at: "2026-09-13T23:22:00Z", total_endpoints: 1, total_findings: 0 },
  score: {
    score: 61,
    rating: "FAIR",
    rating_cap_reason: null,
    subscores: {
      hygiene: 20,
      modern_tls: 19,
      identity_trust: 10,
      agility_signals: 25,
      data_at_rest: 21,
      data_in_motion: 18,
    },
    drivers: [],
  },
  confidence: { confidence_score: 64, confidence_rating: "LOW", factor_breakdown: {} },
  findings: [],
  certificates: [],
  cbom_components: [],
  roadmap: { nodes: [], edges: [] },
  excluded_cert_count: 0,
  projected_score: null,
  identity_findings: [],
  motion_findings: [],
  dar_findings: [],
}

const fetchSpy = vi.fn()

beforeEach(() => {
  fetchSpy.mockReset()
  fetchSpy.mockImplementation(
    async () =>
      new Response(JSON.stringify(ROWS), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
  )
  vi.stubGlobal("fetch", fetchSpy)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  document.body.removeAttribute("data-ready")
})

// ---------------------------------------------------------------------------
// Contract -> context inputs
// ---------------------------------------------------------------------------
function contractCatalog(): Map<number, string> {
  const catalog = new Map<number, string>()
  for (const [qn, dim] of Object.entries(contract.question_dimensions)) catalog.set(Number(qn), dim)
  return catalog
}

function contractAnswers(): Map<number, AnswerState> {
  const answers = new Map<number, AnswerState>()
  for (const a of contract.answers) {
    answers.set(a.question_number, {
      answer_value: a.answer_value as 1 | 2 | 3 | 4,
      suggested_answer: null,
      confirmed_at: "2026-10-24T00:00:00Z",
      evidence_note: "",
    })
  }
  return answers
}

// ---------------------------------------------------------------------------
// Surface readers
// ---------------------------------------------------------------------------
async function complianceMapStates(): Promise<Record<Dim, string[]>> {
  render(
    <QRAMMContext.Provider value={buildCtx(null)}>
      <ComplianceMapTab />
    </QRAMMContext.Provider>,
  )
  await screen.findByText("Executive Leadership")
  const table = screen.getByRole("table", {
    name: "QRAMM compliance framework coverage by practice area",
  })
  const out: Record<Dim, Set<string>> = { CVI: new Set(), SGRM: new Set(), DPE: new Set(), ITR: new Set() }
  const bodyRows = within(table).getAllByRole("row").filter((r) => within(r).queryAllByRole("cell").length > 0)
  for (const row of bodyRows) {
    const cells = within(row).getAllByRole("cell")
    const dim = cells[1].textContent as Dim
    expect(DIMS).toContain(dim)
    out[dim].add(cells[2].textContent ?? "")
  }
  return Object.fromEntries(DIMS.map((d) => [d, [...out[d]]])) as Record<Dim, string[]>
}

function complianceMapFootnote(): string | null {
  return screen.queryByText(QRAMM_COVERAGE_SENTENCE)?.textContent ?? null
}

async function renderPrintSection(): Promise<HTMLElement> {
  scanDataReturn = { data: SCAN_FIXTURE, loading: false, error: null }
  qrammReturn = { scoreResult: SCORE, complianceRows: ROWS, loading: false, error: null }
  const { PrintPage } = await import("@/pages/print")
  const { container } = render(<PrintPage />)
  const section = Array.from(container.querySelectorAll<HTMLElement>(".print-section")).find(
    (s) => s.querySelector("h2")?.textContent === "QRAMM Governance Assessment",
  )
  expect(section).toBeTruthy()
  return section!
}

function tableAfter(section: HTMLElement, heading: string): HTMLTableElement {
  const h3 = Array.from(section.querySelectorAll("h3")).find((h) => h.textContent === heading)
  expect(h3).toBeTruthy()
  let el = h3!.nextElementSibling
  while (el && el.tagName !== "TABLE") el = el.nextElementSibling
  expect(el).toBeTruthy()
  return el as HTMLTableElement
}

async function printStates(): Promise<Record<Dim, string>> {
  const section = await renderPrintSection()
  const rows = Array.from(tableAfter(section, "Dimension Scorecard").querySelectorAll<HTMLTableRowElement>("tbody tr"))
  const out = {} as Record<Dim, string>
  for (const d of DIMS) {
    const row = rows.find((r) => r.cells[0]?.textContent === d)
    expect(row).toBeTruthy()
    const chip = row!.cells[1].querySelector("span.badge")
    expect(chip).not.toBeNull()
    out[d] = chip!.textContent ?? ""
  }
  return out
}

function renderScorecard() {
  render(
    <QRAMMContext.Provider value={buildCtx(SCORE, contractAnswers())}>
      <ScorecardTab qnToDim={contractCatalog()} />
    </QRAMMContext.Provider>,
  )
}

function scorecardNotAssessed(): Set<string> {
  const out = new Set<string>()
  for (const row of Array.from(document.querySelectorAll<HTMLTableRowElement>("tbody tr"))) {
    const dim = row.cells[0]?.textContent ?? ""
    if (!(DIMS as readonly string[]).includes(dim)) continue
    if (row.cells[4]?.textContent === ASSESSMENT_LABEL["not-assessed"]) out.add(dim)
  }
  return out
}

const NOT_ASSESSED = ASSESSMENT_LABEL["not-assessed"]

// ---------------------------------------------------------------------------
describe("QRAMM assessed-state parity — Phase 231 D-09 (one contract, every surface)", () => {
  it("every QRAMM surface agrees with the contract's dimension states", async () => {
    const mapStates = await complianceMapStates()
    cleanup()
    const print = await printStates()
    for (const d of DIMS) {
      const expected = ASSESSMENT_LABEL[EXPECTED_STATE[d]]
      expect({ dim: d, surface: "compliance-map", states: mapStates[d] }).toEqual({
        dim: d,
        surface: "compliance-map",
        states: [expected],
      })
      expect({ dim: d, surface: "print", state: print[d] }).toEqual({
        dim: d,
        surface: "print",
        state: expected,
      })
    }
  })

  it("every QRAMM surface marks the same dimensions Not assessed", async () => {
    const expected = new Set(DIMS.filter((d) => EXPECTED_STATE[d] === "not-assessed"))
    expect([...expected]).toEqual(["ITR"])

    renderScorecard()
    const scorecard = scorecardNotAssessed()
    expect(screen.getByTestId("maturity-not-assessed").textContent).toBe("1 dimension not assessed")
    cleanup()

    const mapStates = await complianceMapStates()
    const map = new Set(DIMS.filter((d) => mapStates[d].includes(NOT_ASSESSED)))
    cleanup()

    const print = await printStates()
    const printSet = new Set(DIMS.filter((d) => print[d] === NOT_ASSESSED))

    expect({ surface: "scorecard", dims: [...scorecard].sort() }).toEqual({
      surface: "scorecard",
      dims: [...expected].sort(),
    })
    expect({ surface: "compliance-map", dims: [...map].sort() }).toEqual({
      surface: "compliance-map",
      dims: [...expected].sort(),
    })
    expect({ surface: "print", dims: [...printSet].sort() }).toEqual({
      surface: "print",
      dims: [...expected].sort(),
    })
  })

  it("the compliance map tab and the print page carry the same coverage sentence", async () => {
    await complianceMapStates()
    expect(complianceMapFootnote()).toBe(QRAMM_COVERAGE_SENTENCE)
    cleanup()
    const section = await renderPrintSection()
    expect(section.querySelector(".qramm-footnote")?.textContent).toBe(QRAMM_COVERAGE_SENTENCE)
  })

  it("print composition counts match the contract rows", async () => {
    const section = await renderPrintSection()
    const table = tableAfter(section, "Compliance Framework Coverage")
    const trs = Array.from(table.querySelectorAll<HTMLTableRowElement>("tbody tr"))
    expect(trs).toHaveLength(FRAMEWORK_ORDER.length)
    FRAMEWORK_ORDER.forEach((fw, i) => {
      const counts: Record<AssessmentState, number> = {
        "scanner-measured": 0,
        "self-assessed": 0,
        "not-assessed": 0,
      }
      for (const row of ROWS) {
        if (row.framework === fw) counts[stateFromCoverageStatus(row.coverage_status)] += 1
      }
      const cells = Array.from(trs[i].cells).slice(1).map((c) => c.textContent)
      expect({ fw, cells }).toEqual({ fw, cells: STATES.map((s) => String(counts[s])) })
    })
  })

  it("the contract states map from the contract coverage statuses", () => {
    for (const d of DIMS) {
      expect({ dim: d, state: stateFromCoverageStatus(EXPECTED_STATUS[d]) }).toEqual({
        dim: d,
        state: EXPECTED_STATE[d],
      })
    }
  })
})
