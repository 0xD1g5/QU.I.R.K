// Phase 206 Plan 04 (COV-04) — UAT-7-08: Findings Page severity filtering.
//
// `useScanData` is mocked (not `fetchApi`); the real `FindingsPage` is
// rendered and the real Radix Select control is driven with `user-event`.
// Both halves of the case are asserted: the excluded-severity rows must be
// GONE and the matching rows must remain — an "included rows are present"
// assertion alone would pass against a filter that does nothing.
//
// Divergence note (recorded in red-proof/206-RED-PROOF-findings-b.md):
// UAT-7-08's Steps say "Type `CRITICAL` in the filter", but the product
// implements severity filtering as a Radix Select dropdown
// (findings.tsx:220-230), not a text input. The dropdown is the control the
// case's Pass Criteria describe the effect of, so it is what this test
// drives; the "type" wording is not satisfiable against this product.
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

// Two CRITICAL rows and two non-CRITICAL rows: filtering to CRITICAL must
// both keep a set of rows and remove a set of rows, so neither half of the
// assertion can pass vacuously.
const CRITICAL_HOSTS = ["crit-a.example.com", "crit-b.example.com"]
const OTHER_HOSTS = ["medium-a.example.com", "low-a.example.com"]

const FIXTURE = {
  findings: [
    makeFinding({ id: 1, severity: "CRITICAL", host: CRITICAL_HOSTS[0], title: "critical finding a" }),
    makeFinding({ id: 2, severity: "MEDIUM", host: OTHER_HOSTS[0], title: "medium finding a" }),
    makeFinding({ id: 3, severity: "CRITICAL", host: CRITICAL_HOSTS[1], title: "critical finding b" }),
    makeFinding({ id: 4, severity: "LOW", host: OTHER_HOSTS[1], title: "low finding a" }),
  ],
}

async function renderFindingsPage() {
  const { FindingsPage } = await import("@/pages/findings")
  return render(<FindingsPage />)
}

function currentHostSet(): string[] {
  // Skip the header row; read the Host cell of each data row.
  const rows = screen.getAllByRole("row").slice(1)
  return rows.map((row) => row.querySelectorAll("td")[1]?.textContent ?? "").sort()
}

async function chooseSeverity(user: ReturnType<typeof userEvent.setup>, label: string) {
  await user.click(screen.getByRole("combobox", { name: "Filter by severity" }))
  const options = await screen.findAllByRole("option")
  const target = options.find((o) => (o.textContent ?? "") === label)
  expect(target, `severity option ${label} should exist`).toBeDefined()
  await user.click(target!)
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("FindingsPage — severity filtering (UAT-7-08)", () => {
  it("narrows the findings table to matching rows when a severity filter is applied", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    // Pre-filter: every fixture row is visible.
    const beforeFilter = currentHostSet()
    expect(beforeFilter).toEqual([...CRITICAL_HOSTS, ...OTHER_HOSTS].sort())

    await chooseSeverity(user, "CRITICAL")

    const afterFilter = currentHostSet()
    // Both halves are required: the matching rows remain...
    expect(afterFilter).toEqual([...CRITICAL_HOSTS].sort())
    // ...and the excluded-severity rows are gone from the table entirely.
    for (const host of OTHER_HOSTS) {
      expect(screen.queryByText(host)).toBeNull()
    }
    // Row count strictly decreased (the case's second Pass Criterion).
    expect(afterFilter.length).toBeLessThan(beforeFilter.length)

    // Clearing the filter restores all rows (the case's third Pass Criterion).
    await chooseSeverity(user, "All Severities")
    expect(currentHostSet()).toEqual(beforeFilter)
  })
})
