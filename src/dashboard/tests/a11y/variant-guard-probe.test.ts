/**
 * Synthetic mutation probe for variant-guard.mjs (221-01, mutation recipe M6).
 *
 * Synthetic input, no filesystem I/O. Fabricated slug `probe-route` and selectors that
 * collide with nothing real. All nodes are green by design: they assert the injected
 * failures ARE caught. Live RED evidence belongs in 221-VERIFICATION, not here.
 */
import { describe, it, expect } from "vitest"
import { renderStateViolations, DEFAULT_LOADING_SELECTOR, DEFAULT_EMPTY_SELECTOR } from "./variant-guard.mjs"
import { VARIANTS, resolveVariant } from "./baseline-diff.mjs"

const A = ".probe-marker-a"
const B = ".probe-marker-b"
const markers = { "scan-latest": A, trends: B }

describe("variant-guard-probe (221-01) -- synthetic input, no filesystem I/O", () => {
  it("empty with a marker present is exactly one violation naming the selector and 'present'", () => {
    const v = renderStateViolations({ variant: "empty", slug: "probe-route", markers: { x: A }, present: { [A]: true }, emptyWitnesses: 1 })
    expect(v).toHaveLength(1)
    expect(v[0]).toContain(A)
    expect(v[0]).toContain("present")
    expect(v[0].startsWith("render state [probe-route/empty]:")).toBe(true)
  })

  it("loading with a marker present is one violation", () => {
    const v = renderStateViolations({ variant: "loading", slug: "probe-route", markers: { x: A }, present: { [A]: true }, skeleton: true })
    expect(v).toHaveLength(1)
  })

  it("loading with all markers absent and no skeleton is one violation naming the loading selector", () => {
    const v = renderStateViolations({ variant: "loading", slug: "probe-route", markers, present: {}, skeleton: false })
    expect(v).toHaveLength(1)
    expect(v[0]).toContain(DEFAULT_LOADING_SELECTOR)
  })

  it("default with a declared marker absent is one violation", () => {
    const v = renderStateViolations({ variant: "default", slug: "probe-route", markers, present: { [A]: true, [B]: false } })
    expect(v).toHaveLength(1)
    expect(v[0]).toContain(B)
  })

  it("empty with all markers absent is legitimate", () => {
    expect(renderStateViolations({ variant: "empty", slug: "probe-route", markers, present: {}, emptyWitnesses: 2 })).toEqual([])
  })

  // 221 WR-02: absence alone is not proof (a crashed or unrendered page has no markers either).
  it("empty with all markers absent but no empty-state witness is one violation naming the empty selector", () => {
    const v = renderStateViolations({ variant: "empty", slug: "probe-route", markers, present: {} })
    expect(v).toHaveLength(1)
    expect(v[0]).toContain(DEFAULT_EMPTY_SELECTOR)
  })

  it("empty with fewer witnesses than marked endpoints is one violation", () => {
    const v = renderStateViolations({ variant: "empty", slug: "probe-route", markers, present: {}, emptyWitnesses: 1 })
    expect(v).toHaveLength(1)
    expect(v[0]).toContain("need 2")
  })

  it("loading with all markers absent and skeleton true is legitimate", () => {
    expect(renderStateViolations({ variant: "loading", slug: "probe-route", markers, present: {}, skeleton: true })).toEqual([])
  })

  it("default with all markers present is legitimate", () => {
    expect(renderStateViolations({ variant: "default", slug: "probe-route", markers, present: { [A]: true, [B]: true } })).toEqual([])
  })

  it("VARIANTS is exactly default, empty, loading", () => {
    expect([...VARIANTS]).toEqual(["default", "empty", "loading"])
  })

  it("resolveVariant({}) is default and an unknown variant throws", () => {
    expect(resolveVariant({})).toBe("default")
    expect(() => resolveVariant({ VITE_A11Y_FIXTURE_VARIANT: "bogus" })).toThrow(/bogus/)
  })
})
