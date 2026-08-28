import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { setupServer } from "msw/node"
import { http, HttpResponse } from "msw"
import { MemoryRouter } from "react-router-dom"
import { AssessmentPage } from "@/pages/qramm-assessment"
import { DIMENSIONS, DIMENSION_PRACTICE_AREAS } from "@/lib/qramm-constants"
import type { QuestionItem } from "@/types/api"

// Phase 170-03 QRAMM-08: real render test proving the 4 dimension tabs
// (CVI/SGRM/DPE/ITR) together cover all 120 catalog questions, 30 per
// dimension — not just a comment-string check (the sibling
// qramm-assessment-tab-comment.test.tsx only asserts a code comment says
// "6-tab" and does not satisfy this requirement).

vi.mock("@/lib/api", () => ({
  fetchApi: (path: string, options?: RequestInit) => fetch(path, options),
}))

vi.mock("@/hooks/useQRAMMSession", () => ({
  useQRAMMSession: () => ({
    session: {
      session_id: 1,
      org_name: null,
      created_at: null,
      status: "in_progress",
      answers_count: 0,
    },
    loading: false,
    error: null,
    reload: () => {},
    resetSession: () => {},
  }),
}))

// Build a 120-question fixture programmatically from the real
// DIMENSION_PRACTICE_AREAS map: 4 dimensions x 3 practice areas x 10
// questions each = 120, with sequential question numbers 1-120.
function buildQuestionCatalog(): QuestionItem[] {
  const questions: QuestionItem[] = []
  let questionNumber = 1
  for (const dim of DIMENSIONS) {
    for (const practiceArea of DIMENSION_PRACTICE_AREAS[dim]) {
      for (let i = 0; i < 10; i++) {
        questions.push({
          question_number: questionNumber,
          dimension: dim,
          practice_area: practiceArea,
          text: `Question ${questionNumber} for practice area ${practiceArea}`,
          maturity_labels: ["1", "2", "3", "4"],
        })
        questionNumber++
      }
    }
  }
  return questions
}

const QUESTION_CATALOG = buildQuestionCatalog()

const server = setupServer(
  http.get("/api/qramm/questions", () => HttpResponse.json(QUESTION_CATALOG)),
)
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderPage() {
  return render(
    <MemoryRouter>
      <AssessmentPage />
    </MemoryRouter>,
  )
}

describe("AssessmentPage — QRAMM-08 dimension tab question coverage", () => {
  it("has exactly 120 questions in the generated fixture, 30 per dimension", () => {
    // Sanity-check the fixture itself matches the documented backend
    // invariant (test_qramm_questions.py: dim_counts == 30 each) before
    // asserting anything about the rendered page.
    expect(QUESTION_CATALOG).toHaveLength(120)
    for (const dim of DIMENSIONS) {
      const count = QUESTION_CATALOG.filter((q) => q.dimension === dim).length
      expect(count).toBe(30)
    }
  })

  it("renders all 4 dimension tabs plus Scorecard and Compliance Map", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "CVI" })).toBeInTheDocument()
    })
    expect(screen.getByRole("tab", { name: "SGRM" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "DPE" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "ITR" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Scorecard" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Compliance Map" })).toBeInTheDocument()
  })

  it("each dimension tab shows 0 of 30 questions answered, summing to 120 total", async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "CVI" })).toBeInTheDocument()
    })

    let totalAcrossDimensions = 0
    for (const dim of DIMENSIONS) {
      fireEvent.click(screen.getByRole("tab", { name: dim }))

      const progress = await waitFor(() =>
        screen.getByLabelText(/\d+ of \d+ questions answered/i),
      )
      const label = progress.getAttribute("aria-label") ?? ""
      const match = label.match(/(\d+) of (\d+) questions answered/i)
      expect(match, `dimension ${dim} progress label did not match expected shape: ${label}`).not.toBeNull()

      const [, answered, total] = match as RegExpMatchArray
      expect(Number(answered)).toBe(0)
      expect(Number(total)).toBe(30)
      totalAcrossDimensions += Number(total)
    }

    expect(totalAcrossDimensions).toBe(120)
  })
})
