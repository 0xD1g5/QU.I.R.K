/**
 * UAT-7-30 ("Print View") — partial coverage, Phase 206 plan 206-11.
 *
 * UAT-7-30 has SIX Pass Criteria. This file covers FIVE of them:
 *
 *   2. No interactive controls (no filters, no toggle buttons)
 *   3. Full-width single-column layout
 *   4. CSS page breaks between major sections
 *   5. Content includes: score summary, findings, certificates, CBOM reference
 *   6. Background colors and borders render (print background styling enabled)
 *
 * It does NOT cover criterion 1:
 *
 *   1. No sidebar visible
 *
 * ...because criterion 1 cannot honestly be asserted from this mount point.
 * `Sidebar` is never inside `PrintPage`'s own subtree — it is a sibling that
 * `AppShell` mounts — so `expect(queryByTestId("sidebar")).toBeNull()` here
 * would be trivially true whatever the shell does, and would prove nothing.
 *
 * Criterion 1 IS covered, at the only mount point where it is meaningful, by
 * `src/dashboard/src/__tests__/app-print-chrome.test.tsx` — which renders the
 * real `AppShell` under `MemoryRouter` and pairs every absence assertion with
 * a positive control on a dashboard route. UAT-7-30 therefore needs BOTH
 * nodes cited; neither covers the case alone.
 *
 * STALE-DECISION NOTE (206-11, 2026-09-21). Phase 206's CONTEXT D-A2 records
 * criterion 1 as a confirmed product defect and instructs that UAT-7-30 be
 * dispositioned FAIL. That ruling was gathered on 2026-09-13 and was correct
 * then. It was overtaken on 2026-09-14 by commit 93e5afb1
 * ("fix(print): render /print without the dashboard chrome"), which moved
 * `/print` out of the shell entirely: `App.tsx:80` now returns `<PrintPage />`
 * before `<Sidebar />` at `App.tsx:87` is ever constructed. Re-verified by
 * command at 206-11 execution time; evidence in
 * `red-proof/206-RED-PROOF-print-style.md`. UAT-7-30's recommended
 * disposition is PASS, and there is no defect left to file.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup, within } from "@testing-library/react"

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

/**
 * A fixture with content in every section UAT-7-30 criterion 5 names, so an
 * empty-state paragraph cannot stand in for a rendered section.
 */
const SCAN_FIXTURE = {
  meta: {
    scan_id: "42",
    scanned_at: "2026-09-13T23:22:00Z",
    total_endpoints: 370,
    total_findings: 37,
  },
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
  findings: [
    {
      severity: "CRITICAL",
      host: "vault.internal",
      port: 8200,
      title: "TLS 1.0 enabled",
      quantum_risk: "Vulnerable",
    },
  ],
  certificates: [
    {
      host: "vault.internal",
      port: 8200,
      cert_subject: "CN=vault.internal",
      cert_not_after: "2027-01-01",
      cert_pubkey_alg: "RSA",
      cert_pubkey_size: 2048,
      quantum_safety: "Vulnerable",
    },
  ],
  cbom_components: [
    {
      algorithm: "RSA-2048",
      type: "public-key",
      key_size: 2048,
      quantum_safety: "Vulnerable",
      source_systems: ["vault.internal"],
    },
  ],
  roadmap: {
    nodes: [{ id: "n1", title: "Migrate vault to ML-KEM", timeframe: "0-6 months", why: null }],
    edges: [],
  },
  excluded_cert_count: 0,
  projected_score: null,
  identity_findings: [],
  motion_findings: [],
  dar_findings: [],
}

afterEach(() => {
  cleanup()
  document.body.removeAttribute("data-ready")
})

describe("PrintPage — UAT-7-30 print view layout", () => {
  it("renders the print view as single-column print sections with page-break styling and no interactive controls", async () => {
    scanDataReturn = { data: SCAN_FIXTURE, loading: false, error: null }
    qrammReturn = { scoreResult: null, complianceRows: null, loading: false, error: null }
    const { PrintPage } = await import("@/pages/print")
    const { container } = render(<PrintPage />)

    // ---- Criterion 3: full-width single-column layout -------------------
    // One centred content column at a fixed max width, and every major
    // section is a direct child of it — not a grid/flex/multi-column track.
    const column = container.querySelector<HTMLElement>("div[style]")
    expect(column).not.toBeNull()
    expect(column!.style.maxWidth).toBe("900px")
    expect(column!.style.margin).toContain("auto")
    expect(column!.style.display).toBe("")
    expect(column!.style.columnCount).toBe("")

    const sections = Array.from(container.querySelectorAll(".print-section"))
    expect(sections.length).toBeGreaterThan(1)
    for (const section of sections) {
      expect(section.parentElement).toBe(column)
    }

    // ---- Criterion 4: CSS page breaks between major sections ------------
    // Read the <style> element the page actually injects, not the source file.
    const styleEl = container.querySelector("style")
    expect(styleEl).not.toBeNull()
    const printCss = styleEl!.textContent ?? ""
    expect(printCss).toContain(".print-section{break-before:page")
    // The first section must not open with a blank leading page.
    expect(printCss).toContain(".print-section:first-child{break-before:avoid}")

    // ---- Criterion 5: content includes score, findings, certs, CBOM -----
    const scope = within(column!)
    // Score summary: the labelled figures, not merely the heading.
    expect(scope.getByText("Executive Summary")).toBeTruthy()
    expect(scope.getByText(/Overall Readiness/)).toBeTruthy()
    expect(scope.getByText("61")).toBeTruthy()
    // Findings section with a real row from the fixture.
    expect(scope.getByText("Findings")).toBeTruthy()
    expect(scope.getByText("TLS 1.0 enabled")).toBeTruthy()
    // Certificate inventory with a real row. Scoped to its own section, and
    // matched on the algorithm cell rather than the host: the fixture host
    // renders three times (findings row, cert host, cert subject CN), so a
    // host lookup would not uniquely prove the certificate section rendered.
    const certSection = sections.find(
      (s) => s.querySelector("h2")?.textContent === "Certificate Inventory",
    ) as HTMLElement | undefined
    expect(certSection).toBeTruthy()
    expect(within(certSection!).getByText("RSA 2048b")).toBeTruthy()
    // CBOM reference with a real component.
    expect(scope.getByText("Cryptographic Bill of Materials")).toBeTruthy()
    expect(scope.getByText("RSA-2048")).toBeTruthy()

    // ---- Criterion 2: no interactive controls ---------------------------
    // Both the accessibility-role view and the raw tag view, so a control
    // that is role-less (or role-overridden) cannot slip past either one.
    for (const role of [
      "button",
      "checkbox",
      "combobox",
      "textbox",
      "switch",
      "slider",
      "radio",
      "menuitem",
      "tab",
    ] as const) {
      expect(scope.queryAllByRole(role)).toHaveLength(0)
    }
    expect(column!.querySelectorAll("button, select, input, textarea, a[href]")).toHaveLength(0)

    // ---- Criterion 6: print background styling enabled ------------------
    // Backgrounds and borders are forced on rather than dropped by the
    // browser's default "do not print backgrounds" behaviour.
    expect(printCss).toContain("body,html{background:#fff!important")
    expect(printCss).toMatch(/th\{[^}]*background:#f4f4f5/)
    expect(printCss).toMatch(/th\{[^}]*border-bottom:2px solid/)
    expect(printCss).toMatch(/\.sev-CRITICAL\{background:/)
  })
})
