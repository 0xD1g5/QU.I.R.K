import { useSearchParams, useNavigate } from "react-router-dom"
import { TrendingUp, TrendingDown } from "lucide-react"
import { useCompareData } from "@/hooks/useCompareData"
import { PageSpinner } from "@/components/PageSpinner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import type { CompareFinding, CompareEndpoint } from "@/types/api"

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: "bg-[hsl(0_72%_51%)] text-white",
  HIGH: "bg-[hsl(24_95%_53%)] text-white",
  MEDIUM: "bg-[hsl(38_92%_50%)] text-black",
  LOW: "bg-[hsl(213_94%_68%)] text-black",
  INFO: "bg-[hsl(240_5%_46%)] text-white",
}

const PILLAR_LABELS: Record<string, string> = {
  hygiene: "Hygiene",
  modern_tls: "Modern TLS",
  identity_trust: "Identity Trust",
  agility_signals: "Agility",
  data_at_rest: "Data at Rest",
  data_in_motion: "Data in Motion",
}

function FindingRow({ finding }: { finding: CompareFinding }) {
  return (
    <TableRow>
      <TableCell>
        <Badge className={`${SEVERITY_STYLES[finding.severity] ?? ""} font-semibold text-xs`}>
          {finding.severity}
        </Badge>
      </TableCell>
      <TableCell className="text-sm">{finding.host}</TableCell>
      <TableCell className="text-sm text-muted-foreground">{finding.protocol ?? "—"}</TableCell>
      <TableCell className="text-sm text-muted-foreground">{finding.description ?? ""}</TableCell>
    </TableRow>
  )
}

function EndpointRow({ ep }: { ep: CompareEndpoint | string }) {
  if (typeof ep === "string") {
    return (
      <TableRow>
        <TableCell className="text-sm">{ep}</TableCell>
        <TableCell className="text-sm text-muted-foreground">—</TableCell>
      </TableRow>
    )
  }
  return (
    <TableRow>
      <TableCell className="text-sm">{ep.host}</TableCell>
      <TableCell className="text-sm text-muted-foreground">{ep.reason ?? "—"}</TableCell>
    </TableRow>
  )
}

const EmptyCompareState = () => (
  <Card>
    <CardContent className="py-8 text-sm text-foreground/70 text-center">
      Select two scans from Scan History to compare them.
    </CardContent>
  </Card>
)

