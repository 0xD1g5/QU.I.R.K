/**
 * COUNT-05 / 237 UI-SPEC U2: /print renders a "Scan Coverage" subsection whenever a recorded
 * scan skipped or failed a phase, using the shared phaseRecordText wording.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup } from "@testing-library/react"
import { phaseRecordText } from "@/lib/coverage-reason"

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: true,
  error: null,
}
const qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: null }

vi.mock("@/hooks/useScanData", () => ({ useScanData: () => scanDataReturn }))
vi.mock("@/hooks/useQRAMMPrintData", () => ({ useQRAMMPrintData: () => qrammReturn }))

type Phase = {
  phase_name: string
  label: string
  status: string
  reason: string | null
  detail: string | null
  duration_sec: number | null
}

const TLS: Phase = { phase_name: "tls", label: "TLS", status: "ran", reason: null, detail: null, duration_sec: 1 }
const DB: Phase = {
  phase_name: "database",
  label: "Database",
  status: "skipped",
  reason: "missing-credentials",
  detail: "no db_targets credentials configured",
  duration_sec: null,
}
const OFF1: Phase = { phase_name: "k8s", label: "Kubernetes", status: "skipped", reason: "disabled-by-config", detail: null, duration_sec: null }
const OFF2: Phase = { phase_name: "vault", label: "Vault", status: "skipped", reason: "disabled-by-config", detail: null, duration_sec: null }

function fixture(coverage: unknown) {
  return {
    meta: { scan_id: "1", scanned_at: "2026-09-13T23:22:00Z", total_endpoints: 3, total_findings: 1 },
    score: {
      score: 50,
      rating: "FAIR",
      rating_cap_reason: null,
      subscores: { hygiene: 1, modern_tls: 1, identity_trust: 1, agility_signals: 1, data_at_rest: 1, data_in_motion: 1 },
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
    coverage,
  }
}

async function renderWith(coverage: unknown) {
  scanDataReturn = { data: fixture(coverage), loading: false, error: null }
  const { PrintPage } = await import("@/pages/print")
  return render(<PrintPage />)
}

const sel = '[data-testid="print-scan-coverage"]'

afterEach(() => {
  cleanup()
  document.body.removeAttribute("data-ready")
})

describe("PrintPage Scan Coverage (COUNT-05)", () => {
  it("renders the skip reason via phaseRecordText for a missing-credentials skip", async () => {
    const { container } = await renderWith({ recorded: true, ran: 1, skipped: 1, phases: [TLS, DB] })
    const el = container.querySelector(sel)
    expect(el).not.toBeNull()
    expect(el!.querySelector("h3")!.textContent).toBe("Scan Coverage")
    expect(el!.textContent).toContain("1 ran / 1 skipped")
    expect(el!.textContent).toContain(
      "Some scan phases did not run or did not finish. Findings and scores in this report cover only the phases that ran.",
    )
    const items = Array.from(el!.querySelectorAll("ul.coverage-list li")).map((li) => li.textContent)
    expect(items).toEqual([phaseRecordText(DB)])
  })

  it("collapses disabled-by-config phases into one line, not bullets", async () => {
    const { container } = await renderWith({ recorded: true, ran: 1, skipped: 3, phases: [TLS, OFF1, DB, OFF2] })
    const el = container.querySelector(sel)!
    const items = Array.from(el.querySelectorAll("ul.coverage-list li")).map((li) => li.textContent)
    expect(items).toEqual([phaseRecordText(DB)])
    expect(el.textContent).toContain("Not enabled in this scan's configuration: Kubernetes, Vault.")
  })

  it("omits the list when every non-ran phase is disabled-by-config", async () => {
    const { container } = await renderWith({ recorded: true, ran: 1, skipped: 1, phases: [TLS, OFF1] })
    const el = container.querySelector(sel)!
    expect(el).not.toBeNull()
    expect(el.querySelector("ul.coverage-list")).toBeNull()
    expect(el.textContent).toContain("Not enabled in this scan's configuration: Kubernetes.")
  })

  it("is absent when every phase ran", async () => {
    const { container } = await renderWith({ recorded: true, ran: 1, skipped: 0, phases: [TLS] })
    expect(container.querySelector(sel)).toBeNull()
  })

  it("is absent when coverage was not recorded", async () => {
    const { container } = await renderWith({ recorded: false, ran: 0, skipped: 0, phases: [] })
    expect(container.querySelector(sel)).toBeNull()
  })

  it("is absent when coverage is undefined", async () => {
    const { container } = await renderWith(undefined)
    expect(container.querySelector(sel)).toBeNull()
  })
})
