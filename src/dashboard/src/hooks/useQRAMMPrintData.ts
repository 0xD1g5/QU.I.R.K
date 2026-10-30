import { useState, useEffect } from "react"
import type {
  QRAMMSessionSummary,
  QRAMMScoreResponse,
  QRAMMComplianceMapRow,
  QRAMMSessionDetail,
} from "@/types/api"
import { fetchApi } from "@/lib/api"

interface UseQRAMMPrintDataResult {
  scoreResult: QRAMMScoreResponse | null
  complianceRows: QRAMMComplianceMapRow[] | null
  // Phase 234 D-15/D-25: from GET /api/qramm/sessions/{id} (SessionRead).
  scoreStale: boolean
  scoreOverallState: "current" | "recalculate" | "stale" | null
  loading: boolean
  error: string | null
}

export function useQRAMMPrintData(): UseQRAMMPrintDataResult {
  const [scoreResult, setScoreResult] = useState<QRAMMScoreResponse | null>(null)
  const [complianceRows, setComplianceRows] = useState<QRAMMComplianceMapRow[] | null>(null)
  const [scoreStale, setScoreStale] = useState(false)
  const [scoreOverallState, setScoreOverallState] = useState<"current" | "recalculate" | "stale" | null>(null)
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

        // Phase 231 D-20: GET .../score is POST-only; the SPA fallback answered 200 text/html, the PDF
        // export then timed out waiting for data-ready. The persisted score lives on the session detail.
        const sessionPath = `/api/qramm/sessions/${scored.session_id}`
        const [scoreResp, mapResp] = await Promise.all([
          fetchApi(sessionPath),
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

        let detail: QRAMMSessionDetail
        try {
          detail = await scoreResp.json()
        } catch {
          // A non-JSON body (e.g. the SPA fallback's HTML) is an API error, not an unhandled throw.
          if (!cancelled) setError(`API error: unexpected response from ${sessionPath}`)
          return
        }
        if (cancelled) return
        if (detail.score == null) {
          // D-20: a summary can say scored while the detail has no score; that is no assessment, not an error
          setScoreResult(null)
          setComplianceRows(null)
          return
        }
        const rows: QRAMMComplianceMapRow[] = await mapResp.json()
        if (!cancelled) {
          setScoreResult(detail.score)
          setComplianceRows(rows)
          setScoreStale(detail.score_stale === true)
          setScoreOverallState(detail.score_overall_state ?? null)
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

  return { scoreResult, complianceRows, scoreStale, scoreOverallState, loading, error }
}
