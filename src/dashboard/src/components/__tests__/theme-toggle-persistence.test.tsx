// Phase 206 Plan 10 (COV-04) — UAT-7-22: Dark/Light Theme Toggle.
//
// Pass Criteria under test (docs/UAT-SERIES.md UAT-7-22):
//   - Clicking the toggle switches the theme instantly
//   - `localStorage` key `quirk-ui-theme` stores "light" or "dark"
//   - Theme persists after a full page reload  -> asserted as the persisted
//     value being what a fresh mount reads back (`getStoredTheme` is the app's
//     own rehydration path; a real F5 is not available in jsdom)
//
// Uncovered Pass Criteria bullets, named explicitly per CONTEXT's partial-
// coverage rule:
//   - "All page elements update: sidebar, cards, charts, tables, badges" and
//     "Both themes are visually coherent (no invisible text, unreadable
//     badges, or broken contrast)" are appearance claims. jsdom has no layout
//     or cascade engine, so neither is honestly assertable here; both route to
//     the browser-tier verdict.
//
// This is NEW coverage: the existing `theme-provider.test.tsx` exercises only
// the `getStoredTheme()` / `VALID_THEMES` utility surface — it never renders a
// provider, never clicks a toggle, and never asserts the applied theme class.
import { describe, it, expect, beforeEach, afterEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ThemeProvider } from "@/components/theme-provider"
import { ModeToggle } from "@/components/mode-toggle"
import { getStoredTheme } from "@/components/theme-context"
import { TooltipProvider } from "@/components/ui/tooltip"

// The app's real storage key, as passed by App.tsx's ThemeProvider.
const STORAGE_KEY = "quirk-ui-theme"

beforeEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove("light", "dark")
})

afterEach(() => {
  localStorage.clear()
  document.documentElement.classList.remove("light", "dark")
})

describe("ModeToggle inside ThemeProvider — UAT-7-22", () => {
  it("switches the theme and persists the selection to localStorage when the theme toggle is used", async () => {
    const user = userEvent.setup()

    render(
      <ThemeProvider defaultTheme="dark" storageKey={STORAGE_KEY}>
        <TooltipProvider>
          <ModeToggle />
        </TooltipProvider>
      </ThemeProvider>,
    )

    // Starting state: the dark default is applied to the document element.
    expect(document.documentElement.classList.contains("dark")).toBe(true)

    await user.click(screen.getByRole("button", { name: "Light mode" }))

    // Half one — the theme actually switched on the document.
    expect(document.documentElement.classList.contains("light")).toBe(true)
    expect(document.documentElement.classList.contains("dark")).toBe(false)

    // Half two — the selection was persisted under the app's real key. This
    // half is the case's own subject; a toggle test that omits it covers
    // UAT-7-22 only partially.
    expect(localStorage.getItem(STORAGE_KEY)).toBe("light")

    // Reload equivalence: the app rehydrates through getStoredTheme(), so a
    // fresh mount would come back up in light mode.
    expect(getStoredTheme(STORAGE_KEY, "dark")).toBe("light")

    // Toggling back (UAT step 8) persists the return trip too.
    await user.click(screen.getByRole("button", { name: "Dark mode" }))
    expect(document.documentElement.classList.contains("dark")).toBe(true)
    expect(localStorage.getItem(STORAGE_KEY)).toBe("dark")
  })
})
