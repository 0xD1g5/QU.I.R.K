import { ChevronDown } from "lucide-react"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible"
import { QuestionCard } from "./QuestionCard"
import type { AnswerState } from "@/context/QRAMMContext"

interface QuestionEntry {
  question_number: number
  text: string
  maturity_labels: string[]
}

interface PracticeAreaSectionProps {
  practiceArea: string             // e.g. "1.1"
  practiceAreaName: string         // e.g. "Cryptographic Discovery & Inventory Management"
  questions: QuestionEntry[]
  answers: Map<number, AnswerState>
  onAnswerChange: (qn: number, partial: Partial<AnswerState>) => void
  onConfirm: (qn: number, pendingValue: number) => void
}

const DEFAULT_ANSWER: AnswerState = {
  answer_value: null,
  suggested_answer: null,
  confirmed_at: null,
  evidence_note: "",
}

export function PracticeAreaSection({
  practiceAreaName,
  questions,
  answers,
  onAnswerChange,
  onConfirm,
}: PracticeAreaSectionProps) {
  const answered = questions.filter(
    (q) => (answers.get(q.question_number)?.answer_value ?? null) != null
  ).length

  return (
    <Collapsible defaultOpen={true}>
      <CollapsibleTrigger className="flex items-center justify-between w-full py-3 px-4 rounded-lg border bg-card hover:bg-muted/50 transition-colors">
        <span className="text-base font-semibold text-left">{practiceAreaName}</span>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-foreground/70">
            {answered}/{questions.length} answered
          </span>
          <ChevronDown className="h-4 w-4 text-foreground/70 transition-transform duration-200 data-[state=open]:rotate-180" />
        </div>
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-6 pt-4">
        {questions.map((q) => (
          <QuestionCard
            key={q.question_number}
            questionNumber={q.question_number}
            questionText={q.text}
            maturityLabels={q.maturity_labels}
            answer={answers.get(q.question_number) ?? DEFAULT_ANSWER}
            onAnswerChange={(partial) => onAnswerChange(q.question_number, partial)}
            onConfirm={(pendingValue) => onConfirm(q.question_number, pendingValue)}
          />
        ))}
      </CollapsibleContent>
    </Collapsible>
  )
}
