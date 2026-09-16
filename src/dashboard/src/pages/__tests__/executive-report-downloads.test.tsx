import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { render, screen, cleanup, fireEvent, waitFor } from "@testing-library/react"

// Phase 209 Plan 02 (DELIV-02) — Wave 0 RED scaffolding for the Executive-page
// download control. The component under test (`ExecutivePage`'s five-format
// download group) does NOT exist yet — it lands in plan 209-04. Every leg in
// this file is expected to FAIL until then. Do not weaken these assertions to
// make them pass early; do not build the UI here to satisfy them.
//
// Copy strings asserted below are VERBATIM from 209-UI-SPEC.md's Copywriting
// Contract (locked, approved 6/6) — a paraphrase here would silently diverge
// from what plan 209-04 is required to render.

// SCORE-04 / D-09/D-10 (184.4): mutable so tests can drive the capped vs.
// uncapped scenario; undefined (default) documents the uncapped case. Copied
// verbatim from the executive-pdf-cleanup.test.tsx mock shape (209-PATTERNS.md).
let scanDataRatingCapReason: string | undefined = undefined

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => ({
    data: {
      meta: { scan_id: "1", scanned_at: "2026-05-15T00:00:00Z", total_endpoints: 0, total_findings: 0 },
      score: {
        score: 50, rating: "Moderate", rating_cap_reason: scanDataRatingCapReason,
        subscores: { hygiene: 0, modern_tls: 0, identity_trust: 0, agility_signals: 0, data_at_rest: 0, data_in_motion: 0 },
        drivers: [],
      },
      confidence: { confidence_score: 0, confidence_rating: "LOW", factor_breakdown: {} },
      findings: [],
      partial_failures: [],
    },
    loading: false,
    error: null,
  }),
}))

const fetchApiMock = vi.fn()
vi.mock("@/lib/api", () => ({
  fetchApi: (...args: unknown[]) => fetchApiMock(...args),
}))

vi.mock("@/components/RegressionAlertChip", () => ({
  RegressionAlertChip: () => null,
}))

const revokeSpy = vi.fn()
const createSpy = vi.fn(() => "blob:fake-url")

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// --- Manifest fixture shape (209-UI-SPEC.md § Interaction Contract) ---------

type FormatKey = "html" | "pdf" | "docx" | "cbom-json" | "cbom-xml"

interface ManifestFormatEntry {
  available: boolean
  reason: string | null
}

interface Manifest {
  scan_time: string | null
  stamp: string
  formats: Record<FormatKey, ManifestFormatEntry>
}

function makeManifest(
  overrides: {
    scan_time?: string | null
    formats?: Partial<Record<FormatKey, ManifestFormatEntry>>
  } = {}
): Manifest {
  const defaults: Record<FormatKey, ManifestFormatEntry> = {
    html: { available: true, reason: null },
    pdf: { available: true, reason: null },
    docx: { available: true, reason: null },
    "cbom-json": { available: true, reason: null },
    "cbom-xml": { available: true, reason: null },
  }
  return {
    scan_time: Object.prototype.hasOwnProperty.call(overrides, "scan_time")
      ? overrides.scan_time ?? null
      : "2026-09-14T09:12:00Z",
    stamp: "20260914T091200Z",
    formats: { ...defaults, ...(overrides.formats ?? {}) },
  }
}

type DownloadResult = {
  ok: boolean
  status?: number
  json?: () => Promise<unknown>
  blob?: () => Promise<Blob>
}

// Module-level mutable state each test configures before rendering.
let manifest: Manifest
let downloadImpl: (fmt: string) => Promise<DownloadResult>

function defaultDownloadImpl(): Promise<DownloadResult> {
  return Promise.resolve({
    ok: true,
    blob: async () => new Blob(["fake-artifact-bytes"], { type: "application/octet-stream" }),
  })
}

// Installs the URL-branching fetchApi mock: manifest GET, per-format download
// GET, and a benign default for the pre-existing /api/export/pdf POST so the
// existing Export PDF button does not throw while these tests render the page.
function installFetchApiMock() {
  fetchApiMock.mockImplementation((url: unknown) => {
    if (typeof url === "string" && url === "/api/reports/latest/manifest") {
      return Promise.resolve({ ok: true, json: async () => manifest })
    }
    if (typeof url === "string" && url.startsWith("/api/export/pdf")) {
      return Promise.resolve({
        ok: true,
        blob: async () => new Blob(["%PDF-1.4"], { type: "application/pdf" }),
      })
    }
    const m = typeof url === "string" ? url.match(/^\/api\/reports\/latest\/([a-z0-9-]+)$/) : null
    if (m) {
      return downloadImpl(m[1])
    }
    return Promise.resolve({ ok: true, json: async () => ({}) })
  })
}

