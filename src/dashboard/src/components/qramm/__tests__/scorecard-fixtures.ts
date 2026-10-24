// Shared QRAMM scorecard test fixtures (Phase 231 D-07a). Not a test file: the
// vitest include glob only collects *.test/*.spec files. Reused by 231-07.

import type { AnswerState, ScoreResult } from "@/context/QRAMMContext"
import { DIMENSIONS } from "@/lib/qramm-constants"
import type { Dimension } from "@/lib/qramm-constants"

/** Question number -> dimension, `perDim` questions per dimension in DIMENSIONS order. */
export function buildCatalog(perDim = 30): Map<number, string> {
  const catalog = new Map<number, string>()
  let qn = 1
  for (const dim of DIMENSIONS) {
    for (let i = 0; i < perDim; i += 1) {
      catalog.set(qn, dim)
      qn += 1
    }
  }
  return catalog
}

/** Answers the first N questions of each dimension in `catalog` with `value`. */
export function buildAnswers(
  catalog: Map<number, string>,
  answeredPerDim: Partial<Record<Dimension, number>>,
  value: 1 | 2 | 3 | 4 = 3,
): Map<number, AnswerState> {
  const answers = new Map<number, AnswerState>()
  const used: Record<string, number> = {}
  for (const [qn, dim] of catalog) {
    const want = answeredPerDim[dim as Dimension] ?? 0
    const done = used[dim] ?? 0
    if (done >= want) continue
    answers.set(qn, {
      answer_value: value,
      suggested_answer: null,
      confirmed_at: "2026-10-24T00:00:00Z",
      evidence_note: "",
    })
    used[dim] = done + 1
  }
  return answers
}

/** A QRAMMContext value carrying `scoreResult` and `answers`. */
export function buildCtx(
  scoreResult: ScoreResult | null,
  answers: Map<number, AnswerState> = new Map(),
) {
  return {
    sessionId: 1 as number | null,
    setSessionId: () => {},
    answers,
    setAnswer: () => {},
    resetAnswers: () => {},
    profile: null,
    setProfile: () => {},
    scoreResult,
    setScoreResult: () => {},
    confirmAnswer: () => {},
    clearPendingDebounces: () => {},
  }
}
