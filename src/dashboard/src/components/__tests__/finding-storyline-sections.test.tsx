/**
 * Phase 202-04 / STORY-01, STORY-02 (D-01, D-07) — StorylineSections.
 *
 * Covers all eight 202-UI-SPEC.md State Matrix rows (S1-S6, S8 — S7 never
 * mounts this component, see the explicit skip below), Invariants 1-3, and
 * the 4.27 -> +4.3 formatting regression (201-UI-E5).
 */
import { describe, it, expect, vi } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import { afterEach } from "vitest"
import { StorylineSections } from "../FindingStorylineSections"
import type { FindingStoryline } from "@/types/api"

afterEach(() => cleanup())

const baseStoryline: FindingStoryline = {
  finding_id: 1,
  narrative:
    "Uses RSA key exchange, vulnerable to a sufficiently large quantum computer via Shor's algorithm.",
  quantum_impact: null,
  remediation_guidance: null,
  theme_slug: "plaintext-http-exposure",
  theme_title: "Disable legacy TLS versions",
  theme_score_lift: 4,
  theme_finding_count: 8,
  theme_closed_count: 6,
  finding_position: 1,
}

const A1_TEXT =
  "Not mapped to a remediation theme — no score-lift attribution exists for this finding."
const A2_TEXT = "Score lift could not be modelled for this theme in this scan."
const A3_TEXT =
  "The theme's constituent findings could not be counted in this scan, so the lift cannot be stated with its condition."
const A5_TEXT =
  "No catalog narrative exists for this finding type yet — the Description and Remediation fields above are the available guidance."
const DISCLAIMER_TEXT =
  "This is the theme's total lift, not this finding's individual contribution. Resolving this finding alone does not yield the full amount."
const ERROR_TEXT = "Could not load the storyline for this finding."

// Scopes queries to the attribution panel element specifically, and asserts
// it was actually found before returning it — per the Phase-185 D-14
// vacuous-query failure mode named in the plan.
function getAttributionPanel(): HTMLElement {
  const label = screen.getByText("Score-lift attribution")
  const panel = label.closest("div")
  expect(panel).not.toBeNull()
  return panel as HTMLElement
}

const BLOCK_TAGS = new Set([
  "DIV",
  "P",
  "SECTION",
  "ARTICLE",
  "UL",
  "OL",
  "LI",
  "TABLE",
  "TR",
  "TD",
  "HEADER",
  "FOOTER",
  "MAIN",
  "ASIDE",
  "NAV",
  "FORM",
  "FIELDSET",
  "BLOCKQUOTE",
  "PRE",
  "H1",
  "H2",
  "H3",
  "H4",
  "H5",
  "H6",
])

function nearestBlockAncestor(el: Element): Element | null {
  let node: Element | null = el.parentElement
  while (node) {
    if (BLOCK_TAGS.has(node.tagName)) return node
    node = node.parentElement
  }
  return null
}

function renderStoryline(overrides: Partial<FindingStoryline> = {}, onRetry = vi.fn()) {
  return render(
    <StorylineSections
      data={{ ...baseStoryline, ...overrides }}
      loading={false}
      error={null}
      onRetry={onRetry}
    />,
  )
}