export function ComparePage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const scanA = searchParams.get("a")
  const scanB = searchParams.get("b")
  const { data, loading, error } = useCompareData(scanA, scanB)

  if (!scanA || !scanB) return <EmptyCompareState />

  if (loading) return <PageSpinner ariaLabel="Loading comparison" />

  if (error) {
    const copy =
      error.includes("same") || error.includes("itself")
        ? "These are the same scan. Select two different scans to compare."
        : "Could not load comparison. Both scans must exist and the server must be reachable."
    return (
      <Card>
        <CardContent className="py-6 text-sm text-destructive">{copy}</CardContent>
      </Card>
    )
  }

  if (!data) return <EmptyCompareState />

  const delta = data.score_delta
  const totalFindings = data.added_findings.length + data.removed_findings.length
  const totalEndpoints =
    data.changed_endpoints.length + data.endpoints_only_in_a.length + data.endpoints_only_in_b.length

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate("/scans")}>
          ← Scan History
        </Button>
        <h1 className="text-xl font-semibold">Scan Comparison</h1>
      </div>

      <Card>
        <CardContent className="grid grid-cols-2 gap-4 py-4 relative">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Scan A</p>
            <p className="text-sm">{new Date(data.scan_a.scanned_at).toLocaleString()}</p>
            <p className="text-2xl font-semibold font-data">{data.scan_a.score}</p>
          </div>
          <div className="text-right">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Scan B</p>
            <p className="text-sm">{new Date(data.scan_b.scanned_at).toLocaleString()}</p>
            <p className="text-2xl font-semibold font-data">{data.scan_b.score}</p>
          </div>
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
            {delta > 0 && (
              <Badge className="bg-[hsl(var(--ds-ok,142_46%_46%))] text-white">
                <TrendingUp className="inline w-4 h-4 mr-1" />
                +{delta} pts improvement
              </Badge>
            )}
            {delta < 0 && (
              <Badge className="bg-[hsl(var(--destructive))] text-white">
                <TrendingDown className="inline w-4 h-4 mr-1" />
                {delta} pts regression
              </Badge>
            )}
            {delta === 0 && <Badge variant="outline">No score change</Badge>}
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="findings">
        <TabsList>
          <TabsTrigger value="findings">Findings ({totalFindings})</TabsTrigger>
          <TabsTrigger value="subscores">Subscores (6)</TabsTrigger>
          <TabsTrigger value="endpoints">Endpoints ({totalEndpoints})</TabsTrigger>
        </TabsList>

        <TabsContent value="findings" className="space-y-6 mt-4">
          <div>
            <p className="text-sm font-semibold mb-2">Added ({data.added_findings.length})</p>
            {data.added_findings.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No new findings since the earlier scan.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Severity</TableHead>
                    <TableHead>Host</TableHead>
                    <TableHead>Protocol</TableHead>
                    <TableHead>Description</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.added_findings.map((f, i) => (
                    <FindingRow key={i} finding={f} />
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          <div>
            <p className="text-sm font-semibold mb-2">Removed ({data.removed_findings.length})</p>
            {data.removed_findings.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No findings resolved between these scans.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Severity</TableHead>
                    <TableHead>Host</TableHead>
                    <TableHead>Protocol</TableHead>
                    <TableHead>Description</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.removed_findings.map((f, i) => (
                    <FindingRow key={i} finding={f} />
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        <TabsContent value="subscores" className="mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Pillar</TableHead>
                <TableHead>Scan A</TableHead>
                <TableHead>Scan B</TableHead>
                <TableHead>Δ</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(["hygiene", "modern_tls", "identity_trust", "agility_signals", "data_at_rest", "data_in_motion"] as const).map(key => {
                const d = data.subscore_deltas[key]
                const colorClass = d > 0
                  ? "text-[hsl(var(--ds-ok))]"
                  : d < 0
                    ? "text-destructive"
                    : "text-muted-foreground"
                return (
                  <TableRow key={key}>
                    <TableCell>{PILLAR_LABELS[key]}</TableCell>
                    <TableCell className="font-data">{data.scan_a.subscores[key]}</TableCell>
                    <TableCell className="font-data">{data.scan_b.subscores[key]}</TableCell>
                    <TableCell className={`font-data ${colorClass}`}>
                      {d === 0 ? "±0" : d > 0 ? `+${d}` : `${d}`}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TabsContent>

        <TabsContent value="endpoints" className="space-y-6 mt-4">
          <div>
            <p className="text-sm font-semibold mb-2">Changed ({data.changed_endpoints.length})</p>
            {data.changed_endpoints.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No endpoint posture changes between these scans.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Host</TableHead>
                    <TableHead>Reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.changed_endpoints.map((ep, i) => (
                    <EndpointRow key={i} ep={ep} />
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          <div>
            <p className="text-sm font-semibold mb-2">Only in A ({data.endpoints_only_in_a.length})</p>
            {data.endpoints_only_in_a.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No endpoints unique to this scan.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Host</TableHead>
                    <TableHead>Note</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.endpoints_only_in_a.map((ep, i) => (
                    <EndpointRow key={i} ep={ep} />
                  ))}
                </TableBody>
              </Table>
            )}
          </div>

          <div>
            <p className="text-sm font-semibold mb-2">Only in B ({data.endpoints_only_in_b.length})</p>
            {data.endpoints_only_in_b.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No endpoints unique to the earlier scan.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Host</TableHead>
                    <TableHead>Note</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.endpoints_only_in_b.map((ep, i) => (
                    <EndpointRow key={i} ep={ep} />
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
