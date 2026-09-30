import { useRef, useEffect, useMemo, useState } from "react"
import cytoscape from "cytoscape"
import dagre from "cytoscape-dagre"
import { useScanData } from "@/hooks/useScanData"
import type { RoadmapNode } from "@/types/api"
import { formatScoreNumber } from "@/lib/utils"
import { resolveToken, useThemeRevision } from "@/lib/cytoscape-theme"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { PageSpinner } from "@/components/PageSpinner"
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table"
import { ZoomIn, ZoomOut, Maximize2, X } from "lucide-react"

// Phase 181 SURF-03: closure_state labels. `not_observed` is deliberately
// "Not verified this scan" — never "Clean" or "No issues" — so this label
// cannot be read as a safety claim about an item that was simply not
// compared this run.
const CLOSURE_STATE_LABEL: Record<string, string> = {
  open: "Open",
  closed: "Closed",
  not_observed: "Not verified this scan",
  resurfaced: "Resurfaced",
}

// Token names, not literals — CLOSURE_STATE_COLOR below wraps each in `hsl(var(...))`,
// which is a real-DOM-only string (Badge inline `style=`); it is never handed to
// Cytoscape (see src/lib/cytoscape-theme.ts's module docstring for why that would
// silently paint nothing).
const CLOSURE_STATE_TOKEN: Record<string, string> = {
  open: "--status-critical",
  closed: "--qs-node-safe",
  not_observed: "--status-neutral",
  resurfaced: "--status-warning",
}

const CLOSURE_STATE_COLOR: Record<string, string> = Object.fromEntries(
  Object.entries(CLOSURE_STATE_TOKEN).map(([state, token]) => [state, `hsl(var(${token}))`]),
)

// Phase 218 D-07(1): text colour for the closure-state detail-panel badge,
// keyed the SAME as CLOSURE_STATE_TOKEN above (not a static text-white class).
// Each entry is derived from its own background's own AA result in both
// themes: "white" only where the bg already clears 4.5:1 with white in both
// themes (status-critical, status-neutral); --qs-node-safe and
// --status-warning route to their existing -foreground tokens because white
// fails on at least one theme (qs-node-safe: 2.30 both themes;
// status-warning: 2.13 dark).
const CLOSURE_STATE_FG: Record<string, string> = {
  open: "white",
  closed: "hsl(var(--qs-node-safe-foreground))",
  not_observed: "white",
  resurfaced: "hsl(var(--status-warning-foreground))",
}

// Mirrors quirk/scanner/pqc_deadlines.py bucket labels; "unmapped" gets an
// explicit human label rather than being dropped from the burndown table.
const BURNDOWN_BUCKET_LABEL: Record<string, string> = {
  key_establishment: "Key Establishment",
  digital_signature: "Digital Signature",
  unmapped: "Unmapped",
}

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

// Token names — resolved to a HEX value via resolveToken() for the Cytoscape build
// effect below, and wrapped as `hsl(var(...))` (PHASE_COLORS) for real-DOM usage
// (legend swatches, detail-panel Badge fallback).
const PHASE_TOKEN: Record<string, string> = {
  NOW:   "--status-critical", // Red — Immediate
  NEXT:  "--status-warning",  // Amber — Short-term
  LATER: "--qs-node-safe",    // Green — Long-term
}

const PHASE_COLORS: Record<string, string> = Object.fromEntries(
  Object.entries(PHASE_TOKEN).map(([phase, token]) => [phase, `hsl(var(${token}))`]),
)

