import { useState, useEffect } from "react"
import type {
  QRAMMSessionSummary,
  QRAMMScoreResponse,
  QRAMMComplianceMapRow,
} from "@/types/api"
import { fetchApi } from "@/lib/api"

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

        const listResp = await fetchApi("/api/qramm/sessions")
        if (!listResp.ok) {
          if (!cancelled) {
            if (listResp.status === 401) {
              setError("Authentication required")
              return
            }
            if (listResp.status === 403) {
              setError("Request blocked")
              return
            }
            if (listResp.status === 429) {
              const retryAfter = listResp.headers.get("Retry-After") ?? "60"
              setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
              return
            }
            setError(`API error: ${listResp.status} ${listResp.statusText}`)
          }
          return
        }
        const list: QRAMMSessionSummary[] = await listResp.json()
        if (cancelled) return

        const scored = list.find((s) => s.status === "scored")
        if (!scored) {
          // No scored session — resolve with null payloads (D-04/D-05). NOT an error.
          // Returning here is safe: the finally block always runs and clears loading.
          if (!cancelled) {
            setScoreResult(null)
            setComplianceRows(null)
          }
          return
        }

        const [scoreResp, mapResp] = await Promise.all([
          fetchApi(`/api/qramm/sessions/${scored.session_id}/score`),
          fetchApi(`/api/qramm/sessions/${scored.session_id}/compliance-map`),
        ])

        if (!scoreResp.ok) {
          if (!cancelled) {
            if (scoreResp.status === 401) {
              setError("Authentication required")
              return
            }
            if (scoreResp.status === 403) {
              setError("Request blocked")
              return
            }
            if (scoreResp.status === 429) {
              const retryAfter = scoreResp.headers.get("Retry-After") ?? "60"
              setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
              return
            }
            setError(`API error: ${scoreResp.status} ${scoreResp.statusText}`)
          }
          return
        }
        if (!mapResp.ok) {
          if (!cancelled) {
            if (mapResp.status === 401) {
              setError("Authentication required")
              return
            }
            if (mapResp.status === 403) {
              setError("Request blocked")
              return
            }
            if (mapResp.status === 429) {
              const retryAfter = mapResp.headers.get("Retry-After") ?? "60"
              setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
              return
            }
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
