/**
 * Phase 195 Plan 05 — exposure-map.tsx component tests (MAP-02).
 *
 * Cytoscape is mocked/shallow (this repo's render-test convention — see
 * cbom-cytoscape-catch.test.tsx / feedback_recharts_static_children): these
 * tests assert on the React-rendered scaffold (empty-state, legend,
 * score-firewall note, container presence, evidence reachability), never on
 * canvas-internal rendering.
 */
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"

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
vi.mock("cytoscape-dagre", () => ({ default: {} }))

vi.mock("@/lib/api", () => ({
  fetchApi: vi.fn(),
}))

import { fetchApi } from "@/lib/api"
import { ExposureMapPage } from "@/pages/exposure-map"

const mockFetchApi = fetchApi as ReturnType<typeof vi.fn>

function mockResponse(body: unknown, ok = true, status = 200) {
  return {
    ok,
    status,
    json: async () => body,
  }
}

describe("ExposureMapPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("(a) renders the empty-state EmptyStateCard and no graph container when there are zero edges", async () => {
    mockFetchApi.mockResolvedValue(mockResponse({ nodes: [], edges: [] }))

    render(<ExposureMapPage />)

    await waitFor(() => {
      expect(screen.getByText("No path data available")).toBeDefined()
    })

    // role="status" — EmptyStateCard's Card wrapper
    expect(screen.getByRole("status")).toBeDefined()
    // No Cytoscape canvas container (role="img" graph container) rendered
    expect(screen.queryByRole("img")).toBeNull()
  })

  it("(b) renders the graph container and makes edge evidence reachable without hover", async () => {
    mockFetchApi.mockResolvedValue(
      mockResponse({
        nodes: [
          { id: "host-a", label: "host-a:443", is_crown_jewel: false },
          { id: "host-b", label: "host-b:443", is_crown_jewel: true },
        ],
        edges: [
          {
            source: "host-a",
            target: "host-b",
            edge_type: "key_reuse",
            evidence: "Key reuse: these endpoints share SPKI fingerprint abc123.",
          },
        ],
      }),
    )

    render(<ExposureMapPage />)

    await waitFor(() => {
      expect(screen.getByRole("img")).toBeDefined()
    })

    // Evidence reachable via the sr-only fallback list (aria-label), not
    // gated behind a hover interaction.
    expect(
      screen.getByLabelText(/Key reuse: these endpoints share SPKI fingerprint abc123\./i),
    ).toBeDefined()
  })

  it("(c) renders the Tier A legend entries and the score-firewall note", async () => {
    mockFetchApi.mockResolvedValue(
      mockResponse({
        nodes: [
          { id: "host-a", label: "host-a:443", is_crown_jewel: false },
          { id: "host-b", label: "host-b:443", is_crown_jewel: false },
        ],
        edges: [
          {
            source: "host-a",
            target: "host-b",
            edge_type: "hardware_bridge",
            evidence: "Confirmed hardware crypto-bridge: device-1 bridges host-a to host-b.",
          },
        ],
      }),
    )

    render(<ExposureMapPage />)

    await waitFor(() => {
      expect(screen.getByText("Edge types")).toBeDefined()
    })

    expect(screen.getByText("Key-reuse cluster")).toBeDefined()
    expect(screen.getByText("Hardware crypto-bridge")).toBeDefined()
    // Tier B row must NOT be present (195-SPIKE-DECISION.md: DECISION DEFERRED)
    expect(screen.queryByText("Declared reachability")).toBeNull()

    // Score-firewall reassurance note — always visible
    expect(
      screen.getByText(/does not affect the quantum-readiness score/i),
    ).toBeDefined()
  })
})
