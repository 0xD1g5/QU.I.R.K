/**
 * COUNT-03 / 237 UI-SPEC U1: Compare Added/Removed rows identify the finding
 * (Port + Finding columns) and fall back to an em dash when the API omits them.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

let compareReturn: { data: unknown; loading: boolean; error: string | null }
vi.mock("@/hooks/useCompareData", () => ({ useCompareData: () => compareReturn }))

const summary = (id: string) => ({
  scan_id: id,
  scanned_at: "2026-09-13T23:22:00Z",
  score: 50,
  subscores: {},
  rating: "FAIR",
})

function makeData(added: unknown[], removed: unknown[]) {
  return {
    scan_a: summary("a"),
    scan_b: summary("b"),
    score_delta: 0,
    subscore_deltas: {},
    added_findings: added,
    removed_findings: removed,
    changed_endpoints: [],
    endpoints_only_in_a: [],
    endpoints_only_in_b: [],
    hardware_drift: [],
  }
}

async function renderCompare(added: unknown[], removed: unknown[]) {
  compareReturn = { data: makeData(added, removed), loading: false, error: null }
  const { ComparePage } = await import("@/pages/compare")
  return render(
    <MemoryRouter initialEntries={["/compare?a=a&b=b"]}>
      <ComparePage />
    </MemoryRouter>,
  )
}

afterEach(() => cleanup())

describe("ComparePage finding identity (COUNT-03)", () => {
  it("renders Port and Finding columns with title and port values", async () => {
    const view = await renderCompare(
      [{ host: "h1", protocol: "HTTP", severity: "HIGH", title: "Unencrypted HTTP service", port: 80 }],
      [{ host: "h2", protocol: null, severity: "MEDIUM", title: null, port: null, description: null }],
    )
    const tables = view.container.querySelectorAll("table")
    expect(tables).toHaveLength(2)
    for (const t of Array.from(tables)) {
      const heads = Array.from(t.querySelectorAll("th")).map((h) => h.textContent)
      expect(heads).toEqual(["Severity", "Host", "Port", "Protocol", "Finding"])
    }
    const added = within(tables[0] as HTMLElement)
    expect(added.getByText("Unencrypted HTTP service")).toBeTruthy()
    expect(added.getByText("80")).toBeTruthy()
    const removedCells = Array.from(tables[1].querySelectorAll("tbody tr td")).map((c) => c.textContent)
    // Severity, Host, Port, Protocol, Finding
    expect(removedCells).toEqual(["MEDIUM", "h2", "—", "—", "—"])
  })

  it("falls back to description when title is absent and shows both when they differ", async () => {
    const view = await renderCompare(
      [
        { host: "h1", severity: "LOW", description: "legacy text" },
        { host: "h3", severity: "LOW", title: "Short title", description: "Longer description" },
      ],
      [],
    )
    expect(view.getByText("legacy text")).toBeTruthy()
    expect(view.getByText("Short title")).toBeTruthy()
    const desc = view.getByText("Longer description")
    expect(desc.className).toContain("text-xs")
  })
})
