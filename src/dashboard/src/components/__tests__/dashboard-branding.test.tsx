// Phase 206 Plan 10 (COV-04), re-pointed by Phase 223 (BRAND-02/03/07) — UAT-7-31: Dashboard Page Title and Branding.
//
// Pass Criteria under test (docs/UAT-SERIES.md UAT-7-31):
//   - Sidebar displays the QU.I.R.K. brand logo (wide) and favicon-tier glyph (narrow)
//       -> asserted by a REAL `Sidebar` render (render assertion); the login card
//          is rendered the same way in a second node.
//   - Browser tab title shows a branded title
//   - Favicon shows the brand favicon, the lens glyph on an Ink tile
//       -> asserted against `src/dashboard/index.html` and `public/` (static-document
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
// logo half of this same case IS a render behaviour and is asserted by
// rendering, not by reading a file.
//
// Byte-equality of favicon.png / favicon.ico to a FRESH render is owned by
// tests/test_brand_assets_freshness.py because vitest has no renderer; this
// file checks only the magic bytes and the SVG source copy.
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
import { LoginPage } from "@/pages/login"

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

const REPO = path.resolve(__dirname, "../../../../..")
const PUBLIC = path.resolve(__dirname, "../../../public")

describe("Dashboard branding — UAT-7-31", () => {
  it("renders the brand logo and glyph in the sidebar and links the brand favicon", () => {
    render(
      <TooltipProvider>
        <MemoryRouter initialEntries={["/"]}>
          <Sidebar />
        </MemoryRouter>
      </TooltipProvider>,
    )

    // jsdom ignores the Tailwind hidden / lg:hidden classes, so both variants resolve.
    const imgs = screen.getAllByRole("img", { name: "QU.I.R.K." })
    expect(imgs).toHaveLength(2)
    expect(
      imgs.map((el) => el.getAttribute("data-brand-variant")).sort(),
    ).toEqual(["glyph", "logo"])
    for (const svg of imgs) {
      expect(svg.querySelectorAll('[fill="#7FE001"]')).toHaveLength(1)
      expect(svg.innerHTML).not.toMatch(/#0D0124/i)
      expect(
        svg.querySelectorAll('[stroke="currentColor"],[fill="currentColor"]').length,
      ).toBeGreaterThan(0)
      expect(svg.querySelector("title")).toBeNull()
      const cls = svg.getAttribute("class") ?? ""
      expect(cls).toContain("text-foreground")
      expect(cls).not.toContain("text-accent")
    }
    expect(screen.queryByText("QU.I.R.K.")).toBeNull()
    expect(screen.queryByText("Q")).toBeNull()

    // Tab title + favicon — static-document assertions (see the treatment note
    // at the head of this file).
    expect(INDEX_HTML).toContain(
      "<title>QU.I.R.K. — Quantum Readiness Dashboard</title>",
    )
    const hrefs = [
      ...INDEX_HTML.matchAll(/<link rel="[^"]*icon"[^>]*href="\/([^"]+)"/g),
    ].map((m) => m[1])
    expect(hrefs).toEqual(["favicon.svg", "favicon.png", "favicon.ico"])

    expect(
      readFileSync(path.join(PUBLIC, "favicon.svg")).equals(
        readFileSync(path.join(REPO, "docs/brand/quirk-favicon-dark.svg")),
      ),
    ).toBe(true)
    const png = readFileSync(path.join(PUBLIC, "favicon.png"))
    expect([...png.subarray(0, 4)]).toEqual([0x89, 0x50, 0x4e, 0x47])
    const ico = readFileSync(path.join(PUBLIC, "favicon.ico"))
    expect([...ico.subarray(0, 4)]).toEqual([0, 0, 1, 0])
    expect(ico.readUInt16LE(4)).toBe(3)
  })

  it("renders the brand logo on the login card without a retyped wordmark", () => {
    render(<LoginPage />)
    const imgs = screen.getAllByRole("img", { name: "QU.I.R.K." })
    expect(imgs).toHaveLength(1)
    expect(imgs[0].getAttribute("data-brand-variant")).toBe("logo")
    expect(screen.queryByText("QU.I.R.K.")).toBeNull()
  })
})