describe("StorylineSections — State Matrix S1-S6", () => {
  it("S1 fully populated: all six attribution elements render in order, narrative renders", () => {
    renderStoryline()
    const panel = getAttributionPanel()
    expect(panel.textContent).toMatch(/Remediation theme: Disable legacy TLS versions/)
    expect(panel.textContent).toMatch(/\+4 pts when all 8 findings in this theme are resolved/)
    expect(panel.textContent).toMatch(/This finding is 1 of 8 in the theme\./)
    expect(panel.textContent).toMatch(/6 of 8 findings in this theme are verified closed\./)
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeInTheDocument()
    expect(
      screen.getByText(
        "Uses RSA key exchange, vulnerable to a sufficiently large quantum computer via Shor's algorithm.",
      ),
    ).toBeInTheDocument()

    // Order: theme line -> lift -> position -> closure -> disclaimer.
    const themeIdx = panel.textContent!.indexOf("Remediation theme:")
    const liftIdx = panel.textContent!.indexOf("pts when all")
    const posIdx = panel.textContent!.indexOf("This finding is")
    const closureIdx = panel.textContent!.indexOf("verified closed")
    const disclaimerIdx = panel.textContent!.indexOf("total lift")
    expect(themeIdx).toBeLessThan(liftIdx)
    expect(liftIdx).toBeLessThan(posIdx)
    expect(posIdx).toBeLessThan(closureIdx)
    expect(closureIdx).toBeLessThan(disclaimerIdx)
  })

  it("S2 A1 theme unmapped: only the A1 sentence renders, nothing else", () => {
    renderStoryline({
      theme_slug: null,
      theme_title: null,
      theme_score_lift: null,
      theme_finding_count: null,
      theme_closed_count: null,
      finding_position: null,
    })
    const panel = getAttributionPanel()
    expect(screen.getByText(A1_TEXT)).toBeInTheDocument()
    expect(panel.textContent).not.toMatch(/Remediation theme:/)
    expect(panel.textContent).not.toMatch(/\+\d/)
    expect(panel.textContent).not.toMatch(/This finding is/)
    expect(panel.textContent).not.toMatch(/verified closed/)
    expect(screen.queryByText(DISCLAIMER_TEXT)).not.toBeInTheDocument()
  })

  it("S3 A2 lift null: theme line + A2 sentence + position + closure; no number, no disclaimer", () => {
    renderStoryline({ theme_score_lift: null })
    const panel = getAttributionPanel()
    expect(panel.textContent).toMatch(/Remediation theme: Disable legacy TLS versions/)
    expect(screen.getByText(A2_TEXT)).toBeInTheDocument()
    expect(panel.textContent).toMatch(/This finding is 1 of 8 in the theme\./)
    expect(panel.textContent).toMatch(/6 of 8 findings in this theme are verified closed\./)
    expect(panel.textContent).not.toMatch(/\+\d/)
    expect(screen.queryByText(DISCLAIMER_TEXT)).not.toBeInTheDocument()
  })

  it("S4 A3 counts null: theme line + A3 sentence only, distinct from A2", () => {
    renderStoryline({ theme_finding_count: null })
    const panel = getAttributionPanel()
    expect(panel.textContent).toMatch(/Remediation theme: Disable legacy TLS versions/)
    expect(screen.getByText(A3_TEXT)).toBeInTheDocument()
    expect(panel.textContent).not.toMatch(/\+\d/)
    expect(panel.textContent).not.toMatch(/This finding is/)
    expect(panel.textContent).not.toMatch(/verified closed/)
    expect(panel.textContent).not.toContain("of 0")
    expect(panel.textContent).not.toContain("of null")
    expect(panel.textContent).not.toEqual(expect.stringContaining(A2_TEXT))
  })

  it("S4 A3 counts === 0: same A3 branch, never '1 of 0' or '0 of 0'", () => {
    renderStoryline({ theme_finding_count: 0 })
    const panel = getAttributionPanel()
    expect(screen.getByText(A3_TEXT)).toBeInTheDocument()
    expect(panel.textContent).not.toContain("of 0")
    expect(panel.textContent).not.toMatch(/\d+ of \d+/)
  })

  it("UI-202-02: theme_finding_count and theme_score_lift both null renders A3 only, not A2 — pinned precedence", () => {
    renderStoryline({ theme_finding_count: null, theme_score_lift: null })
    const panel = getAttributionPanel()
    expect(panel.textContent).toMatch(/Remediation theme: Disable legacy TLS versions/)
    expect(screen.getByText(A3_TEXT)).toBeInTheDocument()
    expect(screen.queryByText(A2_TEXT)).not.toBeInTheDocument()
    expect(panel.textContent).not.toMatch(/\+\d/)
    expect(panel.textContent).not.toMatch(/This finding is/)
    expect(panel.textContent).not.toMatch(/verified closed/)
    expect(screen.queryByText(DISCLAIMER_TEXT)).not.toBeInTheDocument()
  })

  it("S5 A4 position null only: position omitted silently, lift/closure/disclaimer still render", () => {
    renderStoryline({ finding_position: null })
    const panel = getAttributionPanel()
    expect(panel.textContent).toMatch(/\+4 pts when all 8 findings in this theme are resolved/)
    expect(panel.textContent).not.toMatch(/This finding is/)
    expect(panel.textContent).toMatch(/6 of 8 findings in this theme are verified closed\./)
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeInTheDocument()
    // No replacement copy for the omitted position sentence.
    expect(panel.textContent).not.toMatch(/N\/A|Unknown/)
  })

  it("S6 A5 no narrative: A5 renders in the narrative section, attribution panel fully populated", () => {
    renderStoryline({ narrative: null })
    expect(screen.getByText(A5_TEXT)).toBeInTheDocument()
    const panel = getAttributionPanel()
    expect(panel.textContent).toMatch(/Remediation theme: Disable legacy TLS versions/)
    expect(panel.textContent).toMatch(/\+4 pts when all 8 findings in this theme are resolved/)
    expect(panel.textContent).toMatch(/This finding is 1 of 8 in the theme\./)
    expect(panel.textContent).toMatch(/6 of 8 findings in this theme are verified closed\./)
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeInTheDocument()
  })

  // S7 (A6 — no stable id) never mounts this component: the row's trigger
  // is disabled upstream and the drawer never opens. Covered in 202-06's
  // trigger tests instead, not here — this skip keeps the eight-row table
  // visibly complete rather than silently short.
  it.skip("S7 A6 no stable id — trigger disabled upstream, covered in 202-06's trigger tests", () => {})
})

