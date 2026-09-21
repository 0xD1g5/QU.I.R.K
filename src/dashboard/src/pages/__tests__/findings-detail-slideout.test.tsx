// Phase 206 Plan 04 (COV-04) — UAT-7-09: Findings Page detail slide-out.
//
// `useScanData` and `useFindingStoryline` are mocked; the real `FindingsPage`
// is rendered and a real row click drives the Sheet open.
//
// Two findings with entirely disjoint field values are seeded and the SECOND
// row is clicked: asserting only that the slide-out opened would pass even if
// it rendered the wrong finding, so every expected value is read from
// `FIXTURE.findings[1]` and every one of the first finding's distinctive
// values is asserted ABSENT from the slide-out.
//
// Genuinely new coverage: the nearest neighbours
// (`findings-storyline.test.tsx`, `finding-storyline-sections.test.tsx`) own
// the Storyline narrative composition and the F1-F9 focus contract. Their
// closest node, "F2: clicking the row still opens the drawer", asserts only
// that a dialog appears and its heading names the ONE seeded finding — it
// does not assert the finding's own field values, and cannot distinguish a
// right-finding render from a wrong-finding one.
import { describe, it, expect, afterEach, vi } from "vitest"
import { render, screen, cleanup, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { FindingItem } from "@/types/api"

let scanDataReturn: { data: unknown; loading: boolean; error: string | null } = {
  data: null,
  loading: false,
  error: null,
}

vi.mock("@/hooks/useScanData", () => ({
  useScanData: () => scanDataReturn,
}))

// The storyline fetch is not this case's subject; a null-data, non-loading,
// non-error return keeps StorylineSections quiet without faking the fields
// UAT-7-09 actually names, all of which come from the finding itself.
vi.mock("@/hooks/useFindingStoryline", () => ({
  useFindingStoryline: () => ({ data: null, loading: false, error: null, retry: () => {} }),
}))

// Every field differs between the two findings, including severity, protocol,
// host, port and quantum risk, so a wrong-finding render is detectable on any
// single assertion rather than only on the title.
const FIXTURE: { findings: FindingItem[] } = {
  findings: [
    {
      id: 1,
      host: "alpha-host.example.com",
      port: 8443,
      severity: "LOW",
      title: "Alpha finding about session resumption",
      protocol: "SSH",
      description: "Alpha description naming the first fixture finding only.",
      remediation: "Alpha remediation step.",
      quantum_risk: "Safe",
    },
    {
      id: 2,
      host: "bravo-host.example.com",
      port: 9443,
      severity: "CRITICAL",
      title: "Bravo finding about an undersized RSA key",
      protocol: "TLS",
      description: "Bravo description naming the second fixture finding only.",
      remediation: "Bravo remediation step.",
      quantum_risk: "Vulnerable",
    },
  ],
}

const ALPHA = FIXTURE.findings[0]
const BRAVO = FIXTURE.findings[1]

async function renderFindingsPage() {
  const { FindingsPage } = await import("@/pages/findings")
  return render(<FindingsPage />)
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("FindingsPage — detail slide-out (UAT-7-09)", () => {
  it("opens the finding detail slide-out with the selected finding's fields when its row is clicked", async () => {
    scanDataReturn = { data: FIXTURE, loading: false, error: null }
    const user = userEvent.setup()
    await renderFindingsPage()

    // No slide-out before the click.
    expect(screen.queryByRole("dialog")).toBeNull()

    // Click the SECOND fixture row, via a non-button cell (its Title cell) so
    // this is the row-click path the case describes, not the Storyline button.
    // The table's default sort is by severity string, so the row is located by
    // its own title rather than by DOM position.
    await user.click(screen.getByText(BRAVO.title))

    const dialog = await screen.findByRole("dialog")
    const shown = dialog.textContent ?? ""

    // Every field UAT-7-09's Pass Criteria names, read from FIXTURE.
    expect(within(dialog).getByRole("heading", { name: BRAVO.title })).toBeInTheDocument()
    expect(shown).toContain(BRAVO.description!)            // full description visible
    expect(shown).toContain(BRAVO.host)                    // host
    expect(shown).toContain(`${BRAVO.host}:${BRAVO.port}`) // port, rendered host:port
    expect(shown).toContain(BRAVO.protocol!)               // protocol
    expect(shown).toContain(BRAVO.severity)                // severity
    expect(shown).toContain(BRAVO.quantum_risk!)           // quantum risk assessment
    expect(shown).toContain(BRAVO.remediation!)

    // ...and none of the FIRST finding's values, which is what makes the
    // assertions above load-bearing rather than merely "a panel opened".
    expect(shown).not.toContain(ALPHA.title)
    expect(shown).not.toContain(ALPHA.host)
    expect(shown).not.toContain(String(ALPHA.port))
    expect(shown).not.toContain(ALPHA.protocol!)
    expect(shown).not.toContain(ALPHA.severity)
    expect(shown).not.toContain(ALPHA.description!)
    expect(shown).not.toContain(ALPHA.remediation!)
    expect(shown).not.toContain(ALPHA.quantum_risk!)
  })
})
