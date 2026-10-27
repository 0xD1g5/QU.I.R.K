/**
 * Phase 231 QRAMM-19 (D-05 / D-06a / D-21a / D-21b): the print/PDF QRAMM page
 * carries the same three assessment states as the compliance map tab, in text:
 * an Assessment column on the Dimension Scorecard, per-framework composition
 * counts in place of the retired "Coverage Tier" column, and a text chip on
 * every per-framework detail row.
 *
 * Rows always come from the shared D-09 contract fixture (CVI covered, SGRM and
 * DPE self-assessed, ITR pending); no inline rows. Expected counts are computed
 * here from those rows with the shared vocabulary, not retyped.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup } from "@testing-library/react"
import contract from "@/lib/__fixtures__/qramm-assessment-contract.json"
import {
  ASSESSMENT_LABEL,
  ASSESSMENT_PRINT_CLASS,
  QRAMM_COVERAGE_SENTENCE,
  stateFromCoverageStatus,
  type AssessmentState,
} from "@/lib/qramm-assessment"
import type { QRAMMComplianceMapRow } from "@/types/api"

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

const SCORE = {
  overall: 1.25,
  maturity: "Developing",
  dimensions: contract.score,
  profile_multiplier: 1.0,
}

const ROWS = contract.rows as QRAMMComplianceMapRow[]
const FRAMEWORK_ORDER = ["NIST_PQC", "NSM10", "CNSA2", "ISO27001", "ETSI_QS", "PCI_DSS", "CC", "BSI_TR"]
// Phase 234 D-15: the composition table gained a "Stale — recalculate" column.
const STATES: AssessmentState[] = ["scanner-measured", "self-assessed", "not-assessed", "stale"]

afterEach(() => {
  cleanup()
  document.body.removeAttribute("data-ready")
})

async function renderQramm(rows: QRAMMComplianceMapRow[] = ROWS) {
  scanDataReturn = { data: SCAN_FIXTURE, loading: false, error: null }
  qrammReturn = { scoreResult: SCORE, complianceRows: rows, loading: false, error: null }
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

function headers(table: HTMLTableElement): string[] {
  return Array.from(table.querySelectorAll("thead th")).map((th) => th.textContent ?? "")
}

function bodyRows(table: HTMLTableElement): HTMLTableRowElement[] {
  return Array.from(table.querySelectorAll<HTMLTableRowElement>("tbody tr"))
}

function scorecardRow(section: HTMLElement, dim: string): HTMLTableRowElement {
  const row = bodyRows(tableAfter(section, "Dimension Scorecard")).find(
    (r) => r.cells[0]?.textContent === dim,
  )
  expect(row).toBeTruthy()
  return row!
}

function expectChip(cell: HTMLTableCellElement, state: AssessmentState) {
  const chip = cell.querySelector("span.badge")
  expect(chip).not.toBeNull()
  expect(chip!.textContent).toBe(ASSESSMENT_LABEL[state])
  expect(chip!.classList.contains(ASSESSMENT_PRINT_CLASS[state])).toBe(true)
}

function expectedCounts(rows: QRAMMComplianceMapRow[], fw: string): Record<AssessmentState, number> {
  const counts: Record<AssessmentState, number> = {
    "scanner-measured": 0,
    "self-assessed": 0,
    "not-assessed": 0,
    stale: 0,
  }
  for (const row of rows) {
    if (row.framework === fw) counts[stateFromCoverageStatus(row.coverage_status)] += 1
  }
  return counts
}

describe("PrintQRAMM — Phase 231 three-state print rendering", () => {
  it("shows an Assessment column on the print Dimension Scorecard", async () => {
    const section = await renderQramm()
    const table = tableAfter(section, "Dimension Scorecard")
    expect(headers(table)).toEqual(["Dimension", "Assessment", "Raw Score", "Weighted Score"])

    const cvi = scorecardRow(section, "CVI")
    expectChip(cvi.cells[1], "scanner-measured")
    expect(cvi.cells[2].textContent).toBe("0.0")
    expect(cvi.cells[3].textContent).toBe("0.00")

    const sgrm = scorecardRow(section, "SGRM")
    expectChip(sgrm.cells[1], "self-assessed")
    expect(sgrm.cells[2].textContent).toBe("2.0")
    expect(sgrm.cells[3].textContent).toBe("2.00")

    expectChip(scorecardRow(section, "DPE").cells[1], "self-assessed")

    const itr = scorecardRow(section, "ITR")
    expectChip(itr.cells[1], "not-assessed")
    expect(itr.cells[2].textContent).toBe("—")
    expect(itr.cells[3].textContent).toBe("—")

    const footer = bodyRows(table).find((r) => r.textContent?.startsWith("Overall maturity:"))
    expect(footer).toBeTruthy()
    expect(footer!.cells[0].colSpan).toBe(4)
  })

  it("shows per-framework composition counts", async () => {
    const section = await renderQramm()
    const table = tableAfter(section, "Compliance Framework Coverage")
    expect(headers(table)).toEqual(["Framework", "Scanner-measured", "Self-assessed", "Not assessed", "Stale — recalculate"])

    const caption = table.previousElementSibling
    expect(caption?.classList.contains("meta")).toBe(true)
    expect(caption?.textContent).toBe(
      "Counts are practice areas per framework, grouped by how each was assessed.",
    )

    const rows = bodyRows(table)
    expect(rows).toHaveLength(FRAMEWORK_ORDER.length)
    FRAMEWORK_ORDER.forEach((fw, i) => {
      const expected = expectedCounts(ROWS, fw)
      const cells = Array.from(rows[i].cells).slice(1).map((c) => c.textContent)
      expect(cells).toEqual(STATES.map((s) => String(expected[s])))
      expect(rows[i].querySelector("span.badge")).toBeNull()
    })
  })

  it("uses the shared coverage sentence as the print footnote", async () => {
    const section = await renderQramm()
    const footnote = section.querySelector(".qramm-footnote")
    expect(footnote?.textContent).toBe(QRAMM_COVERAGE_SENTENCE)
  })

  it("labels every detail row with an assessment chip", async () => {
    const section = await renderQramm()
    const details = Array.from(section.querySelectorAll<HTMLElement>(".qramm-detail-section"))
    expect(details).toHaveLength(FRAMEWORK_ORDER.length)
    let checked = 0
    FRAMEWORK_ORDER.forEach((fw, i) => {
      const table = details[i].querySelector("table") as HTMLTableElement
      expect(headers(table)).toEqual(["Practice Area", "Dimension", "Relevance Score", "Assessment"])
      const fwRows = ROWS.filter((r) => r.framework === fw)
      const trs = bodyRows(table)
      expect(trs).toHaveLength(fwRows.length)
      fwRows.forEach((row, j) => {
        const state = stateFromCoverageStatus(row.coverage_status)
        expectChip(trs[j].cells[3], state)
        if (state === "not-assessed") {
          expect(trs[j].cells[2].textContent).toBe("—")
        } else {
          expect(trs[j].cells[2].textContent).toBe((row.relevance_score as number).toFixed(2))
        }
        checked += 1
      })
    })
    expect(checked).toBe(ROWS.length)
  })

  it("does not render retired print labels", async () => {
    const section = await renderQramm()
    const text = section.textContent ?? ""
    for (const retired of [
      "Manual only",
      "Scanner-Informed",
      "Scanner-informed",
      "Coverage Tier",
      "Coverage reflects QUIRK scanner findings for CVI only — SGRM, DPE, ITR require manual assessment.",
      "require manual assessment",
    ]) {
      expect(text).not.toContain(retired)
    }
    const cellTexts = Array.from(section.querySelectorAll("td")).map((td) => td.textContent)
    expect(cellTexts).not.toContain("Yes")
    expect(cellTexts).not.toContain("No")
    expect(section.querySelector(".tier-manual")).toBeNull()
  })

  it("reads a dimension with no rows at all as Not assessed", async () => {
    const withoutCvi = ROWS.filter((r) => r.dimension !== "CVI")
    const section = await renderQramm(withoutCvi)
    const cvi = scorecardRow(section, "CVI")
    expectChip(cvi.cells[1], "not-assessed")
    expect(cvi.cells[2].textContent).toBe("—")
    expect(cvi.cells[3].textContent).toBe("—")

    const rows = bodyRows(tableAfter(section, "Compliance Framework Coverage"))
    FRAMEWORK_ORDER.forEach((fw, i) => {
      const expected = expectedCounts(withoutCvi, fw)
      expect(expected["scanner-measured"]).toBe(0)
      const cells = Array.from(rows[i].cells).slice(1).map((c) => c.textContent)
      expect(cells).toEqual(STATES.map((s) => String(expected[s])))
    })
  })

  it("ships the self-assessed and not-assessed print chip CSS and drops tier-manual", async () => {
    const section = await renderQramm()
    const css = section.ownerDocument.querySelector("style")?.textContent ?? ""
    expect(css).toContain(".tier-self{background:transparent;color:var(--print-fg);border:1px solid var(--print-fg)}")
    expect(css).toContain(
      ".tier-none{background:transparent;color:var(--print-muted);border:1px dashed var(--print-muted)}",
    )
    expect(css).toContain(".tier-scanner{background:var(--ds-accent);color:var(--print-fg-inverse)}")
    expect(css).not.toContain(".tier-manual")
  })
})
