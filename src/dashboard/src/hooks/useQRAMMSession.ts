import { useEffect, useState, useContext, useRef, useCallback } from "react"
import { QRAMMContext, type AnswerState } from "@/context/QRAMMContext"
import type { QRAMMSessionSummary, QRAMMAnswerRead } from "@/types/api"
import { fetchApi } from "@/lib/api"

interface UseQRAMMSessionResult {
  session: QRAMMSessionSummary | null
  loading: boolean
  error: string | null
  reload: () => void
  resetSession: () => void
}

export function useQRAMMSession(): UseQRAMMSessionResult {
  const ctx = useContext(QRAMMContext)
  const [session, setSession] = useState<QRAMMSessionSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const seededRef = useRef<number | null>(null)

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

        if (list.length === 0) {
          if (!cancelled) {
            setSession(null)
            ctx.setSessionId(null)
          }
          return
        }

        const latest = list[0]
        if (!cancelled) {
          setSession(latest)
          ctx.setSessionId(latest.session_id)
        }

        // Seed answers only once per session_id load (avoid clobbering edits).
        // seededRef invariant preserved exactly — only cancellation guards added below.
        if (seededRef.current !== latest.session_id) {
          const ansResp = await fetchApi(`/api/qramm/sessions/${latest.session_id}/answers`)
          if (!ansResp.ok) {
            if (!cancelled) {
              if (ansResp.status === 401) {
                setError("Authentication required")
                return
              }
              if (ansResp.status === 403) {
                setError("Request blocked")
                return
              }
              if (ansResp.status === 429) {
                const retryAfter = ansResp.headers.get("Retry-After") ?? "60"
                setError(`Too many requests. Wait ${retryAfter} seconds and try again.`)
                return
              }
              setError(`API error: ${ansResp.status} ${ansResp.statusText}`)
            }
            return
          }
          const rows: QRAMMAnswerRead[] = await ansResp.json()
          if (cancelled) return
          const map = new Map<number, AnswerState>()
          for (const r of rows) {
            map.set(r.question_number, {
              answer_value: (r.answer_value as 1 | 2 | 3 | 4 | null) ?? null,
              suggested_answer: (r.suggested_answer as 1 | 2 | 3 | 4 | null) ?? null,
              confirmed_at: r.confirmed_at,
              evidence_note: r.evidence_note ?? "",
            })
          }
          if (!cancelled) {
            ctx.resetAnswers(map)
            seededRef.current = latest.session_id
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load QRAMM session")
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => { cancelled = true }
  }, [tick]) // eslint-disable-line react-hooks/exhaustive-deps

  // D-26 (IN-04): reset the seededRef so the next session load re-seeds answers
  // after a "New Assessment" flow trigger. Without this, archiveAndReset leaves
  // seededRef pointing at the archived session_id and the next session's answers
  // would not be loaded into the QRAMM context.
  const resetSession = useCallback(() => {
    seededRef.current = null
  }, [])

  return {
    session,
    loading,
    error,
    reload: () => setTick(t => t + 1),
    resetSession,
  }
}
