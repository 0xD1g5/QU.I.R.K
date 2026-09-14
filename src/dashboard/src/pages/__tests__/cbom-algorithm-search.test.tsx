// Phase 206 Plan 06 (COV-04) — UAT-7-25: CBOM Page — Algorithm Search.
//
// `useScanData` is mocked (not `fetchApi`); the real `CbomPage` is rendered
// with `cytoscape`/`cytoscape-cose-bilkent` mocked so the graph tab's
// registration-on-import doesn't crash jsdom, even though this case only
// exercises the table tab.
//
// Case-insensitivity is the case's own stated subject (Pass Criteria:
// "Filter is case-insensitive (`aes` matches `AES-256-GCM`)") — the typed
// query here is deliberately the opposite case of the fixture's stored
// value, so a case-sensitive filter would fail this test.
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
  makeComponent({ algorithm: "AES-256-GCM", type: "cipher", quantum_safety: "Safe", source_systems: ["host-a"] }),
  makeComponent({ algorithm: "RSA-2048", type: "asymmetric", quantum_safety: "Vulnerable", source_systems: ["host-b"] }),
  makeComponent({ algorithm: "SHA-256", type: "hash", quantum_safety: "Safe", source_systems: ["host-c"] }),
]

const FIXTURE = {
  cbom_components: FIXTURE_COMPONENTS,
  hardware_devices: [],
}

describe("CbomPage — UAT-7-25 algorithm search", () => {
  it("filters the CBOM algorithm table case-insensitively as the search box is typed into", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const user = userEvent.setup()

    // Import lazily so the module-level cytoscape mocks above are already
    // registered before `cbom.tsx`'s top-level `cytoscape.use(...)` runs.
    const { CbomPage } = await import("@/pages/cbom")
    render(<CbomPage />)

    // Sanity: all three fixture rows present before filtering.
    expect(await screen.findByText("AES-256-GCM")).toBeInTheDocument()
    expect(screen.getByText("RSA-2048")).toBeInTheDocument()
    expect(screen.getByText("SHA-256")).toBeInTheDocument()

    // Query is lowercase; the fixture's stored value is uppercase — this is
    // the opposite-case query the case's Pass Criteria requires.
    const searchBox = screen.getByPlaceholderText("Filter algorithm...")
    await user.type(searchBox, "aes")

    // Matching row remains.
    expect(screen.getByText("AES-256-GCM")).toBeInTheDocument()
    // Non-matching rows are gone, not merely unasserted.
    expect(screen.queryByText("RSA-2048")).not.toBeInTheDocument()
    expect(screen.queryByText("SHA-256")).not.toBeInTheDocument()
  })
})
