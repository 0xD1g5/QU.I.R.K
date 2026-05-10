import { useState, useRef, useCallback, useEffect } from "react"
import type { ReactNode } from "react"
import { QRAMMContext } from "./QRAMMContext"
import type { AnswerState, OrgProfile, ScoreResult } from "./QRAMMContext"
import { fetchApi } from "@/lib/api"

const DEFAULT_ANSWER: AnswerState = {
  answer_value: null,
  suggested_answer: null,
  confirmed_at: null,
  evidence_note: "",
}

export function QRAMMProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [answers, setAnswers] = useState<Map<number, AnswerState>>(new Map())
  const [profile, setProfile] = useState<OrgProfile | null>(null)
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null)
  // Per-question debounce map — each question gets its own independent timer so
  // rapid edits across different questions do not cancel each other's saves.
  const debounceRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map())
  const sessionIdRef = useRef<number | null>(null)
  sessionIdRef.current = sessionId
  // BR-01 (D-03): synchronous merged-answer ref so persistDraft sees the latest
  // accumulated AnswerState (not the last-changed partial). Update before setAnswers.
  const latestAnswersRef = useRef<Map<number, AnswerState>>(new Map())

  const persistDraft = useCallback((qn: number, fullAnswer: AnswerState) => {
    const sid = sessionIdRef.current
    if (sid == null) return
    const existing = debounceRef.current.get(qn)
    if (existing) clearTimeout(existing)
    const timer = setTimeout(async () => {
      debounceRef.current.delete(qn)
      try {
        // D-01 / Pattern Map: must use fetchApi (CSRF/auth wrapper), not bare fetch.
        await fetchApi("/api/qramm/assessment/draft", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sid,
            question_number: qn,
            answer_value: fullAnswer.answer_value ?? null,
            evidence_note: fullAnswer.evidence_note ?? null,
          }),
        })
      } catch {
        // Toast surfacing happens in the page layer — provider stays silent.
      }
    }, 300)
    debounceRef.current.set(qn, timer)
  }, [])

  const setAnswer = useCallback((questionNumber: number, state: Partial<AnswerState>) => {
    // BR-01 (D-03): merge into latestAnswersRef synchronously, then pass FULL merged answer
    // to persistDraft — guarantees the debounced POST contains the full accumulated state.
    const existing = latestAnswersRef.current.get(questionNumber) ?? DEFAULT_ANSWER
    const merged: AnswerState = { ...existing, ...state }
    const nextMap = new Map(latestAnswersRef.current)
    nextMap.set(questionNumber, merged)
    latestAnswersRef.current = nextMap
    setAnswers(latestAnswersRef.current)
    persistDraft(questionNumber, merged)
  }, [persistDraft])

  const confirmAnswer = useCallback((qn: number, value: 1 | 2 | 3 | 4) => {
    // BR-02 (D-04): direct flush, bypasses debounce.
    // 1. Cancel pending debounce for this question.
    const pending = debounceRef.current.get(qn)
    if (pending) {
      clearTimeout(pending)
      debounceRef.current.delete(qn)
    }
    // 2. Merge confirmed state into latestAnswersRef and React state.
    const existing = latestAnswersRef.current.get(qn) ?? DEFAULT_ANSWER
    const merged: AnswerState = {
      ...existing,
      answer_value: value,
      confirmed_at: new Date().toISOString(),
    }
    const nextMap = new Map(latestAnswersRef.current)
    nextMap.set(qn, merged)
    latestAnswersRef.current = nextMap
    setAnswers(latestAnswersRef.current)
    // 3. Direct fetch — no debounce. Backend auto-sets confirmed_at when answer_value
    //    arrives for a row with suggested_answer != null (qramm.py:565).
    const sid = sessionIdRef.current
    if (sid == null) return
    fetchApi("/api/qramm/assessment/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sid,
        question_number: qn,
        answer_value: value,
      }),
    }).catch(() => {})
  }, [])

  const clearPendingDebounces = useCallback(() => {
    // WR-14 (D-05): abort all pending timers (called from handleNewAssessment).
    debounceRef.current.forEach((t) => clearTimeout(t))
    debounceRef.current.clear()
  }, [])

  const resetAnswers = useCallback((next: Map<number, AnswerState>) => {
    // Keep latestAnswersRef aligned with the explicit reset (e.g., new session seeding).
    latestAnswersRef.current = next
    setAnswers(next)
  }, [])

  // WR-03 (D-05): clear all pending debounce timers on provider unmount.
  useEffect(() => {
    return () => {
      debounceRef.current.forEach((t) => clearTimeout(t))
      debounceRef.current.clear()
    }
  }, [])

  return (
    <QRAMMContext.Provider value={{
      sessionId, setSessionId,
      answers, setAnswer, resetAnswers,
      confirmAnswer, clearPendingDebounces,
      profile, setProfile,
      scoreResult, setScoreResult,
    }}>
      {children}
    </QRAMMContext.Provider>
  )
}
