/**
 * SCORE-06 honest-absence on /print: an unassessed subscore must render as an
 * em-dash — never as a zero, and never as nothing at all.
 *
 * `docs/report-interpretation.md` documents the em-dash convention and
 * `executive.tsx`'s SubscoreSlot already implements it. `print.tsx` rendered the
 * raw value at all seven score sites, so a null printed as empty space under its
 * label. Observed live in a PDF export of a real 370-endpoint scan:
 * "Data in Motion" appeared as a bare label with no number above it, which reads
 * as a broken report rather than as an honest "not assessed".
 *
 * This matters more after 999.115, not less — excluding unassessed domains from
 * the headline is precisely what produces the nulls.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup } from "@testing-library/react"

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

/** Mirrors the real shape: unassessed domains come back as null, not 0. */
function makeScanFixture(subscores: Record<string, number | null>, score: number | null = 19) {
  return {
    meta: { scan_id: "1", scanned_at: "2026-09-13T23:22:00Z", total_endpoints: 370, total_findings: 37 },
    score: {
      score,
      rating: "POOR",
      rating_cap_reason: null,
      subscores,
      drivers: [],
    },
    confidence: { confidence_score: 64, confidence_rating: "LOW", factor_breakdown: {} },
    findings: [],
    certificates: [],
    cbom_components: [],
    roadmap: { nodes: [], edges: [] },
    identity_findings: [],
    motion_findings: [],
    dar_findings: [],
  }
}

const ALL_ASSESSED = {
  hygiene: 20, modern_tls: 19, identity_trust: 10,
  agility_signals: 25, data_at_rest: 21, data_in_motion: 18,
}

function numbersFrom(container: HTMLElement): string[] {
  return Array.from(container.querySelectorAll(".score-number")).map(
    (el) => el.textContent ?? "",
  )
}

afterEach(() => {
  cleanup()
  document.body.removeAttribute("data-ready")
})

describe("PrintPage — SCORE-06 honest absence", () => {
  it("renders an em-dash for an unassessed subscore, not an empty slot", async () => {
    scanDataReturn = {
      data: makeScanFixture({ ...ALL_ASSESSED, data_in_motion: null }),
      loading: false,
      error: null,
    }
    qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: null }
    const { PrintPage } = await import("@/pages/print")
    const { container } = render(<PrintPage />)

    const numbers = numbersFrom(container)
    expect(numbers).toContain("—")
    // The specific failure this replaces: a null rendered as "".
    expect(numbers).not.toContain("")
  })

  it("never substitutes a zero for an unassessed subscore", async () => {
    // A 0 would misreport "not tested" as "tested and terrible" — the exact
    // misreading the em-dash convention exists to prevent.
    scanDataReturn = {
      data: makeScanFixture({
        hygiene: null, modern_tls: null, identity_trust: null,
        agility_signals: null, data_at_rest: null, data_in_motion: null,
      }, null),
      loading: false,
      error: null,
    }
    qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: null }
    const { PrintPage } = await import("@/pages/print")
    const { container } = render(<PrintPage />)

    const numbers = numbersFrom(container)
    expect(numbers).toHaveLength(7)          // overall + six domains
    expect(numbers.every((n) => n === "—")).toBe(true)
    expect(numbers).not.toContain("0")
  })

  it("POSITIVE CONTROL: a real 0 subscore still renders as 0, not as an em-dash", async () => {
    // Without this the assertions above would pass against a component that
    // em-dashed everything. 0 and null mean different things and must look it.
    scanDataReturn = {
      data: makeScanFixture({ ...ALL_ASSESSED, hygiene: 0 }),
      loading: false,
      error: null,
    }
    qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: null }
    const { PrintPage } = await import("@/pages/print")
    const { container } = render(<PrintPage />)

    const numbers = numbersFrom(container)
    expect(numbers).toContain("0")
    expect(numbers).not.toContain("—")
  })

  it("POSITIVE CONTROL: a fully assessed scan renders seven real numbers", async () => {
    scanDataReturn = { data: makeScanFixture(ALL_ASSESSED), loading: false, error: null }
    qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: null }
    const { PrintPage } = await import("@/pages/print")
    const { container } = render(<PrintPage />)

    expect(numbersFrom(container)).toEqual(["19", "20", "19", "10", "25", "21", "18"])
  })
})
