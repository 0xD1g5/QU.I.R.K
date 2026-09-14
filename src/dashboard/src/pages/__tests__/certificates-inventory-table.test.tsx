import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup, within } from "@testing-library/react"

// UAT-7-10 — Certificates Page — Inventory Table.
//
// Model: components/__tests__/ConnectorsPanel.test.tsx (module-level FIXTURE, vi.mock of the data
// hook, real render()). Mocks @/hooks/useScanData per RESEARCH § Q2 — certificates.tsx has no other
// data seam.
//
// Fixture design: three certificates that differ meaningfully —
//   - `expired.example.com`: cert_not_after in the past -> expired, red date + AlertTriangle icon.
//   - `safe.example.com`: cert_not_after ~400 days out -> muted date, no AlertTriangle icon.
//   - `selfsigned.example.com`: cert_subject === cert_issuer (a self-signed cert by definition),
//     also far from expiry, included for column/row-count coverage.
//
// UAT-7-10's fourth Pass Criteria bullet ("Self-signed certs flagged") is NOT asserted here: reading
// certificates.tsx in full shows no self-signed detection logic anywhere in the component — no
// comparison of cert_subject/cert_issuer, no dedicated flag/badge for it. This is a second,
// independently-discovered absent feature alongside UAT-7-12 (see 206-RED-PROOF-certificates-
// identity.md's Citations section and the companion todo).

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null }

const now = new Date("2027-06-15T00:00:00Z")

function isoDaysFromNow(days: number): string {
  const d = new Date(now.getTime() + days * 86400000)
  return d.toISOString().slice(0, 10)
}

const FIXTURE = {
  certificates: [
    {
      host: "expired.example.com",
      port: 443,
      cert_subject: "CN=expired.example.com",
      cert_issuer: "CN=Test Intermediate CA",
      cert_not_after: isoDaysFromNow(-10), // expired 10 days ago
      cert_pubkey_alg: "RSA",
      cert_pubkey_size: 2048,
      quantum_safety: "Vulnerable",
    },
    {
      host: "safe.example.com",
      port: 8443,
      cert_subject: "CN=safe.example.com",
      cert_issuer: "CN=Test Intermediate CA",
      cert_not_after: isoDaysFromNow(400), // far from expiry
      cert_pubkey_alg: "ECDSA",
      cert_pubkey_size: 256,
      quantum_safety: "At Risk",
    },
    {
      host: "selfsigned.example.com",
      port: 9443,
      cert_subject: "CN=selfsigned.example.com",
      cert_issuer: "CN=selfsigned.example.com", // subject === issuer -> self-signed
      cert_not_after: isoDaysFromNow(400),
      cert_pubkey_alg: "RSA",
      cert_pubkey_size: 4096,
      quantum_safety: "Unknown",
    },
  ],
  excluded_cert_count: 0,
}

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe("CertificatesPage — inventory table (UAT-7-10)", () => {
  it("renders the certificate inventory table with its documented columns and expiry and self-signed indicators", async () => {
    vi.useFakeTimers()
    vi.setSystemTime(now)
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)

    // Documented columns (UAT-7-10 Pass Criteria: "Columns: Subject, Issuer, Expiry, Algorithm,
    // Quantum Safety" — certificates.tsx additionally renders Host and Port ahead of Subject).
    const table = screen.getByRole("table")
    for (const name of ["Host", "Port", "Subject CN", "Issuer", "Expiry", "Algorithm", "Quantum Safety"]) {
      expect(within(table).getByRole("columnheader", { name })).toBeInTheDocument()
    }

    // One row per fixture certificate.
    const rows = within(table).getAllByRole("row")
    expect(rows.length - 1).toBe(FIXTURE.certificates.length) // -1 for the header row
    for (const cert of FIXTURE.certificates) {
      expect(within(table).getAllByText(cert.host).length).toBeGreaterThan(0)
    }

    // Expired-cert visual indicator: the AlertTriangle icon renders inside the expired cert's
    // Expiry cell (daysToExpiry < 30) and is absent from the far-from-expiry certs' Expiry cells.
    const expiredRow = within(table).getAllByText("expired.example.com")[0].closest("tr")
    const safeRow = within(table).getAllByText("safe.example.com")[0].closest("tr")
    const selfSignedRow = within(table).getAllByText("selfsigned.example.com")[0].closest("tr")
    if (!expiredRow || !safeRow || !selfSignedRow) throw new Error("expected all three fixture rows to render")

    const expiredExpiryCell = within(expiredRow).getAllByRole("cell")[4] // Host, Port, Subject, Issuer, Expiry
    const safeExpiryCell = within(safeRow).getAllByRole("cell")[4]
    const selfSignedExpiryCell = within(selfSignedRow).getAllByRole("cell")[4]

    expect(expiredExpiryCell.querySelector("svg")).not.toBeNull()
    expect(safeExpiryCell.querySelector("svg")).toBeNull()
    expect(selfSignedExpiryCell.querySelector("svg")).toBeNull()

    // Negative half: the indicator is conditional, not rendered unconditionally on every row.
    const allExpiryCells = rows.slice(1).map((r) => within(r).getAllByRole("cell")[4])
    const iconCount = allExpiryCells.filter((c) => c.querySelector("svg") !== null).length
    expect(iconCount).toBe(1)

    // Self-signed flagging is NOT asserted here — see this file's header comment and the
    // 206-RED-PROOF-certificates-identity.md Citations section for the absence finding.
  })
})