describe("StorylineSections — Independence (position/closure/narrative)", () => {
  it("finding_position null with counts present keeps the closure sentence", () => {
    renderStoryline({ finding_position: null })
    const panel = getAttributionPanel()
    expect(panel.textContent).toMatch(/6 of 8 findings in this theme are verified closed\./)
  })

  it("theme_closed_count null with position present keeps the position sentence", () => {
    renderStoryline({ theme_closed_count: null })
    const panel = getAttributionPanel()
    expect(panel.textContent).toMatch(/This finding is 1 of 8 in the theme\./)
    expect(panel.textContent).not.toMatch(/verified closed/)
  })
})

describe("StorylineSections — Invariant 1 (single-node condition)", () => {
  it("the <p> matching /\\+\\d/ also matches /when all/, with no block element between the span and that <p>", () => {
    const { container } = renderStoryline()
    const paragraphs = Array.from(container.querySelectorAll("p"))
    const liftParagraph = paragraphs.find(
      (p) => /\+\d/.test(p.textContent ?? "") && /when all/.test(p.textContent ?? ""),
    )
    expect(liftParagraph).toBeTruthy()
    expect(liftParagraph!.tagName).toBe("P")

    const span = liftParagraph!.querySelector("span")
    expect(span).toBeTruthy()
    expect(span!.textContent).toMatch(/^\+4$/)

    const ancestor = nearestBlockAncestor(span!)
    expect(ancestor).toBe(liftParagraph)
  })
})

describe("StorylineSections — Invariant 2 (disclaimer co-presence, 8 states)", () => {
  it.each([
    ["S1 fully populated", {}, true],
    ["S2 A1 theme unmapped", { theme_slug: null }, false],
    ["S3 A2 lift null", { theme_score_lift: null }, false],
    ["S4 A3 counts null", { theme_finding_count: null }, false],
    ["S5 A4 position null only", { finding_position: null }, true],
    ["S6 A5 no narrative", { narrative: null }, true],
  ] as const)("%s: disclaimer present iff a lift number renders (expected=%s)", (_name, overrides, expected) => {
    renderStoryline(overrides as Partial<FindingStoryline>)
    if (expected) {
      expect(screen.getByText(DISCLAIMER_TEXT)).toBeInTheDocument()
    } else {
      expect(screen.queryByText(DISCLAIMER_TEXT)).not.toBeInTheDocument()
    }
  })

  it("S8 fetch error: no lift number, no disclaimer", () => {
    render(
      <StorylineSections data={null} loading={false} error={ERROR_TEXT} onRetry={vi.fn()} />,
    )
    expect(screen.queryByText(DISCLAIMER_TEXT)).not.toBeInTheDocument()
    expect(screen.queryByText(/\+\d/)).not.toBeInTheDocument()
  })

  // S7 never mounts this component — see the State Matrix skip above.
  it.skip("S7 A6 no stable id — not applicable, trigger disabled upstream (covered in 202-06)", () => {})
})

