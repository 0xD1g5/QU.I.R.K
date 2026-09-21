/**
 * Phase 206 Plan 07 (COV-04) — UAT-7-14: CBOM Page — Graph Visualization.
 *
 * Cytoscape is mocked (this repo's render-test convention — see
 * exposure-map.test.tsx / roadmap-dag-visualization.test.tsx). The testable
 * seam is the configuration object `cbom.tsx` hands to `cytoscape({...})`:
 * the `elements` array it builds — one node per algorithm, one node per
 * distinct source system, and one edge per algorithm→system pairing.
 *
 * NOT a source-text test: nothing here reads the source file. Every assertion
 * runs against the runtime argument captured from the mocked constructor.
 *
 * Coverage boundary (the bullets a mocked graph engine cannot reach) is
 * recorded verbatim in
 * `.planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-cbom-graph.md`.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { CbomComponent } from "@/types/api"

type CyElement = {
  group?: string
  data: Record<string, unknown>
}
type CyConfig = {
  elements: CyElement[]
  style: { selector: string; style: Record<string, unknown> }[]
}

let capturedConfig: CyConfig | null = null

vi.mock("cytoscape", () => {
  const mockCyCore = {
    on: vi.fn(),
    edges: vi.fn(() => ({ removeClass: vi.fn(), addClass: vi.fn() })),
    elements: vi.fn(() => ({ style: vi.fn() })),
    layout: vi.fn(() => ({ run: vi.fn() })),
    destroy: vi.fn(),
    zoom: vi.fn(() => 1),
    fit: vi.fn(),
  }
  const ctor = vi.fn((config: unknown) => {
    capturedConfig = config as CyConfig
    return mockCyCore
  }) as unknown as {
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

// Two algorithms share a source system, so the fixture forces a genuinely
// connected bipartite graph rather than three isolated pairs.
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
  {
    algorithm: "SHA-256",
    type: "hash",
    key_size: 256,
    quantum_safety: "Safe",
    source_systems: ["10.0.0.7:8443"],
  },
]

afterEach(() => {
  cleanup()
  capturedConfig = null
})

describe("CbomPage — UAT-7-14 graph visualization", () => {
  it("builds the CBOM graph elements from the fixture with one node per algorithm and asset", async () => {
    scanDataReturn = {
      data: { cbom_components: FIXTURE_COMPONENTS, hardware_devices: [] },
      loading: false,
      error: null,
    }
    const user = userEvent.setup()

    // Lazy import so the hoisted cytoscape mocks are registered before
    // `cbom.tsx`'s module-level `cytoscape.use(coseBilkent)` runs.
    const { CbomPage } = await import("@/pages/cbom")
    render(<CbomPage />)

    // The graph tab is not the default; Radix unmounts inactive TabsContent,
    // so the graph is only constructed after this real tab click.
    await user.click(screen.getByRole("tab", { name: "Graph" }))
    await waitFor(() => expect(capturedConfig).not.toBeNull())
    const config = capturedConfig as CyConfig

    // --- Expected counts derived from the fixture, never hardcoded ---
    const expectedAlgorithms = FIXTURE_COMPONENTS.map((c) => c.algorithm)
    const expectedSystems = Array.from(
      new Set(FIXTURE_COMPONENTS.flatMap((c) => c.source_systems)),
    )
    const expectedEdgeCount = FIXTURE_COMPONENTS.reduce(
      (n, c) => n + c.source_systems.length,
      0,
    )

    const nodeElements = config.elements.filter((el) => el.group === "nodes")
    const edgeElements = config.elements.filter((el) => el.group === "edges")

    // --- Bullet: "Graph renders with visible nodes and edges" (element layer) ---
    expect(nodeElements).toHaveLength(
      expectedAlgorithms.length + expectedSystems.length,
    )
    expect(edgeElements).toHaveLength(expectedEdgeCount)

    // --- One node per algorithm, carrying the identifier the fixture supplies ---
    for (const alg of expectedAlgorithms) {
      const el = nodeElements.find((n) => n.data.id === `alg-${alg}`)
      expect(el, `no graph node built for algorithm ${alg}`).toBeDefined()
      expect(el?.data.label).toBe(alg)
      expect(el?.data.nodeType).toBe("algorithm")
    }

    // --- One node per distinct asset (source system) ---
    for (const sys of expectedSystems) {
      const el = nodeElements.find((n) => n.data.id === `sys-${sys}`)
      expect(el, `no graph node built for source system ${sys}`).toBeDefined()
      expect(el?.data.label).toBe(sys)
      expect(el?.data.nodeType).toBe("system")
    }

    // Nothing extra: the element set is exactly the algorithm ∪ system set.
    const builtNodeIds = nodeElements.map((n) => n.data.id as string).sort()
    expect(builtNodeIds).toEqual(
      [
        ...expectedAlgorithms.map((a) => `alg-${a}`),
        ...expectedSystems.map((s) => `sys-${s}`),
      ].sort(),
    )

    // --- Every edge's source and target resolves to a node in this same array ---
    const nodeIdSet = new Set(builtNodeIds)
    expect(edgeElements.length).toBeGreaterThan(0)
    for (const edge of edgeElements) {
      expect(
        nodeIdSet.has(edge.data.source as string),
        `edge ${String(edge.data.id)} has unresolvable source ${String(edge.data.source)}`,
      ).toBe(true)
      expect(
        nodeIdSet.has(edge.data.target as string),
        `edge ${String(edge.data.id)} has unresolvable target ${String(edge.data.target)}`,
      ).toBe(true)
    }

    // --- Bullet: "At least 3 connected nodes visible" — asserted as the size
    // of the connected component reachable through the built edges, not as a
    // bare node count (isolated nodes would not satisfy the case).
    const connectedIds = new Set<string>()
    for (const edge of edgeElements) {
      connectedIds.add(edge.data.source as string)
      connectedIds.add(edge.data.target as string)
    }
    expect(connectedIds.size).toBeGreaterThanOrEqual(3)
  })
})