// Phase 218 D-07(1)/D-07(3): single source of truth for the phase foreground
// colour, keyed the SAME as PHASE_TOKEN above. Each entry is derived from its
// own background's own AA result in both themes: "white" only where the bg
// already clears 4.5:1 with white in both themes (status-critical);
// --status-warning and --qs-node-safe route to their existing -foreground
// tokens because white fails on at least one theme (status-warning: 2.13
// dark; qs-node-safe: 2.30 both themes). "white" is a literal CSS keyword,
// not a --token reference — it is accepted natively by both the real DOM
// (PHASE_FG below) and Cytoscape's canvas renderer (buildRoadmapStyle()), so
// it is the one case that needs no resolveToken() lookup. Both the
// real-DOM detail-panel badge text colour (PHASE_FG) and the Cytoscape
// graph node label colour (buildRoadmapStyle()) derive from this ONE map so
// they cannot drift apart — before D-07(3), buildRoadmapStyle() painted every
// node label the same flat --chart-node-label colour regardless of phase,
// failing AA for NEXT (dark 2.14) and LATER (dark 2.30, light 2.30) while
// NOW stayed wrong in light (2.65) too.
const PHASE_FG_TOKEN: Record<string, string> = {
  NOW:   "white",
  NEXT:  "--status-warning-foreground",
  LATER: "--qs-node-safe-foreground",
}

/** Real-DOM `color:` value for a PHASE_FG_TOKEN entry — "white" stays a
 * literal keyword; anything else is wrapped as `hsl(var(--x))`, Tailwind's
 * own idiom for a runtime `style=` colour. */
function phaseFgToRealDom(tok: string): string {
  return tok === "white" ? "white" : `hsl(var(${tok}))`
}

const PHASE_FG: Record<string, string> = Object.fromEntries(
  Object.entries(PHASE_FG_TOKEN).map(([phase, tok]) => [phase, phaseFgToRealDom(tok)]),
)

const PHASE_LABEL: Record<string, string> = {
  NOW:   "0-30 days",
  NEXT:  "31-90 days",
  LATER: "90+ days",
}

const PHASE_ORDER = ["NOW", "NEXT", "LATER"]

