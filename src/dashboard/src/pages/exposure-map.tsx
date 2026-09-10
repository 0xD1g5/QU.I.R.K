import { useRef, useEffect, useMemo, useState } from "react"
import cytoscape from "cytoscape"
import dagre from "cytoscape-dagre"
import { fetchApi } from "@/lib/api"
import type { ExposureEdge, ExposureMapResponse } from "@/types/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import { PageSpinner } from "@/components/PageSpinner"
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "@/components/ui/tooltip"
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react"

// Register dagre layout (D-07 — dagre only; no alternate layout engine used).
// D-24 (IN-02) pattern: log via console.error and re-throw genuine failures
// so the visualization fails loudly rather than silently; the /already/i
// guard swallows HMR re-registration only (matches roadmap.tsx/cbom.tsx).
try {
  cytoscape.use(dagre)
} catch (e) {
  console.error('cytoscape.use(dagre) failed:', e)
  if (!(e instanceof Error) || !/already/i.test(e.message)) throw e
}

// Tier A only (195-SPIKE-DECISION.md: DECISION DEFERRED) — no
// "declared_reachability" entry here. Do not add one unless a future spike
// records DECISION: GO.
const EDGE_TYPE_LABEL: Record<string, string> = {
  key_reuse: "Key-reuse cluster",
  hardware_bridge: "Hardware crypto-bridge",
}

