import { useState, useContext, useMemo } from "react"
import { RadarChart, PolarGrid, PolarAngleAxis, Radar } from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Loader2 } from "lucide-react"
import { QRAMMContext } from "@/context/QRAMMContext"
import {
  DIMENSIONS,
  MATURITY_LABEL,
  MATURITY_BADGE_CLASS,
  MATURITY_BAR_CLASS,
  DIMENSION_COUNT,
} from "@/lib/qramm-constants"
import { getBenchmarks } from "@/lib/qramm-benchmarks"
import type { QRAMMScoreResponse } from "@/types/api"

interface ScorecardTabProps {
  /** Lookup map from question number to dimension string, derived from the catalog. */
  qnToDim: Map<number, string>
}

export function ScorecardTab({ qnToDim }: ScorecardTabProps) {
  const ctx = useContext(QRAMMContext)
  const [calculating, setCalculating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Compute completion percentages per dimension using the authoritative catalog
  // lookup rather than hard-coded question-number arithmetic.
  const completionByDim = useMemo(() => {
    const answered: Record<string, number> = {}
    const totals: Record<string, number> = {}
    for (const [qn, dim] of qnToDim) {
      totals[dim] = (totals[dim] ?? 0) + 1
      const a = ctx.answers.get(qn)
      if (a?.answer_value != null) answered[dim] = (answered[dim] ?? 0) + 1
    }
    return Object.fromEntries(
      DIMENSIONS.map(d => [d, totals[d] ? Math.round(((answered[d] ?? 0) / totals[d]) * 100) : 0])
    )
  }, [ctx.answers, qnToDim])

  // Approximate maturity distribution by bucketing each dimension's score.
  // When every dimension's score is null (Phase 74 "Indeterminate" sentinel),
  // we render an em-dash row in place of bars rather than a row of zero-width
  // bars — see D-10 (WR-11).
  const maturityDist = useMemo(() => {
    const dist: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0 }
    if (!ctx.scoreResult) return dist
    for (const dim of DIMENSIONS) {
      const dscore = ctx.scoreResult.dimensions[dim]?.score
      if (dscore == null) continue
      const bucket = Math.max(1, Math.min(4, Math.round(dscore)))
      dist[bucket] += 1
    }
    return dist
  }, [ctx.scoreResult])

  const isIndeterminate = useMemo(() => {
    if (!ctx.scoreResult) return false
    if (ctx.scoreResult.maturity === "Indeterminate") return true
    return DIMENSIONS.every(
      (dim) => ctx.scoreResult!.dimensions[dim]?.score == null,
    )
  }, [ctx.scoreResult])

  async function handleCalculate() {
    if (!ctx.sessionId) return
    setCalculating(true)
    setError(null)
    try {
      const resp = await fetch(`/api/qramm/sessions/${ctx.sessionId}/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_multiplier: ctx.profile?.multiplier ?? null,
        }),
      })
      if (!resp.ok) {
        setError("Could not calculate score — check your connection and try again")
        return
      }
      const json: QRAMMScoreResponse = await resp.json()
      ctx.setScoreResult(json)
    } catch {
      setError("Could not calculate score — check your connection and try again")
    } finally {
      setCalculating(false)
    }
  }

  const benchmarks = getBenchmarks(ctx.profile?.industry)

  const chartData = DIMENSIONS.map((dim) => ({
    axis: dim,
    score: ctx.scoreResult?.dimensions[dim]?.score ?? 0,
    benchmark: benchmarks
      ? benchmarks[dim.toLowerCase() as keyof typeof benchmarks]
      : 0,
  }))

  return (
    <div className="space-y-6 pt-4">
      {/* Calculate Score action */}
      <Card>
        <CardContent className="p-4 space-y-3">
          <Button
            variant="default"
            className="w-full"
            onClick={handleCalculate}
            disabled={calculating}
          >
            {calculating ? (
              <>
                <Loader2 className="animate-spin mr-2 h-4 w-4" />
                Calculating...
              </>
            ) : (
              "Calculate Score"
            )}
          </Button>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </CardContent>
      </Card>

      {/* Main content: radar + maturity distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: RadarChart (span 3) */}
        <div className="lg:col-span-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Dimension Radar</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center">
              <RadarChart
                width={320}
                height={320}
                data={chartData}
                aria-label="QRAMM radar chart showing dimension scores"
                role="img"
              >
                <PolarGrid stroke="hsl(var(--border))" />
                <PolarAngleAxis
                  dataKey="axis"
                  tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 12 }}
                />
                <Radar
                  name="Assessment"
                  dataKey="score"
                  fill="rgba(75, 168, 168, 0.20)"
                  fillOpacity={ctx.scoreResult ? 1 : 0}
                  stroke="hsl(var(--accent))"
                  strokeOpacity={ctx.scoreResult ? 1 : 0}
                  isAnimationActive={false}
                />
                <Radar
                  name="Benchmark"
                  dataKey="benchmark"
                  fill="rgba(110, 122, 149, 0.15)"
                  fillOpacity={ctx.scoreResult && benchmarks ? 1 : 0}
                  stroke="hsl(var(--muted-foreground))"
                  strokeOpacity={ctx.scoreResult && benchmarks ? 1 : 0}
                  strokeDasharray="4 2"
                  isAnimationActive={false}
                />
              </RadarChart>
              {!ctx.scoreResult && (
                <p className="text-xs text-muted-foreground mt-4 text-center max-w-[280px]">
                  Answer questions across all dimensions, then click Calculate Score to generate your QRAMM scorecard.
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right: Maturity distribution (span 2) */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Maturity Distribution</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {([4, 3, 2, 1] as const).map((level) => {
                const count = maturityDist[level] ?? 0
                return (
                  <div key={level} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold">{MATURITY_LABEL[level]}</span>
                      <span className="font-data text-sm">
                        {ctx.scoreResult && !isIndeterminate ? count : "—"}
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-muted">
                      {ctx.scoreResult && !isIndeterminate && (
                        <div
                          data-testid={`maturity-bar-${level}`}
                          className={`h-2 rounded-full ${MATURITY_BAR_CLASS[level]}`}
                          style={{ width: `${(count / DIMENSION_COUNT) * 100}%` }}
                        />
                      )}
                    </div>
                  </div>
                )
              })}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dimension summary table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dimension Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs font-semibold uppercase tracking-[0.08em]">
                  Dimension
                </TableHead>
                <TableHead className="text-xs font-semibold">Raw Score</TableHead>
                <TableHead className="text-xs font-semibold">Weighted Score</TableHead>
                <TableHead className="text-xs font-semibold">Industry Benchmark</TableHead>
                <TableHead className="text-xs font-semibold">Maturity Level</TableHead>
                <TableHead className="text-xs font-semibold">Completion %</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {DIMENSIONS.map((dim) => {
                const d = ctx.scoreResult?.dimensions[dim]
                const benchmark = benchmarks
                  ? benchmarks[dim.toLowerCase() as keyof typeof benchmarks]
                  : null
                // Phase 74 "Indeterminate" sentinel: d.score can be null even
                // when d itself is present. Guard with a numeric typeof check
                // before invoking .toFixed / Math.round (D-10 null-safety).
                const dscore = typeof d?.score === "number" ? d.score : null
                const dweighted = typeof d?.weighted === "number" ? d.weighted : null
                const maturityInt =
                  dscore != null
                    ? Math.max(1, Math.min(4, Math.round(dscore)))
                    : null
                return (
                  <TableRow key={dim}>
                    <TableCell className="text-sm">{dim}</TableCell>
                    <TableCell className="font-data">
                      {dscore != null ? dscore.toFixed(2) : "—"}
                    </TableCell>
                    <TableCell className="font-data">
                      {dweighted != null ? dweighted.toFixed(2) : "—"}
                    </TableCell>
                    <TableCell className="font-data">
                      {benchmark != null ? benchmark.toFixed(2) : "—"}
                    </TableCell>
                    <TableCell>
                      {maturityInt != null ? (
                        <Badge className={MATURITY_BADGE_CLASS[maturityInt]}>
                          {MATURITY_LABEL[maturityInt]}
                        </Badge>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="font-data">
                      {completionByDim[dim]}%
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
