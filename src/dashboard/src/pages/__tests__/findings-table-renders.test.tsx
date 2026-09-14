// Phase 206 Plan 03 (COV-04) — UAT-7-06: Findings Page table renders with
// its documented columns and one row per fixture finding.
//
// `useScanData` is mocked (not `fetchApi`); the real `FindingsPage` is
// rendered so the table structure, not a leaf component, is under test.
import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import type { FindingItem } from "@/types/api"

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: false,
  error: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

function makeFinding(overrides: Partial<FindingItem> = {}): FindingItem {
  return {
    id: 1,
    host: "web01.example.com",
    port: 443,
    severity: "HIGH",
    title: "TLS certificate uses undersized RSA key",
    protocol: "TLS",
    ...overrides,
  }
}

// Kept well under 25 rows so this fixture is never truncated by the
// pagination behaviour that UAT-7-24 tests separately.
const FIXTURE = {
  findings: [
    makeFinding({ id: 1, severity: "CRITICAL", host: "web01.example.com", port: 443, title: "TLS certificate uses undersized RSA key", protocol: "TLS" }),
    makeFinding({ id: 2, severity: "HIGH", host: "web02.example.com", port: 22, title: "SSH server allows weak KEX", protocol: "SSH" }),
    makeFinding({ id: 3, severity: "MEDIUM", host: "web03.example.com", port: 443, title: "Certificate chain incomplete", protocol: "TLS" }),
    makeFinding({ id: 4, severity: "LOW", host: "web04.example.com", port: 8080, title: "HTTP header missing HSTS", protocol: "HTTP" }),
  ],
}

async function renderFindingsPage() {
  const { FindingsPage } = await import("@/pages/findings")
  return render(<FindingsPage />)
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("FindingsPage — table renders (UAT-7-06)", () => {
  it("renders the findings table with its documented columns and one row per fixture finding", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    await renderFindingsPage()

    // UAT-7-06 Pass Criteria names: Severity, Host, Port, Protocol, Finding Title.
    // The current implementation's Title column header is literally "Title".
    for (const name of ["Severity", "Host", "Port", "Protocol", "Title"]) {
      expect(screen.getByRole("columnheader", { name })).toBeInTheDocument()
    }

    // Row count matches the fixture, derived rather than hardcoded.
    const rows = screen.getAllByRole("row")
    // getAllByRole("row") includes the header row; subtract it.
    expect(rows.length - 1).toBe(FIXTURE.findings.length)

    for (const finding of FIXTURE.findings) {
      expect(screen.getByText(finding.title)).toBeInTheDocument()
    }
  })
})
