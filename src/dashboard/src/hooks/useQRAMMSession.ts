import { useEffect, useState, useContext, useRef } from "react"
import { QRAMMContext, type AnswerState } from "@/context/QRAMMContext"
import type { QRAMMSessionSummary, QRAMMAnswerRead } from "@/types/api"

interface UseQRAMMSessionResult {
  session: QRAMMSessionSummary | null
  loading: boolean
  error: string | null
  reload: () => void
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

        const listResp = await fetch("/api/qramm/sessions")
        if (!listResp.ok) {
          setError(`API error: ${listResp.status} ${listResp.statusText}`)
          return
        }
        const list: QRAMMSessionSummary[] = await listResp.json()
        if (cancelled) return

        if (list.length === 0) {
          setSession(null)
          ctx.setSessionId(null)
          return
        }

        const latest = list[0]
        setSession(latest)
        ctx.setSessionId(latest.session_id)

        // Seed answers only once per session_id load (avoid clobbering edits).
        if (seededRef.current !== latest.session_id) {
          const ansResp = await fetch(`/api/qramm/sessions/${latest.session_id}/answers`)
          if (!ansResp.ok) {
            setError(`API error: ${ansResp.status} ${ansResp.statusText}`)
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
          ctx.resetAnswers(map)
          seededRef.current = latest.session_id
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

  return {
    session,
    loading,
    error,
    reload: () => setTick(t => t + 1),
  }
}
