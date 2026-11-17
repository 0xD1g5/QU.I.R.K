import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup, within } from "@testing-library/react"

// IDENT-06 (Phase 238 D-06, UI-SPEC U1/U2): the Identity page shows a fourth JWT/JWKS card fed by
// identity_findings rows with protocol "JWT" and by the jwt_scanning coverage record.

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null }

const LABELS: Record<string, string> = {
  kerberos_scanning: "Kerberos",
  saml_scanning: "SAML",
  jwt_scanning: "JWT",
  dnssec_scanning: "DNSSEC",
}

const ran = (n: string) => ({ phase_name: n, label: LABELS[n], status: "ran", reason: null, detail: null, duration_sec: 1 })

const finding = (protocol: string, severity: string) => ({
  protocol,
  severity,
  title: "JWKS key declares alg:none",
  host: "https://idp.example",
  port: 443,
  algorithm: "none",
  description: "",
  remediation: "",
  quantum_risk: "",
})

function cardFor(label: string): HTMLElement {
  const heading = screen.getByText(label)
  const card = heading.closest('[class*="rounded-xl"]')
  expect(card).not.toBeNull()
  return card as HTMLElement
}

afterEach(() => {
  cleanup()
})

describe("IdentityPage — JWT/JWKS card (IDENT-06)", () => {
  it("shows the JWT/JWKS card with a Critical badge for one JWT finding", async () => {
    scanDataReturn = { data: { identity_findings: [finding("JWT", "CRITICAL")] }, loading: false, error: null }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)

    const card = cardFor("JWT/JWKS")
    expect(within(card).getByText("1")).toBeInTheDocument()
    expect(within(card).getByText("Critical")).toBeInTheDocument()
    expect(within(card).getByText("finding")).toBeInTheDocument()
  })

  it("shows Ran on the JWT/JWKS card when jwt_scanning ran with no findings", async () => {
    const phases = ["kerberos_scanning", "saml_scanning", "jwt_scanning", "dnssec_scanning"].map(ran)
    scanDataReturn = { data: { identity_findings: [], coverage: { recorded: true, ran: 4, skipped: 0, phases } }, loading: false, error: null }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)

    const card = cardFor("JWT/JWKS")
    expect(within(card).getByText("Ran")).toBeInTheDocument()
    expect(within(card).queryByText("Not Scanned")).not.toBeInTheDocument()
  })

  it("shows the unexpected-response skip on the JWT/JWKS card as human text", async () => {
    const phases = [
      ran("kerberos_scanning"),
      ran("saml_scanning"),
      { phase_name: "jwt_scanning", label: "JWT", status: "skipped", reason: "unexpected-response", detail: null, duration_sec: null },
      ran("dnssec_scanning"),
    ]
    scanDataReturn = { data: { identity_findings: [], coverage: { recorded: true, ran: 3, skipped: 1, phases } }, loading: false, error: null }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)

    const card = cardFor("JWT/JWKS")
    expect(within(card).getByText("Skipped")).toBeInTheDocument()
    expect(within(card).getByText("a target answered with something other than the expected document")).toBeInTheDocument()
    expect(card.textContent).not.toContain("unexpected-response")
    expect(card.textContent).not.toContain("unexpected_response")
    expect(card.textContent).not.toMatch(/\b[a-z]+[-_][a-z]+(?:[-_][a-z]+)*:/)
  })

  it("lays the four identity cards out in a one, two and four column grid", async () => {
    scanDataReturn = { data: { identity_findings: [] }, loading: false, error: null }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)

    const grid = cardFor("Kerberos").parentElement as HTMLElement
    expect(grid.className).toContain("sm:grid-cols-2")
    expect(grid.className).toContain("xl:grid-cols-4")
    expect(grid.className).not.toContain("md:grid-cols-3")
    expect(document.body.innerHTML).not.toContain("md:grid-cols-3")

    const titles = Array.from(grid.children).map(
      (c) => (c.firstElementChild?.firstElementChild?.textContent ?? "").trim(),
    )
    expect(titles).toEqual(["Kerberos", "SAML/OIDC", "JWT/JWKS", "DNSSEC"])
  })

  it("does not count a BEARER_TOKEN finding on the JWT/JWKS card", async () => {
    scanDataReturn = { data: { identity_findings: [finding("BEARER_TOKEN", "CRITICAL")] }, loading: false, error: null }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)

    const card = cardFor("JWT/JWKS")
    expect(within(card).getByText("0")).toBeInTheDocument()
    expect(within(card).queryByText("Critical")).not.toBeInTheDocument()
  })

  it("shows the exact empty-state sentence for an unexpected-response JWT skip", async () => {
    const detail = "1 of 1 targets answered with something other than the expected document: https://idp.example (unexpected_response: not a JWKS (no keys array))"
    const phases = [
      ran("kerberos_scanning"),
      ran("saml_scanning"),
      ran("dnssec_scanning"),
      { phase_name: "jwt_scanning", label: "JWT", status: "skipped", reason: "unexpected-response", detail, duration_sec: null },
    ]
    scanDataReturn = { data: { identity_findings: [], coverage: { recorded: true, ran: 3, skipped: 1, phases } }, loading: false, error: null }
    const { IdentityPage } = await import("@/pages/identity")
    render(<IdentityPage />)

    const sentence =
      "Skipped (JWT) — 1 of 1 targets answered with something other than the expected document: https://idp.example (not a JWKS (no keys array))"
    const el = screen.getByText(sentence)
    expect(el).toBeInTheDocument()
    expect(el.textContent).not.toContain("unexpected-response")
    expect(el.textContent).not.toContain("unexpected_response")
    expect(el.textContent).not.toMatch(/\b[a-z]+[-_][a-z]+(?:[-_][a-z]+)*:/)
    expect(document.body.textContent).not.toContain("unexpected_response")
  })
})
