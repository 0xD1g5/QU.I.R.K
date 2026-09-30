import React, { useRef, useEffect, useMemo, useState } from "react"
import cytoscape from "cytoscape"
import coseBilkent from "cytoscape-cose-bilkent"
import { useScanData } from "@/hooks/useScanData"
import type { CbomComponent, HardwareComponent } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CbomSkeleton } from "./cbom.skeleton"
import { EmptyStateCard } from "@/components/EmptyStateCard"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { ZoomIn, ZoomOut, Maximize2, X } from "lucide-react"
import { firstNonZeroComp } from "./cbom-utils"
import { resolveToken, useThemeRevision } from "@/lib/cytoscape-theme"

// Register Cytoscape layout extension once.
// D-24 (IN-02): log via console.error and re-throw genuine failures so
// the visualization fails loudly rather than silently. The /already/i
// message guard swallows HMR re-registration (RESEARCH C-12 Pattern 8).
try {
  cytoscape.use(coseBilkent)
} catch (e) {
  console.error('cytoscape.use(coseBilkent) failed:', e)
  if (!(e instanceof Error) || !/already/i.test(e.message)) throw e
}

// Token names, not literals. QS_TOKEN is the single source of truth for which token each
// quantum-safety state maps to; QS_NODE_COLOR (real-DOM `style=` legend swatches below) reads
// from it, and QS_BADGE mirrors it for every state whose fill is legible behind text.
//
// DELIBERATE DIVERGENCE — Safe. QS_TOKEN's Safe is `--qs-node-safe` (142 71% 45%, #21c45d): a
// Cytoscape NODE FILL, correct for a graph node and a legend swatch, where nothing is drawn on
// top of it. QS_BADGE's Safe is `--status-safe-deep` (142 71% 30%, #16833e), because a badge
// puts white text ON the fill and #21c45d + white is 2.30:1 — below AA's 4.5:1 and even below
// the 3:1 large-text allowance. #16833e + white is 4.83:1.
//
// Do NOT "restore consistency" by pointing QS_BADGE.Safe back at QS_TOKEN.Safe. That is exactly
// the regression plan 213-07 shipped: it replaced the literal `hsl(142_71%_30%)` with
// `var(--qs-node-safe)` — same hue, same saturation, lightness 30% -> 45%, which reads as the
// same green in review but is the one channel contrast depends on. The 30% was deliberate
// (`4d18cdf4`, 165-04, "flip teal/severity foregrounds to AA-clearing dark tokens"). It shipped
// in v5.25.0 and turned the `Axe + Console Gate` red for five consecutive runs on main.
// `src/components/__tests__/cbom-badge-contrast-guard.test.ts` now fails if it comes back.
// The sibling sites `findings.tsx:145` and this file's own TIER_BADGE "Tier 3" use
// `--status-safe-deep` for the same reason.
//
// QS_BADGE's class strings must stay FULLY STATIC — never built via template-literal
// interpolation from QS_TOKEN. Tailwind's JIT scanner does a static regex pass over raw
// source text (including comments) and does not evaluate JS expressions, so an interpolated
// class candidate is scanned as its literal, unresolved source text and emits broken,
// unparseable CSS at build time (confirmed live: a production build with an interpolated
// class here failed at the lightningcss minify step, and even failed a SECOND time from an
// interpolated example previously written directly into this comment). QS_NODE_COLOR has no
// such constraint — it is a plain runtime string handed to an inline `style=` prop, which
// Tailwind's scanner never looks at.
const QS_TOKEN: Record<string, string> = {
  Safe: "--qs-node-safe",
  "At Risk": "--status-warning",
  Vulnerable: "--status-critical",
  Unknown: "--status-neutral",
}

const QS_BADGE: Record<string, string> = {
  Safe: "bg-[hsl(var(--status-safe-deep))] text-white",
  "At Risk": "bg-[hsl(var(--status-warning))] text-[hsl(var(--status-warning-foreground))]",
  Vulnerable: "bg-[hsl(var(--status-critical))] text-white",
  Unknown: "bg-[hsl(var(--status-neutral))] text-white",
}