export function ExposureMapPage() {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [data, setData] = useState<ExposureMapResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hoveredEdge, setHoveredEdge] = useState<ExposureEdge | null>(null)
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    async function load() {
      try {
        const resp = await fetchApi("/api/exposure-map")
        if (!resp.ok) {
          if (!cancelled) {
            setError(
              `Exposure map data could not be loaded. HTTP ${resp.status}. Reload the page or check the API log.`,
            )
          }
          return
        }
        const json = (await resp.json()) as ExposureMapResponse
        if (!cancelled) setData(json)
      } catch (e) {
        if (!cancelled) {
          const reason = e instanceof Error ? e.message : "Unknown error"
          setError(`Exposure map data could not be loaded. ${reason}. Reload the page or check the API log.`)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  const nodes = useMemo(() => data?.nodes ?? [], [data])
  // D-11 (UI-side mirror of the backend evidence guard): never render an
  // edge whose evidence is empty/missing.
  const evidenceEdges = useMemo(
    () => (data?.edges ?? []).filter((e) => e.evidence && e.evidence.trim()),
    [data],
  )

  // WR-01: cytoscape throws synchronously ("Can not create edge ... with
  // nonexistant source/target") if any edge references a node id absent from
  // `nodes`, crashing the whole page render. Filter to edges whose BOTH
  // endpoints are present so the graph degrades to its valid subset instead
  // of crashing. `edges` (the dangling-safe set) feeds the cytoscape
  // elements, edgeById hover lookups, the sr-only list, and the empty-state
  // gate — all consumers share one array so indices stay aligned.
  const edges = useMemo(() => {
    const nodeIds = new Set(nodes.map((n) => n.id))
    return evidenceEdges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
  }, [nodes, evidenceEdges])

  // Surface dropped dangling edges (referential-integrity slips in the
  // backend payload) so the filter is observable, not silent.
  useEffect(() => {
    const dropped = evidenceEdges.length - edges.length
    if (dropped > 0) {
      console.warn(
        `Exposure map: dropped ${dropped} edge(s) referencing node id(s) absent from the node set.`,
      )
    }
  }, [evidenceEdges, edges])

  const edgeById = useMemo(() => {
    const m: Record<string, ExposureEdge> = {}
    edges.forEach((e, i) => {
      m[`edge-${i}`] = e
    })
    return m
  }, [edges])

  useEffect(() => {
    if (!containerRef.current || !edges.length) return

    const elements: cytoscape.ElementDefinition[] = []
    for (const n of nodes) {
      elements.push({
        data: { id: n.id, label: n.label, isCrownJewel: n.is_crown_jewel ? "true" : "false" },
        group: "nodes",
      })
    }
    edges.forEach((e, i) => {
      elements.push({
        data: { id: `edge-${i}`, source: e.source, target: e.target, edgeType: e.edge_type },
        group: "edges",
      })
    })

    // Cytoscape renders to a <canvas>, which cannot resolve CSS custom
    // properties (`var(--x)`) — passing them yields cytoscape's default gray,
    // which is why the graph edge/nodes rendered gray while the DOM legend
    // swatch (real CSS) showed the correct color. Resolve tokens to concrete
    // values here at init so the canvas gets a real color while staying
    // theme-aware (getComputedStyle reads the active light/dark override).
    const cssVar = (name: string): string =>
      getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    const dsHigh = cssVar("--ds-high") || "#d4893a"        // key-reuse amber
    const dsMedium = cssVar("--ds-medium") || "#8892a4"    // hardware-bridge / node slate
    const accent = `hsl(${cssVar("--accent") || "180 37% 47%"})`  // crown-jewel / selection teal

    // Pitfall 5: rankDir MUST be "LR" (attack-path narrative reads
    // left-to-right), not roadmap.tsx's "TB".
    const layout: cytoscape.LayoutOptions = {
      name: "dagre",
      rankDir: "LR",
      nodeSep: 50,
      rankSep: 90,
      animate: false,
    } as cytoscape.LayoutOptions

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        // Base node style — neutral fill for all nodes (no risk-implying color).
        {
          selector: "node",
          style: {
            "label": "data(label)",
            "font-size": 12,
            "font-family": "JetBrains Mono, ui-monospace, monospace",
            "color": "#fff",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            "width": 150,
            "height": 52,
            "shape": "roundrectangle",
            "background-color": dsMedium,
            "border-width": 0,
          },
        },
        // Crown-jewel badge — small accent-teal ring overlay, not a full recolor.
        {
          selector: "node[isCrownJewel='true']",
          style: {
            "border-width": 3,
            "border-color": accent,
            "border-style": "solid",
          },
        },
        {
          selector: "node:selected",
          style: { "border-width": 3, "border-color": accent },
        },
        // Edge-type taxonomy (D-06/UI-SPEC): key-reuse amber solid,
        // hardware-bridge gray dashed. declared_reachability is Tier B —
        // omitted entirely per 195-SPIKE-DECISION.md DECISION: DEFERRED.
        {
          selector: "edge[edgeType='key_reuse']",
          style: {
            "width": 2,
            "line-color": dsHigh,
            "target-arrow-color": dsHigh,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "line-style": "solid",
          },
        },
        {
          selector: "edge[edgeType='hardware_bridge']",
          style: {
            "width": 2,
            "line-color": dsMedium,
            "target-arrow-color": dsMedium,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "line-style": "dashed",
          },
        },
      ],
      layout,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    })

    // Evidence tooltip (D-09) — shadcn Tooltip anchored near the edge, NOT a
    // native title attribute (must support multi-line evidence body copy).
    cyRef.current.on("mouseover", "edge", (evt) => {
      const edgeId = evt.target.data("id") as string
      const e = edgeById[edgeId]
      if (!e) return
      const pos =
        typeof evt.target.renderedMidpoint === "function"
          ? evt.target.renderedMidpoint()
          : evt.renderedPosition
      setHoveredEdge(e)
      if (pos) setHoverPos({ x: pos.x, y: pos.y })
    })
    cyRef.current.on("mouseout", "edge", () => {
      setHoveredEdge(null)
      setHoverPos(null)
    })

    return () => {
      cyRef.current?.destroy()
      cyRef.current = null
      setHoveredEdge(null)
      setHoverPos(null)
    }
  }, [nodes, edges, edgeById])

  if (loading) return <PageSpinner ariaLabel="Loading quantum exposure map" />

  if (error) {
    return <p className="text-muted-foreground text-sm">{error}</p>
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Quantum Exposure Map</h1>
        <p className="text-muted-foreground text-sm">
          Verified attack-path relationships only — every edge is evidence-backed. No inferred or
          fabricated paths.
        </p>
        {/* Score-firewall reassurance note (D-10) — always visible, not
            conditional on data presence. */}
        <p className="text-xs" style={{ color: "var(--ds-medium)" }}>
          Exposure map data is advisory and does not affect the quantum-readiness score.
        </p>
      </div>

      {edges.length === 0 ? (
        <div className="space-y-2">
          <h2 style={{ fontSize: 20, fontWeight: 600 }}>No path data available</h2>
          <EmptyStateCard message="No verified key-reuse clusters or confirmed hardware crypto-bridge chains were found in this scan. Nothing is fabricated or inferred here — check back after a scan surfaces reusable keys or hardware bridge evidence." />
        </div>
      ) : (
        <TooltipProvider>
          <div className="relative">
            {/* Zoom controls — top-left, mirrors roadmap.tsx precedent */}
            <div className="absolute top-3 left-3 z-10 flex flex-col gap-1">
              <Button
                variant="outline"
                size="icon"
                className="h-7 w-7"
                onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)}
                aria-label="Zoom in"
              >
                <ZoomIn className="h-3 w-3" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-7 w-7"
                onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)}
                aria-label="Zoom out"
              >
                <ZoomOut className="h-3 w-3" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-7 w-7"
                onClick={() => cyRef.current?.fit()}
                aria-label="Fit to screen"
              >
                <Maximize2 className="h-3 w-3" />
              </Button>
            </div>

            {/* Legend panel — top-right (UI-SPEC Component Notes). Tier B
                "Declared reachability" row omitted per DECISION: DEFERRED. */}
            <Card className="absolute top-3 right-3 z-10 w-56">
              <CardContent className="p-3 space-y-2">
                <h2 style={{ fontSize: 16, fontWeight: 600 }}>Edge types</h2>
                <div className="space-y-1 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <span className="inline-block w-4 h-0.5" style={{ background: "var(--ds-high)" }} />
                    Key-reuse cluster
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block w-4 h-0.5"
                      style={{
                        background:
                          "repeating-linear-gradient(to right, var(--ds-medium) 0 3px, transparent 3px 6px)",
                      }}
                    />
                    Hardware crypto-bridge
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Evidence tooltip — positioned near the last-hovered edge midpoint */}
            {hoveredEdge && hoverPos && (
              <Tooltip open>
                <TooltipTrigger asChild>
                  <span
                    className="absolute z-20 w-px h-px"
                    style={{ left: hoverPos.x, top: hoverPos.y }}
                    aria-hidden="true"
                  />
                </TooltipTrigger>
                <TooltipContent side="top">
                  <p className="font-semibold text-xs">Evidence</p>
                  <p className="text-xs whitespace-pre-wrap max-w-[260px]">{hoveredEdge.evidence}</p>
                </TooltipContent>
              </Tooltip>
            )}

            <div
              ref={containerRef}
              role="img"
              aria-label="Quantum exposure map graph. Nodes are endpoints or devices; edges are verified relationships. Hover an edge for its evidence citation."
              className="rounded-lg border border-border bg-card"
              style={{ width: "100%", height: "calc(100vh - 260px)", minHeight: 400 }}
            />
            <p className="text-xs text-muted-foreground mt-1.5 text-center">
              Hover an edge for evidence · Scroll to zoom · Drag to pan
            </p>

            {/* sr-only evidence list — reachable via keyboard/screen-reader
                without hover (D-09, UI-SPEC Dimension 2 checker recommendation). */}
            <ul className="sr-only">
              {edges.map((e, i) => (
                <li
                  key={`edge-evidence-${i}`}
                  aria-label={`Edge from ${e.source} to ${e.target}, ${EDGE_TYPE_LABEL[e.edge_type] ?? e.edge_type}: ${e.evidence}`}
                >
                  {EDGE_TYPE_LABEL[e.edge_type] ?? e.edge_type} — {e.source} to {e.target}: {e.evidence}
                </li>
              ))}
            </ul>
          </div>
        </TooltipProvider>
      )}
    </div>
  )
}
