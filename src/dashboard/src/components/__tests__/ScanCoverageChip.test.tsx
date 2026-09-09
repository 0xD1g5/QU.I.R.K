// Phase 192 Plan 09 (OBS-02 / D-12) — coverage chips + expandable detail.
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { ScanCoverageChip } from "../ScanCoverageChip"

const mockFetchApi = vi.fn()

vi.mock("@/lib/api", () => ({
  fetchApi: (...args: unknown[]) => mockFetchApi(...args),
}))

function jsonResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    json: async () => body,
  }
}

afterEach(() => {
  mockFetchApi.mockReset()
})

describe("ScanCoverageChip", () => {
  it("renders '{N} ran / {M} skipped' chip pair with no detail table until toggled", async () => {
    mockFetchApi.mockResolvedValue(
      jsonResponse({
        recorded: true,
        ran: 3,
        skipped: 2,
        phases: [
          { phase_name: "tls_scanning", label: "TLS", status: "ran", reason: null, detail: null, duration_sec: 4.2 },
          { phase_name: "vault_scanning", label: "Vault", status: "skipped", reason: "missing-credentials", detail: "connectors.vault_token / VAULT_TOKEN not set", duration_sec: null },
        ],
      }),
    )
    render(<ScanCoverageChip scanRunId="run-1" />)

    expect(await screen.findByText("3 ran")).toBeInTheDocument()
    expect(screen.getByText("2 skipped")).toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
  })

  it("reveals per-phase detail rows when 'Show detail' is activated", async () => {
    mockFetchApi.mockResolvedValue(
      jsonResponse({
        recorded: true,
        ran: 1,
        skipped: 1,
        phases: [
          { phase_name: "tls_scanning", label: "TLS", status: "ran", reason: null, detail: null, duration_sec: 4.2 },
          { phase_name: "vault_scanning", label: "Vault", status: "skipped", reason: "missing-credentials", detail: "connectors.vault_token / VAULT_TOKEN not set", duration_sec: null },
        ],
      }),
    )
    render(<ScanCoverageChip scanRunId="run-1" />)

    const trigger = await screen.findByText("Show detail")
    fireEvent.click(trigger)

    expect(await screen.findByText("TLS — ran in 4.2s")).toBeInTheDocument()
    expect(
      screen.getByText(
        "Vault — skipped: missing-credentials (connectors.vault_token / VAULT_TOKEN not set)",
      ),
    ).toBeInTheDocument()
  })

  it("renders the honest not-recorded notice and no chips/table for an unrecorded scan", async () => {
    mockFetchApi.mockResolvedValue(
      jsonResponse({ recorded: false, ran: 0, skipped: 0, phases: [] }),
    )
    render(<ScanCoverageChip scanRunId="pre-v521-run" />)

    expect(await screen.findByText("Coverage data not recorded")).toBeInTheDocument()
    expect(
      screen.getByText(
        "This scan predates per-phase coverage tracking (pre-v5.21). Re-scan to get full coverage detail.",
      ),
    ).toBeInTheDocument()
    expect(screen.queryByText(/ran$/)).not.toBeInTheDocument()
    expect(screen.queryByText(/skipped$/)).not.toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
  })

  it("renders nothing (no fabricated '0 ran / 0 skipped') on a failed fetch", async () => {
    mockFetchApi.mockResolvedValue(jsonResponse({}, false, 500))
    const { container } = render(<ScanCoverageChip scanRunId="run-err" />)

    await waitFor(() => expect(mockFetchApi).toHaveBeenCalled())
    await waitFor(() => expect(container).toBeEmptyDOMElement())
    expect(screen.queryByText("0 ran")).not.toBeInTheDocument()
  })

  it("colors each skip reason's status cell per the UI-spec token mapping, and ran rows --ds-ok", async () => {
    mockFetchApi.mockResolvedValue(
      jsonResponse({
        recorded: true,
        ran: 1,
        skipped: 1,
        phases: [
          { phase_name: "tls_scanning", label: "TLS", status: "ran", reason: null, detail: null, duration_sec: 4.2 },
          { phase_name: "vault_scanning", label: "Vault", status: "skipped", reason: "missing-credentials", detail: "VAULT_TOKEN not set", duration_sec: null },
        ],
      }),
    )
    render(<ScanCoverageChip scanRunId="run-1" />)
    fireEvent.click(await screen.findByText("Show detail"))

    const ranStatusCell = await screen.findByText("ran")
    expect(ranStatusCell.className).toContain("--ds-ok")

    const skippedStatusCell = screen.getByText("skipped: missing-credentials")
    expect(skippedStatusCell.className).toContain("--ds-high")
  })
})
