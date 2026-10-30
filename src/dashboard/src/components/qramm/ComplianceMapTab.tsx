import { useState, useEffect, useContext, useRef } from "react"
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
import { fetchApi } from "@/lib/api"
import {
  ASSESSMENT_BADGE_VARIANT,
  ASSESSMENT_LABEL,
  QRAMM_COVERAGE_SENTENCE,
  stateFromCoverageStatus,
} from "@/lib/qramm-assessment"
import type { AssessmentState } from "@/lib/qramm-assessment"
import type {
  QRAMMComplianceMapRow,
  QRAMMRowCoverageStatus,
  QRAMMScoreResponse,
} from "@/types/api"

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

const UNSCORED_BANNER =
  "Run and score a QRAMM assessment to see session-derived relevance scores."

// Phase 231 D-05/D-06a: legend rows in UI-SPEC order; labels come from the
// shared vocabulary, descriptions are the UI-SPEC copy.
const TIER_LEGEND: Array<{ state: AssessmentState; description: string }> = [
  {
    state: "scanner-measured",
    description: "CVI practice areas, scored with QUIRK scanner evidence.",
  },
  {
    state: "self-assessed",
    description:
      "SGRM, DPE and ITR practice areas scored from answers entered by hand. " +
      "No scanner evidence backs these scores.",
  },
  {
    state: "not-assessed",
    description:
      "No question in this dimension has been answered yet, so its practice " +
      "areas have no score.",
  },
]

interface PracticeRow {
  practice_area: string
  dimension: string
  scanner_informed: boolean
  coverage_status: QRAMMRowCoverageStatus | null
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
        coverage_status: r.coverage_status,
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
  const [reloadKey, setReloadKey] = useState(0)
  const [statusMessage, setStatusMessage] = useState("")
  // Set only by a successful Calculate Score, so the initial mount and a
  // sessionId-change refetch never announce (Phase 231 D-21c).
  const announceNextLoad = useRef(false)

  async function handleCalculate() {
    if (!ctx.sessionId) return
    setScoring(true)
    setScoreError(null)
    setStatusMessage("")
    try {
      const resp = await fetchApi(`/api/qramm/sessions/${ctx.sessionId}/score`, {
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
      announceNextLoad.current = true
      setReloadKey((k) => k + 1)
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
    fetchApi(`/api/qramm/sessions/${ctx.sessionId}/compliance-map`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data: QRAMMComplianceMapRow[]) => {
        if (cancelled) return
        setRows(data)
        setLoading(false)
        if (announceNextLoad.current) {
          setStatusMessage("Compliance map updated.")
          announceNextLoad.current = false
        }
      })
      .catch(() => {
        if (cancelled) return
        setError("Check your connection and try again.")
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // D-07 (WR-13): scoreResult intentionally omitted — compliance rows are
    // framework-question mapping, independent of scored values. Re-fetching
    // on every scoreResult mutation produced a spurious refetch loop.
    // Phase 231 D-10: reloadKey is an explicit post-score trigger; scoreResult
    // stays out of the deps so a context update cannot loop.
  }, [ctx.sessionId, reloadKey])

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
            <p className="sr-only" role="status" aria-live="polite">
              {statusMessage}
            </p>
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
                      <TableHead className="text-xs font-semibold uppercase tracking-[0.08em]">
                        Assessment
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
                    {grouped.map((row) => {
                      // Phase 231 D-01: the tier comes from coverage_status,
                      // never scanner_informed (true for an unanswered CVI too).
                      const state = stateFromCoverageStatus(row.coverage_status)
                      return (
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
                          <TableCell>
                            <Badge variant={ASSESSMENT_BADGE_VARIANT[state]}>
                              {ASSESSMENT_LABEL[state]}
                            </Badge>
                          </TableCell>
                          {FRAMEWORK_KEYS.map((fw) => (
                            <TableCell key={fw} className="font-data text-sm">
                              {state === "not-assessed"
                                ? "—"
                                : formatScore(row.scores[fw] ?? null)}
                            </TableCell>
                          ))}
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
                <p className="text-xs text-muted-foreground mt-4">
                  {QRAMM_COVERAGE_SENTENCE}
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
              {TIER_LEGEND.map(({ state, description }) => (
                <div key={state} className="flex items-center gap-3">
                  <Badge
                    variant={ASSESSMENT_BADGE_VARIANT[state]}
                    title={ASSESSMENT_LABEL[state]}
                  >
                    {ASSESSMENT_LABEL[state]}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {description}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
