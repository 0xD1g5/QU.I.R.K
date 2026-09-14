// Phase 206 Plan 06 (COV-04) — UAT-7-26: CBOM Page — Quantum Safety Filter.
//
// `useScanData` is mocked (not `fetchApi`); the real `CbomPage` is rendered
// with `cytoscape`/`cytoscape-cose-bilkent` mocked so the graph tab's
// registration-on-import doesn't crash jsdom, even though this case only
// exercises the table tab.
//
// The filter is driven through the rendered `Select` control with
// `user-event`, not by poking filter state directly — the case is about the
// dropdown narrowing the table.
import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { CbomComponent } from "@/types/api"

vi.mock("cytoscape", () => {
  const mockCyCore = {
    on: vi.fn(),
    destroy: vi.fn(),
    zoom: vi.fn(() => 1),
    fit: vi.fn(),
  }
  const ctor = vi.fn(() => mockCyCore) as unknown as {
    (...args: unknown[]): typeof mockCyCore
    use: (...args: unknown[]) => void
  }
  ctor.use = vi.fn()
  return { default: ctor }
})
vi.mock("cytoscape-cose-bilkent", () => ({ default: {} }))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: false,
  error: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

function makeComponent(overrides: Partial<CbomComponent> = {}): CbomComponent {
  return {
    algorithm: "algorithm",
    type: "cipher",
    key_size: 256,
    quantum_safety: "Safe",
    source_systems: ["host-a"],
    ...overrides,
  }
}

const FIXTURE_COMPONENTS: CbomComponent[] = [
  makeComponent({ algorithm: "AES-256-GCM", quantum_safety: "Safe", source_systems: ["host-a"] }),
  makeComponent({ algorithm: "RSA-2048", quantum_safety: "Vulnerable", source_systems: ["host-b"] }),
  makeComponent({ algorithm: "SHA-256", quantum_safety: "Safe", source_systems: ["host-c"] }),
]

const FIXTURE = {
  cbom_components: FIXTURE_COMPONENTS,
  hardware_devices: [],
}

describe("CbomPage — UAT-7-26 quantum-safety filter", () => {
  it("filters the CBOM algorithm table to the selected quantum-safety classification", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const user = userEvent.setup()

    const { CbomPage } = await import("@/pages/cbom")
    render(<CbomPage />)

    // Sanity: all three fixture rows present before filtering.
    expect(await screen.findByText("AES-256-GCM")).toBeInTheDocument()
    expect(screen.getByText("RSA-2048")).toBeInTheDocument()
    expect(screen.getByText("SHA-256")).toBeInTheDocument()

    await user.click(screen.getByRole("combobox", { name: "Filter by quantum safety" }))
    await user.click(await screen.findByRole("option", { name: "Vulnerable" }))

    // Selected classification's row remains.
    expect(screen.getByText("RSA-2048")).toBeInTheDocument()
    // Other classification's rows are gone, not merely unasserted.
    expect(screen.queryByText("AES-256-GCM")).not.toBeInTheDocument()
    expect(screen.queryByText("SHA-256")).not.toBeInTheDocument()
  })
})
