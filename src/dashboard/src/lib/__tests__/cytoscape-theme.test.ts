import { describe, it, expect, vi, afterEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { resolveToken, useThemeRevision } from "../cytoscape-theme"

afterEach(() => {
  document.documentElement.removeAttribute("style")
  document.documentElement.className = ""
  vi.restoreAllMocks()
})

describe("resolveToken", () => {
  it("returns the computed hex value for a hex-family property set on documentElement", () => {
    document.documentElement.style.setProperty("--test-ds-high", "#d4893a")
    expect(resolveToken("--test-ds-high")).toBe("#d4893a")
  })

  it("converts a raw HSL-component property to hex rather than returning the raw triple", () => {
    document.documentElement.style.setProperty("--test-status-critical", "0 72% 51%")
    // 0 72% 51% -> #dc2828 (same conversion hslToHex uses elsewhere in this codebase)
    expect(resolveToken("--test-status-critical")).toBe("#dc2828")
  })

  it("returns an empty string and warns for an unknown token", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {})
    const result = resolveToken("--this-token-does-not-exist")
    expect(result).toBe("")
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining("--this-token-does-not-exist"),
    )
  })
})

describe("useThemeRevision", () => {
  it("increments when the documentElement class attribute is mutated", async () => {
    const { result } = renderHook(() => useThemeRevision())
    expect(result.current).toBe(0)

    act(() => {
      document.documentElement.className = "light"
    })

    await waitFor(() => expect(result.current).toBe(1))
  })

  it("does not increment on an unrelated attribute change", async () => {
    const { result } = renderHook(() => useThemeRevision())
    expect(result.current).toBe(0)

    await act(async () => {
      document.documentElement.setAttribute("data-unrelated", "x")
      // Give any (unexpected) MutationObserver callback a turn to fire before asserting
      // the negative — a plain synchronous assertion here would pass trivially even if
      // the observer were wrongly unscoped, because the callback hasn't run yet.
      await new Promise((r) => setTimeout(r, 20))
    })

    expect(result.current).toBe(0)
  })

  it("disconnects the observer on unmount", async () => {
    const disconnectSpy = vi.spyOn(MutationObserver.prototype, "disconnect")
    const { unmount } = renderHook(() => useThemeRevision())
    unmount()
    expect(disconnectSpy).toHaveBeenCalled()
  })
})
