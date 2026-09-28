import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup, within, fireEvent } from "@testing-library/react"

// UAT-7-12 — Certificates Page — Expiry column sort (UIFIX-01).
//
// Model: certificates-inventory-table.test.tsx (module-level FIXTURE, vi.mock of the data hook,
// real render()). Mocks @/hooks/useScanData per RESEARCH § Q2 — certificates.tsx has no other
// data seam.
//
// Fixture design (D-07): the fixture is deliberately NOT rendered in chronological DOM order, and
// includes a pair whose chronological order and whose `formatDateOnly` STRING order disagree —
// "Jan 4, 2027" sorts before "Sep 9, 2026" lexicographically (J < S) even though Sep 2026 is
// chronologically EARLIER than Jan 2027. A sort implemented over the display string would pass a
// naive smoke test and still be wrong; Test 3 below is the one that would catch it.

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null }

const FIXTURE = {
  certificates: [
    {
      // Chronologically LATEST (2027-01-04) but lexicographically EARLIEST display string
      // ("Jan 4, 2027" < "Sep 9, 2026") — the D-07 disagreement pair, part 1.
      host: "jan2027.example.com",
      port: 443,
      cert_subject: "CN=jan2027.example.com",
      cert_issuer: "CN=Test Intermediate CA",
      cert_not_after: "2027-01-04",
      cert_pubkey_alg: "RSA",
      cert_pubkey_size: 2048,
      quantum_safety: "Safe",
    },
    {
      // No expiry at all — must sort LAST in both ascending and descending order (Test 4).
      host: "noexpiry.example.com",
      port: 8443,
      cert_subject: "CN=noexpiry.example.com",
      cert_issuer: "CN=Test Intermediate CA",
      cert_not_after: null,
      cert_pubkey_alg: "ECDSA",
      cert_pubkey_size: 256,
      quantum_safety: "Unknown",
    },
    {
      // Chronologically EARLIEST of the three dated certs (2026-03-15).
      host: "mar2026.example.com",
      port: 9443,
      cert_subject: "CN=mar2026.example.com",
      cert_issuer: "CN=Test Intermediate CA",
      cert_not_after: "2026-03-15",
      cert_pubkey_alg: "RSA",
      cert_pubkey_size: 4096,
      quantum_safety: "At Risk",
    },
    {
      // Chronologically MIDDLE (2026-09-09) but lexicographically LATEST display string
      // ("Sep 9, 2026" > "Jan 4, 2027") — the D-07 disagreement pair, part 2.
      host: "sep2026.example.com",
      port: 1443,
      cert_subject: "CN=sep2026.example.com",
      cert_issuer: "CN=Test Intermediate CA",
      cert_not_after: "2026-09-09",
      cert_pubkey_alg: "ECDSA",
      cert_pubkey_size: 384,
      quantum_safety: "Vulnerable",
    },
  ],
  excluded_cert_count: 0,
}

// Chronological ascending order of hosts (null-expiry cert last).
const ASCENDING_HOSTS = [
  "mar2026.example.com",
  "sep2026.example.com",
  "jan2027.example.com",
  "noexpiry.example.com",
]

// Chronological descending order of hosts (null-expiry cert STILL last, per Test 4).
const DESCENDING_HOSTS = [
  "jan2027.example.com",
  "sep2026.example.com",
  "mar2026.example.com",
  "noexpiry.example.com",
]

// Lexicographic-string-sort ascending order — what a display-string sort would WRONGLY produce.
// If the implementation ever regresses to sorting on the formatted string, Test 3 would observe
// this order instead of ASCENDING_HOSTS.
const WRONG_LEXICOGRAPHIC_ASCENDING_HOSTS = [
  "jan2027.example.com", // "Jan 4, 2027"
  "noexpiry.example.com", // "—" sorts before letters
  "mar2026.example.com", // "Mar 15, 2026"
  "sep2026.example.com", // "Sep 9, 2026"
]

function hostsInDomOrder(): string[] {
  const table = screen.getByRole("table")
  const rows = within(table).getAllByRole("row").slice(1) // drop header row
  return rows.map((row) => within(row).getAllByRole("cell")[0].textContent ?? "")
}

afterEach(() => {
  cleanup()
})

describe("CertificatesPage — Expiry column sort (UAT-7-12)", () => {
  it("sorts the certificate table ascending by expiry after one click on the Expiry header", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)

    const table = screen.getByRole("table")
    const expiryHeader = within(table).getByRole("columnheader", { name: "Expiry" })
    fireEvent.click(expiryHeader)

    expect(hostsInDomOrder()).toEqual(ASCENDING_HOSTS)
  })

  it("reverses to descending expiry order on a second click of the Expiry header", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)

    const table = screen.getByRole("table")
    const expiryHeader = within(table).getByRole("columnheader", { name: "Expiry" })
    fireEvent.click(expiryHeader)
    fireEvent.click(expiryHeader)

    expect(hostsInDomOrder()).toEqual(DESCENDING_HOSTS)
  })

  it("sorts on the parsed Date, not the formatted display string (D-07 disagreement guard)", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)

    const table = screen.getByRole("table")
    const expiryHeader = within(table).getByRole("columnheader", { name: "Expiry" })
    fireEvent.click(expiryHeader)

    const order = hostsInDomOrder()
    expect(order).toEqual(ASCENDING_HOSTS)
    expect(order).not.toEqual(WRONG_LEXICOGRAPHIC_ASCENDING_HOSTS)
  })

  it("sorts the null-expiry certificate to the end in both ascending and descending order", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)

    const table = screen.getByRole("table")
    const expiryHeader = within(table).getByRole("columnheader", { name: "Expiry" })

    fireEvent.click(expiryHeader) // ascending
    expect(hostsInDomOrder().at(-1)).toBe("noexpiry.example.com")

    fireEvent.click(expiryHeader) // descending
    expect(hostsInDomOrder().at(-1)).toBe("noexpiry.example.com")
  })

  it("exposes aria-sort as none, then ascending, then descending across two clicks", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const { CertificatesPage } = await import("@/pages/certificates")
    render(<CertificatesPage />)

    const table = screen.getByRole("table")
    const expiryHeader = within(table).getByRole("columnheader", { name: "Expiry" })

    expect(expiryHeader).toHaveAttribute("aria-sort", "none")
    fireEvent.click(expiryHeader)
    expect(expiryHeader).toHaveAttribute("aria-sort", "ascending")
    fireEvent.click(expiryHeader)
    expect(expiryHeader).toHaveAttribute("aria-sort", "descending")
  })
})
