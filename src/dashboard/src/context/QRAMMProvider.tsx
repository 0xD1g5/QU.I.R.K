import { useState, useRef, useCallback } from "react"
import type { ReactNode } from "react"
import { QRAMMContext } from "./QRAMMContext"
import type { AnswerState, OrgProfile, ScoreResult } from "./QRAMMContext"

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

  const persistDraft = useCallback((qn: number, state: Partial<AnswerState>) => {
    const sid = sessionIdRef.current
    if (sid == null) return
    const existing = debounceRef.current.get(qn)
    if (existing) clearTimeout(existing)
    const timer = setTimeout(async () => {
      debounceRef.current.delete(qn)
      try {
        await fetch("/api/qramm/assessment/draft", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sid,
            question_number: qn,
            ...("answer_value" in state && { answer_value: state.answer_value ?? null }),
            ...("evidence_note" in state && { evidence_note: state.evidence_note ?? null }),
          }),
        })
      } catch {
        // Toast surfacing happens in the page layer — provider stays silent.
        // (UI-SPEC: "Answer not saved — check your connection")
      }
    }, 300)
    debounceRef.current.set(qn, timer)
  }, [])

  const setAnswer = useCallback((questionNumber: number, state: Partial<AnswerState>) => {
    setAnswers(prev => {
      const next = new Map(prev)
      const existing = next.get(questionNumber) ?? {
        answer_value: null,
        suggested_answer: null,
        confirmed_at: null,
        evidence_note: "",
      }
      const merged: AnswerState = { ...existing, ...state }
      next.set(questionNumber, merged)
      return next
    })
    persistDraft(questionNumber, state)
  }, [persistDraft])

  const resetAnswers = useCallback((next: Map<number, AnswerState>) => {
    setAnswers(next)
  }, [])

  return (
    <QRAMMContext.Provider value={{
      sessionId, setSessionId,
      answers, setAnswer, resetAnswers,
      profile, setProfile,
      scoreResult, setScoreResult,
    }}>
      {children}
    </QRAMMContext.Provider>
  )
}
