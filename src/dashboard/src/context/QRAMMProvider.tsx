import { useState, useRef, useCallback } from "react"
import type { ReactNode } from "react"
import { QRAMMContext } from "./QRAMMContext"
import type { AnswerState, OrgProfile, ScoreResult } from "./QRAMMContext"

export function QRAMMProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [answers, setAnswers] = useState<Map<number, AnswerState>>(new Map())
  const [profile, setProfile] = useState<OrgProfile | null>(null)
  const [scoreResult, setScoreResult] = useState<ScoreResult | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const sessionIdRef = useRef<number | null>(null)
  sessionIdRef.current = sessionId

  const persistDraft = useCallback((qn: number, state: Partial<AnswerState>) => {
    const sid = sessionIdRef.current
    if (sid == null) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        await fetch("/api/qramm/assessment/draft", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sid,
            question_number: qn,
            answer_value: state.answer_value ?? null,
            evidence_note: state.evidence_note ?? null,
          }),
        })
      } catch {
        // Toast surfacing happens in the page layer — provider stays silent.
        // (UI-SPEC: "Answer not saved — check your connection")
      }
    }, 300)
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