const QS_NODE_COLOR: Record<string, string> = {
  Safe: `hsl(var(${QS_TOKEN.Safe}))`,
  "At Risk": `hsl(var(${QS_TOKEN["At Risk"]}))`,
  Vulnerable: `hsl(var(${QS_TOKEN.Vulnerable}))`,
  Unknown: `hsl(var(${QS_TOKEN.Unknown}))`,
}

// ── Table Tab ──────────────────────────────────────────────────────────────

interface CbomTableProps {
  components: CbomComponent[]
}

function CbomTable({ components }: CbomTableProps) {
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
      <EmptyStateCard message="No CBOM components in this scan — ensure the scanner completed successfully and that motion + data-at-rest scanners ran." />
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
          <SelectTrigger className="w-40 h-8 text-sm" aria-label="Filter by quantum safety">
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
        <Table regionLabel="Cryptographic algorithm inventory">
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Algorithm</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Type</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Key Size</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Quantum Safety</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Source Systems</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((c, i) => {
              const sources = c.source_systems.slice(0, 3)
              const overflow = c.source_systems.length - 3
              return (
                <TableRow key={i}>
                  <TableCell className="font-mono text-xs">{c.algorithm}</TableCell>
                  <TableCell className="text-sm">{c.type ?? "—"}</TableCell>
                  <TableCell className="text-sm">
                    {c.key_size ? `${c.key_size} bits` : "—"}
                  </TableCell>
                  <TableCell>
                    {c.quantum_safety ? (
                      <Badge className={`${QS_BADGE[c.quantum_safety] ?? ""} text-xs`}>
                        {c.quantum_safety}
                      </Badge>
                    ) : <span className="text-muted-foreground">—</span>}
                  </TableCell>
                  <TableCell className="text-xs">
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

// ── Hardware Inventory ─────────────────────────────────────────────────────

// The underscore-HSL literal formerly here was a 213-02 near-duplicate collapse onto
// --status-neutral (see 213-02-SUMMARY.md's collapse table) — not a distinct token.
const HW_DEVICE_BADGE = "bg-[hsl(var(--badge-hardware-device))] text-white"
const HW_FIRMWARE_BADGE = "bg-[hsl(var(--status-neutral))] text-white"

const TIER_BADGE: Record<string, string> = {
  "Tier 1": "bg-[hsl(var(--status-critical))] text-white",
  "Tier 2": "bg-[hsl(var(--status-warning))] text-[hsl(var(--status-warning-foreground))]",
  "Tier 3": "bg-[hsl(var(--status-safe-deep))] text-white",
  "Tier N/A": "bg-[hsl(var(--status-neutral))] text-white",
}

function HardwareInventory({ devices }: { devices: HardwareComponent[] }) {
  if (!devices.length) return null

  return (
    <div className="space-y-3 mt-6">
      <h2 style={{ fontSize: 16, fontWeight: 600 }}>Hardware Inventory</h2>
      <div className="rounded-md border border-border">
        <Table regionLabel="Hardware inventory">
          <TableHeader>
            <TableRow>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Type</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Host</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Port</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Vendor</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Model</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">PQC Status</TableHead>
              <TableHead scope="col" className="text-xs font-semibold text-foreground">Remediation Tier</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {devices.map((d, i) => (
              <React.Fragment key={`hw-${i}`}>
                <TableRow>
                  <TableCell>
                    <Badge className={`${HW_DEVICE_BADGE} text-xs`}>[DEVICE]</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{d.host}</TableCell>
                  <TableCell className="text-sm">{d.port}</TableCell>
                  <TableCell className="text-sm">{d.vendor}</TableCell>
                  <TableCell className="text-sm">{d.model}</TableCell>
                  <TableCell>
                    <Badge className={`${QS_BADGE[d.pqc_status] ?? QS_BADGE["Unknown"]} text-xs`}>
                      {d.pqc_status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={`${TIER_BADGE[d.remediation_tier] ?? TIER_BADGE["Tier N/A"]} text-xs`}>
                      {d.remediation_tier}
                    </Badge>
                  </TableCell>
                </TableRow>
                <TableRow className="bg-muted/30">
                  <TableCell>
                    <Badge className={`${HW_FIRMWARE_BADGE} text-xs`}>[FIRMWARE]</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{d.host}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{d.port}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{d.vendor}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{d.model}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{d.pqc_status}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{d.remediation_tier}</TableCell>
                </TableRow>
              </React.Fragment>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}

// ── Graph Tab ──────────────────────────────────────────────────────────────

type NodeDetail =
  | { nodeType: "algorithm"; id: string; label: string; qs: string; keySize: number | null; type: string; systems: string[] }
  | { nodeType: "system"; id: string; label: string; algorithms: string[] }

// Cytoscape draws to a <canvas> and cannot resolve CSS custom properties — every colour handed
// to it below is resolved to a concrete hex value via resolveToken() at call time, never a
// var(--x) reference and never a reconstructed HSL function-call string (see cytoscape-theme.ts).
// Quantum-safety colour is expressed as an attribute SELECTOR (node[qs='...']) rather than a
// per-element `data(color)` mapper, so a theme toggle only needs to re-apply this stylesheet via
// cy.style() rather than walking every element and rewriting its data.
function buildCbomGraphStyle(): cytoscape.StylesheetJsonBlock[] {
  const nodeLabelColor = resolveToken("--chart-node-label")
  const slateDark = resolveToken("--chart-slate-dark")
  const slateMid = resolveToken("--chart-slate-mid")
  const slateLight = resolveToken("--chart-slate-light")
  const highlightColor = resolveToken("--chart-edge-highlight")
  const neutralColor = resolveToken("--status-neutral")
  const qsColor: Record<string, string> = {
    Safe: resolveToken(QS_TOKEN.Safe),
    "At Risk": resolveToken(QS_TOKEN["At Risk"]),
    Vulnerable: resolveToken(QS_TOKEN.Vulnerable),
    Unknown: resolveToken(QS_TOKEN.Unknown),
  }

  return [
    {
      selector: "node[nodeType='algorithm'][qs='Safe']",
      style: { "background-color": qsColor.Safe },
    },
    {
      selector: "node[nodeType='algorithm'][qs='At Risk']",
      style: { "background-color": qsColor["At Risk"] },
    },
    {
      selector: "node[nodeType='algorithm'][qs='Vulnerable']",
      style: { "background-color": qsColor.Vulnerable },
    },
    {
      selector: "node[nodeType='algorithm'][qs='Unknown']",
      style: { "background-color": qsColor.Unknown },
    },
    {
      selector: "node[nodeType='algorithm']",
      style: {
        "label": "data(label)",
        "font-size": 12,
        "font-family": "monospace",
        "color": nodeLabelColor,
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "wrap",
        "text-max-width": "90px",
        "width": 90,
        "height": 90,
        "shape": "ellipse",
        "border-width": 0,
      },
    },
    {
      selector: "node[nodeType='system']",
      style: {
        "background-color": slateDark,
        "label": "data(label)",
        "font-size": 11,
        "color": slateLight,
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "wrap",
        "text-max-width": "110px",
        "width": 120,
        "height": 36,
        "shape": "roundrectangle",
        "border-width": 1,
        "border-color": slateMid,
      },
    },
    {
      selector: "node:selected",
      style: {
        "border-width": 3,
        "border-color": highlightColor,
      },
    },
    {
      selector: "edge",
      style: {
        "width": 1.5,
        "line-color": neutralColor,
        "opacity": 0.8,
        "curve-style": "bezier",
      },
    },
    {
      selector: "edge.highlighted",
      style: {
        "line-color": highlightColor,
        "opacity": 1,
        "width": 2.5,
      },
    },
  ] as cytoscape.StylesheetJsonBlock[]
}

function CbomGraph({ components }: { components: CbomComponent[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [selected, setSelected] = useState<NodeDetail | null>(null)
  const themeRevision = useThemeRevision()

  // Build lookup maps for click handler
  const algBySystem = useMemo(() => {
    const m: Record<string, string[]> = {}
    for (const comp of components) {
      for (const sys of comp.source_systems) {
        if (!m[sys]) m[sys] = []
        m[sys].push(comp.algorithm)
      }
    }
    return m
  }, [components])

  const compByAlg = useMemo(() => {
    const m: Record<string, CbomComponent[]> = {}
    for (const comp of components) {
      if (!m[comp.algorithm]) m[comp.algorithm] = []
      m[comp.algorithm].push(comp)
    }
    return m
  }, [components])

  useEffect(() => {
    if (!containerRef.current || !components.length) return

    const elements: cytoscape.ElementDefinition[] = []
    const systemsSeen = new Set<string>()

    for (const comp of components) {
      elements.push({
        data: {
          id: `alg-${comp.algorithm}`,
          label: comp.algorithm,
          nodeType: "algorithm",
          qs: comp.quantum_safety ?? "Unknown",
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
      ? { name: "breadthfirst", roots: components.map((c) => `alg-${c.algorithm}`), directed: false, spacingFactor: 1.6 }
      : { name: "cose-bilkent", animate: false, randomize: true, nodeRepulsion: 10000 }

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: buildCbomGraphStyle(),
      layout,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    })

    // Click handler — show detail panel
    cyRef.current.on("tap", "node", (evt) => {
      const node = evt.target
      const d = node.data()

      // Highlight connected edges
      cyRef.current?.edges().removeClass("highlighted")
      node.connectedEdges().addClass("highlighted")

      if (d.nodeType === "algorithm") {
        // compByAlg maps algorithm -> array; pick first-non-zero (D-27, closes react-frontend/IN-05)
        const comp = firstNonZeroComp(compByAlg[d.label])
        setSelected({
          nodeType: "algorithm",
          id: d.id,
          label: d.label,
          qs: comp?.quantum_safety ?? d.qs ?? "Unknown",
          keySize: comp?.key_size ?? null,
          type: comp?.type ?? "—",
          systems: comp?.source_systems ?? [],
        })
      } else {
        setSelected({
          nodeType: "system",
          id: d.id,
          label: d.label,
          algorithms: algBySystem[d.label] ?? [],
        })
      }
    })

    // Click on background — deselect
    cyRef.current.on("tap", (evt) => {
      if (evt.target === cyRef.current) {
        cyRef.current?.edges().removeClass("highlighted")
        setSelected(null)
      }
    })

    return () => {
      cyRef.current?.destroy()
      cyRef.current = null
    }
  }, [components, compByAlg, algBySystem])

  // Theme-change-only restyle — re-resolves every token and re-applies via cy.style()
  // instead of tearing down and rebuilding the graph, preserving pan/zoom/selection.
  useEffect(() => {
    if (!cyRef.current) return
    cyRef.current.style(buildCbomGraphStyle())
  }, [themeRevision])

  if (!components.length) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground text-sm">
        No CBOM data to graph.
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Legend — top-left overlay */}
      <div className="absolute top-3 left-3 z-10 flex flex-col gap-1 text-xs bg-background/90 border border-border rounded px-2 py-1.5 backdrop-blur-sm">
        <span className="text-muted-foreground font-medium mb-0.5">Algorithm</span>
        {Object.entries(QS_NODE_COLOR).map(([label, color]) => (
          <span key={label} className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full" style={{ background: color }} />
            {label}
          </span>
        ))}
        <span className="text-muted-foreground font-medium mt-1 mb-0.5">System</span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-3 h-2.5 rounded" style={{ background: "hsl(var(--chart-slate-mid))" }} />
          Host:Port
        </span>
      </div>

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
          className="absolute bottom-8 right-3 z-20 w-60 rounded-lg border border-border bg-background/95 p-3 text-sm space-y-2 backdrop-blur-sm shadow-lg"
          style={{ maxHeight: "60%", overflowY: "auto" }}
        >
          <div className="flex items-start justify-between gap-2">
            <span className="font-semibold font-mono text-xs break-all leading-snug">{selected.label}</span>
            <Button variant="ghost" size="icon" className="h-5 w-5 shrink-0 -mt-0.5" onClick={() => setSelected(null)} aria-label="Close">
              <X className="h-3 w-3" />
            </Button>
          </div>

          {selected.nodeType === "algorithm" && (
            <>
              <div className="flex items-center gap-2">
                <Badge className={`${QS_BADGE[selected.qs] ?? ""} text-xs`}>{selected.qs}</Badge>
                <span className="text-xs text-muted-foreground capitalize">{selected.type}</span>
                {selected.keySize && <span className="text-xs text-muted-foreground">{selected.keySize}b</span>}
              </div>
              <div className="space-y-0.5">
                <div className="text-xs text-muted-foreground">On {selected.systems.length} system{selected.systems.length !== 1 ? "s" : ""}</div>
                {selected.systems.map((s) => (
                  <div key={s} className="font-mono text-xs text-muted-foreground bg-muted/40 px-1.5 py-0.5 rounded">{s}</div>
                ))}
              </div>
            </>
          )}

          {selected.nodeType === "system" && (
            <ul className="space-y-1">
              {selected.algorithms.map((alg) => {
                const comp = firstNonZeroComp(compByAlg[alg])  // D-27 (closes react-frontend/IN-05)
                return (
                  <li key={alg} className="flex items-center gap-2">
                    <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ background: QS_NODE_COLOR[comp?.quantum_safety ?? "Unknown"] ?? QS_NODE_COLOR.Unknown }} />
                    <span className="font-mono text-xs">{alg}</span>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}

      <div
        ref={containerRef}
        role="img"
        aria-label="CBOM algorithm-to-system bipartite graph. Click a node to inspect."
        className="rounded-lg border border-border bg-card"
        style={{ width: "100%", height: "calc(100vh - 260px)", minHeight: 400 }}
      />
      <p className="text-xs text-muted-foreground mt-1.5 text-center">Click any node to inspect · Scroll to zoom · Drag to pan</p>
    </div>
  )
}

// ── Page ───────────────────────────────────────────────────────────────────

export function CbomPage() {
  const { data, loading, error } = useScanData()
  // Stabilize reference so CbomGraph's useEffect dep array doesn't trigger on every parent render
  const components = useMemo(() => data?.cbom_components ?? [], [data])
  const hardwareDevices = useMemo(() => data?.hardware_devices ?? [], [data])

  // Lift segment filter to page scope so BOTH the Table and Graph tabs share
  // the same filtered dataset (IN-03: segment filter applies to the whole page,
  // not just the table tab).
  const [segmentFilter, setSegmentFilter] = useState("all")

  const distinctSegments = useMemo(() => {
    const segs = components
      .map((c) => c.segment)
      .filter((s): s is string => typeof s === "string" && s.length > 0)
    return Array.from(new Set(segs)).sort()
  }, [components])

  const filteredComponents = useMemo(
    () =>
      segmentFilter === "all"
        ? components
        : components.filter((c) => c.segment === segmentFilter),
    [components, segmentFilter],
  )

  if (loading) return <CbomSkeleton />

  if (error) return <p className="text-muted-foreground text-sm">{error}</p>

  return (
    <div className="space-y-4">
      <h1 style={{ fontSize: 20, fontWeight: 600 }}>CBOM Viewer</h1>
      {/* UI-FIX-1: segment filter lives above <Tabs> so it is visible on both
          the Table and Graph tabs. State + filtered dataset remain lifted to
          CbomPage scope (IN-03); only the Select JSX moved here. */}
      <Select value={segmentFilter} onValueChange={setSegmentFilter}>
        <SelectTrigger className="w-40 h-8 text-sm" aria-label="Filter by segment">
          <SelectValue placeholder="All segments" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All segments</SelectItem>
          {distinctSegments.map((seg) => (
            <SelectItem key={seg} value={seg}>{seg}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Tabs defaultValue="table">
        <TabsList>
          <TabsTrigger value="table">Table</TabsTrigger>
          <TabsTrigger value="graph">Graph</TabsTrigger>
        </TabsList>
        <TabsContent value="table" className="mt-4">
          <CbomTable components={filteredComponents} />
          <HardwareInventory devices={hardwareDevices} />
        </TabsContent>
        <TabsContent value="graph" className="mt-4">
          <CbomGraph components={filteredComponents} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
