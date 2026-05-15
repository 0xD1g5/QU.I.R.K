import { useRef, useEffect, useMemo, useState } from "react"
import cytoscape from "cytoscape"
import dagre from "cytoscape-dagre"
import { useScanData } from "@/hooks/useScanData"
import type { RoadmapNode } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { PageSpinner } from "@/components/PageSpinner"
import { ZoomIn, ZoomOut, Maximize2, X } from "lucide-react"

// Register dagre layout (DAG directed graph — per D-16).
// D-24 (IN-02): log via console.error and re-throw genuine failures so
// the visualization fails loudly rather than silently. The /already/i
// message guard swallows HMR re-registration (RESEARCH C-12 Pattern 8).
try {
  cytoscape.use(dagre)
} catch (e) {
  console.error('cytoscape.use(dagre) failed:', e)
  if (!(e instanceof Error) || !/already/i.test(e.message)) throw e
}

const PHASE_COLORS: Record<string, string> = {
  NOW:   "hsl(0, 72%, 51%)",    // Red — Immediate
  NEXT:  "hsl(38, 92%, 50%)",   // Amber — Short-term
  LATER: "hsl(142, 71%, 45%)",  // Green — Long-term
}

const PHASE_LABEL: Record<string, string> = {
  NOW:   "0-30 days",
  NEXT:  "31-90 days",
  LATER: "90+ days",
}

const PHASE_ORDER = ["NOW", "NEXT", "LATER"]