// Cytoscape draws to a <canvas> and cannot resolve CSS custom properties — every colour handed
// to it below is resolved to a concrete hex value via resolveToken() at call time, never a
// var(--x) reference and never a reconstructed HSL function-call string (see cytoscape-theme.ts).
// Building the style array as its own function (rather than inlining it in the effect) is what
// lets the theme-change effect below re-apply fresh colours via cy.style() without tearing down
// and rebuilding the whole graph, which would otherwise reset the user's pan/zoom/selection.
function buildRoadmapStyle(): cytoscape.StylesheetJsonBlock[] {
  const nodeLabelColor = resolveToken("--chart-node-label")
  const neutralColor = resolveToken("--status-neutral")
  const highlightColor = resolveToken("--chart-edge-highlight")
  const phaseColor: Record<string, string> = {
    NOW: resolveToken(PHASE_TOKEN.NOW),
    NEXT: resolveToken(PHASE_TOKEN.NEXT),
    LATER: resolveToken(PHASE_TOKEN.LATER),
  }
  // Phase 218 D-07(3): per-phase label colour, resolved from the SAME
  // PHASE_FG_TOKEN map PHASE_FG (real-DOM) derives from — "white" is a
  // literal CSS keyword Cytoscape accepts natively (no resolveToken() lookup
  // possible or needed); every other entry resolves through resolveToken()
  // like every other Cytoscape colour in this function, never a var(--x)
  // string (see this function's own module-level comment).
  const phaseLabelColor: Record<string, string> = {
    NOW: PHASE_FG_TOKEN.NOW === "white" ? "white" : resolveToken(PHASE_FG_TOKEN.NOW),
    NEXT: PHASE_FG_TOKEN.NEXT === "white" ? "white" : resolveToken(PHASE_FG_TOKEN.NEXT),
    LATER: PHASE_FG_TOKEN.LATER === "white" ? "white" : resolveToken(PHASE_FG_TOKEN.LATER),
  }

  return [
    // Base node style
    {
      selector: "node",
      style: {
        "label": "data(label)",
        "font-size": 12,
        "font-family": "Inter, sans-serif",
        "color": nodeLabelColor,
        "text-valign": "center",
        "text-halign": "center",
        "text-wrap": "wrap",
        "text-max-width": "120px",
        "width": 150,
        "height": 52,
        "shape": "roundrectangle",
        "background-color": neutralColor,
        "border-width": 0,
      },
    },
    // Phase-specific colors via data selector (reliable approach). D-07(3):
    // "color" (label text) is now per-phase too, not the shared base
    // nodeLabelColor — see phaseLabelColor above.
    { selector: "node[phase='NOW']",   style: { "background-color": phaseColor.NOW, "color": phaseLabelColor.NOW } },
    { selector: "node[phase='NEXT']",  style: { "background-color": phaseColor.NEXT, "color": phaseLabelColor.NEXT } },
    { selector: "node[phase='LATER']", style: { "background-color": phaseColor.LATER, "color": phaseLabelColor.LATER } },
    // Selected state
    {
      selector: "node:selected",
      style: { "border-width": 3, "border-color": highlightColor },
    },
    // Cross-phase edges (visible arrows)
    {
      selector: "edge[rankOnly='false']",
      style: {
        "width": 2,
        "line-color": neutralColor,
        "target-arrow-color": neutralColor,
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
  ] as cytoscape.StylesheetJsonBlock[]
}

export function RoadmapPage() {
  const { data, loading, error } = useScanData()
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [selected, setSelected] = useState<RoadmapNode | null>(null)
  const themeRevision = useThemeRevision()

  const nodes = useMemo(() => data?.roadmap?.nodes ?? [], [data])
  const burndown = data?.burndown ?? null
  const projectedScore = data?.projected_score ?? null

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
      style: buildRoadmapStyle(),
      layout,
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    })

    // Click handler — show detail panel
    cyRef.current.on("tap", "node", (evt) => {
      const nodeId = evt.target.data("id") as string
      const neutralColor = resolveToken("--status-neutral")
      const highlightColor = resolveToken("--chart-edge-highlight")
      cyRef.current?.edges().style({ "line-color": neutralColor, "target-arrow-color": neutralColor })
      evt.target.connectedEdges("[rankOnly='false']").style({
        "line-color": highlightColor,
        "target-arrow-color": highlightColor,
      })
      setSelected(nodeById[nodeId] ?? null)
    })

    cyRef.current.on("tap", (evt) => {
      if (evt.target === cyRef.current) {
        const neutralColor = resolveToken("--status-neutral")
        cyRef.current?.edges().style({ "line-color": neutralColor, "target-arrow-color": neutralColor })
        setSelected(null)
      }
    })

    return () => {
      cyRef.current?.destroy()
      cyRef.current = null
    }
  }, [nodes, nodeById])

  // Theme-change-only restyle: re-resolves every token via buildRoadmapStyle() and applies
  // it in place with cy.style(), instead of tearing down and rebuilding the whole graph
  // (which would reset the user's pan/zoom/selection on every toggle). This is the fix for
  // the gap this plan exists to close — none of the effects above ever re-ran on a theme
  // change, so the graph rendered the theme active at first paint forever.
  useEffect(() => {
    if (!cyRef.current) return
    cyRef.current.style(buildRoadmapStyle())
  }, [themeRevision])

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
            {/* 201-UI-V1/S1 fix: the phase/closure/lift badges must render as
                a real flex row (`flex ... gap-1.5`), not bare siblings inside
                the panel's `space-y-2` vertical stack — per the UI-SPEC's
                Layout & Placement Contract ("same row (flex row, gap-1.5)").
                gap-1.5 replaces the prior off-grid ml-1.5 (6px) margins. */}
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge
                className="text-xs"
                style={{
                  background: PHASE_COLORS[selected.phase] ?? "hsl(var(--status-neutral))",
                  color: PHASE_FG[selected.phase] ?? "white",
                }}
              >
                {PHASE_LABEL[selected.phase] ?? selected.timeframe}
              </Badge>
              {/* Phase 181 SURF-03: closure badge is omitted entirely when
                  closure_state is null, rather than showing an "Unknown" chip —
                  null means "no persisted lookup available", not "unknown state". */}
              {selected.closure_state && (
                <Badge
                  className="text-xs"
                  style={{
                    background: CLOSURE_STATE_COLOR[selected.closure_state] ?? "hsl(var(--status-neutral))",
                    color: CLOSURE_STATE_FG[selected.closure_state] ?? "white",
                  }}
                >
                  {CLOSURE_STATE_LABEL[selected.closure_state] ?? selected.closure_state}
                </Badge>
              )}
              {/* Phase 201 LIFT-05: lift badge is omitted entirely when
                  score_lift is null — null means this item's resolution is
                  not modelable, not "zero improvement". A "+0 pts" badge is
                  forbidden by the UI-SPEC. */}
              {selected.score_lift != null && selected.score_lift > 0 && (
                <Badge
                  className="text-xs"
                  style={{
                    background: "var(--ds-ok-dim)",
                    border: "1px solid var(--ds-ok-bdr)",
                    color: "var(--ds-ok)",
                  }}
                >
                  +{formatScoreNumber(selected.score_lift)} pts
                </Badge>
              )}
            </div>
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

      {/* Phase 201 LIFT-05: Projected Score card — sits directly above the
          Remediation Burndown card per the UI-SPEC's Layout & Placement
          Contract. Omitted entirely when projected_score is null (e.g. the
          scan's current score is None, or the aggregate rescore could not
          be computed) — never a placeholder card. No chart/gauge/arrow is
          introduced here; this repo forbids conditionally mounting a
          Recharts child, and this stat sidesteps that hazard by never
          using a chart component at all. */}
      {projectedScore != null && (
        <div className="rounded-lg border border-border bg-card p-4 space-y-2">
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Projected Score</h2>
          <p>
            Projected score if all items resolved:{" "}
            <span style={{ fontSize: 20, fontWeight: 600, color: "var(--ds-ok)" }}>
              {formatScoreNumber(projectedScore)}
            </span>
          </p>
          <p className="text-xs text-muted-foreground">
            Advisory — this projection is a simulation and does not affect the readiness score.
          </p>
        </div>
      )}

      {/* Phase 181 SURF-03: Remediation Burndown — extends this existing
          roadmap surface rather than adding a new tab, since closure is a
          property of the roadmap items already displayed above. Table, not
          a chart: this repo forbids conditionally mounting/unmounting chart
          series children, and a table sidesteps that trap entirely while
          being the more honest presentation for buckets that overlap by
          design (see quirk/intelligence/burndown.py D-36). */}
      <div className="rounded-lg border border-border bg-card p-4 space-y-2">
        <h2 style={{ fontSize: 16, fontWeight: 600 }}>Remediation Burndown</h2>
        <p className="text-xs text-muted-foreground">
          Advisory — remediation closure state and burndown do not affect the readiness score.
        </p>
        {!burndown || burndown.unavailable_reason ? (
          <p className="text-sm text-muted-foreground">
            {burndown?.unavailable_reason ?? "Closure state was not computed for this scan."}
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Deadline</TableHead>
                <TableHead>Standard</TableHead>
                <TableHead className="text-right">Fingerprints</TableHead>
                <TableHead className="text-right">Open</TableHead>
                <TableHead className="text-right">Closed</TableHead>
                <TableHead className="text-right">Not Verified</TableHead>
                <TableHead className="text-right">Resurfaced</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* unmapped is rendered like any other bucket, never filtered
                  out — some algorithms map to no deadline and the table
                  should say so rather than implying complete coverage. No
                  column here is ever summed across rows (D-36). */}
              {burndown.buckets.map((bucket) => (
                <TableRow key={bucket.bucket}>
                  <TableCell className="font-medium">
                    {BURNDOWN_BUCKET_LABEL[bucket.bucket] ?? bucket.bucket}
                    {bucket.date ? ` (${bucket.date})` : " — No deadline mapped"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{bucket.standard ?? "—"}</TableCell>
                  <TableCell className="text-right">{bucket.fingerprints}</TableCell>
                  <TableCell className="text-right">{bucket.open}</TableCell>
                  <TableCell className="text-right">{bucket.closed}</TableCell>
                  <TableCell className="text-right">{bucket.not_observed}</TableCell>
                  <TableCell className="text-right">{bucket.resurfaced}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}
