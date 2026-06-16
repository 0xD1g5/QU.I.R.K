import { useState, useEffect, useContext, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { fetchApi } from "@/lib/api"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { PageSpinner } from "@/components/PageSpinner"
import { QRAMMContext, type AnswerState } from "@/context/QRAMMContext"
import { useQRAMMSession } from "@/hooks/useQRAMMSession"
import {
  DIMENSIONS,
  type Dimension,
  DIMENSION_PRACTICE_AREAS,
  PRACTICE_AREA_NAMES,
} from "@/lib/qramm-constants"
import { PracticeAreaSection } from "@/components/qramm/PracticeAreaSection"
import { ScorecardTab } from "@/components/qramm/ScorecardTab"
import { ComplianceMapTab } from "@/components/qramm/ComplianceMapTab"
import type { QuestionItem } from "@/types/api"

// ── Dimension tab inner component ─────────────────────────────────────────────

interface DimensionTabProps {
  dimension: Dimension
  questionsByArea: Map<string, QuestionItem[]>
  answers: Map<number, AnswerState>
  onAnswerChange: (qn: number, partial: Partial<AnswerState>) => void
  onConfirm: (qn: number, pendingValue: number) => void
}

function DimensionTab({
  dimension,
  questionsByArea,
  answers,
  onAnswerChange,
  onConfirm,
}: DimensionTabProps) {
  const practiceAreas = DIMENSION_PRACTICE_AREAS[dimension]

  // Count answered questions across all practice areas for this dimension
  const allQuestions = practiceAreas.flatMap(
    (pa) => questionsByArea.get(pa) ?? []
  )
  const answered = allQuestions.filter(
    (q) => (answers.get(q.question_number)?.answer_value ?? null) != null
  ).length
  const total = allQuestions.length

  return (
    <div className="space-y-6 pt-4">
      {/* Per-dimension progress */}
      <div className="space-y-1.5">
        <Progress
          value={total > 0 ? (answered / total) * 100 : 0}
          aria-label={`${answered} of ${total} questions answered`}
        />
        <p className="text-xs text-foreground/70">
          {answered} of {total} answered
        </p>
      </div>

      {/* Practice area sections */}
      {practiceAreas.map((pa) => {
        const questions = questionsByArea.get(pa) ?? []
        return (
          <PracticeAreaSection
            key={pa}
            practiceArea={pa}
            practiceAreaName={PRACTICE_AREA_NAMES[pa] ?? pa}
            questions={questions}
            answers={answers}
            onAnswerChange={onAnswerChange}
            onConfirm={onConfirm}
          />
        )
      })}
    </div>
  )
}

// ── AssessmentPage ─────────────────────────────────────────────────────────────

export function AssessmentPage() {
  const ctx = useContext(QRAMMContext)
  const navigate = useNavigate()
  const { session, loading: sessionLoading, resetSession } = useQRAMMSession()

  const [questions, setQuestions] = useState<QuestionItem[]>([])
  const [questionsLoading, setQuestionsLoading] = useState(true)
  const [showNewAssessmentConfirm, setShowNewAssessmentConfirm] = useState(false)
  const [archiving, setArchiving] = useState(false)

  // Fetch question catalog on mount (cancellation guard pattern)
  useEffect(() => {
    let cancelled = false
    setQuestionsLoading(true)

    fetchApi("/api/qramm/questions")
      .then((r) => {
        if (!r.ok) throw new Error(`/api/qramm/questions: ${r.status}`)
        return r.json() as Promise<QuestionItem[]>
      })
      .then((data) => {
        if (!cancelled) {
          setQuestions(data)
          setQuestionsLoading(false)
        }
      })
      .catch(() => {
        if (!cancelled) setQuestionsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  // Group questions by practice_area — recompute only when catalog changes
  const questionsByArea = useMemo(() => {
    const map = new Map<string, QuestionItem[]>()
    for (const q of questions) {
      const bucket = map.get(q.practice_area) ?? []
      bucket.push(q)
      map.set(q.practice_area, bucket)
    }
    // Sort each bucket by question_number ascending
    for (const [pa, bucket] of map) {
      map.set(
        pa,
        bucket.sort((a, b) => a.question_number - b.question_number)
      )
    }
    return map
  }, [questions])

  // Authoritative question-number → dimension lookup derived from the catalog.
  // Passed to ScorecardTab to avoid hard-coded arithmetic on question ranges.
  const qnToDim = useMemo(() => {
    const m = new Map<number, string>()
    for (const q of questions) m.set(q.question_number, q.dimension)
    return m
  }, [questions])

  // Answer change handler — delegates to QRAMMProvider's debounced persister
  function handleAnswerChange(qn: number, partial: Partial<AnswerState>) {
    ctx.setAnswer(qn, partial)
  }

  // Confirm handler for auto-filled questions — direct flush via QRAMMProvider.confirmAnswer
  // (BR-02): cancels pending debounce for the question, merges confirmed_at into local state,
  // and POSTs answer_value directly. Backend auto-sets confirmed_at server-side.
  function handleConfirm(qn: number, pendingValue: number) {
    ctx.confirmAnswer(qn, pendingValue as 1 | 2 | 3 | 4)
  }

  // New Assessment: archive current session, reset context, redirect to /qramm.
  // Only reset client context and navigate on a successful DELETE — a non-ok
  // response does not throw, so we must check resp.ok explicitly to avoid
  // diverging client and server state on failure.
  async function handleNewAssessment() {
    if (!ctx.sessionId) return
    ctx.clearPendingDebounces()  // WR-14: abort timers before resetting state
    setArchiving(true)
    try {
      const resp = await fetchApi(`/api/qramm/sessions/${ctx.sessionId}`, { method: "DELETE" })
      if (!resp.ok && resp.status !== 404) {
        // Server still has the session — do NOT reset context or navigate.
        return
      }
      ctx.setSessionId(null)
      ctx.resetAnswers(new Map())
      ctx.setProfile(null)
      ctx.setScoreResult(null)
      resetSession()  // D-26 (IN-04): clear seededRef so the next session re-seeds
      navigate("/qramm")
    } catch {
      // Network error — leave context intact so the user can retry.
    } finally {
      setArchiving(false)
    }
  }

  // Loading state
  if (sessionLoading || questionsLoading) {
    return <PageSpinner ariaLabel="Loading QRAMM assessment" />
  }

  // Empty state — no session exists
  if (!session) {
    return (
      <Card className="max-w-lg mx-auto mt-12">
        <CardHeader>
          <CardTitle>No Assessment Started</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Complete the Org Profile to begin your QRAMM assessment.
          </p>
          <Button onClick={() => navigate("/qramm")}>Begin Org Profile</Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">QRAMM Assessment</h1>
        <div className="space-y-2 text-right">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowNewAssessmentConfirm((v) => !v)}
          >
            New Assessment
          </Button>
          {showNewAssessmentConfirm && (
            <div className="rounded-md border bg-card p-4 text-left space-y-3 shadow-sm">
              <p className="text-sm font-medium">Start a New Assessment?</p>
              <p className="text-xs text-muted-foreground">
                Starting a new assessment will archive your current progress. This cannot be undone.
              </p>
              <div className="flex gap-2 justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowNewAssessmentConfirm(false)}
                >
                  Keep Current Assessment
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  disabled={archiving}
                  onClick={handleNewAssessment}
                >
                  {archiving ? "Archiving…" : "Confirm New Assessment"}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 6-tab assessment layout: CVI, SGRM, DPE, ITR, Scorecard, Compliance Map — closes react-frontend/IN-01 (D-23) */}
      <Tabs defaultValue="cvi">
        <TabsList>
          <TabsTrigger value="cvi">CVI</TabsTrigger>
          <TabsTrigger value="sgrm">SGRM</TabsTrigger>
          <TabsTrigger value="dpe">DPE</TabsTrigger>
          <TabsTrigger value="itr">ITR</TabsTrigger>
          <TabsTrigger value="scorecard">Scorecard</TabsTrigger>
          <TabsTrigger value="compliance">Compliance Map</TabsTrigger>
        </TabsList>

        {DIMENSIONS.map((dim) => (
          <TabsContent key={dim} value={dim.toLowerCase()}>
            <DimensionTab
              dimension={dim}
              questionsByArea={questionsByArea}
              answers={ctx.answers}
              onAnswerChange={handleAnswerChange}
              onConfirm={handleConfirm}
            />
          </TabsContent>
        ))}

        <TabsContent value="scorecard">
          <ScorecardTab qnToDim={qnToDim} />
        </TabsContent>

        <TabsContent value="compliance">
          <ComplianceMapTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