// Reason text is contractually "reachable in the DOM (as tooltip content,
// title, or aria-describedby target)" per the UI-SPEC — plan 209-04 keeps the
// tooltip-shape freedom, so this assertion checks multiple plausible surfaces
// rather than one hardcoded implementation detail.
function expectReasonReachable(reason: string) {
  const byText = screen.queryByText(reason)
  const byTitle = document.querySelector(`[title="${reason}"]`)
  const byAriaLabel = document.querySelector(`[aria-label="${reason}"]`)
  const byAriaDescription = Array.from(document.querySelectorAll("[aria-describedby]")).find((el) => {
    const id = el.getAttribute("aria-describedby")
    const described = id ? document.getElementById(id) : null
    return described?.textContent === reason
  })
  expect(byText || byTitle || byAriaLabel || byAriaDescription).toBeTruthy()
}

beforeEach(() => {
  fetchApiMock.mockReset()
  revokeSpy.mockReset()
  createSpy.mockClear()
  createSpy.mockImplementation(() => "blob:fake-url")
  scanDataRatingCapReason = undefined
  manifest = makeManifest()
  downloadImpl = defaultDownloadImpl
  vi.stubGlobal("URL", {
    createObjectURL: createSpy,
    revokeObjectURL: revokeSpy,
  })
  vi.stubGlobal("ResizeObserver", ResizeObserverStub)
  vi.useFakeTimers({ shouldAdvanceTime: true })
  installFetchApiMock()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

// ---------------------------------------------------------------------------
// Task 1: render / availability legs
// ---------------------------------------------------------------------------

describe("ExecutivePage — DELIV-02 report download group (render/availability)", () => {
  it("renders all five download buttons with the locked labels", async () => {
    // The module under test MUST be imported dynamically, AFTER vi.mock
    // registration — a static top-level import would bind the real fetchApi
    // and every branch above would silently no-op (209-PATTERNS.md).
    const { ExecutivePage } = await import("@/pages/executive")
    const { container } = render(<ExecutivePage />)

    await waitFor(() => expect(fetchApiMock).toHaveBeenCalled())

    const labels = ["HTML", "PDF", "DOCX", "CBOM (JSON)", "CBOM (XML)"]
    for (const label of labels) {
      const button = await screen.findByRole("button", { name: label })
      expect(button).toBeEnabled()
    }

    const group = container.querySelector('[aria-label="Download report artifacts"]')
    expect(group).not.toBeNull()
  })

  it("shows the scan-time disclosure when the manifest reports a scan_time", async () => {
    manifest = makeManifest({ scan_time: "2026-09-14T09:12:00Z" })
    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    const disclosure = await screen.findByText(/^Report from scan: /)
    expect(disclosure.textContent).toMatch(/^Report from scan: /)
  })

  it("shows the explicit-unknown scan-time copy when scan_time is null", async () => {
    manifest = makeManifest({ scan_time: null })
    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    const unknownLine = await screen.findByText("Report artifacts found — scan time unknown")
    // D-01/D-03: never substitute render time or today's date for a genuinely
    // unknown scan time — the line must carry no digits at all.
    expect(unknownLine.textContent).not.toMatch(/\d/)
    expect(screen.queryByText(/^Report from scan: /)).not.toBeInTheDocument()
  })

  it("renders an unavailable format disabled with its verbatim reason", async () => {
    const reason = "DOCX requires the optional extra: pip install quirk[docx]"
    manifest = makeManifest({ formats: { docx: { available: false, reason } } })
    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    const docxButton = await screen.findByRole("button", { name: "DOCX" })
    expect(docxButton).toBeDisabled()

    for (const label of ["HTML", "PDF", "CBOM (JSON)", "CBOM (XML)"]) {
      const button = await screen.findByRole("button", { name: label })
      expect(button).toBeEnabled()
    }

    expectReasonReachable(reason)
    // D-09: never collapse the specific reason into a generic "unavailable".
    expect(screen.queryByText(/^unavailable$/i)).not.toBeInTheDocument()
  })

  it("renders the fresh-install copy when every format is unavailable", async () => {
    const noScanReason = "No scan has run yet."
    manifest = makeManifest({
      scan_time: null,
      formats: {
        html: { available: false, reason: noScanReason },
        pdf: { available: false, reason: noScanReason },
        docx: { available: false, reason: noScanReason },
        "cbom-json": { available: false, reason: noScanReason },
        "cbom-xml": { available: false, reason: noScanReason },
      },
    })
    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    await screen.findByText("No report artifacts yet — run a scan first.")

    // D-10: every button still renders, disabled — not removed. An empty
    // control is exactly what D-10 forbids.
    for (const label of ["HTML", "PDF", "DOCX", "CBOM (JSON)", "CBOM (XML)"]) {
      const button = await screen.findByRole("button", { name: label })
      expect(button).toBeDisabled()
    }

    expect(screen.queryByText(/no report exists/i)).not.toBeInTheDocument()
  })
})

// ---------------------------------------------------------------------------
// Task 2: download-interaction legs (per-format loading, failure trap, blob
// cleanup)
// ---------------------------------------------------------------------------

describe("ExecutivePage — DELIV-02 report download group (interaction state machine)", () => {
  it("clicking a format downloads it through fetchApi and creates exactly one object URL", async () => {
    const originalCreateElement = document.createElement.bind(document)
    const createdAnchors: HTMLAnchorElement[] = []
    const createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
      const el = originalCreateElement(tag)
      if (tag === "a") createdAnchors.push(el as HTMLAnchorElement)
      return el
    })
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {})

    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    const pdfButton = await screen.findByRole("button", { name: "PDF" })
    fireEvent.click(pdfButton)

    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1))

    const downloadCall = fetchApiMock.mock.calls.find(
      ([url]) => typeof url === "string" && url.includes("/api/reports/latest/pdf")
    )
    expect(downloadCall).toBeTruthy()
    const [, opts] = downloadCall as [string, { method?: string } | undefined]
    // Read-only download route: never a POST.
    expect(opts?.method).not.toBe("POST")

    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(createdAnchors[createdAnchors.length - 1]?.download).toBeTruthy()

    vi.advanceTimersByTime(500)
    expect(revokeSpy).toHaveBeenCalledWith("blob:fake-url")

    createElementSpy.mockRestore()
    clickSpy.mockRestore()
  })

  it("only the clicked format enters the loading state", async () => {
    // Boxed in an object (rather than a bare `let`) to sidestep a TS control-flow
    // narrowing quirk where a `let` reassigned only inside a Promise executor
    // narrows to `never` at the later read site.
    const docxResolver: { fn: ((v: DownloadResult) => void) | null } = { fn: null }
    downloadImpl = (fmt: string) => {
      if (fmt === "docx") {
        return new Promise<DownloadResult>((resolve) => {
          docxResolver.fn = resolve
        })
      }
      return defaultDownloadImpl()
    }

    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    const docxButton = await screen.findByRole("button", { name: "DOCX" })
    fireEvent.click(docxButton)

    // Only DOCX enters loading; a single global "downloading" boolean would
    // fail this assertion by disabling every button.
    await waitFor(() => expect(screen.getByRole("button", { name: /Preparing…/ })).toBeInTheDocument())

    for (const label of ["HTML", "PDF", "CBOM (JSON)", "CBOM (XML)"]) {
      const button = screen.getByRole("button", { name: label })
      expect(button).toBeEnabled()
    }

    // Resolve the hung promise so the test does not leave an unhandled
    // pending state behind for later tests.
    docxResolver.fn?.({ ok: true, blob: async () => new Blob(["x"]) })
    await waitFor(() => expect(screen.queryByRole("button", { name: /Preparing…/ })).not.toBeInTheDocument())
  })

  it("a non-200 download never creates an object URL and surfaces the failure copy", async () => {
    downloadImpl = (fmt: string) => {
      if (fmt === "pdf") {
        return Promise.resolve({ ok: false, status: 500, json: async () => ({ detail: "boom" }) })
      }
      return defaultDownloadImpl()
    }

    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    const pdfButton = await screen.findByRole("button", { name: "PDF" })
    fireEvent.click(pdfButton)

    await screen.findByText(/Download failed:/)

    // This is the executable form of the D-07 trap: a JSON error body must
    // never be treated as a downloadable blob.
    expect(createSpy).not.toHaveBeenCalled()
    expect(screen.getByText(/Download failed:/).textContent).toContain("boom")
  })

  it("falls back to the generic failure copy when the error body cannot be parsed", async () => {
    downloadImpl = (fmt: string) => {
      if (fmt === "pdf") {
        return Promise.resolve({
          ok: false,
          status: 502,
          json: async () => {
            throw new Error("not json")
          },
        })
      }
      return defaultDownloadImpl()
    }

    const { ExecutivePage } = await import("@/pages/executive")
    render(<ExecutivePage />)

    const pdfButton = await screen.findByRole("button", { name: "PDF" })
    fireEvent.click(pdfButton)

    await screen.findByText("Could not reach the report file. Try again.")
    expect(createSpy).not.toHaveBeenCalled()
  })

  it("concurrent downloads each revoke their own blob URL on unmount", async () => {
    let counter = 0
    createSpy.mockImplementation(() => `blob:fake-${counter++}`)

    const { ExecutivePage } = await import("@/pages/executive")
    const { unmount } = render(<ExecutivePage />)

    const htmlButton = await screen.findByRole("button", { name: "HTML" })
    const pdfButton = await screen.findByRole("button", { name: "PDF" })

    fireEvent.click(htmlButton)
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(1))

    fireEvent.click(pdfButton)
    await waitFor(() => expect(createSpy).toHaveBeenCalledTimes(2))

    // The existing single-ref-pair pattern in executive.tsx cannot satisfy
    // this leg — it only tracks one blob URL / timer pair at a time. This is
    // the leg that forces plan 04 to generalize that discipline to a
    // per-format map.
    unmount()

    expect(revokeSpy).toHaveBeenCalledWith("blob:fake-0")
    expect(revokeSpy).toHaveBeenCalledWith("blob:fake-1")
  })
})
