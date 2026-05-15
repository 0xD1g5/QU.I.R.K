import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { setupServer } from "msw/node"
import { http, HttpResponse } from "msw"
import { MemoryRouter } from "react-router-dom"
import { OrgProfilePage } from "@/pages/qramm-profile"

// Mock fetchApi to call native fetch so MSW intercepts.
vi.mock("@/lib/api", () => ({
  fetchApi: (path: string, options?: RequestInit) => fetch(path, options),
}))

// Stub useQRAMMSession so the page renders the form (State C) directly.
vi.mock("@/hooks/useQRAMMSession", () => ({
  useQRAMMSession: () => ({ session: null, loading: false, reload: () => {} }),
}))

const server = setupServer()
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

function renderPage() {
  return render(
    <MemoryRouter>
      <OrgProfilePage />
    </MemoryRouter>,
  )
}

async function fillFormAndSubmit() {
  // The form has required Select fields; we cannot easily drive Radix selects
  // in jsdom. Instead we submit the form directly via the form's submit event
  // so handleSubmit runs unconditionally (it does its own validation by
  // failing the network call rather than requiring fields).
  const form = document.querySelector("form")
  if (!form) throw new Error("form not found")
  fireEvent.submit(form)
}

describe("OrgProfilePage — D-04 (WR-08) submitError surfaces API detail", () => {
  it("renders the API detail string from a JSON {detail: ...} body", async () => {
    server.use(
      http.post("/api/qramm/sessions", () =>
        HttpResponse.json({ detail: "Organization Name required" }, { status: 400 }),
      ),
    )
    renderPage()
    await fillFormAndSubmit()
    await waitFor(() =>
      expect(screen.getByText(/Organization Name required/i)).toBeInTheDocument(),
    )
  })

  it("renders the raw-string error body when the API returns a plain string", async () => {
    server.use(
      http.post("/api/qramm/sessions", () =>
        new HttpResponse("server exploded", { status: 500 }),
      ),
    )
    renderPage()
    await fillFormAndSubmit()
    await waitFor(() =>
      expect(screen.getByText(/server exploded/i)).toBeInTheDocument(),
    )
  })
})
