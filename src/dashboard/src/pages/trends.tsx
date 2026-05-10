import { useTrendsData } from "@/hooks/useTrendsData"
import { useTimelineData } from "@/hooks/useTimelineData"
import type { SampleFinding } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { PageSpinner } from "@/components/PageSpinner"
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { LineChart, Line, XAxis, YAxis } from "recharts"
import {
  ChartContainer,
  ChartTooltip,
} from "@/components/ui/chart"
import type { ChartConfig } from "@/components/ui/chart"

const TIMELINE_CHART_CONFIG: ChartConfig = {
  score:           { label: "Overall",        color: "hsl(var(--quantum-safe))" },
  hygiene:         { label: "Hygiene",        color: "hsl(180 37% 47%)" },
  modern_tls:      { label: "TLS",            color: "hsl(213 94% 68%)" },
  identity_trust:  { label: "Identity",       color: "hsl(38 92% 50%)" },
  agility_signals: { label: "Agility",        color: "hsl(28 64% 52%)" },
  data_at_rest:    { label: "Data at Rest",   color: "hsl(270 50% 60%)" },
  data_in_motion:  { label: "Data in Motion", color: "hsl(152 47% 45%)" },
}

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH: "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM: "bg-[hsl(38_92%_50%)] text-black",
  LOW: "bg-[hsl(213_94%_68%)] text-black",
  INFO: "bg-[hsl(240_5%_46%)] text-white",
}

function ScoreDeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <Badge variant="outline">— First scan</Badge>
  if (delta > 0) return (
    <Badge className="bg-[hsl(var(--quantum-safe))] text-white">
      ▲ +{delta} pts
    </Badge>
  )
  if (delta < 0) return (
    <Badge className="bg-[hsl(var(--destructive))] text-white">
      ▼ {delta} pts
    </Badge>
  )
  return <Badge variant="outline" className="text-muted-foreground">No change</Badge>
}

