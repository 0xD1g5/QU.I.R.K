// Phase 202-06 / STORY-01, STORY-02 — integration coverage for the findings
// page's Storyline trigger column, the extended Sheet, and the F1-F9 focus
// contract (202-UI-SPEC.md). `useFindingStoryline` and `useScanData` are
// mocked so this file tests composition and focus only — 202-02 and 202-04
// own the hook and component behaviours respectively.
//
// Real keyboard/pointer events (`userEvent`) are used throughout rather than
// calling handlers directly: a handler-level test would pass even if the
// actual focus contract (Radix's FocusScope + our pre-open focus() call)
// were broken, and 202-07's Puppeteer capture would then be the first thing
// to notice, after the a11y baseline had already been taken.
import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { FindingItem, FindingStoryline } from "@/types/api"

const mockRetry = vi.fn()

let storylineReturn: {
  data: FindingStoryline | null
  loading: boolean
  error: string | null
  retry: () => void
} = { data: null, loading: false, error: null, retry: mockRetry }

vi.mock("@/hooks/useFindingStoryline", () => ({
  useFindingStoryline: () => storylineReturn,
}))

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: false,
  error: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

function makeFinding(overrides: Partial<FindingItem> = {}): FindingItem {
  return {
    id: 1,
    host: "web01.example.com",
    port: 443,
    severity: "HIGH",
    title: "TLS certificate uses undersized RSA key",
    protocol: "TLS",
    ...overrides,
  }
}

const FINDING_A = makeFinding({ id: 1, title: "TLS certificate uses undersized RSA key" })
const FINDING_B = makeFinding({ id: 2, host: "web02.example.com", title: "Plaintext HTTP exposed" })
const FINDING_NO_ID = makeFinding({
  id: null,
  host: "kdc.example.com",
  port: 88,
  protocol: "KERBEROS",
  title: "Kerberos ticket uses RC4 encryption",
})

function makeFixture(findings: FindingItem[]) {
  return { findings }
}

const FULL_STORYLINE: FindingStoryline = {
  finding_id: 1,
  narrative: "RSA-2048 keys are vulnerable to Shor's algorithm on a sufficiently large quantum computer.",
  quantum_impact: null,
  remediation_guidance: null,
  theme_slug: "undersized-rsa-keys",
  theme_title: "Replace undersized RSA keys",
  theme_score_lift: 4,
  theme_finding_count: 8,
  theme_closed_count: 2,
  finding_position: 1,
}

async function renderFindingsPage() {
  const { FindingsPage } = await import("@/pages/findings")
  return render(<FindingsPage />)
}

function triggerLabel(finding: FindingItem) {
  return `Open storyline for ${finding.title} at ${finding.host}:${finding.port}`
}

function disabledTriggerLabel(finding: FindingItem) {
  return `Storyline unavailable for ${finding.title} at ${finding.host}:${finding.port}`
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  storylineReturn = { data: null, loading: false, error: null, retry: mockRetry }
})

describe("FindingsPage — Storyline trigger column (F1)", () => {
  it("renders a Storyline column header and one enabled trigger per finding, reachable in the tab order", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A, FINDING_B]), loading: false, error: null }
    await renderFindingsPage()

    expect(screen.getByRole("columnheader", { name: "Storyline" })).toBeInTheDocument()
    const triggerA = screen.getByRole("button", { name: triggerLabel(FINDING_A) })
    const triggerB = screen.getByRole("button", { name: triggerLabel(FINDING_B) })
    expect(triggerA).toHaveAttribute("aria-haspopup", "dialog")
    expect(triggerB).toHaveAttribute("aria-haspopup", "dialog")
    // Reachable by keyboard: not disabled, and a real <button> (native tab order).
    expect(triggerA.tagName).toBe("BUTTON")
    expect(triggerA).not.toBeDisabled()
  })

  it("A6/S7: a finding with id: null renders a disabled trigger with the exact title string, and activating it never opens the drawer", async () => {
    scanDataReturn = { data: makeFixture([FINDING_NO_ID]), loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    const disabledTrigger = screen.getByRole("button", { name: disabledTriggerLabel(FINDING_NO_ID) })
    expect(disabledTrigger).toBeDisabled()
    expect(disabledTrigger).toHaveAttribute(
      "title",
      "Storyline unavailable — this finding has no stable identifier in this scan.",
    )

    await user.click(disabledTrigger)
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })
})

