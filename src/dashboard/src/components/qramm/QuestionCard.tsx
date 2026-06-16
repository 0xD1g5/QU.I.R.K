import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import type { AnswerState } from "@/context/QRAMMContext"

interface QuestionCardProps {
  questionNumber: number
  questionText: string
  maturityLabels: string[]   // 4 entries from QRAMM_QUESTIONS
  answer: AnswerState
  onAnswerChange: (next: Partial<AnswerState>) => void
  onConfirm: (pendingValue: number) => void
}

export function QuestionCard({
  questionNumber,
  questionText,
  maturityLabels,
  answer,
  onAnswerChange,
  onConfirm,
}: QuestionCardProps) {
  // Local pending value for two-step confirm flow (D-04, D-05, D-06)
  const [pendingValue, setPendingValue] = useState<number | null>(null)

  const isAutoFilled =
    answer.suggested_answer != null && answer.confirmed_at == null

  // Modified means: auto-filled, user picked a different value from the suggestion,
  // but has not yet clicked Confirm
  const isModified =
    isAutoFilled &&
    pendingValue != null &&
    pendingValue !== answer.suggested_answer

  // The radio group display value:
  // - For auto-filled: show pendingValue if set, else show suggested_answer
  // - For regular: show answer_value if set, else empty string
  const radioDisplayValue = isAutoFilled
    ? String(pendingValue ?? answer.suggested_answer ?? "")
    : answer.answer_value != null
    ? String(answer.answer_value)
    : ""

  function handleRadioChange(val: string) {
    const numeric = Number(val)
    // T-54-18: validate 1 <= n <= 4 before updating state
    if (!Number.isInteger(numeric) || numeric < 1 || numeric > 4) return

    if (isAutoFilled) {
      // D-04/D-05: for auto-filled questions, hold in local pending state only.
      // answer_value stays null until Confirm is clicked.
      setPendingValue(numeric)
    } else {
      // Non-auto-filled: write immediately via context (QRAMMProvider debounces 300ms)
      onAnswerChange({ answer_value: numeric as 1 | 2 | 3 | 4 })
    }
  }

  function handleEvidenceChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    // Evidence note always writes immediately (no two-step gate on text)
    // T-54-17: evidence_note is rendered as a textarea value (React-controlled),
    // never via unsafe HTML injection APIs. React auto-escapes string children.
    onAnswerChange({ evidence_note: e.target.value })
  }

  function handleConfirm() {
    const valueToConfirm = pendingValue ?? answer.suggested_answer
    if (valueToConfirm == null) return
    // D-06: Confirm writes answer_value + sets confirmed_at optimistically
    onConfirm(valueToConfirm)
    setPendingValue(null)
  }

  return (
    <Card>
      <CardContent className="p-6">
        {/* Header row: question label + text + badge */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex-1">
            <span className="text-xs text-foreground/70 font-semibold block mb-1">
              Q{questionNumber}
            </span>
            <p className="text-sm leading-relaxed">{questionText}</p>
          </div>
          {/* Auto-fill or modified badge */}
          {isAutoFilled && !isModified && (
            <Badge
              className="severity-accent-chip shrink-0 mt-0.5"
              role="status"
              aria-label={`Question ${questionNumber} auto-filled from scan`}
            >
              Auto-filled from scan
            </Badge>
          )}
          {isModified && (
            <Badge
              className="severity-medium-chip shrink-0 mt-0.5"
              role="status"
              aria-label={`Question ${questionNumber} modified from scan suggestion`}
            >
              Modified from scan suggestion
            </Badge>
          )}
        </div>

        {/* Radio group */}
        <RadioGroup
          value={radioDisplayValue}
          onValueChange={handleRadioChange}
          className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4"
        >
          {maturityLabels.map((label, idx) => {
            const value = String(idx + 1)
            const id = `q${questionNumber}-opt-${value}`
            return (
              <div key={value} className="flex items-start gap-2">
                <RadioGroupItem value={value} id={id} className="mt-0.5 shrink-0" />
                <Label htmlFor={id} className="text-sm cursor-pointer leading-snug">
                  {label}
                  <span className="text-xs text-foreground/70"> ({idx + 1})</span>
                </Label>
              </div>
            )
          })}
        </RadioGroup>

        {/* Confirm button — only for auto-filled questions */}
        {isAutoFilled && (
          <div className="flex justify-end mb-3">
            <Button
              variant="default"
              size="sm"
              onClick={handleConfirm}
              aria-label={`Confirm answer for question ${questionNumber}`}
            >
              Confirm Answer
            </Button>
          </div>
        )}

        {/* Evidence note textarea */}
        <div className="space-y-1">
          <label
            htmlFor={`q${questionNumber}-evidence`}
            className="text-xs text-foreground/70"
          >
            Evidence note (optional):
          </label>
          <textarea
            id={`q${questionNumber}-evidence`}
            value={answer.evidence_note}
            onChange={handleEvidenceChange}
            placeholder="Add supporting evidence..."
            className="min-h-[80px] w-full text-sm rounded-md border border-input bg-transparent px-3 py-2 shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring resize-y"
            maxLength={2000}
          />
        </div>
      </CardContent>
    </Card>
  )
}
