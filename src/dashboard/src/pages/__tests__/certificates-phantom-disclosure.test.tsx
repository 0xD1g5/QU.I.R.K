import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import { PrintCerts } from "@/pages/print"

// Phase 194 WR-01: the phantom-cert empty-state string and disclosure line
// must be byte-identical across the dashboard (certificates.tsx) and print
// (print.tsx) surfaces (D-13/D-14). These are the single canonical strings
// both surfaces are asserted against below.
const EMPTY_STATE = "No TLS certificates discovered in this scan."
const DISCLOSURE = (n: number) => `${n} TLS endpoints failed handshake and are not shown.`

// Phase 194 DASH-09 / D-13 / D-14 — dashboard-surface coverage: the phantom-cert
// disclosure line and the locked empty-state text.

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: true,
  error: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

function makeCert(i: number) {
  return {
    host: `host${i}.example.com`,
    port: 443,
    cert_subject: `CN=host${i}.example.com`,
    cert_issuer: "CN=Test CA",
    cert_not_after: "2027-01-01",
    cert_pubkey_alg: "RSA",
    cert_pubkey_size: 2048,
    quantum_safety: "Vulnerable",
  }
}

function makeFixture(certCount: number, excludedCertCount: number) {
  return {
    certificates: Array.from({ length: certCount }, (_, i) => makeCert(i)),
    excluded_cert_count: excludedCertCount,
  }
}

afterEach(() => {
  cleanup()
})

describe("CertificatesPage — DASH-09 phantom-cert disclosure (D-13/D-14)", () => {
  it("renders the table and the disclosure line when some endpoints were excluded", async () => {
    scanDataReturn = { data: makeFixture(3, 2), loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)
    expect(screen.getByText("2 TLS endpoints failed handshake and are not shown.")).toBeInTheDocument()
    expect(screen.getAllByText("host0.example.com").length).toBeGreaterThan(0)
  })

  it("renders no disclosure text when excluded_cert_count is 0 with certs present", async () => {
    scanDataReturn = { data: makeFixture(3, 0), loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)
    expect(screen.queryByText(/failed handshake and are not shown/)).not.toBeInTheDocument()
  })

  it("renders the empty state AND the disclosure line when every TLS endpoint failed (2026-09-05 scenario)", async () => {
    scanDataReturn = { data: makeFixture(0, 5), loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)
    expect(screen.getByText("No TLS certificates discovered in this scan.")).toBeInTheDocument()
    expect(screen.getByText("5 TLS endpoints failed handshake and are not shown.")).toBeInTheDocument()
  })

  it("renders the empty state with no disclosure line when nothing was scanned and nothing excluded", async () => {
    scanDataReturn = { data: makeFixture(0, 0), loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)
    expect(screen.getByText("No TLS certificates discovered in this scan.")).toBeInTheDocument()
    expect(screen.queryByText(/failed handshake and are not shown/)).not.toBeInTheDocument()
  })
})

describe("Phantom-cert copy is byte-identical across dashboard and print surfaces (WR-01)", () => {
  it("renders the same empty-state string and disclosure line on both surfaces", async () => {
    // Dashboard surface — empty-with-exclusions.
    scanDataReturn = { data: makeFixture(0, 5), loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    const { unmount } = render(<CertificatesPage />)
    expect(screen.getByText(EMPTY_STATE)).toBeInTheDocument()
    expect(screen.getByText(DISCLOSURE(5))).toBeInTheDocument()
    unmount()

    // Print surface — same input, must render the identical two strings.
    render(<PrintCerts certs={[]} excludedCount={5} />)
    expect(screen.getByText(EMPTY_STATE)).toBeInTheDocument()
    expect(screen.getByText(DISCLOSURE(5))).toBeInTheDocument()
  })
})
