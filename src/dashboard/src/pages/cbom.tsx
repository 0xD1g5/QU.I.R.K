import { useRef, useEffect, useMemo, useState } from "react"
import cytoscape from "cytoscape"
import coseBilkent from "cytoscape-cose-bilkent"
import { useScanData } from "@/hooks/useScanData"
import type { CbomComponent } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react"

// Register Cytoscape layout extension once
try {
  cytoscape.use(coseBilkent as cytoscape.Ext)
} catch {
  // already registered
}

const QS_BADGE: Record<string, string> = {
  Safe: "bg-[hsl(142_71%_45%)] text-white",
  "At Risk": "bg-[hsl(38_92%_50%)] text-black",
  Vulnerable: "bg-[hsl(0_72%_51%)] text-white",
  Unknown: "bg-[hsl(240_5%_46%)] text-white",
}

const QS_NODE_COLOR: Record<string, string> = {
  Safe: "hsl(142 71% 45%)",
  "At Risk": "hsl(38 92% 50%)",
  Vulnerable: "hsl(0 72% 51%)",
  Unknown: "hsl(240 5% 46%)",
}

// ── Table Tab ──────────────────────────────────────────────────────────────

function CbomTable({ components }: { components: CbomComponent[] }) {
  const [qsFilter, setQsFilter] = useState<string>("all")
  const [search, setSearch] = useState("")

  const filtered = useMemo(() => {
    return components.filter((c) => {
      const matchQs = qsFilter === "all" || c.quantum_safety === qsFilter
      const matchSearch = !search || c.algorithm.toLowerCase().includes(search.toLowerCase())
      return matchQs && matchSearch
    })
  }, [components, qsFilter, search])

  if (!components.length) {
    return (
      <div className="text-center py-12">
        <h2 className="text-foreground font-semibold text-xl">No CBOM data available</h2>
        <p className="text-muted-foreground mt-2 text-sm">
          The most recent scan did not produce CBOM output. Ensure the scanner completed successfully.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-3 items-center">
        <Input
          placeholder="Filter algorithm..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs h-8 text-sm"
        />
        <Select value={qsFilter} onValueChange={setQsFilter}>
          <SelectTrigger className="w-40 h-8 text-sm">
            <SelectValue placeholder="Quantum Safety" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="Safe">Safe</SelectItem>
            <SelectItem value="At Risk">At Risk</SelectItem>
            <SelectItem value="Vulnerable">Vulnerable</SelectItem>
            <SelectItem value="Unknown">Unknown</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="text-xs font-semibold">Algorithm</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Type</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Key Size</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Quantum Safety</TableHead>
              <TableHead scope="col" className="text-xs font-semibold">Source Systems</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((c, i) => {
              const sources = c.source_systems.slice(0, 3)
              const overflow = c.source_systems.length - 3
              return (
                <TableRow key={i}>
                  <TableCell className="font-mono text-xs">{c.algorithm}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{c.type ?? "—"}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {c.key_size ? `${c.key_size} bits` : "—"}
                  </TableCell>
                  <TableCell>
                    {c.quantum_safety ? (
                      <Badge className={`${QS_BADGE[c.quantum_safety] ?? ""} text-xs`}>
                        {c.quantum_safety}
                      </Badge>
                    ) : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {sources.join(", ")}
                    {overflow > 0 && <span className="ml-1 text-accent">+{overflow} more</span>}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

// ── Graph Tab ──────────────────────────────────────────────────────────────

function CbomGraph({ components }: { components: CbomComponent[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)

  useEffect(() => {
    if (!containerRef.current || !components.length) return

    // Build bipartite graph: algorithm nodes + system nodes, edges = usage
    const elements: cytoscape.ElementDefinition[] = []
    const systemsSeen = new Set<string>()

    for (const comp of components) {
      elements.push({
        data: {
          id: `alg-${comp.algorithm}`,
          label: comp.algorithm,
          nodeType: "algorithm",
          qs: comp.quantum_safety ?? "Unknown",
          color: QS_NODE_COLOR[comp.quantum_safety ?? "Unknown"] ?? QS_NODE_COLOR.Unknown,
        },
        group: "nodes",
      })
      for (const sys of comp.source_systems) {
        if (!systemsSeen.has(sys)) {
          systemsSeen.add(sys)
          elements.push({
            data: {
              id: `sys-${sys}`,
              label: sys,
              nodeType: "system",
              color: "hsl(240 6% 25%)",
            },
            group: "nodes",
          })
        }
        elements.push({
          data: {
            id: `edge-${comp.algorithm}-${sys}`,
            source: `alg-${comp.algorithm}`,
            target: `sys-${sys}`,
            weight: 1,
          },
          group: "edges",
        })
      }
    }

    const layout = components.length < 15
      ? { name: "breadthfirst", roots: components.map((c) => `alg-${c.algorithm}`), directed: false }
      : { name: "cose-bilkent", animate: false, randomize: true, nodeRepulsion: 8000 }

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node[nodeType='algorithm']",
          style: {
            "background-color": "data(color)",
            "label": "data(label)",
            "font-size": 11,
            "font-family": "monospace",
            "color": "#fff",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "ellipsis",
            "text-max-width": "80px",
            "width": 80,
            "height": 80,
            "shape": "ellipse",
          },
        },
        {
          selector: "node[nodeType='system']",
          style: {
            "background-color": "data(color)",
            "label": "data(label)",
            "font-size": 10,
            "color": "hsl(240 5% 65%)",
            "text-valign": "bottom",
            "text-halign": "center",
            "text-wrap": "ellipsis",
            "text-max-width": "90px",
            "width": 60,
            "height": 30,
            "shape": "roundrectangle",
          },
        },
        {
          selector: "edge",
          style: {
            "width": 1.5,
            "line-color": "hsl(240 6% 30%)",
            "opacity": 0.7,
            "curve-style": "bezier",
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
  }, [components])

  if (!components.length) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        No CBOM data to graph.
      </div>
    )
  }

  return (
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
        aria-label="CBOM algorithm-to-system bipartite graph. Algorithm nodes colored by quantum safety: green = safe, amber = at risk, red = vulnerable."
        style={{ width: "100%", height: "calc(100vh - 260px)", minHeight: 400, background: "hsl(240 10% 4%)", borderRadius: 8 }}
      />
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────

export function CbomPage() {
  const { data, loading, error } = useScanData()

  if (loading) {
    return (
      <div className="space-y-4">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>CBOM Viewer</h1>
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}</div>
      </div>
    )
  }

  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  const components = data?.cbom_components ?? []

  return (
    <div className="space-y-4">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>CBOM Viewer</h1>
      <Tabs defaultValue="table">
        <TabsList>
          <TabsTrigger value="table">Table</TabsTrigger>
          <TabsTrigger value="graph">Graph</TabsTrigger>
        </TabsList>
        <TabsContent value="table" className="mt-4">
          <CbomTable components={components} />
        </TabsContent>
        <TabsContent value="graph" className="mt-4">
          <CbomGraph components={components} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
