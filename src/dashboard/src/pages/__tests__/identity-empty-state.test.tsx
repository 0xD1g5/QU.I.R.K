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
  it("renders a Not Scanned state for each identity protocol card when identity findings are absent", async () => {
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
})
