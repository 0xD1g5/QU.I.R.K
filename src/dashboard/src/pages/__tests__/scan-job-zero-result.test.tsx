/**
 * Phase 121-01 — scan-job zero-result terminal message stubs (PORT-09, PORT-10).
 *
 * Tests are intentionally RED: the zero-result detection + terminal message
 * does not exist yet. These stubs define the sampling points for Plans 03–04
 * which will make them green.
 *
 * Covers:
 * - Completed job with zeroResult=true shows "no crypto endpoints" / "no endpoints" message (PORT-09)
 * - Completed job with zeroResult=false does NOT show zero-result message (PORT-10)
 */
import { describe, it, expect, vi } from "vitest"
import { render } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"

// Mock useJobStatus so we can control returned state without network
vi.mock("@/hooks/useJobStatus", () => ({
  useJobStatus: vi.fn(),
}))

// Mock useSelectedScan (navigation side-effects)
vi.mock("@/hooks/useSelectedScan", () => ({
  useSelectedScan: () => ({ selectedScanId: null, setSelectedScanId: vi.fn() }),
}))

// Mock fetchApi (cancel button, etc.)
vi.mock("@/lib/api", () => ({
  fetchApi: vi.fn().mockResolvedValue({ ok: true }),
}))

import { useJobStatus } from "@/hooks/useJobStatus"
import { ScanJobPage } from "@/pages/scan-job"

const mockUseJobStatus = useJobStatus as ReturnType<typeof vi.fn>

/**
 * Minimal JobStatus-shaped data for a completed job with zero endpoints.
 * Plan 04 will add zeroResult as a hook return shape; for now we drive it
 * via the `zeroResult: true` field alongside `kind: "ok"` / `data.status: "completed"`.
 */
const COMPLETED_ZERO: ReturnType<typeof useJobStatus> = {
  kind: "ok",
  zeroResult: true,
  data: {
    job_id: "job-abc-123",
    status: "completed",
    current_stage: null,
    started_at: "2026-06-11T10:00:00Z",
    completed_at: "2026-06-11T10:05:00Z",
    scan_run_id: "2026-06-11T10:00:00Z",
    error_message: null,
    stage_index: 7,
    stage_total: 7,
  },
} as unknown as ReturnType<typeof useJobStatus>

const COMPLETED_NONZERO: ReturnType<typeof useJobStatus> = {
  kind: "ok",
  zeroResult: false,
  data: {
    job_id: "job-abc-456",
    status: "completed",
    current_stage: null,
    started_at: "2026-06-11T10:00:00Z",
    completed_at: "2026-06-11T10:05:00Z",
    scan_run_id: "2026-06-11T10:00:00Z",
    error_message: null,
    stage_index: 7,
    stage_total: 7,
  },
} as unknown as ReturnType<typeof useJobStatus>

function renderJobPage(jobId = "job-abc-123") {
  return render(
    <MemoryRouter initialEntries={[`/scan/jobs/${jobId}`]}>
      <Routes>
        <Route path="/scan/jobs/:jobId" element={<ScanJobPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe("ScanJobPage — zero-result terminal message (PORT-09, PORT-10)", () => {
  it("PORT-09: shows zero-result terminal message when job completed with zero endpoints", () => {
    mockUseJobStatus.mockReturnValue(COMPLETED_ZERO)
    renderJobPage()

    // Must render some variant of "no crypto endpoints" or "no endpoints found" (case-insensitive)
    const body = document.body.textContent?.toLowerCase() ?? ""
    const hasZeroMsg =
      body.includes("no crypto endpoints") || body.includes("no endpoints found")
    expect(hasZeroMsg).toBe(true)
  })

  it("PORT-10: does NOT show zero-result message when job completed with non-zero endpoints", () => {
    mockUseJobStatus.mockReturnValue(COMPLETED_NONZERO)
    renderJobPage("job-abc-456")

    const body = document.body.textContent?.toLowerCase() ?? ""
    const hasZeroMsg =
      body.includes("no crypto endpoints") || body.includes("no endpoints found")
    expect(hasZeroMsg).toBe(false)
  })
})
