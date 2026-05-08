import { useState, useEffect, useContext } from "react"
import { Loader2 } from "lucide-react"
import {
  Card, CardContent, CardHeader, CardTitle,
} from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { QRAMMContext } from "@/context/QRAMMContext"
import type { QRAMMComplianceMapRow, QRAMMScoreResponse } from "@/types/api"

const FRAMEWORK_KEYS = [
  "NIST_PQC", "NSM10", "CNSA2", "ISO27001",
  "ETSI_QS", "PCI_DSS", "CC", "BSI_TR",
] as const

const FRAMEWORK_HEADER_LABELS: Record<string, string> = {
  NIST_PQC: "NIST PQC",
  NSM10:    "NSM-10",
  CNSA2:    "CNSA 2.0",
  ISO27001: "ISO 27001",
  ETSI_QS:  "ETSI QS",
  PCI_DSS:  "PCI-DSS",
  CC:       "CC",
  BSI_TR:   "BSI TR",
}

const PRACTICE_AREA_NAMES: Record<string, string> = {
  "1.1": "Cryptographic Discovery & Inventory Management",
  "1.2": "Vulnerability Assessment & Classification",
  "1.3": "Cryptographic Dependency Mapping",
  "2.1": "Executive Leadership",
  "2.2": "Risk & Compliance",
  "2.3": "Third-Party Management",
  "3.1": "Data Classification",
  "3.2": "Storage Security",
  "3.3": "Transit Security",
  "4.1": "Infrastructure",
  "4.2": "Implementation",
  "4.3": "Testing & Validation",
}

const FOOTNOTE =
  "Coverage reflects QUIRK scanner findings for CVI only — " +
  "SGRM, DPE, ITR require manual assessment."

const UNSCORED_BANNER =
  "Run and score a QRAMM assessment to see session-derived relevance scores."

interface PracticeRow {
  practice_area: string
  dimension: string
  scanner_informed: boolean
  scores: Record<string, number | null>
}

function groupRows(rows: QRAMMComplianceMapRow[]): PracticeRow[] {
  const byPa: Record<string, PracticeRow> = {}
  for (const r of rows) {
    if (!byPa[r.practice_area]) {
      byPa[r.practice_area] = {
        practice_area: r.practice_area,
        dimension: r.dimension,
        scanner_informed: r.scanner_informed,
        scores: {},
      }
    }
    byPa[r.practice_area].scores[r.framework] = r.relevance_score
  }
  return Object.values(byPa).sort((a, b) =>
    a.practice_area.localeCompare(b.practice_area, undefined, { numeric: true })
  )
}

function formatScore(score: number | null): string {
  if (score === null || score === undefined) return "—"
  return score.toFixed(2)
}

export function ComplianceMapTab() {
  const ctx = useContext(QRAMMContext)
  const [rows, setRows] = useState<QRAMMComplianceMapRow[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [scoring, setScoring] = useState(false)
  const [scoreError, setScoreError] = useState<string | null>(null)

  async function handleCalculate() {
    if (!ctx.sessionId) return
    setScoring(true)
    setScoreError(null)
    try {
      const resp = await fetch(`/api/qramm/sessions/${ctx.sessionId}/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_multiplier: ctx.profile?.multiplier ?? null }),
      })
      if (!resp.ok) {
        setScoreError("Could not calculate score — check your connection and try again.")
        return
      }
      const json: QRAMMScoreResponse = await resp.json()
      ctx.setScoreResult(json)
    } catch {
      setScoreError("Could not calculate score — check your connection and try again.")
    } finally {
      setScoring(false)
    }
  }

  useEffect(() => {
    if (!ctx.sessionId) {
      setRows([])
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    fetch(`/api/qramm/sessions/${ctx.sessionId}/compliance-map`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data: QRAMMComplianceMapRow[]) => {
        if (cancelled) return
        setRows(data)
        setLoading(false)
      })
      .catch(() => {
        if (cancelled) return
        setError("Check your connection and try again.")
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [ctx.sessionId, ctx.scoreResult])

  const grouped = groupRows(rows)
  const isUnscored = rows.length === 0 || rows.every(
    (r) => r.relevance_score === null
  )

  return (
    <div className="space-y-6 pt-4">
      {error && (
        <Card>
          <CardHeader>
            <CardTitle>Could not load compliance map</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">{error}</p>
          </CardContent>
        </Card>
      )}

      {!error && isUnscored && (
        <Card>
          <CardContent className="pt-6 space-y-3">
            <p className="text-sm text-muted-foreground">{UNSCORED_BANNER}</p>
            <Button
              variant="default"
              size="sm"
              onClick={handleCalculate}
              disabled={scoring || !ctx.sessionId}
            >
              {scoring ? (
                <><Loader2 className="animate-spin h-4 w-4 mr-2" />Calculating…</>
              ) : "Calculate Score"}
            </Button>
            {scoreError && (
              <p className="text-sm text-destructive">{scoreError}</p>
            )}
          </CardContent>
        </Card>
      )}

      {!error && (
        <Card>
          <CardHeader>
            <CardTitle>Compliance Framework Coverage</CardTitle>
          </CardHeader>
          <CardContent className="min-h-[200px]">
            {loading ? (
              <div
                className="flex items-center justify-center min-h-[200px]"
                aria-label="Loading compliance map"
              >
                <Loader2
                  className="animate-spin h-6 w-6 text-muted-foreground"
                />
              </div>
            ) : (
              <>
                <Table aria-label="QRAMM compliance framework coverage by practice area">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs font-semibold uppercase tracking-[0.08em]">
                        Practice Area
                      </TableHead>
                      <TableHead className="text-xs font-semibold uppercase tracking-[0.08em]">
                        Dimension
                      </TableHead>
                      {FRAMEWORK_KEYS.map((fw) => (
                        <TableHead
                          key={fw}
                          className="text-xs font-semibold uppercase tracking-[0.08em]"
                        >
                          {FRAMEWORK_HEADER_LABELS[fw]}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {grouped.map((row) => (
                      <TableRow key={row.practice_area}>
                        <TableCell className="text-sm">
                          <span className="font-data mr-2">
                            {row.practice_area}
                          </span>
                          {PRACTICE_AREA_NAMES[row.practice_area]}
                        </TableCell>
                        <TableCell className="text-xs uppercase tracking-[0.08em] text-muted-foreground">
                          {row.dimension}
                        </TableCell>
                        {FRAMEWORK_KEYS.map((fw) => (
                          <TableCell key={fw} className="font-data text-sm">
                            {row.scanner_informed
                              ? formatScore(row.scores[fw] ?? null)
                              : "—"}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <p className="text-xs text-muted-foreground mt-4">
                  {FOOTNOTE}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      )}

      {!error && (
        <Card>
          <CardHeader>
            <CardTitle>Coverage Tiers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <Badge variant="default" title="Scanner-informed">
                  Scanner-informed
                </Badge>
                <span className="text-sm text-muted-foreground">
                  At least one relevant dimension is scanner-informed (CVI)
                </span>
              </div>
              <div className="flex items-center gap-3">
                <Badge variant="secondary" title="Manual only">
                  Manual only
                </Badge>
                <span className="text-sm text-muted-foreground">
                  All relevant dimensions require manual assessment
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