describe("FindingsPage — opening the drawer (F2, keyboard activation)", () => {
  it("activating a trigger by keyboard (Enter) opens the drawer and the SheetTitle names that finding", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A, FINDING_B]), loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    const trigger = screen.getByRole("button", { name: triggerLabel(FINDING_A) })
    trigger.focus()
    await user.keyboard("{Enter}")

    const dialog = screen.getByRole("dialog")
    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByRole("heading", { name: FINDING_A.title })).toBeInTheDocument()
  })

  it("F2: clicking the row still opens the drawer", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A]), loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    // Click a cell that is not the trigger button itself (the title cell).
    await user.click(screen.getByText(FINDING_A.title))

    expect(screen.getByRole("dialog")).toBeInTheDocument()
  })
})

describe("FindingsPage — focus contract F3-F7", () => {
  it("F3: after open, activeElement is inside SheetContent with accessible name Close", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A]), loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    await user.click(screen.getByRole("button", { name: triggerLabel(FINDING_A) }))

    const dialog = screen.getByRole("dialog")
    expect(dialog.contains(document.activeElement)).toBe(true)
    expect(document.activeElement).toHaveAccessibleName("Close")
  })

  it("F4: no focus reaches the findings table/filters/pagination while the drawer is open", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A, FINDING_B]), loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    await user.click(screen.getByRole("button", { name: triggerLabel(FINDING_A) }))
    const dialog = screen.getByRole("dialog")
    expect(dialog.contains(document.activeElement)).toBe(true)

    // Tab repeatedly — more than the number of tabbable elements inside the
    // drawer — and assert focus never leaves SheetContent.
    for (let i = 0; i < 10; i++) {
      await user.tab()
      expect(dialog.contains(document.activeElement)).toBe(true)
    }
  })

  it("F5 + F6 (Escape): SheetContent unmounts and focus returns to the exact triggering button", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A, FINDING_B]), loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    const trigger = screen.getByRole("button", { name: triggerLabel(FINDING_A) })
    await user.click(trigger)
    expect(screen.getByRole("dialog")).toBeInTheDocument()

    await user.keyboard("{Escape}")

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    expect(document.activeElement?.getAttribute("aria-label")).toBe(triggerLabel(FINDING_A))
  })

  it("F6 via the Close button: focus returns to the exact triggering button", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A, FINDING_B]), loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    const trigger = screen.getByRole("button", { name: triggerLabel(FINDING_B) })
    await user.click(trigger)
    expect(screen.getByRole("dialog")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Close" }))

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    expect(document.activeElement?.getAttribute("aria-label")).toBe(triggerLabel(FINDING_B))
  })

  it("F6 via an overlay click: focus returns to the exact triggering button", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A, FINDING_B]), loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    const trigger = screen.getByRole("button", { name: triggerLabel(FINDING_A) })
    await user.click(trigger)
    expect(screen.getByRole("dialog")).toBeInTheDocument()

    // Radix's overlay sits in the same portal as the dialog; find it as the
    // fixed inset-0 sibling rendered before SheetContent.
    const overlay = document.querySelector(".fixed.inset-0.z-50") as HTMLElement
    expect(overlay).toBeTruthy()
    await user.click(overlay)

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    expect(document.activeElement?.getAttribute("aria-label")).toBe(triggerLabel(FINDING_A))
  })

  it("F6 after a MOUSE-initiated open (clicking the row, not the button) holds", async () => {
    // This is the path Radix's FocusScope would otherwise restore to <body>,
    // since a plain row click focuses nothing by default.
    scanDataReturn = { data: makeFixture([FINDING_A]), loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    await user.click(screen.getByText(FINDING_A.host))
    expect(screen.getByRole("dialog")).toBeInTheDocument()

    await user.keyboard("{Escape}")

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    expect(document.activeElement?.getAttribute("aria-label")).toBe(triggerLabel(FINDING_A))
  })
})

