import { describe, it, expect, beforeAll, afterAll, afterEach, beforeEach, vi } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { setupServer } from "msw/node"
import { http, HttpResponse } from "msw"
import { useContext, type ReactNode } from "react"
import { QRAMMProvider } from "../QRAMMProvider"
import { QRAMMContext } from "../QRAMMContext"

// MSW must see fetchApi as a normal fetch — stub it to native fetch.
vi.mock("@/lib/api", () => ({
  fetchApi: (path: string, options?: RequestInit) => fetch(path, options),
}))

const recordedRequests: { url: string; body: unknown }[] = []

const server = setupServer(
  http.post("/api/qramm/assessment/draft", async ({ request }) => {
    const body = await request.json()
    recordedRequests.push({ url: request.url, body })
    return HttpResponse.json({ ok: true })
  }),
)

beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
  recordedRequests.length = 0
  vi.useRealTimers()
})
afterAll(() => server.close())

const wrapper = ({ children }: { children: ReactNode }) => (
  <QRAMMProvider>{children}</QRAMMProvider>
)

describe("QRAMMProvider — HOOK-02 debounce coalescing", () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: false })
  })

  it("coalesces 20 rapid setAnswer calls within 300ms into exactly 1 POST", async () => {
    const { result } = renderHook(() => useContext(QRAMMContext), { wrapper })

    // Establish session — required for persistDraft to fire
    act(() => {
      result.current.setSessionId(42)
    })

    // 20 rapid setAnswer calls within a single debounce window
    act(() => {
      for (let i = 1; i <= 20; i++) {
        result.current.setAnswer(1, { answer_value: ((i % 4) + 1) as 1 | 2 | 3 | 4 })
      }
    })

    // Last write
    const lastValue = ((20 % 4) + 1) as 1 | 2 | 3 | 4

    // Before timer fires — no POST yet
    expect(recordedRequests.length).toBe(0)

    // Advance fake timers past the 300ms debounce — this fires the setTimeout callback.
    // advanceTimersByTimeAsync also flushes microtasks so the async fetch can proceed.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(350)
    })

    // Give MSW a moment to record the intercepted request (real microtasks)
    await act(async () => {
      await new Promise((r) => { vi.useRealTimers(); setTimeout(r, 100) })
    })

    // Exactly 1 POST recorded
    expect(recordedRequests.length).toBe(1)
    const body = recordedRequests[0].body as {
      session_id: number
      question_number: number
      answer_value: number
    }
    expect(body.session_id).toBe(42)
    expect(body.question_number).toBe(1)
    expect(body.answer_value).toBe(lastValue)
  })
})
