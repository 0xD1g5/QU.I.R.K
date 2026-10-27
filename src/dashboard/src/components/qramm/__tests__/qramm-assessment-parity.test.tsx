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
import { MATURITY_LABEL } from "@/lib/qramm-constants"
import { buildCtx } from "./scorecard-fixtures"

const DIMS = ["CVI", "SGRM", "DPE", "ITR"] as const
type Dim = (typeof DIMS)[number]
const FRAMEWORK_ORDER = ["NIST_PQC", "NSM10", "CNSA2", "ISO27001", "ETSI_QS", "PCI_DSS", "CC", "BSI_TR"]
const STATES: AssessmentState[] = ["scanner-measured", "self-assessed", "not-assessed", "stale"]

const ROWS = contract.rows as QRAMMComplianceMapRow[]
const EXPECTED_STATE = contract.expected_dimension_state as Record<Dim, AssessmentState>
const EXPECTED_STATUS = contract.expected_coverage_status as Record<Dim, QRAMMRowCoverageStatus>

// Phase 234 SCORE-10: the overall, maturity and per-dimension answered counts come from the
// contract (D-14); profile_multiplier is the one neutral value the contract does not carry.
const SCORE: ScoreResult = {
  overall: contract.expected_overall,
  maturity: contract.expected_maturity,
  dimensions: contract.score,
  profile_multiplier: 1.0,
  answered_by_dimension: contract.expected_answered_by_dimension,
  assessed_dimensions: contract.expected_assessed_dimensions,
  dimensions_assessed: contract.expected_dimensions_assessed,
  dimensions_total: contract.expected_dimensions_total,
}

// D-25: a score saved before Phase 234 is the same score with the contract's removed keys gone.
const LEGACY_SCORE = Object.fromEntries(
  Object.entries(SCORE).filter(([k]) => !contract.legacy_score_json.removed_score_keys.includes(k)),
) as unknown as ScoreResult

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
  scoreStale?: boolean
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

// The rows the stubbed compliance-map endpoint answers with (ComplianceMapTab reads them via fetchApi).
let mapRows: QRAMMComplianceMapRow[] = ROWS

