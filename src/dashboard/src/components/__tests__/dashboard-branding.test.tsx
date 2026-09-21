// Phase 206 Plan 10 (COV-04) — UAT-7-31: Dashboard Page Title and Branding.
//
// Pass Criteria under test (docs/UAT-SERIES.md UAT-7-31):
//   - Sidebar displays bold monospace electric-blue QU.I.R.K. wordmark
//       -> asserted by a REAL `Sidebar` render (render assertion).
//   - Browser tab title shows a branded title
//   - Favicon shows an electric-blue "Q" (not the browser default)
//       -> asserted against `src/dashboard/index.html` (static-document
//          assertion — see the treatment note below).
//
// TAB-TITLE / FAVICON TREATMENT, stated explicitly rather than left implied:
// the app never sets `document.title` at runtime (`grep -rn "document.title"
// src/dashboard/src/` returns nothing), and the favicon is three static
// `<link rel="icon">` tags. Both facts live in `index.html`, which Vite copies
// verbatim into the build; they are NOT React render output, so there is no
// render assertion that could reach them. This file therefore asserts them
// against `index.html` itself.
//
// This is NOT the banned source-text-regex substitution. That ban's own stated
// rationale (206-CONTEXT.md, Red-Proof Discipline) is that grepping source
// "does not cover a *render* case" — it turns on whether the case's claim is a
// render behaviour. A `<title>` element and a `<link rel="icon">` in a static
// HTML document are not render behaviours; the static document IS the artifact
// the Pass Criterion describes. This mirrors D-A1's carve-out reasoning for
// UAT-7-21 and, like it, is justified per-claim, not a general loosening: the
// wordmark half of this same case IS a render behaviour and is asserted by
// rendering, not by reading a file.
//
// Uncovered Pass Criteria bullet, named explicitly per CONTEXT's partial-
// coverage rule: "No JS console errors on page load" is UAT-7-32's subject and
// is structurally browser-only (Phase 207); it is not asserted here.
import { describe, it, expect, vi } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Sidebar } from "@/components/sidebar"

vi.mock("@/context/auth-context", () => ({
  useAuth: () => ({ status: "authenticated", setToken: () => {}, logout: () => {} }),
}))

vi.mock("@/context/vertical-context", () => ({
  useVertical: () => ({
    id: "general",
    label: "General",
    Icon: () => null,
    accentColor: "",
    navItem: null,
    PageComponent: null,
  }),
}))

vi.mock("@/hooks/useScanList", () => ({
  useScanList: () => ({ sessions: [], loading: false, error: null }),
}))

vi.mock("@/hooks/useSelectedScan", () => ({
  useSelectedScan: () => ({ selectedScanId: null, setSelectedScanId: () => {} }),
}))

const INDEX_HTML = readFileSync(
  path.resolve(__dirname, "../../../index.html"),
  "utf-8",
)

describe("Dashboard branding — UAT-7-31", () => {
  it("renders the QUIRK wordmark in the sidebar and the configured document title", () => {
    render(
      <TooltipProvider>
        <MemoryRouter initialEntries={["/"]}>
          <Sidebar />
        </MemoryRouter>
      </TooltipProvider>,
    )

    // Wordmark — render assertion against the real Sidebar.
    const wordmark = screen.getByText("QU.I.R.K.")
    expect(wordmark).toBeInTheDocument()
    // "bold monospace electric-blue": weight and typeface are literal classes;
    // the colour is the `accent` design token (the electric-blue defined in
    // index.css), asserted as the token rather than as a hex literal because
    // hardcoded hex on components is what UAT-7-21 forbids.
    expect(wordmark.className).toContain("font-black")
    expect(wordmark.className).toContain("font-mono")
    expect(wordmark.className).toContain("text-accent")

    // Collapsed-sidebar monogram ships alongside the full wordmark.
    expect(screen.getByText("Q")).toBeInTheDocument()

    // Tab title + favicon — static-document assertions (see the treatment note
    // at the head of this file).
    expect(INDEX_HTML).toContain(
      "<title>QU.I.R.K. — Quantum Readiness Dashboard</title>",
    )
    expect(INDEX_HTML).toMatch(/<link rel="icon"[^>]*href="\/favicon\.svg"/)
  })
})
