import { useRef, useEffect } from "react"
import cytoscape from "cytoscape"
import dagre from "cytoscape-dagre"
import { useScanData } from "@/hooks/useScanData"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react"

// Register dagre layout (DAG directed graph — per D-16)
try {
  cytoscape.use(dagre as cytoscape.Ext)
} catch {
  // already registered
}

// Timeframe → node color per UI-SPEC Section 5
const TIMEFRAME_COLOR: Record<string, string> = {
  "0-30 days": "hsl(0 72% 51%)",     // Red 600 — Immediate
  "31-90 days": "hsl(38 92% 50%)",   // Amber 500 — Short-term
  "90+ days": "hsl(142 71% 45%)",    // Green 500 — Long-term
}

export function RoadmapPage() {
  const { data, loading, error } = useScanData()
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  const nodes = data?.roadmap?.nodes ?? []
  const edges = data?.roadmap?.edges ?? []

  useEffect(() => {
    if (!containerRef.current || !nodes.length) return

    const elements: cytoscape.ElementDefinition[] = [
      ...nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.title,
          timeframe: n.timeframe,
          why: n.why ?? "",
          color: TIMEFRAME_COLOR[n.timeframe] ?? "hsl(240 5% 46%)",
        },
        group: "nodes" as const,
      })),
      ...edges.map((e) => ({
        data: {
          id: `edge-${e.source}-${e.target}`,
          source: e.source,
          target: e.target,
          label: e.reason ?? "",
        },
        group: "edges" as const,
      })),
    ]

    // dagre layout for DAG; breadthfirst fallback if dagre not available
    const layout: cytoscape.LayoutOptions = {
      name: "dagre",
      rankDir: "TB",
      nodeSep: 60,
      rankSep: 80,
      animate: false,
    } as cytoscape.LayoutOptions

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            "label": "data(label)",
            "font-size": 12,
            "font-family": "Inter, sans-serif",
            "color": "#fff",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            "width": 140,
            "height": 50,
            "shape": "roundrectangle",
          },
        },
        {
          selector: "edge",
          style: {
            "width": 2,
            "line-color": "hsl(240 6% 30%)",
            "target-arrow-color": "hsl(240 6% 30%)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "label": "data(label)",
            "font-size": 10,
            "color": "hsl(240 5% 65%)",
            "text-rotation": "autorotate",
          },
        },
      ],
      layout,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    })

    return () => {
      cyRef.current?.destroy()
      cyRef.current = null
    }
  }, [nodes, edges])

  if (loading) {
    return (
      <div className="space-y-4">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Migration Roadmap</h1>
        <Skeleton className="w-full" style={{ height: "calc(100vh - 200px)", minHeight: 400 }} />
      </div>
    )
  }

  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  if (!nodes.length) {
    return (
      <div className="space-y-4">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Migration Roadmap</h1>
        <div className="text-center py-12">
          <h2 className="text-foreground font-semibold text-xl">No migration roadmap generated</h2>
          <p className="text-muted-foreground mt-2 text-sm">
            Run a scan with at least one finding to generate a prioritized migration roadmap.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Migration Roadmap</h1>
        {/* Legend */}
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded" style={{ background: "hsl(0 72% 51%)" }} />
            Immediate (0-30d)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded" style={{ background: "hsl(38 92% 50%)" }} />
            Short-term (31-90d)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded" style={{ background: "hsl(142 71% 45%)" }} />
            Long-term (90+d)
          </span>
        </div>
      </div>

      <div className="relative">
        {/* Zoom controls */}
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
        <div
          ref={containerRef}
          role="img"
          aria-label="Migration roadmap directed acyclic graph. Nodes represent migration tasks colored by urgency: red = immediate, amber = short-term, green = long-term."
          style={{ width: "100%", height: "calc(100vh - 220px)", minHeight: 400, background: "hsl(240 10% 4%)", borderRadius: 8 }}
        />
      </div>
    </div>
  )
}