beforeEach(() => {
  mapRows = ROWS
  fetchSpy.mockReset()
  fetchSpy.mockImplementation(
    async () =>
      new Response(JSON.stringify(mapRows), {
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

function contractAnswers(
  list: Array<{ question_number: number; answer_value: number }> = contract.answers,
): Map<number, AnswerState> {
  const answers = new Map<number, AnswerState>()
  for (const a of list) {
    answers.set(a.question_number, {
      answer_value: a.answer_value as 1 | 2 | 3 | 4,
      suggested_answer: null,
      confirmed_at: "2026-10-24T00:00:00Z",
      evidence_note: "",
    })
  }
  return answers
}

/** Per-dimension answered counts of an answer list, through the contract's question catalog. */
function answeredCounts(list: Array<{ question_number: number }>): Record<Dim, number> {
  const out: Record<Dim, number> = { CVI: 0, SGRM: 0, DPE: 0, ITR: 0 }
  const qd = contract.question_dimensions as Record<string, string>
  for (const a of list) out[qd[String(a.question_number)] as Dim] += 1
  return out
}

/** The contract rows with each dimension's coverage_status replaced; a stale row carries no relevance. */
function rowsWithStatus(status: Record<string, string>): QRAMMComplianceMapRow[] {
  return ROWS.map((r) => {
    const cs = status[r.dimension] as QRAMMRowCoverageStatus
    return { ...r, coverage_status: cs, relevance_score: cs === "stale" ? null : r.relevance_score }
  })
}

// ---------------------------------------------------------------------------
// Surface readers
// ---------------------------------------------------------------------------
async function complianceMapStates(rows: QRAMMComplianceMapRow[] = ROWS): Promise<Record<Dim, string[]>> {
  mapRows = rows
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

async function renderPrintSection(
  score: ScoreResult = SCORE,
  rows: QRAMMComplianceMapRow[] = ROWS,
  scoreStale = false,
): Promise<HTMLElement> {
  scanDataReturn = { data: SCAN_FIXTURE, loading: false, error: null }
  qrammReturn = { scoreResult: score, complianceRows: rows, loading: false, error: null, scoreStale }
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

async function printStates(
  score: ScoreResult = SCORE,
  rows: QRAMMComplianceMapRow[] = ROWS,
  scoreStale = false,
): Promise<Record<Dim, string>> {
  const section = await renderPrintSection(score, rows, scoreStale)
  const trs = Array.from(tableAfter(section, "Dimension Scorecard").querySelectorAll<HTMLTableRowElement>("tbody tr"))
  const out = {} as Record<Dim, string>
  for (const d of DIMS) {
    const row = trs.find((r) => r.cells[0]?.textContent === d)
    expect(row).toBeTruthy()
    const chip = row!.cells[1].querySelector("span.badge")
    expect(chip).not.toBeNull()
    out[d] = chip!.textContent ?? ""
  }
  return out
}

function renderScorecard(
  score: ScoreResult | null = SCORE,
  answers: Map<number, AnswerState> = contractAnswers(),
) {
  render(
    <QRAMMContext.Provider value={buildCtx(score, answers)}>
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

/** Scorecard Dimension Summary: cell[4] (Maturity Level) text per dimension. */
function scorecardMaturityCells(): Record<Dim, string> {
  const out = {} as Record<Dim, string>
  for (const row of Array.from(document.querySelectorAll<HTMLTableRowElement>("tbody tr"))) {
    const dim = row.cells[0]?.textContent ?? ""
    if ((DIMS as readonly string[]).includes(dim)) out[dim as Dim] = row.cells[4]?.textContent ?? ""
  }
  return out
}

/** Maturity Distribution bucket counts, read from the bar widths (count / 4 * 100%). */
function scorecardBuckets(): Record<number, number> {
  const out: Record<number, number> = {}
  for (const level of [1, 2, 3, 4]) {
    const bar = screen.queryByTestId(`maturity-bar-${level}`) as HTMLElement | null
    out[level] = bar ? Math.round((parseFloat(bar.style.width) / 100) * DIMS.length) : -1
  }
  return out
}

/** Expected buckets: the contract scores of the dimensions that may count toward a maturity level. */
function expectedBuckets(counted: readonly string[]): Record<number, number> {
  const out: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0 }
  const score = contract.score as Record<string, { score: number }>
  for (const d of counted) out[Math.max(1, Math.min(4, Math.round(score[d].score)))] += 1
  return out
}

function printOverallRow(section: HTMLElement): string {
  const rows = Array.from(tableAfter(section, "Dimension Scorecard").querySelectorAll<HTMLTableRowElement>("tbody tr"))
  const footer = rows.find((r) => r.textContent?.startsWith("Overall maturity:"))
  expect(footer).toBeTruthy()
  return footer!.textContent ?? ""
}

const NOT_ASSESSED = ASSESSMENT_LABEL["not-assessed"]
const SELF_ASSESSED = ASSESSMENT_LABEL["self-assessed"]
const MATURITY_WORDS = Object.values(MATURITY_LABEL)

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
        stale: 0,
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
  // -------------------------------------------------------------------------
  // Phase 234 SCORE-10 (D-14, D-15, D-23, D-25): the shared contract's overall,
  // stale and legacy cases. The pytest half asserts the same keys on the API.
  // -------------------------------------------------------------------------
  it("the scorecard and the print page show the contract's overall and N of 4 assessed", async () => {
    const overall = contract.expected_overall.toFixed(2)
    const nOf4 = `${contract.expected_dimensions_assessed} of ${contract.expected_dimensions_total} dimensions assessed`

    renderScorecard()
    expect({
      overall: screen.queryByTestId("qramm-overall")?.textContent ?? null,
      maturity: screen.queryByTestId("qramm-overall-maturity")?.textContent ?? null,
      assessed: screen.queryByTestId("qramm-dimensions-assessed")?.textContent ?? null,
    }).toEqual({ overall, maturity: contract.expected_maturity, assessed: nOf4 })
    expect(screen.queryByTestId("qramm-score-stale")).toBeNull()
    cleanup()

    const section = await renderPrintSection()
    expect(printOverallRow(section)).toBe(
      `Overall maturity: ${contract.expected_maturity} (${overall}) — ${nOf4}`,
    )
  })

  it("a stale saved score reads Stale on every QRAMM surface, never Self-assessed", async () => {
    const sc = contract.stale_case
    const expectedState = sc.expected_dimension_state as Record<Dim, AssessmentState>
    const staleDims = DIMS.filter((d) => expectedState[d] === "stale")
    expect(staleDims).toEqual(["ITR"])
    const staleLabel = ASSESSMENT_LABEL[expectedState.ITR]
    expect({ twin: "ASSESSMENT_LABEL.stale", label: staleLabel }).toEqual({
      twin: "ASSESSMENT_LABEL.stale",
      label: expect.any(String),
    })

    // The score was saved against answers_before_score; answers_after_score arrived later.
    const scoredCounts = answeredCounts(sc.answers_before_score)
    const staleScore: ScoreResult = { ...SCORE, answered_by_dimension: scoredCounts }
    const live = contractAnswers([...sc.answers_before_score, ...sc.answers_after_score])

    renderScorecard(staleScore, live)
    const cells = scorecardMaturityCells()
    expect({ surface: "scorecard", ITR: cells.ITR }).toEqual({ surface: "scorecard", ITR: staleLabel })
    expect(Object.values(cells)).not.toContain(SELF_ASSESSED)
    expect(screen.queryByTestId("qramm-score-stale")).not.toBeNull()
    expect({ surface: "scorecard", buckets: scorecardBuckets() }).toEqual({
      surface: "scorecard",
      buckets: expectedBuckets(DIMS.filter((d) => expectedState[d] !== "stale" && expectedState[d] !== "not-assessed")),
    })
    cleanup()

    const rows = rowsWithStatus(sc.expected_coverage_status)
    const mapStates = await complianceMapStates(rows)
    cleanup()
    const print = await printStates(staleScore, rows, sc.expected_score_stale)

    for (const d of DIMS) {
      const expected = ASSESSMENT_LABEL[expectedState[d]]
      expect({ dim: d, surface: "compliance-map", states: mapStates[d] }).toEqual({
        dim: d,
        surface: "compliance-map",
        states: [expected],
      })
      expect({ dim: d, surface: "print", state: print[d] }).toEqual({ dim: d, surface: "print", state: expected })
    }
    expect(mapStates.ITR).not.toContain(SELF_ASSESSED)
    expect(print.ITR).not.toBe(SELF_ASSESSED)
  })

  it("a score saved before the upgrade shows Recalculate instead of an overall maturity level", async () => {
    const lg = contract.legacy_score_json
    const expectedState = lg.expected_dimension_state as Record<Dim, AssessmentState>
    const label = lg.expected_overall_label
    expect(LEGACY_SCORE).not.toHaveProperty("answered_by_dimension")

    renderScorecard(LEGACY_SCORE, contractAnswers(lg.answers))
    expect(screen.queryByTestId("qramm-overall")?.textContent ?? null).toBe(label)
    expect(screen.queryByTestId("qramm-overall-maturity")).toBeNull()
    expect(screen.queryByTestId("qramm-dimensions-assessed")).toBeNull()
    const cells = scorecardMaturityCells()
    for (const d of DIMS) {
      expect({ dim: d, surface: "scorecard", state: cells[d] }).toEqual({
        dim: d,
        surface: "scorecard",
        state: ASSESSMENT_LABEL[expectedState[d]],
      })
    }
    for (const word of [...MATURITY_WORDS, SELF_ASSESSED]) expect(Object.values(cells)).not.toContain(word)
    expect({ surface: "scorecard", buckets: scorecardBuckets() }).toEqual({
      surface: "scorecard",
      buckets: { 1: 0, 2: 0, 3: 0, 4: 0 },
    })
    cleanup()

    const rows = rowsWithStatus(lg.expected_coverage_status)
    const mapStates = await complianceMapStates(rows)
    cleanup()
    const section = await renderPrintSection(LEGACY_SCORE, rows, lg.expected_score_stale)
    const overallRow = printOverallRow(section)
    expect(overallRow).toContain(label)
    for (const word of MATURITY_WORDS) expect(overallRow).not.toContain(word)
    cleanup()
    const print = await printStates(LEGACY_SCORE, rows, lg.expected_score_stale)

    for (const d of DIMS) {
      const expected = ASSESSMENT_LABEL[expectedState[d]]
      expect({ dim: d, surface: "compliance-map", states: mapStates[d] }).toEqual({
        dim: d,
        surface: "compliance-map",
        states: [expected],
      })
      expect({ dim: d, surface: "print", state: print[d] }).toEqual({ dim: d, surface: "print", state: expected })
      expect(mapStates[d]).not.toContain(SELF_ASSESSED)
      expect(print[d]).not.toBe(SELF_ASSESSED)
    }
  })

  it("an answered but unscored session shows no stale dimension", () => {
    // W2: with no score there is nothing to be stale (Python's score_data-is-None branch).
    renderScorecard(null, contractAnswers())
    expect(screen.queryByText(/Stale — recalculate/)).toBeNull()
    expect(screen.queryByTestId("qramm-score-stale")).toBeNull()
    expect(screen.queryByTestId("qramm-overall")).toBeNull()
    const cells = scorecardMaturityCells()
    for (const d of DIMS) expect({ dim: d, cell: cells[d] }).toEqual({ dim: d, cell: "—" })
  })
  it("a saved score missing one dimension's count reads that dimension Stale, never Self-assessed", () => {
    // 234-02 Deviation 2 (T-234-02): a blob that omits a live-answered dimension's count cannot
    // vouch for that dimension's answers; the server reads it stale and so must the TS twin.
    const counts = { ...contract.expected_answered_by_dimension } as Record<string, number>
    delete counts.SGRM
    renderScorecard({ ...SCORE, answered_by_dimension: counts }, contractAnswers())
    const cells = scorecardMaturityCells()
    expect({ dim: "SGRM", cell: cells.SGRM }).toEqual({ dim: "SGRM", cell: ASSESSMENT_LABEL.stale })
    expect(Object.values(cells)).not.toContain(SELF_ASSESSED)
    expect(cells.ITR).toBe(NOT_ASSESSED)
    expect(screen.queryByTestId("qramm-score-stale")).not.toBeNull()
  })
})
