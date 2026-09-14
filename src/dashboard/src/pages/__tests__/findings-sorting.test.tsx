// Phase 206 Plan 03 (COV-04) — UAT-7-07: Findings Page severity sort toggle.
//
// `useScanData` is mocked (not `fetchApi`); the real `FindingsPage` is
// rendered. Row order is captured before and after each header click and
// compared — a click-happened-only assertion would pass against a no-op
// sort handler, which this case explicitly forbids.
import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
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
    title: "finding",
    protocol: "TLS",
    ...overrides,
  }
}

// Deliberately not in severity order (alphabetical or otherwise) so an
// unsorted table is distinguishable from a sorted one.
const FIXTURE = {
  findings: [
    makeFinding({ id: 1, severity: "MEDIUM", host: "host-medium.example.com", title: "medium finding" }),
    makeFinding({ id: 2, severity: "CRITICAL", host: "host-critical.example.com", title: "critical finding" }),
    makeFinding({ id: 3, severity: "LOW", host: "host-low.example.com", title: "low finding" }),
    makeFinding({ id: 4, severity: "HIGH", host: "host-high.example.com", title: "high finding" }),
  ],
}

async function renderFindingsPage() {
  const { FindingsPage } = await import("@/pages/findings")
  return render(<FindingsPage />)
}

function currentHostOrder(): string[] {
  // Skip the header row; read the Host cell text of each data row in DOM order.
  const rows = screen.getAllByRole("row").slice(1)
  return rows.map((row) => {
    const hostCell = row.querySelectorAll("td")[1]
    return hostCell?.textContent ?? ""
  })
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("FindingsPage — severity sort toggle (UAT-7-07)", () => {
  it("toggles ascending and descending order when the Severity column header is clicked", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    const initialOrder = currentHostOrder()
    expect(initialOrder.length).toBe(FIXTURE.findings.length)

    const severityHeader = screen.getByRole("columnheader", { name: "Severity" })
    await user.click(severityHeader)
    const afterFirstClick = currentHostOrder()

    // A no-op sort handler would leave the order identical to the initial
    // mount order — the first click must actually change row order.
    expect(afterFirstClick).not.toEqual(initialOrder)

    await user.click(severityHeader)
    const afterSecondClick = currentHostOrder()

    // The second click must produce yet another distinguishable order from
    // the first click's result — a real ascending/descending toggle, not a
    // handler that fires but leaves rows in place.
    expect(afterSecondClick).not.toEqual(afterFirstClick)

    // Both post-click orders must be reorderings of the same row set, not a
    // row-count regression.
    expect([...afterFirstClick].sort()).toEqual([...initialOrder].sort())
    expect([...afterSecondClick].sort()).toEqual([...initialOrder].sort())
  })
})