describe("FindingsPage — cross-finding leakage and independent narrative/attribution (S6)", () => {
  it("never shows finding A's narrative while the SheetTitle names finding B", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A, FINDING_B]), loading: false, error: null }
    const user = userEvent.setup()

    storylineReturn = {
      data: { ...FULL_STORYLINE, finding_id: 1, narrative: "Finding A's narrative text." },
      loading: false,
      error: null,
      retry: mockRetry,
    }
    await renderFindingsPage()

    await user.click(screen.getByRole("button", { name: triggerLabel(FINDING_A) }))
    expect(within(screen.getByRole("dialog")).getByRole("heading", { name: FINDING_A.title })).toBeInTheDocument()
    expect(screen.getByText("Finding A's narrative text.")).toBeInTheDocument()

    // Close mid-fetch (simulated by leaving loading true / data null for B).
    storylineReturn = { data: null, loading: true, error: null, retry: mockRetry }
    await user.keyboard("{Escape}")
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()

    // Open finding B — the mocked hook now reflects B's own storyline, and
    // A's narrative text must not be present anywhere in the document.
    storylineReturn = {
      data: { ...FULL_STORYLINE, finding_id: 2, narrative: "Finding B's narrative text." },
      loading: false,
      error: null,
      retry: mockRetry,
    }
    await user.click(screen.getByRole("button", { name: triggerLabel(FINDING_B) }))

    expect(within(screen.getByRole("dialog")).getByRole("heading", { name: FINDING_B.title })).toBeInTheDocument()
    expect(screen.getByText("Finding B's narrative text.")).toBeInTheDocument()
    expect(screen.queryByText("Finding A's narrative text.")).not.toBeInTheDocument()
  })

  it("S6: a null narrative does not suppress the attribution block in the real composed drawer", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A]), loading: false, error: null }
    const user = userEvent.setup()
    storylineReturn = {
      data: { ...FULL_STORYLINE, narrative: null },
      loading: false,
      error: null,
      retry: mockRetry,
    }
    await renderFindingsPage()

    await user.click(screen.getByRole("button", { name: triggerLabel(FINDING_A) }))

    expect(
      screen.getByText(
        "No catalog narrative exists for this finding type yet — the Description and Remediation fields above are the available guidance.",
      ),
    ).toBeInTheDocument()
    expect(screen.getByText("Score-lift attribution")).toBeInTheDocument()
    expect(screen.getByText("Replace undersized RSA keys")).toBeInTheDocument()
    expect(screen.getByText(/\+4/)).toBeInTheDocument()
  })
})

describe("FindingsPage — S8 error state through the real drawer", () => {
  it("renders the error string and Retry storyline, with no absence string", async () => {
    scanDataReturn = { data: makeFixture([FINDING_A]), loading: false, error: null }
    const user = userEvent.setup()
    storylineReturn = {
      data: null,
      loading: false,
      error: "Could not load the storyline for this finding.",
      retry: mockRetry,
    }
    await renderFindingsPage()

    await user.click(screen.getByRole("button", { name: triggerLabel(FINDING_A) }))

    expect(screen.getByText("Could not load the storyline for this finding.")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Retry storyline" })).toBeInTheDocument()
    expect(
      screen.queryByText(
        "No catalog narrative exists for this finding type yet — the Description and Remediation fields above are the available guidance.",
      ),
    ).not.toBeInTheDocument()
  })
})

describe("FindingsPage — no console output (mirrors 202-07's a11y console gate)", () => {
  it("produces no console.warn / console.error while opening and closing the drawer", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {})
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {})

    scanDataReturn = { data: makeFixture([FINDING_A]), loading: false, error: null }
    const user = userEvent.setup()
    storylineReturn = { data: FULL_STORYLINE, loading: false, error: null, retry: mockRetry }
    await renderFindingsPage()

    await user.click(screen.getByRole("button", { name: triggerLabel(FINDING_A) }))
    await user.keyboard("{Escape}")

    expect(warnSpy).not.toHaveBeenCalled()
    expect(errorSpy).not.toHaveBeenCalled()

    warnSpy.mockRestore()
    errorSpy.mockRestore()
  })
})
