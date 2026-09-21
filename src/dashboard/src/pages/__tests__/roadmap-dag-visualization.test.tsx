/**
 * Phase 206 Plan 08 — UAT-7-15 (Roadmap Page — DAG Visualization).
 *
 * Cytoscape is mocked/shallow (this repo's render-test convention — see
 * exposure-map.test.tsx / roadmap-score-lift.test.tsx). The testable seam is
 * the configuration object `roadmap.tsx` hands to `cytoscape({...})`: the
 * `elements` array (one node per roadmap item, carrying its `phase` datum and
 * its title as `label`) and the `style` array (the `node[phase='...']`
 * selectors that bind each horizon to its own background color). Canvas-
 * internal rendering, layout geometry and edge routing are NOT reachable here
 * and are named as uncovered bullets in
 * `.planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-roadmap.md`.
 *
 * NOT a source-text test: nothing here reads the source file. Assertions run
 * against the captured runtime argument.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup, waitFor } from "@testing-library/react"

type CyElement = {
  group?: string
  data: Record<string, unknown>
}
type CyStyleRule = {
  selector: string
  style: Record<string, unknown>
}
type CyConfig = {
  elements: CyElement[]
  style: CyStyleRule[]
}

let capturedConfig: CyConfig | null = null

vi.mock("cytoscape", () => {
  const mockCyCore = {
    on: vi.fn(),
    edges: vi.fn(() => ({ style: vi.fn() })),
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
vi.mock("cytoscape-dagre", () => ({ default: {} }))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: true,
  error: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

// One item in each of the three horizons, so a page that collapsed them to a
// single coding cannot pass.
const FIXTURE_ITEMS = [
  {
    id: "n1",
    title: "Rotate expiring TLS certificates",
    phase: "NOW",
    timeframe: "0-30 days",
    why: "Certificates expire within 30 days.",
    closure_state: null,
    slug: "rotate-expiring-certs",
    score_lift: null,
  },
  {
    id: "n2",
    title: "Migrate SSH host keys off RSA-2048",
    phase: "NEXT",
    timeframe: "31-90 days",
    why: "RSA-2048 host keys are harvest-now-decrypt-later exposed.",
    closure_state: null,
    slug: "migrate-ssh-host-keys",
    score_lift: null,
  },
  {
    id: "n3",
    title: "Adopt hybrid KEM at the edge",
    phase: "LATER",
    timeframe: "90+ days",
    why: "Hybrid key establishment requires vendor firmware support.",
    closure_state: null,
    slug: "adopt-hybrid-kem",
    score_lift: null,
  },
]

afterEach(() => {
  cleanup()
  capturedConfig = null
})

describe("RoadmapPage — UAT-7-15 DAG horizon coding", () => {
  it("builds roadmap DAG elements with NOW NEXT and LATER horizon classes from the fixture", async () => {
    scanDataReturn = {
      data: {
        roadmap: { nodes: FIXTURE_ITEMS, edges: [] },
        burndown: null,
        excluded_cert_count: 0,
        projected_score: null,
      },
      loading: false,
      error: null,
    }

    const { RoadmapPage } = await import("@/pages/roadmap")
    render(<RoadmapPage />)

    await waitFor(() => expect(capturedConfig).not.toBeNull())
    const config = capturedConfig as CyConfig

    // --- Bullet: "Nodes labeled with roadmap item titles" + per-node horizon datum ---
    const nodeElements = config.elements.filter((el) => el.group === "nodes")
    expect(nodeElements).toHaveLength(FIXTURE_ITEMS.length)

    for (const item of FIXTURE_ITEMS) {
      const el = nodeElements.find((n) => n.data.id === item.id)
      expect(el, `no DAG node element built for roadmap item ${item.id}`).toBeDefined()
      // Each node carries its own horizon datum — this is the class the
      // node[phase='...'] style selectors below key off.
      expect(el?.data.phase).toBe(item.phase)
      // ...and its own roadmap item title as the rendered label.
      expect(el?.data.label).toBe(item.title)
    }

    // All three horizons are present and distinct on the elements array, so a
    // build that collapsed every item into one horizon fails here.
    const phasesBuilt = nodeElements.map((n) => n.data.phase)
    expect(new Set(phasesBuilt).size).toBe(3)
    expect(phasesBuilt).toContain("NOW")
    expect(phasesBuilt).toContain("NEXT")
    expect(phasesBuilt).toContain("LATER")

    // --- Bullet: "Graph renders with colored nodes (red=NOW, yellow=NEXT, green=LATER)" ---
    // Asserted at the style-binding seam: one selector per horizon, each
    // binding its own background-color, all three mutually distinct.
    const colorFor = (phase: string) => {
      const rule = config.style.find((s) => s.selector === `node[phase='${phase}']`)
      expect(rule, `no style rule bound for node[phase='${phase}']`).toBeDefined()
      return rule?.style["background-color"] as string
    }
    const nowColor = colorFor("NOW")
    const nextColor = colorFor("NEXT")
    const laterColor = colorFor("LATER")

    expect(nowColor).toBeTruthy()
    expect(nextColor).toBeTruthy()
    expect(laterColor).toBeTruthy()
    // Distinct codings — the whole point of the case. A single shared color
    // (or a fallback to the base gray) fails this.
    expect(new Set([nowColor, nextColor, laterColor]).size).toBe(3)

    const baseNodeRule = config.style.find((s) => s.selector === "node")
    const baseColor = baseNodeRule?.style["background-color"] as string
    expect(nowColor).not.toBe(baseColor)
    expect(nextColor).not.toBe(baseColor)
    expect(laterColor).not.toBe(baseColor)

    // --- Directed edges exist between the horizons (see the fragment's
    // uncovered-bullets section: these are phase-sequencing edges, NOT
    // per-item dependency edges — the case's dependency bullet is a carve-out).
    const edgeElements = config.elements.filter((el) => el.group === "edges")
    const crossPhaseEdges = edgeElements.filter((e) => e.data.rankOnly === "false")
    expect(crossPhaseEdges.length).toBeGreaterThan(0)
    for (const edge of crossPhaseEdges) {
      expect(nodeElements.some((n) => n.data.id === edge.data.source)).toBe(true)
      expect(nodeElements.some((n) => n.data.id === edge.data.target)).toBe(true)
    }
    const arrowRule = config.style.find((s) => s.selector === "edge[rankOnly='false']")
    expect(arrowRule?.style["target-arrow-shape"]).toBe("triangle")
  })
})
