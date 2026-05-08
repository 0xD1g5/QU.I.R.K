import { createContext } from "react"

export interface AnswerState {
  answer_value: 1 | 2 | 3 | 4 | null
  suggested_answer: 1 | 2 | 3 | 4 | null
  confirmed_at: string | null   // ISO8601
  evidence_note: string
}

export interface OrgProfile {
  industry: string
  org_size: string
  geographic_scope: string
  data_sensitivity: string
  regulatory_obligations: string[]
  multiplier: number
}

export interface ScoreResult {
  overall: number
  maturity: string
  dimensions: Record<string, { score: number; weighted: number }>
  profile_multiplier: number
}

interface QRAMMContextValue {
  sessionId: number | null
  setSessionId: (id: number | null) => void
  answers: Map<number, AnswerState>
  setAnswer: (questionNumber: number, state: Partial<AnswerState>) => void
  resetAnswers: (next: Map<number, AnswerState>) => void
  profile: OrgProfile | null
  setProfile: (p: OrgProfile | null) => void
  scoreResult: ScoreResult | null
  setScoreResult: (r: ScoreResult | null) => void
}

export const QRAMMContext = createContext<QRAMMContextValue>({
  sessionId: null,
  setSessionId: () => {},
  answers: new Map(),
  setAnswer: () => {},
  resetAnswers: () => {},
  profile: null,
  setProfile: () => {},
  scoreResult: null,
  setScoreResult: () => {},
})
