/**
 * COUNT-06 / 237 UI-SPEC U3: Scan History marks running and incomplete scans and
 * withholds their score and counts; a running scan cannot be selected for compare.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

let listReturn: { sessions: unknown[]; loading: boolean; error: string | null }
vi.mock("@/hooks/useScanList", () => ({ useScanList: () => listReturn }))
vi.mock("@/components/ScanCoverageChip", () => ({ ScanCoverageChip: () => null }))

const base = {
  total_endpoints: 5,
  profile: "standard",
  calibration: null,
  target: "10.0.0.1",
  rating: "FAIR",
}
const counts = { high: 4, medium: 3, low: 2 }
const NOTE = "Scores and finding counts are shown only for completed scans."

async function renderPage(sessions: unknown[]) {
  listReturn = { sessions, loading: false, error: null }
  const { ScanHistoryPage } = await import("@/pages/scan-history")
  return render(
    <MemoryRouter>
      <ScanHistoryPage />
    </MemoryRouter>,
  )
}

afterEach(() => cleanup())

describe("ScanHistoryPage status (COUNT-06)", () => {
  it("badges running and incomplete rows, withholds numbers, disables only the running checkbox", async () => {
    const view = await renderPage([
      { ...base, scan_id: "c", scanned_at: "2026-09-13T10:00:00Z", score: 61, finding_counts: counts, status: "complete" },
      { ...base, scan_id: "r", scanned_at: "2026-09-13T11:00:00Z", score: 48, finding_counts: counts, status: "running" },
      { ...base, scan_id: "i", scanned_at: "2026-09-13T12:00:00Z", score: 40, finding_counts: counts, status: "incomplete" },
    ])
    const running = screen.getByLabelText("status: Running")
    expect(running.textContent).toBe("Running")
    const incomplete = screen.getByLabelText("status: Incomplete")
    expect(incomplete.textContent).toBe("Incomplete")
    const dashes = screen.getAllByLabelText("not counted")
    expect(dashes).toHaveLength(6)
    dashes.forEach((d) => expect(d.textContent).toBe("—"))
    // The two withheld scores (48, 40) never render; the complete row's do.
    expect(view.container.textContent).not.toContain("48")
    expect(view.container.textContent).toContain("61")

    const boxes = screen.getAllByRole("checkbox")
    expect(boxes).toHaveLength(3)
    const disabled = boxes.filter((b) => (b as HTMLButtonElement).disabled)
    expect(disabled).toHaveLength(1)
    expect(disabled[0].getAttribute("aria-label")).toMatch(/^Scan from .+ is still running and cannot be compared$/)
    expect(screen.getByText(NOTE)).toBeTruthy()
  })

  it("shows no note and real counts when every row is complete or status is absent", async () => {
    const view = await renderPage([
      { ...base, scan_id: "c", scanned_at: "2026-09-13T10:00:00Z", score: 61, finding_counts: counts, status: "complete" },
      { ...base, scan_id: "o", scanned_at: "2026-09-13T09:00:00Z", score: 55, finding_counts: counts },
    ])
    expect(screen.queryByText(NOTE)).toBeNull()
    expect(screen.queryByLabelText("status: Running")).toBeNull()
    expect(screen.queryAllByLabelText("not counted")).toHaveLength(0)
    expect(view.container.textContent).toContain("55")
    expect(screen.getAllByRole("checkbox").every((b) => !(b as HTMLButtonElement).disabled)).toBe(true)
  })
})