describe("StorylineSections — Invariant 3 (division trip-wire)", () => {
  it("lift 7 / count 2 renders 7 and 2, and NEITHER 3.5 NOR 3 appears anywhere in the panel", () => {
    renderStoryline({
      theme_score_lift: 7,
      theme_finding_count: 2,
      finding_position: null,
      theme_closed_count: null,
    })
    const panel = getAttributionPanel()
    expect(panel.textContent).toContain("7")
    expect(panel.textContent).toContain("2")
    expect(panel.textContent).not.toContain("3.5")
    expect(panel.textContent).not.toMatch(/\b3\b/)
  })
})

describe("StorylineSections — Number Formatting Contract (201-UI-E5 regression)", () => {
  it("theme_score_lift: 4.27 renders exactly '+4.3 pts when all 8 findings in this theme are resolved'", () => {
    renderStoryline({ theme_score_lift: 4.27, theme_finding_count: 8 })
    expect(
      screen.getByText((_content, node) => {
        return node?.textContent === "+4.3 pts when all 8 findings in this theme are resolved"
      }),
    ).toBeInTheDocument()
  })

  it("theme_score_lift: 4 renders '+4', not '+4.0'", () => {
    renderStoryline({ theme_score_lift: 4, theme_finding_count: 8 })
    const panel = getAttributionPanel()
    const span = Array.from(panel.querySelectorAll("span")).find((s) =>
      /^\+/.test(s.textContent ?? ""),
    )
    expect(span!.textContent).toBe("+4")
    expect(panel.textContent).not.toMatch(/\+4\.0/)
  })

  it("theme_score_lift: 0 renders '+0 pts ...' — a real zero, not absence", () => {
    renderStoryline({ theme_score_lift: 0, theme_finding_count: 8 })
    const panel = getAttributionPanel()
    expect(panel.textContent).toMatch(/\+0 pts when all 8 findings in this theme are resolved/)
  })
})

describe("StorylineSections — never render null as 0/dash/N/A", () => {
  it("theme_score_lift: null renders none of 0/+0/N/A/Unknown/standalone em-dash", () => {
    renderStoryline({ theme_score_lift: null })
    const panel = getAttributionPanel()
    expect(panel.textContent).not.toMatch(/\b0\b/)
    expect(panel.textContent).not.toContain("+0")
    expect(panel.textContent).not.toMatch(/N\/A|Unknown/)
    expect(panel.textContent).not.toContain("—")
  })
})

describe("StorylineSections — S8 fetch error", () => {
  it("renders the error string and Retry storyline button; no absence copy leaks through", () => {
    render(
      <StorylineSections data={null} loading={false} error={ERROR_TEXT} onRetry={vi.fn()} />,
    )
    expect(screen.getByText(ERROR_TEXT)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Retry storyline" })).toBeInTheDocument()
    expect(screen.queryByText(A1_TEXT)).not.toBeInTheDocument()
    expect(screen.queryByText(A2_TEXT)).not.toBeInTheDocument()
    expect(screen.queryByText(A3_TEXT)).not.toBeInTheDocument()
    expect(screen.queryByText(A5_TEXT)).not.toBeInTheDocument()
  })

  it("calls onRetry exactly once when the Retry storyline button is clicked", async () => {
    const onRetry = vi.fn()
    const { default: userEvent } = await import("@testing-library/user-event")
    render(<StorylineSections data={null} loading={false} error={ERROR_TEXT} onRetry={onRetry} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole("button", { name: "Retry storyline" }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it("disables the Retry storyline button with aria-busy=true while a retry is in flight", () => {
    render(<StorylineSections data={null} loading={true} error={ERROR_TEXT} onRetry={vi.fn()} />)
    const button = screen.getByRole("button", { name: "Retry storyline" })
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute("aria-busy", "true")
  })
})

describe("StorylineSections — loading state", () => {
  it("shows role=status, sr-only 'Loading storyline…', real SCORE-LIFT ATTRIBUTION label over skeleton, no numerals", () => {
    render(<StorylineSections data={null} loading={true} error={null} onRetry={vi.fn()} />)
    const status = screen.getByRole("status")
    expect(status).toBeInTheDocument()
    expect(screen.getByText("Loading storyline…")).toHaveClass("sr-only")
    expect(screen.getByText("Score-lift attribution")).toBeInTheDocument()
    expect(status.textContent).not.toMatch(/\d/)
  })
})
