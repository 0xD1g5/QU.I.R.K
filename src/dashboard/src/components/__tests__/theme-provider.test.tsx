import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import { VALID_THEMES, getStoredTheme } from "@/components/theme-context"

// D-05 (WR-04): theme-provider must validate localStorage value against an
// allowlist (VALID_THEMES) and silently fall back to defaultTheme on any
// unrecognized or missing value. No console.warn — theme is QoL, not security.

const STORAGE_KEY = "quirk-ui-theme"

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})

describe("VALID_THEMES allowlist", () => {
  it("exposes the canonical three themes as a const tuple", () => {
    expect(VALID_THEMES).toEqual(["light", "dark", "system"])
  })
})

describe("getStoredTheme — D-05 (WR-04) localStorage allowlist", () => {
  it.each([
    ["light", "light"],
    ["dark", "dark"],
    ["system", "system"],
    ["banana", "system"],
    ["", "system"],
  ])("returns %s -> %s", (stored, expected) => {
    localStorage.setItem(STORAGE_KEY, stored)
    expect(getStoredTheme(STORAGE_KEY, "system")).toBe(expected)
  })

  it("returns default when key absent", () => {
    localStorage.removeItem(STORAGE_KEY)
    expect(getStoredTheme(STORAGE_KEY, "system")).toBe("system")
  })

  it("does not call console.warn on invalid value", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {})
    localStorage.setItem(STORAGE_KEY, "banana")
    getStoredTheme(STORAGE_KEY, "system")
    expect(warn).not.toHaveBeenCalled()
  })

  it("respects a non-system defaultTheme when value is invalid", () => {
    localStorage.setItem(STORAGE_KEY, "banana")
    expect(getStoredTheme(STORAGE_KEY, "dark")).toBe("dark")
  })
})
