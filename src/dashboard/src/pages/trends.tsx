import { useTrendsData } from "@/hooks/useTrendsData"
import type { SampleFinding } from "@/types/api"
import { Badge } from "@/components/ui/badge"
import { PageSpinner } from "@/components/PageSpinner"
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

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
