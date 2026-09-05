// Phase 184.3-06 (SCORE-03 SC-2) — the reproduction site.
//
// Roadmap's measured reproduction: a scan that ran at 11:12:58 EDT was rendering as
// "Last scan: Sep 4, 2026 3:13 PM" — the ECMAScript local-parse rule treats an offset-less
// ISO string ("2026-09-04T15:12:58") as UTC, then toLocaleTimeString formats THAT UTC instant
// in the browser's local zone, silently adding back the UTC offset a second time.
//
// The previous version of this file asserted label FORMAT only
// (`textContent.includes("Last scan:")`) against a fixture that was ALREADY timezone-aware
// ("2026-08-02T14:56:00Z"), so the suite could never observe the skew — the "render tests
// assert presence, not appearance" failure this codebase has hit before. This file replaces
// that blind assertion with a TZ-pinned wall-clock proof.
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { ScanDateBadge } from "../ScanDateBadge"
import { TooltipProvider } from "@/components/ui/tooltip"

const mockUseScanList = vi.fn()

vi.mock("@/hooks/useScanList", () => ({
  useScanList: () => mockUseScanList(),
}))

function renderBadge() {
  return render(
    <TooltipProvider>
      <ScanDateBadge />
    </TooltipProvider>,
  )
}

describe("ScanDateBadge — TAIL-01 persistent scan-date badge", () => {
  beforeEach(() => {
    vi.stubEnv("TZ", "America/New_York")
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("renders nothing while loading (brief-flash prevention only)", () => {
    mockUseScanList.mockReturnValue({ sessions: [], loading: true, error: null })
    const { container } = renderBadge()
    expect(container).toBeEmptyDOMElement()
  })

  it("shows 'No scan yet' in a status region when there are zero sessions", () => {
    mockUseScanList.mockReturnValue({ sessions: [], loading: false, error: null })
    renderBadge()
    expect(screen.getByRole("status")).toBeInTheDocument()
    expect(screen.getAllByText("No scan yet").length).toBeGreaterThan(0)
  })

  it("renders the correct wall-clock time for an offset-bearing scanned_at (SC-2, D-10 fix)", () => {
    // Fixed API shape: an explicit +00:00 offset. 15:12:58 UTC == 11:12:58 AM EDT.
    mockUseScanList.mockReturnValue({
      sessions: [{ scan_id: "abc", scanned_at: "2026-09-04T15:12:58+00:00", total_endpoints: 5 }],
      loading: false,
      error: null,
    })
    renderBadge()
    expect(screen.getByRole("status")).toBeInTheDocument()
    const matches = screen.getAllByText((_, node) => {
      return !!node?.textContent?.includes("Last scan:")
    })
    expect(matches.length).toBeGreaterThan(0)
    const text = matches[0].textContent ?? ""
    expect(text).toContain("Last scan: ")
    expect(text).toContain("11:12")
    expect(text).toMatch(/AM/)
    expect(text).toContain("EDT")
    expect(text).not.toContain("3:12")
  })

  it("documents the pre-fix API shape: an offset-less scanned_at parses as UTC and renders 3:12 (historical bug reproduction)", () => {
    // This fixture is the OFFSET-LESS shape the API used to emit. Per the ECMAScript spec, a
    // date-time string with no offset/zone designator parses as UTC. Formatting that UTC
    // instant in America/New_York shifts it forward to 3:12 PM — this is the exact skew SC-2
    // exists to name. Fixing the API serialization boundary (plans 01-04) is what retires this
    // shape in production; this case exists so a future reader understands why the two
    // fixtures in this file differ, not because it is an inconsistency.
    mockUseScanList.mockReturnValue({
      sessions: [{ scan_id: "def", scanned_at: "2026-09-04T15:12:58", total_endpoints: 5 }],
      loading: false,
      error: null,
    })
    renderBadge()
    const matches = screen.getAllByText((_, node) => {
      return !!node?.textContent?.includes("Last scan:")
    })
    expect(matches.length).toBeGreaterThan(0)
    const text = matches[0].textContent ?? ""
    expect(text).toContain("3:12")
  })
})
