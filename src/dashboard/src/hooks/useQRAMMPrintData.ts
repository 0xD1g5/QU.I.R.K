import { useState, useEffect } from "react"
import type {
  QRAMMSessionSummary,
  QRAMMScoreResponse,
  QRAMMComplianceMapRow,
} from "@/types/api"

interface UseQRAMMPrintDataResult {
  scoreResult: QRAMMScoreResponse | null
  complianceRows: QRAMMComplianceMapRow[] | null
  loading: boolean
  error: string | null
}

export function useQRAMMPrintData(): UseQRAMMPrintDataResult {
  const [scoreResult, setScoreResult] = useState<QRAMMScoreResponse | null>(null)
  const [complianceRows, setComplianceRows] = useState<QRAMMComplianceMapRow[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        setLoading(true)
        setError(null)

        const listResp = await fetch("/api/qramm/sessions")
        if (!listResp.ok) {
          if (!cancelled) {
            setError(`API error: ${listResp.status} ${listResp.statusText}`)
          }
          return
        }
        const list: QRAMMSessionSummary[] = await listResp.json()
        if (cancelled) return

        const scored = list.find((s) => s.status === "scored")
        if (!scored) {
          // No scored session — resolve with null payloads (D-04/D-05). NOT an error.
          if (!cancelled) {
            setScoreResult(null)
            setComplianceRows(null)
          }
          return
        }

        const [scoreResp, mapResp] = await Promise.all([
          fetch(`/api/qramm/sessions/${scored.session_id}/score`),
          fetch(`/api/qramm/sessions/${scored.session_id}/compliance-map`),
        ])

        if (!scoreResp.ok) {
          if (!cancelled) {
            setError(`API error: ${scoreResp.status} ${scoreResp.statusText}`)
          }
          return
        }
        if (!mapResp.ok) {
          if (!cancelled) {
            setError(`API error: ${mapResp.status} ${mapResp.statusText}`)
          }
          return
        }

        const score: QRAMMScoreResponse = await scoreResp.json()
        const rows: QRAMMComplianceMapRow[] = await mapResp.json()
        if (!cancelled) {
          setScoreResult(score)
          setComplianceRows(rows)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load QRAMM data")
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [])

  return { scoreResult, complianceRows, loading, error }
}
