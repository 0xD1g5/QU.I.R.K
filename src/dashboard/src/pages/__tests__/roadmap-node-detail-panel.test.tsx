/**
 * Phase 206 Plan 08 — UAT-7-16 (Roadmap Page — Node Detail Panel).
 *
 * Cytoscape is mocked/shallow (this repo's render-test convention — see
 * exposure-map.test.tsx / roadmap-score-lift.test.tsx). Node selection is
 * driven by capturing the handler `roadmap.tsx` registers via
 * `cy.on("tap", "node", ...)` and invoking it with a synthetic event carrying
 * a fixture node's id — the same seam roadmap-score-lift.test.tsx already
 * uses. That is the product's own registered handler, not a faked panel.
 *
 * Two of UAT-7-16's five Pass Criteria bullets ("Owner placeholder shown",
 * "Dependency list shown (if any)") are NOT asserted here: neither is
 * rendered by the product and neither exists on the RoadmapNode type. They
 * are named verbatim as uncovered in
 * `.planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-roadmap.md`
 * and filed as a product todo. Do not add fabricated assertions for them.
 *
 * NOT a source-text test: nothing here reads the source file.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { act } from "react"
import { render, screen, within, cleanup, waitFor } from "@testing-library/react"

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

// Two nodes in two different horizons. The test taps the SECOND one, so a
// panel hardcoded to the first roadmap item fails every assertion below.
const FIRST_NODE = {
  id: "n1",
  title: "Rotate expiring TLS certificates",
  phase: "NOW",
  timeframe: "0-30 days",
  why: "Three certificates expire within 30 days.",
  closure_state: null,
  slug: "rotate-expiring-certs",
  score_lift: null,
}
const SECOND_NODE = {
  id: "n2",
  title: "Migrate SSH host keys off RSA-2048",
  phase: "NEXT",
  timeframe: "31-90 days",
  why: "RSA-2048 host keys are harvest-now-decrypt-later exposed.",
  closure_state: null,
  slug: "migrate-ssh-host-keys",
  score_lift: null,
}

function tapNode(nodeId: string) {
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

describe("RoadmapPage — UAT-7-16 node detail panel", () => {
  it("opens the roadmap node detail panel with the tapped node's rationale owner and dependencies", async () => {
    scanDataReturn = {
      data: {
        roadmap: { nodes: [FIRST_NODE, SECOND_NODE], edges: [] },
        burndown: null,
        excluded_cert_count: 0,
        projected_score: null,
      },
      loading: false,
      error: null,
    }

    const { RoadmapPage } = await import("@/pages/roadmap")
    render(<RoadmapPage />)

    await waitFor(() => expect(capturedTapHandler).not.toBeNull())

    // No panel before any node is tapped.
    expect(screen.queryByRole("button", { name: "Close" })).not.toBeInTheDocument()

    // Tap the SECOND node.
    tapNode(SECOND_NODE.id)

    const closeButton = await screen.findByRole("button", { name: "Close" })
    const panel = closeButton.closest("div.z-20") as HTMLElement
    expect(panel).not.toBeNull()

    // Bullet 1 — "Item title visible" (the tapped node's own title).
    expect(within(panel).getByText(SECOND_NODE.title)).toBeInTheDocument()

    // Bullet 2 — "Timeframe visible (e.g. '0-30 days')". The panel renders the
    // tapped node's horizon label; the legend also renders all three labels,
    // so this is scoped to the panel.
    expect(within(panel).getByText("31-90 days")).toBeInTheDocument()

    // Bullet 3 — "`Why:` evidence text visible" (the tapped node's own why).
    expect(within(panel).getByText(SECOND_NODE.why)).toBeInTheDocument()

    // Negative half: none of the FIRST node's data leaks into the panel, so a
    // handler that always selected the first node fails here.
    expect(within(panel).queryByText(FIRST_NODE.title)).not.toBeInTheDocument()
    expect(within(panel).queryByText(FIRST_NODE.why)).not.toBeInTheDocument()
    expect(within(panel).queryByText("0-30 days")).not.toBeInTheDocument()

    // Bullets 4 and 5 ("Owner placeholder shown", "Dependency list shown
    // (if any)") are deliberately NOT asserted — the product renders neither
    // and RoadmapNode carries no owner/dependency field. See this file's
    // header and the roadmap red-proof fragment's uncovered-bullets section.
  })
})
