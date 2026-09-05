// Phase 184.3-06 (SCORE-03 SC-4) — the sibling-drift closure.
//
// `ScanSelector.tsx` was byte-for-byte the same `new Date(...).toLocale*` defect as
// ScanDateBadge.tsx (T-184.3-20/SC-4), but had ZERO test coverage of any kind before this file.
// Fixing ScanDateBadge while leaving ScanSelector untested/unfixed would have been exactly the
// enumeration-drift failure this milestone exists to remove — this file is the concrete closure
// of that gap: net-new coverage, TZ-pinned, asserting rendered DOM text rather than a directly
// imported formatter function (proving the COMPONENT renders correctly, not just the helper).
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ScanSelector } from "../ScanSelector"

const mockUseScanList = vi.fn()
const mockUseSelectedScan = vi.fn()

vi.mock("@/hooks/useScanList", () => ({
  useScanList: () => mockUseScanList(),
}))

vi.mock("@/hooks/useSelectedScan", () => ({
  useSelectedScan: () => mockUseSelectedScan(),
}))

const TWO_SESSIONS = [
  { scan_id: "abc", scanned_at: "2026-09-04T15:12:58+00:00", total_endpoints: 5 },
  { scan_id: "def", scanned_at: "2026-08-01T12:00:00+00:00", total_endpoints: 3 },
]

function renderSelector() {
  return render(<ScanSelector />)
}

describe("ScanSelector — SC-4 sibling coverage", () => {
  beforeEach(() => {
    vi.stubEnv("TZ", "America/New_York")
    mockUseSelectedScan.mockReturnValue({ selectedScanId: null, setSelectedScanId: vi.fn() })

    // jsdom implements neither the Pointer Events capture API nor scrollIntoView, both of
    // which Radix UI's Select primitive calls when opening the listbox. This is a standard,
    // scoped-to-this-file jsdom workaround (not a Radix/jsdom bug this plan needs to fix) —
    // left local rather than added to the shared test-setup.ts since ScanSelector is the only
    // component in this plan's scope that opens a Radix popover.
    Element.prototype.hasPointerCapture = vi.fn()
    Element.prototype.setPointerCapture = vi.fn()
    Element.prototype.releasePointerCapture = vi.fn()
    Element.prototype.scrollIntoView = vi.fn()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("returns null while loading", () => {
    mockUseScanList.mockReturnValue({ sessions: TWO_SESSIONS, loading: true, error: null })
    const { container } = renderSelector()
    expect(container).toBeEmptyDOMElement()
  })

  it("returns null when only one session exists", () => {
    mockUseScanList.mockReturnValue({ sessions: [TWO_SESSIONS[0]], loading: false, error: null })
    const { container } = renderSelector()
    expect(container).toBeEmptyDOMElement()
  })

  it("renders option labels with the correct wall-clock time, zone label, and endpoint suffix when opened", async () => {
    // Two-or-more sessions are required to clear ScanSelector's `sessions.length <= 1` early
    // return — with fewer than two seeded, every assertion below would pass vacuously against
    // an empty DOM (T-184.3-22).
    mockUseScanList.mockReturnValue({ sessions: TWO_SESSIONS, loading: false, error: null })
    renderSelector()

    // Route taken: drive the real open interaction with @testing-library/user-event (already a
    // devDependency — verified via package.json before use, not installed) rather than asserting
    // against formatScanLabel in isolation. Radix Select only registers/renders its
    // SelectItem children into the accessible tree once the listbox is opened, so opening it is
    // required to prove the COMPONENT — not just the helper function — renders the fixed text.
    const user = userEvent.setup()
    const trigger = screen.getByRole("combobox", { name: "Select scan" })
    await user.click(trigger)

    const options = await screen.findAllByRole("option")
    const optionTexts = options.map((o) => o.textContent ?? "")
    const targetOption = optionTexts.find((t) => t.includes("11:12"))

    expect(targetOption).toBeDefined()
    expect(targetOption).toContain("11:12")
    expect(targetOption).toMatch(/AM/)
    expect(targetOption).toContain("EDT")
    expect(targetOption).not.toContain("3:12")
    expect(targetOption).toContain(" · ")
    expect(targetOption).toContain(" ep")
  })
})
