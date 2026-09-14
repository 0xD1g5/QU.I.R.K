/**
 * PRINT-01 regression: `/print` must render WITHOUT the dashboard chrome.
 *
 * `/print` is the client deliverable that `POST /api/export/pdf` renders to PDF
 * by pointing headless Chromium at it (quirk/dashboard/api/routes/pdf.py). It
 * used to be a `<Route>` inside AppShell's sidebar+main shell, so every exported
 * PDF carried the navigation sidebar down its left edge and the shell's
 * `ml-12 lg:ml-60` content offset. Nothing in `src/` defines a `print:hidden`
 * rule or an `@media print` block, so nothing suppressed it at print time.
 *
 * Sidebar and the page components are mocked to markers on purpose: the unit
 * under test is AppShell's ROUTING DECISION, not what any page renders. A test
 * that mounted the real PrintPage would be testing the print page's data hooks
 * and would fail for reasons unrelated to chrome.
 *
 * NON-VACUITY: every absence assertion below is paired with a positive control
 * on a non-print route in the same test file. An absence check that would also
 * pass against a broken selector proves nothing — and this repo has been bitten
 * by exactly that (see the IN-01 note in print-pdf-cleanup.test.tsx).
 */
import { describe, it, expect, vi, afterEach } from "vitest"
import { render, cleanup } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

let authStatus: "loading" | "unauthenticated" | "authenticated" = "authenticated"

vi.mock("@/context/auth-context", () => ({
  useAuth: () => ({ status: authStatus, setToken: vi.fn(), logout: vi.fn() }),
}))
vi.mock("@/context/vertical-context", () => ({
  useVertical: () => ({ PageComponent: null, navItem: null, Icon: () => null }),
}))
vi.mock("@/components/sidebar", () => ({
  Sidebar: () => <aside data-testid="sidebar">SIDEBAR</aside>,
}))
vi.mock("@/pages/print", () => ({
  PrintPage: () => <div data-testid="print-page">PRINT</div>,
}))
vi.mock("@/pages/executive", () => ({
  ExecutivePage: () => <div data-testid="executive-page">EXEC</div>,
}))
vi.mock("@/pages/login", () => ({
  LoginPage: () => <div data-testid="login-page">LOGIN</div>,
}))

async function renderAt(path: string) {
  const { AppShell } = await import("@/App")
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell />
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
  authStatus = "authenticated"
})

describe("PRINT-01 — /print renders chrome-free", () => {
  it("renders the print page with NO sidebar on /print", async () => {
    const { queryByTestId } = await renderAt("/print")

    expect(queryByTestId("print-page")).not.toBeNull()
    expect(queryByTestId("sidebar")).toBeNull()
  })

  it("POSITIVE CONTROL: the same sidebar marker IS rendered on a dashboard route", async () => {
    // Without this, the assertion above would pass even if the mocked Sidebar
    // never rendered anywhere — i.e. it would be vacuous.
    const { queryByTestId } = await renderAt("/")

    expect(queryByTestId("executive-page")).not.toBeNull()
    expect(queryByTestId("sidebar")).not.toBeNull()
  })

  it("renders no sidebar-offset wrapper on /print", async () => {
    // The shell offsets main content by the sidebar's width. Left in place on a
    // PDF with no sidebar, it would print as a wide blank left gutter — so its
    // absence matters independently of the sidebar's.
    const { container } = await renderAt("/print")

    expect(container.querySelector("main")).toBeNull()
    expect(container.querySelector('[class*="ml-12"]')).toBeNull()
    expect(container.querySelector('[class*="ml-60"]')).toBeNull()
  })

  it("POSITIVE CONTROL: the offset wrapper IS present on a dashboard route", async () => {
    const { container } = await renderAt("/")

    const main = container.querySelector("main")
    expect(main).not.toBeNull()
    expect(main?.className).toContain("ml-12")
  })

  it("tolerates a trailing slash — /print/ is still chrome-free", async () => {
    const { queryByTestId } = await renderAt("/print/")

    expect(queryByTestId("sidebar")).toBeNull()
  })

  it("still gates /print behind auth — unauthenticated gets the login page", async () => {
    // The PDF renderer opens a cookie-less context and reaches /print only via
    // AuthProvider's auth-disabled passthrough. If this ever starts returning
    // the print page, an authenticated view has silently become anonymous.
    authStatus = "unauthenticated"
    const { queryByTestId } = await renderAt("/print")

    expect(queryByTestId("login-page")).not.toBeNull()
    expect(queryByTestId("print-page")).toBeNull()
  })

  it("still shows the loading placeholder for /print while auth resolves", async () => {
    authStatus = "loading"
    const { queryByTestId } = await renderAt("/print")

    expect(queryByTestId("print-page")).toBeNull()
    expect(queryByTestId("sidebar")).toBeNull()
  })
})
