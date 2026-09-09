/**
 * Phase 192 Plan 10 (PARITY-01) — Effective config panel mounted on the
 * scan-submit surface, above the submit button (D-02). Verifies the panel
 * is present-but-collapsed at rest, reflects live form edits into its
 * request once expanded, and that the pre-existing submit flow (including
 * 422 handling) is completely unaffected by the new disclosure panel.
 */
import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

const mockFetchApi = vi.fn()

vi.mock("@/lib/api", () => ({
  fetchApi: (...args: unknown[]) => mockFetchApi(...args),
}))

vi.mock("@/context/vertical-context", () => ({
  useVertical: () => ({ id: "general", label: "General", preset: null }),
}))

import { ScanNewPage } from "@/pages/scan-new"

function renderPage() {
  return render(
    <MemoryRouter>
      <ScanNewPage />
    </MemoryRouter>,
  )
}

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: async () => body }
}

afterEach(() => {
  mockFetchApi.mockReset()
})

describe("ScanNewPage — Effective config panel mount (PARITY-01)", () => {
  it("renders the collapsed 'Effective config' trigger above the submit button, with no config fetch at rest", () => {
    renderPage()

    expect(screen.getByText("Effective config")).toBeInTheDocument()
    expect(screen.queryByText("Grouped")).not.toBeInTheDocument()
    expect(mockFetchApi).not.toHaveBeenCalled()

    const submitButton = screen.getByRole("button", { name: /run scan/i })
    expect(submitButton).toBeInTheDocument()
  })

  it("reflects an edited targets value into the config-preview request once expanded", async () => {
    mockFetchApi.mockResolvedValue(
      jsonResponse({
        vertical: "general",
        profile: "standard",
        redacted_field_count: 0,
        sections: [],
        raw: {},
      }),
    )
    renderPage()

    const targetsInput = screen.getByLabelText("Targets")
    fireEvent.change(targetsInput, { target: { value: "edited.example.com" } })

    fireEvent.click(screen.getByText("Effective config"))

    await waitFor(() => expect(mockFetchApi).toHaveBeenCalled())
    const calledPath = mockFetchApi.mock.calls[0][0] as string
    expect(calledPath).toContain("targets=edited.example.com")
  })

  it("leaves the existing submit flow, including 422 handling, unaffected", async () => {
    mockFetchApi.mockResolvedValue(
      jsonResponse(
        { detail: [{ msg: "Targets field is required.", loc: ["body", "targets"] }] },
        false,
        422,
      ),
    )
    renderPage()

    const targetsInput = screen.getByLabelText("Targets")
    fireEvent.change(targetsInput, { target: { value: "example.com" } })

    const submitButton = screen.getByRole("button", { name: /run scan/i })
    fireEvent.click(submitButton)

    expect(await screen.findByText("Targets field is required.")).toBeInTheDocument()
    expect(mockFetchApi).toHaveBeenCalledWith(
      "/api/jobs",
      expect.objectContaining({ method: "POST" }),
    )
  })
})