function SampleTable({ items }: { items: SampleFinding[] }) {
  if (items.length === 0) return null
  return (
    <details className="rounded-md border border-border">
      <summary className="cursor-pointer px-4 py-2 text-sm font-semibold">
        Show {items.length} samples
      </summary>
      <div className="rounded-md border-t border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Host</TableHead>
              <TableHead>Port</TableHead>
              <TableHead>Protocol</TableHead>
              <TableHead>Severity</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((f, i) => (
              <TableRow key={`${f.host}-${f.port}-${f.protocol}-${i}`} className="hover:bg-accent/5">
                <TableCell className="text-sm py-2">{f.host}</TableCell>
                <TableCell className="text-sm py-2">{f.port}</TableCell>
                <TableCell className="text-sm py-2">{f.protocol}</TableCell>
                <TableCell className="text-sm py-2">
                  <Badge className={`${SEVERITY_STYLES[f.severity] ?? ""} text-xs`}>
                    {f.severity}
                  </Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </details>
  )
}

function formatTs(iso: string | null): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (isNaN(d.getTime())) return "—"
  return d.toLocaleString()
}

export function TrendsPage() {
  const { data, loading, error } = useTrendsData()
  const { data: timelineData, loading: timelineLoading, error: timelineError } = useTimelineData()

  const chartDataAsc = [...(timelineData?.sessions ?? [])]
    .reverse() // API returns newest-first; chart renders oldest-left to newest-right
    .map(s => ({
      session_ts:      s.session_ts,
      score:           s.score,
      hygiene:         s.subscores.hygiene,
      modern_tls:      s.subscores.modern_tls,
      identity_trust:  s.subscores.identity_trust,
      agility_signals: s.subscores.agility_signals,
      data_at_rest:    s.subscores.data_at_rest,
      data_in_motion:  s.subscores.data_in_motion,
      high:            s.finding_counts.high,
      medium:          s.finding_counts.medium,
      low:             s.finding_counts.low,
    }))
  const showChart = chartDataAsc.length >= 2

  if (loading) return <PageSpinner ariaLabel="Loading trends" />
  if (error) return <p className="text-muted-foreground text-sm">{error}</p>
  if (!data) {
    return (
      <div className="space-y-4 py-8">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Trends</h1>
        <p className="text-muted-foreground text-sm">
          No trend data available. Run a scan first to initialize the trends view.
        </p>
      </div>
    )
  }

  // D-06: baseline empty state — only one session exists
  if (!data.previous_session_ts) {
    return (
      <div className="space-y-4 py-8">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Trends</h1>
        <p className="text-muted-foreground text-sm">
          No scan history yet. Run two or more scans to see trend lines.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-baseline justify-between">
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Trends</h1>
        <p className="text-muted-foreground text-sm">
          Comparing {formatTs(data.previous_session_ts)} → {formatTs(data.current_session_ts)}
        </p>
      </div>

      {/* Phase 64 TREND-01: Score & Pillar Timeline */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold">Score & Pillar Timeline</h2>
        {timelineLoading ? (
          <PageSpinner ariaLabel="Loading trend timeline" />
        ) : timelineError ? (
          <p className="text-muted-foreground text-sm">{timelineError}</p>
        ) : showChart ? (
          <ChartContainer config={TIMELINE_CHART_CONFIG}>
            <LineChart data={chartDataAsc} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <XAxis
                dataKey="session_ts"
                tickFormatter={(v: string) => new Date(v).toLocaleString([], {
                  month: "2-digit", day: "2-digit",
                  hour: "2-digit", minute: "2-digit",
                })}
              />
              <YAxis domain={[0, 100]} tickCount={6} />
              <ChartTooltip
                content={(props: any) => {
                  if (!props.active || !props.payload || props.payload.length === 0) return null
                  const row = props.payload[0].payload as {
                    session_ts: string; score: number;
                    hygiene: number; modern_tls: number; identity_trust: number;
                    agility_signals: number; data_at_rest: number; data_in_motion: number;
                    high: number; medium: number; low: number;
                  }
                  return (
                    <div className="rounded-md border bg-background p-2 text-xs shadow-sm">
                      <div className="mb-1 font-medium">{new Date(row.session_ts).toLocaleString()}</div>
                      {props.payload.map((entry: any) => (
                        <div key={entry.dataKey} className="flex items-center gap-2">
                          <span className="inline-block h-2 w-2 rounded-sm" style={{ background: entry.color }} />
                          <span className="text-muted-foreground">{TIMELINE_CHART_CONFIG[entry.dataKey as keyof typeof TIMELINE_CHART_CONFIG]?.label ?? entry.dataKey}:</span>
                          <span className="font-mono">{entry.value}</span>
                        </div>
                      ))}
                      <div className="mt-1 border-t pt-1 font-mono">
                        Findings: HIGH {row.high} MED {row.medium} LOW {row.low}
                      </div>
                    </div>
                  )
                }}
              />
              {/* STATIC — never conditionally mount/unmount <Line> (Recharts static-children rule) */}
              <Line type="monotone" dataKey="score"           stroke="hsl(var(--quantum-safe))" strokeWidth={2.5} dot={{ r: 3 }} isAnimationActive={false} />
              <Line type="monotone" dataKey="hygiene"         stroke="hsl(180 37% 47%)"         strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} isAnimationActive={false} />
              <Line type="monotone" dataKey="modern_tls"      stroke="hsl(213 94% 68%)"         strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} isAnimationActive={false} />
              <Line type="monotone" dataKey="identity_trust"  stroke="hsl(38 92% 50%)"          strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} isAnimationActive={false} />
              <Line type="monotone" dataKey="agility_signals" stroke="hsl(28 64% 52%)"          strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} isAnimationActive={false} />
              <Line type="monotone" dataKey="data_at_rest"    stroke="hsl(270 50% 60%)"         strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} isAnimationActive={false} />
              <Line type="monotone" dataKey="data_in_motion"  stroke="hsl(152 47% 45%)"         strokeWidth={1.5} dot={{ r: 2 }} strokeOpacity={0.85} isAnimationActive={false} />
            </LineChart>
          </ChartContainer>
        ) : (
          <p className="text-muted-foreground text-sm">
            Run two or more scans to see the score &amp; pillar timeline.
          </p>
        )}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Score Delta</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">
            {data.previous_score ?? "—"} → {data.current_score ?? "—"}
          </span>
          <ScoreDeltaBadge delta={data.score_delta} />
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>New Findings</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-3 text-sm">
            <Badge className={SEVERITY_STYLES.CRITICAL}>CRITICAL/HIGH {data.new_high}</Badge>
            <Badge className={SEVERITY_STYLES.MEDIUM}>MEDIUM {data.new_medium}</Badge>
            <Badge className={SEVERITY_STYLES.LOW}>LOW {data.new_low}</Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Resolved Findings</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-3 text-sm">
            <Badge className={SEVERITY_STYLES.CRITICAL}>CRITICAL/HIGH {data.resolved_high}</Badge>
            <Badge className={SEVERITY_STYLES.MEDIUM}>MEDIUM {data.resolved_medium}</Badge>
            <Badge className={SEVERITY_STYLES.LOW}>LOW {data.resolved_low}</Badge>
          </CardContent>
        </Card>
      </div>

      <p className="text-muted-foreground text-sm">
        Scan errors: {data.scan_errors_new_count} new, {data.scan_errors_resolved_count} resolved
      </p>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold">New Findings (top 5)</h2>
        <SampleTable items={data.new_findings_sample} />
      </div>

      <div className="space-y-2">
        <h2 className="text-sm font-semibold">Resolved Findings (top 5)</h2>
        <SampleTable items={data.resolved_findings_sample} />
      </div>
    </div>
  )
}
