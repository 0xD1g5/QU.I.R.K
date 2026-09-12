/**
 * Phase 201 Plan 06 — LIFT-05 dashboard rendering: the per-item "+N pts"
 * lift badge in the roadmap detail panel, the Projected Score card, and
 * the print-surface equivalents (roadmap.tsx / print.tsx).
 *
 * Cytoscape is mocked/shallow (this repo's render-test convention — see
 * exposure-map.test.tsx / cbom-cytoscape-catch.test.tsx): node selection is
 * driven by capturing the registered `tap` handler and invoking it directly,
 * rather than depending on canvas-internal click dispatch.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { act } from "react"
import { render, screen, cleanup, waitFor } from "@testing-library/react"

type TapHandler = (evt: {
  target: {
    data: (key: string) => string
    connectedEdges: (sel: string) => { style: (s: unknown) => void }
  }
}) => void

let capturedTapHandler: TapHandler | null = null

vi.mock("cytoscape", () => {
  const mockCyCore = {
    on: vi.fn((event: string, selectorOrCb: unknown, maybeCb?: unknown) => {
      if (event === "tap" && selectorOrCb === "node") {
        capturedTapHandler = maybeCb as TapHandler
      }
    }),
    edges: vi.fn(() => ({ style: vi.fn() })),
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
vi.mock("cytoscape-dagre", () => ({ default: {} }))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: true,
  error: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

function makeNode(overrides: Record<string, unknown> = {}) {
  return {
    id: "n1",
    title: "Rotate expiring TLS certificates",
    phase: "NOW",
    timeframe: "0-30 days",
    why: "Certificates expire within 30 days.",
    closure_state: null,
    slug: "rotate-expiring-certs",
    score_lift: null,
    ...overrides,
  }
}

function makeFixture(opts: {
  nodes: ReturnType<typeof makeNode>[]
  projected_score?: number | null
}) {
  return {
    roadmap: { nodes: opts.nodes },
    burndown: null,
    excluded_cert_count: 0,
    projected_score: opts.projected_score ?? null,
  }
}

// Selects a node by invoking the captured cytoscape `tap` handler directly —
// the mocked cytoscape core never dispatches real DOM/canvas events.
function selectNode(nodeId: string) {
  act(() => {
    capturedTapHandler?.({
      target: {
        data: () => nodeId,
        connectedEdges: () => ({ style: () => {} }),
      },
    })
  })
}

afterEach(() => {
  cleanup()
  capturedTapHandler = null
})

describe("RoadmapPage — LIFT-05 per-item lift badge (dashboard)", () => {
  it("renders a '+4 pts' badge on the badge row when the selected node has score_lift: 4", async () => {
    scanDataReturn = {
      data: makeFixture({ nodes: [makeNode({ id: "n1", score_lift: 4 })] }),
      loading: false,
      error: null,
    }
    const { RoadmapPage } = await import("@/pages/roadmap")
    render(<RoadmapPage />)

    await waitFor(() => expect(capturedTapHandler).not.toBeNull())
    selectNode("n1")

    expect(await screen.findByText("+4 pts")).toBeInTheDocument()
  })

  it("renders no lift badge when score_lift is null, and existing phase badge is unaffected", async () => {
    scanDataReturn = {
      data: makeFixture({ nodes: [makeNode({ id: "n1", score_lift: null })] }),
      loading: false,
      error: null,
    }
    const { RoadmapPage } = await import("@/pages/roadmap")
    render(<RoadmapPage />)

    await waitFor(() => expect(capturedTapHandler).not.toBeNull())
    selectNode("n1")

    // Existing phase badge still renders (the legend also contains this
    // text, so scope to the Badge element specifically).
    expect(await screen.findAllByText("0-30 days")).toHaveLength(2)
    // No lift badge anywhere — never a "+0 pts" or gray placeholder.
    expect(screen.queryByText(/pts$/)).not.toBeInTheDocument()
  })
})

describe("RoadmapPage — LIFT-05 Projected Score card (dashboard)", () => {
  it("renders the Projected Score card with the locked body text and verbatim disclaimer when projected_score: 78", async () => {
    scanDataReturn = {
      data: makeFixture({ nodes: [makeNode()], projected_score: 78 }),
      loading: false,
      error: null,
    }
    const { RoadmapPage } = await import("@/pages/roadmap")
    render(<RoadmapPage />)

    expect(await screen.findByText("Projected Score")).toBeInTheDocument()
    // Number is rendered in a nested styled span, so match on the container's
    // full text content rather than requiring a single text node.
    expect(
      screen.getByText((_content, node) => {
        return node?.textContent === "Projected score if all items resolved: 78"
      }),
    ).toBeInTheDocument()
    // Exact full-string match, including the em dash — proven to fail on a
    // single-character change (verified by a temporary mutation, see SUMMARY).
    expect(
      screen.getByText(
        "Advisory — this projection is a simulation and does not affect the readiness score.",
      ),
    ).toBeInTheDocument()
  })

  it("renders no Projected Score card at all when projected_score is null", async () => {
    scanDataReturn = {
      data: makeFixture({ nodes: [makeNode()], projected_score: null }),
      loading: false,
      error: null,
    }
    const { RoadmapPage } = await import("@/pages/roadmap")
    render(<RoadmapPage />)

    await waitFor(() => expect(screen.getByRole("img")).toBeInTheDocument())
    expect(screen.queryByText("Projected Score")).not.toBeInTheDocument()
    expect(
      screen.queryByText(
        "Advisory — this projection is a simulation and does not affect the readiness score.",
      ),
    ).not.toBeInTheDocument()
  })
})

describe("PrintRoadmap — LIFT-05 print-surface equivalents", () => {
  it("renders '(+4 pts)' after a node title with a lift, and nothing after a node without one", async () => {
    const { PrintRoadmap } = await import("@/pages/print")
    render(
      <PrintRoadmap
        nodes={[
          makeNode({ id: "n1", title: "Rotate expiring TLS certificates", score_lift: 4 }),
          makeNode({ id: "n2", title: "Assign remediation owners", score_lift: null, why: null }),
        ]}
        projectedScore={null}
      />,
    )

    expect(screen.getByText("(+4 pts)")).toBeInTheDocument()
    expect(screen.getByText("Assign remediation owners")).toBeInTheDocument()
    // Only one lift parenthetical exists — the second node has none.
    expect(screen.queryAllByText(/^\(\+.*pts\)$/)).toHaveLength(1)
  })

  it("renders the projected line and advisory before the grouped list when a projection exists", async () => {
    const { PrintRoadmap } = await import("@/pages/print")
    render(<PrintRoadmap nodes={[makeNode({ id: "n1" })]} projectedScore={78} />)

    expect(
      screen.getByText((_content, node) => {
        return (
          node?.tagName === "P" &&
          (node.textContent?.includes("Projected score if all items resolved: 78") ?? false)
        )
      }),
    ).toBeInTheDocument()
    expect(
      screen.getByText((_content, node) => {
        return (
          node?.tagName === "P" &&
          (node.textContent?.includes(
            "Advisory — this projection is a simulation and does not affect the readiness score.",
          ) ??
            false)
        )
      }),
    ).toBeInTheDocument()
  })

  it("renders no projected line at all when projectedScore is null", async () => {
    const { PrintRoadmap } = await import("@/pages/print")
    render(<PrintRoadmap nodes={[makeNode({ id: "n1" })]} projectedScore={null} />)

    expect(screen.queryByText(/Projected score if all items resolved/)).not.toBeInTheDocument()
  })
})
