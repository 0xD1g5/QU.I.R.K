/**
 * Phase 206 Plan 07 (COV-04) — UAT-7-28: CBOM Graph — Zoom Controls.
 *
 * Cytoscape is mocked. The testable seam is the set of calls the real
 * zoom-in / zoom-out / fit buttons make on the instance: the test clicks the
 * actual rendered controls (never the handlers directly) and asserts the
 * mocked `cy.zoom(...)` / `cy.fit()` APIs received the right calls, including
 * the zoom DIRECTION the component passes.
 *
 * NOT a source-text test. Scroll-wheel zoom and click-drag panning are
 * cytoscape-internal and unreachable against a mock; they are named as
 * uncovered bullets in
 * `.planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-cbom-graph.md`.
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { CbomComponent } from "@/types/api"

type MockCy = {
  on: ReturnType<typeof vi.fn>
  destroy: ReturnType<typeof vi.fn>
  zoom: ReturnType<typeof vi.fn>
  fit: ReturnType<typeof vi.fn>
}

let capturedCy: MockCy | null = null
let capturedConfig: Record<string, unknown> | null = null

vi.mock("cytoscape", () => {
  const ctor = vi.fn((config: unknown) => {
    const core = {
      on: vi.fn(),
      edges: vi.fn(() => ({ removeClass: vi.fn(), addClass: vi.fn() })),
      elements: vi.fn(() => ({ style: vi.fn() })),
      layout: vi.fn(() => ({ run: vi.fn() })),
      destroy: vi.fn(),
      // Returns a stable current zoom level so the component's
      // `zoom(zoom() * factor)` read-modify-write is deterministic.
      zoom: vi.fn(() => 1),
      fit: vi.fn(),
    }
    capturedCy = core as unknown as MockCy
    capturedConfig = config as Record<string, unknown>
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
    source_systems: ["10.0.0.5:443"],
  },
  {
    algorithm: "RSA-2048",
    type: "asymmetric",
    key_size: 2048,
    quantum_safety: "Vulnerable",
    source_systems: ["10.0.0.6:22"],
  },
]

afterEach(() => {
  cleanup()
  capturedCy = null
  capturedConfig = null
})

describe("CbomPage — UAT-7-28 graph zoom controls", () => {
  it("calls the cytoscape zoom and fit APIs when the CBOM zoom controls are used", async () => {
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

    // Only argument-bearing calls are zoom WRITES; the no-arg calls are the
    // component reading the current level before scaling it.
    const zoomWrites = () =>
      cy.zoom.mock.calls.filter((c) => c.length > 0).map((c) => c[0] as number)

    expect(zoomWrites()).toHaveLength(0)
    expect(cy.fit).not.toHaveBeenCalled()

    // --- Bullet: "Zoom in/out buttons change zoom level visibly" — asserted
    // at the API boundary, including direction.
    await user.click(screen.getByRole("button", { name: "Zoom in" }))
    let writes = zoomWrites()
    expect(writes).toHaveLength(1)
    const zoomedIn = writes[0]
    // Current level is 1 (mock); zooming IN must request a strictly larger level.
    expect(zoomedIn).toBeGreaterThan(1)

    await user.click(screen.getByRole("button", { name: "Zoom out" }))
    writes = zoomWrites()
    expect(writes).toHaveLength(2)
    const zoomedOut = writes[1]
    // ...and zooming OUT a strictly smaller one. A button wired to the wrong
    // direction (or to nothing) fails here.
    expect(zoomedOut).toBeLessThan(1)
    expect(zoomedOut).toBeLessThan(zoomedIn)

    // --- Bullet: "'Fit to Viewport' shows all nodes within visible area" —
    // asserted as the fit() delegation; the resulting viewport geometry is
    // cytoscape-internal and not reachable here.
    await user.click(screen.getByRole("button", { name: "Fit to screen" }))
    expect(cy.fit).toHaveBeenCalledTimes(1)
    // Fit must not smuggle in a zoom write.
    expect(zoomWrites()).toHaveLength(2)

    // Supporting evidence only for the scroll-wheel / drag-pan bullets: the
    // page enables both interactions on the instance. Whether cytoscape then
    // honours a wheel or drag gesture is engine-internal — see the fragment's
    // uncovered-bullet list; this assertion does not claim those bullets.
    expect(capturedConfig?.userZoomingEnabled).toBe(true)
    expect(capturedConfig?.userPanningEnabled).toBe(true)
  })
})
