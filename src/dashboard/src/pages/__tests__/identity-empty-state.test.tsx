import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup, within } from "@testing-library/react"

// UAT-7-34 — Identity Page — Protocol Summary Cards (No Scan Data).
//
// Phase 169-06 explicitly REJECTED sensors-loading.test.tsx as a substitute for this case: that
// file asserts SensorsPage's own loading/empty/populated states, a different page and a different
// hook entirely (useSensorRegistry, not useScanData). This test asserts identity.tsx's own subject:
// its three protocol summary cards, individually, on an explicitly-empty `identity_findings` array
// (the declared type is `IdentityFinding[]`, never optional — RESEARCH § interfaces), not an
// omitted key.

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null }

const FIXTURE = {
  identity_findings: [] as unknown[],
}

afterEach(() => {
  cleanup()
})

describe("IdentityPage — protocol summary cards, no scan data (UAT-7-34)", () => {
  it("renders a Not Scanned state for each identity protocol card when identity findings are absent (no-coverage static fallback)", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)

    // Three cards visible, one per protocol named in UAT-7-34's Pass Criteria.
    for (const label of ["Kerberos", "SAML/OIDC", "DNSSEC"]) {
      const heading = screen.getByText(label)
      expect(heading).toBeInTheDocument()

      // Each card individually shows the "Not Scanned" status badge, not an error — walk up to
      // the Card container and assert within it, so this is a per-card check rather than a raw
      // count of "Not Scanned" occurrences anywhere on the page.
      const card = heading.closest('[class*="rounded-xl"]') ?? heading.closest("div")?.parentElement
      expect(card).not.toBeNull()
      if (card) {
        expect(within(card as HTMLElement).getByText("Not Scanned")).toBeInTheDocument()
      }
    }

    // Exactly three "Not Scanned" badges — one per card, not fewer (a card silently omitted) or
    // more (an unrelated element coincidentally matching the text).
    expect(screen.getAllByText("Not Scanned").length).toBe(3)

    // The empty-findings table branch renders its own empty-state copy rather than crashing or
    // rendering an interactive (sortable/filterable) table against zero rows.
    expect(
      screen.getByText(
        "No identity protocol findings in this scan — enable Kerberos, SAML, or DNSSEC scanners in config.yaml and run a scan.",
      ),
    ).toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
  })

  it("identity empty state shows the recorded saml refusal", async () => {
    const phase = (n: string) => ({ phase_name: n, label: n, status: "skipped", reason: "internal-target-refused", detail: null, duration_sec: null })
    scanDataReturn = { data: { ...FIXTURE, coverage: { recorded: true, ran: 0, skipped: 3, phases: ["kerberos_scanning", "saml_scanning", "dnssec_scanning"].map(phase) } }, loading: false, error: null }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)
    expect(screen.getAllByText(/internal targets refused by server policy/).length).toBeGreaterThan(0)
  })

  it("identity empty state shows ran with zero results", async () => {
    const phase = (n: string) => ({ phase_name: n, label: n, status: "ran", reason: null, detail: null, duration_sec: 1 })
    scanDataReturn = { data: { ...FIXTURE, coverage: { recorded: true, ran: 3, skipped: 0, phases: ["kerberos_scanning", "saml_scanning", "dnssec_scanning"].map(phase) } }, loading: false, error: null }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)
    expect(screen.getByText(/Ran, 0 results/)).toBeInTheDocument()
  })

  it("identity summary cards read the coverage record, not Not Scanned", async () => {
    // C-WR-08: the cards above the empty state must agree with it.
    scanDataReturn = {
      data: {
        ...FIXTURE,
        coverage: {
          recorded: true, ran: 1, skipped: 2,
          phases: [
            { phase_name: "kerberos_scanning", label: "Kerberos", status: "skipped", reason: "internal-target-refused", detail: null, duration_sec: null },
            { phase_name: "saml_scanning", label: "SAML", status: "ran", reason: null, detail: null, duration_sec: 1 },
            { phase_name: "dnssec_scanning", label: "DNSSEC", status: "skipped", reason: "disabled-by-config", detail: null, duration_sec: null },
          ],
        },
      },
      loading: false, error: null,
    }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)

    const cardFor = (label: string) => {
      const heading = screen.getByText(label, { selector: "[data-slot='card-title'], h3, div" })
      return (heading.closest('[class*="rounded-xl"]') ?? heading.parentElement?.parentElement) as HTMLElement
    }
    const saml = cardFor("SAML/OIDC")
    expect(within(saml).getByText("Ran")).toBeInTheDocument()
    expect(within(saml).queryByText("Not Scanned")).not.toBeInTheDocument()

    const kerberos = cardFor("Kerberos")
    expect(within(kerberos).getByText("Skipped")).toBeInTheDocument()
    expect(within(kerberos).getByText(/internal targets refused by server policy/)).toBeInTheDocument()

    expect(within(cardFor("DNSSEC")).getByText("Not Scanned")).toBeInTheDocument()
    expect(screen.getAllByText("Not Scanned").length).toBe(1)
  })

  it("identity summary card shows Failed for a phase that raised", async () => {
    scanDataReturn = {
      data: {
        ...FIXTURE,
        coverage: {
          recorded: true, ran: 0, skipped: 1,
          phases: [
            { phase_name: "kerberos_scanning", label: "Kerberos", status: "skipped", reason: "failed", detail: "RuntimeError: boom", duration_sec: null },
          ],
        },
      },
      loading: false, error: null,
    }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)

    expect(screen.getByText("Failed")).toBeInTheDocument()
    expect(screen.getByText("the scanner stopped with an error")).toBeInTheDocument()
    expect(screen.getAllByText("Not Scanned").length).toBe(2)
  })
})
