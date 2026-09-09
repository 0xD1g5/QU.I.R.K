import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import { PrintCerts } from "@/pages/print"

// Phase 194 DASH-09 / D-13 / D-14 — print-surface coverage: PrintCerts must
// carry the identical copy strings as certificates.tsx (cross-surface guard).

vi.mock("@/hooks/useScanData", () => ({ useScanData: () => ({ data: null, loading: true, error: null }) }))
vi.mock("@/hooks/useQRAMMPrintData", () => ({
  useQRAMMPrintData: () => ({ scoreResult: null, complianceRows: null, loading: true, error: null }),
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

afterEach(() => {
  cleanup()
})

describe("PrintCerts — DASH-09 phantom-cert disclosure (D-13/D-14)", () => {
  it("renders the table and the disclosure line when some endpoints were excluded", () => {
    render(<PrintCerts certs={[makeCert(0), makeCert(1), makeCert(2)]} excludedCount={2} />)
    expect(screen.getByText("2 TLS endpoints failed handshake and are not shown.")).toBeInTheDocument()
    expect(screen.getAllByText("host0.example.com").length).toBeGreaterThan(0)
  })

  it("renders no disclosure text when excludedCount is 0 with certs present", () => {
    render(<PrintCerts certs={[makeCert(0), makeCert(1), makeCert(2)]} excludedCount={0} />)
    expect(screen.queryByText(/failed handshake and are not shown/)).not.toBeInTheDocument()
  })

  it("renders the empty state AND the disclosure line when every TLS endpoint failed", () => {
    render(<PrintCerts certs={[]} excludedCount={5} />)
    expect(screen.getByText("No TLS certificates discovered in this scan.")).toBeInTheDocument()
    expect(screen.getByText("5 TLS endpoints failed handshake and are not shown.")).toBeInTheDocument()
  })

  it("renders the empty state with no disclosure line when nothing was scanned and nothing excluded", () => {
    render(<PrintCerts certs={[]} excludedCount={0} />)
    expect(screen.getByText("No TLS certificates discovered in this scan.")).toBeInTheDocument()
    expect(screen.queryByText(/failed handshake and are not shown/)).not.toBeInTheDocument()
  })
})
