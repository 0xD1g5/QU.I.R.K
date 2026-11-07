import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null }

const phase = (phase_name: string, status: string, reason: string | null, detail: string | null = null) => ({
  phase_name, label: phase_name.replace("_scanning", ""), status, reason, detail, duration_sec: null,
})
const cov = (...phases: unknown[]) => ({ recorded: true, ran: 0, skipped: phases.length, phases })

afterEach(() => {
  cleanup()
})

const EMPTY = { dar_findings: [] as unknown[], score: { subscores: { data_at_rest: 0 } } }

async function renderPage(data: unknown) {
  scanDataReturn = { data, loading: false, error: null }
  const { DataAtRestPage } = await import("@/pages/data-at-rest")
  render(<DataAtRestPage />)
}

describe("DataAtRestPage empty states (COVTRUTH-04)", () => {
  it("data at rest vault card shows the recorded missing-credentials reason", async () => {
    await renderPage({ ...EMPTY, coverage: cov(phase("vault_scanning", "skipped", "missing-credentials")) })
    expect(screen.getByText(/missing credentials/)).toBeInTheDocument()
    expect(screen.queryByText(/enable the Vault connector/)).not.toBeInTheDocument()
  })

  it("data at rest object storage card shows internal-target refusal", async () => {
    await renderPage({ ...EMPTY, coverage: cov(phase("s3_scanning", "skipped", "internal-target-refused"), phase("blob_scanning", "skipped", "internal-target-refused")) })
    expect(screen.getAllByText(/internal targets refused by server policy/).length).toBeGreaterThan(0)
  })

  it("data at rest database card shows ran with zero results", async () => {
    await renderPage({ ...EMPTY, coverage: { recorded: true, ran: 1, skipped: 0, phases: [phase("db_scanning", "ran", null)] } })
    expect(screen.getByText(/Ran, 0 results/)).toBeInTheDocument()
  })

  it("data at rest cards fall back to static text without coverage", async () => {
    await renderPage(EMPTY)
    expect(screen.getByText(/enable the DB scanner in your config/)).toBeInTheDocument()
    expect(screen.getByText(/enable the object storage scanner/)).toBeInTheDocument()
    expect(screen.getByText(/enable the Kubernetes scanner/)).toBeInTheDocument()
    expect(screen.getByText(/enable the Vault connector/)).toBeInTheDocument()
  })

  it("database table shows failed targets as failed rows", async () => {
    const row = (host: string, scan_error: string | null) => ({
      category: "database", protocol: "POSTGRESQL", host, port: 5432, severity: "INFO",
      title: scan_error ? "POSTGRESQL connection failed" : "POSTGRESQL ok",
      encryption_at_rest: scan_error ? null : true, tls_in_transit: scan_error ? null : true,
      quantum_risk: null, remediation: null, scan_error,
    })
    await renderPage({ ...EMPTY, dar_findings: [row("a", null), row("b", "connection refused"), row("c", "timed out")] })
    expect(screen.getAllByRole("row").length).toBe(4)
    expect(screen.getAllByLabelText("status: Failed").length).toBe(2)
    expect(screen.getByText("connection refused")).toBeInTheDocument()
  })
})
