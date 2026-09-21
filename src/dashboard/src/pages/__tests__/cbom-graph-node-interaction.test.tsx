/**
 * Phase 206 Plan 07 (COV-04) — UAT-7-27: CBOM Graph — Node Interaction.
 *
 * Cytoscape is mocked. The testable seam is the `tap`/`node` handler that
 * `cbom.tsx` registers on the instance: the test captures it from the mocked
 * `cy.on(...)` call and invokes it with a synthetic event whose `target`
 * returns a fixture node's data, then asserts the real React detail panel
 * renders THAT node's type-specific fields.
 *
 * Two nodes of different types are driven (an algorithm node, then a source
 * system node) and the algorithm node driven first is deliberately NOT the
 * first element in the fixture, so a handler that always selected the first
 * node cannot pass.
 *
 * NOT a source-text test. The real click-on-canvas half (hit-testing a
 * rendered node) is unreachable against a mocked engine and is named as an
 * uncovered bullet in
 * `.planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-cbom-graph.md`.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup, screen, waitFor, act, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { CbomComponent } from "@/types/api"

type TapHandler = (evt: { target: unknown }) => void

type MockCy = {
  on: ReturnType<typeof vi.fn>
  edges: ReturnType<typeof vi.fn>
  destroy: ReturnType<typeof vi.fn>
  zoom: ReturnType<typeof vi.fn>
  fit: ReturnType<typeof vi.fn>
}

let capturedCy: MockCy | null = null
let capturedElements: { group?: string; data: Record<string, unknown> }[] = []

vi.mock("cytoscape", () => {
  const ctor = vi.fn((config: { elements?: unknown }) => {
    const core = {
      on: vi.fn(),
      edges: vi.fn(() => ({ removeClass: vi.fn(), addClass: vi.fn() })),
      elements: vi.fn(() => ({ style: vi.fn() })),
      layout: vi.fn(() => ({ run: vi.fn() })),
      destroy: vi.fn(),
      zoom: vi.fn(() => 1),
      fit: vi.fn(),
    }
    capturedCy = core as unknown as MockCy
    capturedElements = (config.elements ?? []) as {
      group?: string
      data: Record<string, unknown>
    }[]
    return core
  }) as unknown as {
    (...args: unknown[]): unknown
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

const FIXTURE_COMPONENTS: CbomComponent[] = [
  {
    algorithm: "AES-256-GCM",
    type: "cipher",
    key_size: 256,
    quantum_safety: "Safe",
    source_systems: ["10.0.0.5:443", "10.0.0.6:22"],
  },
  {
    algorithm: "RSA-2048",
    type: "asymmetric",
    key_size: 2048,
    quantum_safety: "Vulnerable",
    source_systems: ["10.0.0.5:443"],
  },
]

/** The detail panel is the element that owns the "Close" control. */
function detailPanel(): HTMLElement {
  const close = screen.getByRole("button", { name: "Close" })
  // button -> header flex row -> panel
  const panel = close.parentElement?.parentElement
  expect(panel, "detail panel element not found above the Close button").toBeTruthy()
  return panel as HTMLElement
}

afterEach(() => {
  cleanup()
  capturedCy = null
  capturedElements = []
})

describe("CbomPage — UAT-7-27 graph node interaction", () => {
  it("updates the CBOM detail panel with the tapped node's type-specific fields", async () => {
    scanDataReturn = {
      data: { cbom_components: FIXTURE_COMPONENTS, hardware_devices: [] },
      loading: false,
      error: null,
    }
    const user = userEvent.setup()

    const { CbomPage } = await import("@/pages/cbom")
    render(<CbomPage />)

    await user.click(screen.getByRole("tab", { name: "Graph" }))
    await waitFor(() => expect(capturedCy).not.toBeNull())
    const cy = capturedCy as MockCy

    // Capture the node-scoped tap handler the page registered on the instance.
    const nodeTapCall = cy.on.mock.calls.find(
      (call) => call[0] === "tap" && call[1] === "node",
    )
    expect(nodeTapCall, 'no cy.on("tap", "node", ...) registration captured').toBeDefined()
    const onNodeTap = nodeTapCall?.[2] as TapHandler

    // No panel before any tap.
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument()

    const dataFor = (id: string) => {
      const el = capturedElements.find((e) => e.data.id === id)
      expect(el, `no built element with id ${id}`).toBeDefined()
      return el!.data
    }
    const synthetic = (id: string) => ({
      target: {
        data: () => dataFor(id),
        connectedEdges: () => ({ addClass: vi.fn() }),
      },
    })

    // --- Bullet: "Algorithm node click shows: algorithm name, quantum-safety
    // classification, connected source systems". RSA-2048 is the SECOND
    // fixture component, so a panel pinned to the first node fails here.
    const rsa = FIXTURE_COMPONENTS[1]
    act(() => onNodeTap(synthetic(`alg-${rsa.algorithm}`)))

    let panel = detailPanel()
    expect(within(panel).getByText(rsa.algorithm)).toBeInTheDocument()
    expect(within(panel).getByText(rsa.quantum_safety as string)).toBeInTheDocument()
    expect(within(panel).getByText(rsa.type as string)).toBeInTheDocument()
    expect(within(panel).getByText(`${rsa.key_size}b`)).toBeInTheDocument()
    expect(
      within(panel).getByText(`On ${rsa.source_systems.length} system`),
    ).toBeInTheDocument()
    for (const sys of rsa.source_systems) {
      expect(within(panel).getByText(sys)).toBeInTheDocument()
    }
    // The other algorithm's identity must NOT be on the panel.
    expect(within(panel).queryByText(FIXTURE_COMPONENTS[0].algorithm)).not.toBeInTheDocument()

    // --- Bullets: "Source system node click shows: host:port or file path,
    // connected algorithms" + "Panel updates when clicking different nodes".
    const sharedSystem = "10.0.0.5:443"
    act(() => onNodeTap(synthetic(`sys-${sharedSystem}`)))

    panel = detailPanel()
    expect(within(panel).getByText(sharedSystem)).toBeInTheDocument()
    // Both fixture algorithms reference this system, so both must be listed.
    const expectedAlgs = FIXTURE_COMPONENTS.filter((c) =>
      c.source_systems.includes(sharedSystem),
    ).map((c) => c.algorithm)
    expect(expectedAlgs.length).toBeGreaterThan(1)
    for (const alg of expectedAlgs) {
      expect(within(panel).getByText(alg)).toBeInTheDocument()
    }
    // The algorithm-node-only fields are gone — the panel really switched
    // type, it did not merely append.
    expect(within(panel).queryByText(`${rsa.key_size}b`)).not.toBeInTheDocument()
    expect(within(panel).queryByText(/^On \d+ system/)).not.toBeInTheDocument()
  })
})
