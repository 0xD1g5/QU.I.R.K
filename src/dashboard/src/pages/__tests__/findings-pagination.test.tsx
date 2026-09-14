// Phase 206 Plan 03 (COV-04) — UAT-7-24: Findings Page pagination at 25 rows
// per page, advancing with the Next control.
//
// `useScanData` is mocked (not `fetchApi`); the real `FindingsPage` is
// rendered. Page size is read from one named constant so the assertion and
// the fixture size cannot silently drift apart.
import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { FindingItem } from "@/types/api"

// Mirrors findings.tsx's `initialState.pagination.pageSize`.
const PAGE_SIZE = 25

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: false,
  error: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

function makeFinding(index: number): FindingItem {
  return {
    id: index,
    host: `host-${index}.example.com`,
    port: 443,
    severity: "MEDIUM",
    title: `finding number ${index}`,
    protocol: "TLS",
  }
}

// Strictly more than one page, generated rather than hand-listed.
const TOTAL_FINDINGS = PAGE_SIZE + 2
const FIXTURE = {
  findings: Array.from({ length: TOTAL_FINDINGS }, (_, i) => makeFinding(i + 1)),
}

async function renderFindingsPage() {
  const { FindingsPage } = await import("@/pages/findings")
  return render(<FindingsPage />)
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("FindingsPage — pagination (UAT-7-24)", () => {
  it("paginates the findings table at 25 rows per page and advances with the next control", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    // Page 1: exactly PAGE_SIZE data rows.
    const page1Rows = screen.getAllByRole("row").slice(1)
    expect(page1Rows.length).toBe(PAGE_SIZE)
    expect(screen.getByText(FIXTURE.findings[0].host)).toBeInTheDocument()
    expect(screen.queryByText(FIXTURE.findings[PAGE_SIZE].host)).not.toBeInTheDocument()

    // Page-count indicator reflects the fixture size: ceil(27/25) = 2 pages.
    const expectedPageCount = Math.ceil(TOTAL_FINDINGS / PAGE_SIZE)
    expect(screen.getByText(`Page 1 of ${expectedPageCount}`)).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Next" }))

    // Page 2: the remainder renders, and page 1's first row disappears.
    const page2Rows = screen.getAllByRole("row").slice(1)
    expect(page2Rows.length).toBe(TOTAL_FINDINGS - PAGE_SIZE)
    expect(screen.getByText(FIXTURE.findings[PAGE_SIZE].host)).toBeInTheDocument()
    expect(screen.queryByText(FIXTURE.findings[0].host)).not.toBeInTheDocument()
    expect(screen.getByText(`Page 2 of ${expectedPageCount}`)).toBeInTheDocument()
  })
})