export function RoadmapPage() {
  const { data, loading, error } = useScanData()
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [selected, setSelected] = useState<RoadmapNode | null>(null)

  const nodes = useMemo(() => data?.roadmap?.nodes ?? [], [data])

  // Build nodesByPhase lookup for detail panel
  const nodeById = useMemo(() => {
    const m: Record<string, RoadmapNode> = {}
    for (const n of nodes) m[n.id] = n
    return m
  }, [nodes])

  useEffect(() => {
    if (!containerRef.current || !nodes.length) return

    const nodesByPhase: Record<string, RoadmapNode[]> = {}
    for (const phase of PHASE_ORDER) nodesByPhase[phase] = []
    for (const n of nodes) {
      if (PHASE_ORDER.includes(n.phase)) nodesByPhase[n.phase].push(n)
    }

    const elements: cytoscape.ElementDefinition[] = []

    // Node elements
    for (const n of nodes) {
      elements.push({
        data: { id: n.id, label: n.title, phase: n.phase },
        group: "nodes",
      })
    }

    // Within-phase ordering edges (invisible — force same-phase nodes into a rank column)
    for (const phase of PHASE_ORDER) {
      const pNodes = nodesByPhase[phase]
      for (let i = 0; i < pNodes.length - 1; i++) {
        elements.push({
          data: {
            id: `rank-${pNodes[i].id}-${pNodes[i + 1].id}`,
            source: pNodes[i].id,
            target: pNodes[i + 1].id,
            rankOnly: "true",
          },
          group: "edges",
        })
      }
    }

    // Cross-phase edges: connect last of each phase to ALL nodes in next phase
    for (let pi = 0; pi < PHASE_ORDER.length - 1; pi++) {
      const srcPhase = PHASE_ORDER[pi]
      const tgtPhase = PHASE_ORDER[pi + 1]
      const srcNodes = nodesByPhase[srcPhase]
      const tgtNodes = nodesByPhase[tgtPhase]
      if (!srcNodes.length || !tgtNodes.length) continue
      const anchor = srcNodes[srcNodes.length - 1]
      for (const tgt of tgtNodes) {
        elements.push({
          data: {
            id: `phase-${anchor.id}-${tgt.id}`,
            source: anchor.id,
            target: tgt.id,
            rankOnly: "false",
          },
          group: "edges",
        })
      }
    }

    const layout: cytoscape.LayoutOptions = {
      name: "dagre",
      rankDir: "TB",
      nodeSep: 50,
      rankSep: 90,
      animate: false,
    } as cytoscape.LayoutOptions

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        // Base node style
        {
          selector: "node",
          style: {
            "label": "data(label)",
            "font-size": 12,
            "font-family": "Inter, sans-serif",
            "color": "#fff",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            "width": 150,
            "height": 52,
            "shape": "roundrectangle",
            "background-color": "hsl(240, 5%, 46%)",
            "border-width": 0,
          },
        },
        // Phase-specific colors via data selector (reliable approach)
        { selector: "node[phase='NOW']",   style: { "background-color": PHASE_COLORS.NOW } },
        { selector: "node[phase='NEXT']",  style: { "background-color": PHASE_COLORS.NEXT } },
        { selector: "node[phase='LATER']", style: { "background-color": PHASE_COLORS.LATER } },
        // Selected state
        {
          selector: "node:selected",
          style: { "border-width": 3, "border-color": "hsl(210, 100%, 65%)" },
        },
        // Cross-phase edges (visible arrows)
        {
          selector: "edge[rankOnly='false']",
          style: {
            "width": 2,
            "line-color": "hsl(240, 6%, 40%)",
            "target-arrow-color": "hsl(240, 6%, 40%)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        // Within-phase rank-only edges (invisible)
        {
          selector: "edge[rankOnly='true']",
          style: {
            "opacity": 0,
            "width": 0,
          },
        },
      ],
      layout,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    })

    // Click handler — show detail panel
    cyRef.current.on("tap", "node", (evt) => {
      const nodeId = evt.target.data("id") as string
      cyRef.current?.edges().style({ "line-color": "hsl(240, 6%, 40%)", "target-arrow-color": "hsl(240, 6%, 40%)" })
      evt.target.connectedEdges("[rankOnly='false']").style({
        "line-color": "hsl(210, 100%, 65%)",
        "target-arrow-color": "hsl(210, 100%, 65%)",
      })
      setSelected(nodeById[nodeId] ?? null)
    })

    cyRef.current.on("tap", (evt) => {
      if (evt.target === cyRef.current) {
        cyRef.current?.edges().style({ "line-color": "hsl(240, 6%, 40%)", "target-arrow-color": "hsl(240, 6%, 40%)" })
        setSelected(null)
      }
    })

    return () => {
      cyRef.current?.destroy()
      cyRef.current = null
    }
  }, [nodes, nodeById])

  if (loading) return <PageSpinner ariaLabel="Loading remediation roadmap" />

  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  if (!nodes.length) {
    return (
      <div className="space-y-4 py-8">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Remediation Roadmap</h1>
        <p className="text-muted-foreground text-sm">
          No remediation items in this scan — either no findings exist or the scoring engine produced no recommendations.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Migration Roadmap</h1>
        {/* Legend */}
        <div className="flex gap-4 text-xs text-muted-foreground">
          {PHASE_ORDER.map((phase) => (
            <span key={phase} className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded" style={{ background: PHASE_COLORS[phase] }} />
              {PHASE_LABEL[phase]}
            </span>
          ))}
        </div>
      </div>

      <div className="relative">
        {/* Zoom controls — top-right */}
        <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
          <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.2)} aria-label="Zoom in">
            <ZoomIn className="h-3 w-3" />
          </Button>
          <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 0.8)} aria-label="Zoom out">
            <ZoomOut className="h-3 w-3" />
          </Button>
          <Button variant="outline" size="icon" className="h-7 w-7" onClick={() => cyRef.current?.fit()} aria-label="Fit to screen">
            <Maximize2 className="h-3 w-3" />
          </Button>
        </div>

        {/* Detail panel — bottom-right overlay, always inside graph bounds */}
        {selected && (
          <div
            className="absolute bottom-8 right-3 z-20 w-64 rounded-lg border border-border bg-background/95 p-3 text-sm space-y-2 backdrop-blur-sm shadow-lg"
            style={{ maxHeight: "55%", overflowY: "auto" }}
          >
            <div className="flex items-start justify-between gap-2">
              <span className="font-semibold text-sm leading-snug">{selected.title}</span>
              <Button variant="ghost" size="icon" className="h-5 w-5 shrink-0 -mt-0.5" onClick={() => setSelected(null)} aria-label="Close">
                <X className="h-3 w-3" />
              </Button>
            </div>
            <Badge className="text-xs text-white" style={{ background: PHASE_COLORS[selected.phase] ?? "hsl(240 5% 46%)" }}>
              {PHASE_LABEL[selected.phase] ?? selected.timeframe}
            </Badge>
            {selected.why && (
              <p className="text-xs leading-relaxed text-muted-foreground">{selected.why}</p>
            )}
          </div>
        )}

        <div
          ref={containerRef}
          role="img"
          aria-label="Migration roadmap DAG. Nodes colored by urgency: red = immediate (0-30d), amber = short-term (31-90d), green = long-term (90+d). Click a node to inspect."
          className="rounded-lg border border-border bg-card"
          style={{ width: "100%", height: "calc(100vh - 220px)", minHeight: 400 }}
        />
        <p className="text-xs text-muted-foreground mt-1.5 text-center">Click any node to inspect · Scroll to zoom · Drag to pan</p>
      </div>
    </div>
  )
}
