import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"

// Phase 185 D-14 — "covered but blind" guard.
//
// The coverage gap that let CR-01 escape detection was not a missing test — it was a
// missing FETCH INTERCEPTION: /hardware and /compare's data hooks called endpoints the
// Vite a11y fixture middleware did not match, so the pages silently rendered their
// empty-state branches under the harness and a hollow axe scan passed. This test closes
// that loop mechanically: it reads each hook's real fetch target out of source, and
// asserts the middleware in `vite.config.ts` actually has a handler prefix that matches
// it. A future hook that changes its endpoint, or a middleware handler that is deleted,
// fails this test rather than silently reintroducing an empty-render baseline.

const VITE_CONFIG_PATH = path.resolve(__dirname, "../../vite.config.ts")
const viteConfigSource = readFileSync(VITE_CONFIG_PATH, "utf-8")

const HOOKS_DIR = path.resolve(__dirname, "../../src/hooks")

interface HookFetchTarget {
  hookFile: string
  /** The literal URL prefix the hook fetches, as it appears in vite.config.ts's startsWith() checks. */
  urlPrefix: string
}

// Each hook's fetch target is extracted directly from its source text below, not
// hand-copied — the regexes point at the actual fetch call so a change to the hook's
// endpoint changes what this test extracts, not just what it expects.
const HOOK_TARGETS: HookFetchTarget[] = [
  {
    hookFile: "useHardwareDrift.ts",
    urlPrefix: extractQuotedConstUrl("useHardwareDrift.ts"),
  },
  {
    hookFile: "useVendorPqcTrends.ts",
    urlPrefix: extractQuotedConstUrl("useVendorPqcTrends.ts"),
  },
  {
    hookFile: "useCompareData.ts",
    urlPrefix: extractTemplateLiteralPrefix("useCompareData.ts"),
  },
]

function extractQuotedConstUrl(hookFile: string): string {
  const source = readFileSync(path.resolve(HOOKS_DIR, hookFile), "utf-8")
  const match = source.match(/const url = ["']([^"']+)["']/)
  if (!match) {
    throw new Error(`Could not extract fetch URL from ${hookFile} — hook source shape changed`)
  }
  return match[1]
}

function extractTemplateLiteralPrefix(hookFile: string): string {
  const source = readFileSync(path.resolve(HOOKS_DIR, hookFile), "utf-8")
  // Matches fetchApi(`/api/compare?a=...`) — extracts the literal prefix before the
  // first template-literal interpolation.
  const match = source.match(/fetchApi\(\s*`([^$`]+)\$\{/)
  if (!match) {
    throw new Error(`Could not extract fetch URL prefix from ${hookFile} — hook source shape changed`)
  }
  return match[1]
}

describe("a11y fixture middleware covers every /hardware + /compare fetch target (D-14)", () => {
  it.each(HOOK_TARGETS)(
    "$hookFile's fetch target ($urlPrefix) is matched by a vite.config.ts handler",
    ({ hookFile, urlPrefix }) => {
      // The middleware matches via `req.url?.startsWith('<prefix>')`. A hook's URL is
      // covered if some handler's startsWith() prefix is itself a prefix of the hook's
      // URL (e.g. handler prefix "/api/compare" covers hook URL "/api/compare?a=1&b=2").
      const startsWithPrefixes = [
        ...viteConfigSource.matchAll(/req\.url\?\.startsWith\(['"]([^'"]+)['"]\)/g),
      ].map((m) => m[1])

      const covered = startsWithPrefixes.some((prefix) => urlPrefix.startsWith(prefix))

      expect(
        covered,
        `${hookFile} fetches "${urlPrefix}" but no vite.config.ts startsWith() handler prefix matches it. ` +
          `Known handler prefixes: ${JSON.stringify(startsWithPrefixes)}`,
      ).toBe(true)
    },
  )

  it("has three distinct handler prefixes for the hardware-drift, vendor-trends, and compare endpoints", () => {
    expect(viteConfigSource).toContain("/api/hardware/drift")
    expect(viteConfigSource).toContain("/api/hardware/vendor-trends")
    expect(viteConfigSource).toContain("/api/compare")
  })

  it("fixture files referenced by the new handlers are non-empty and well-shaped", () => {
    const drift = JSON.parse(
      readFileSync(path.resolve(__dirname, "fixture-hardware-drift.json"), "utf-8"),
    )
    expect(Array.isArray(drift.latest_events)).toBe(true)
    expect(drift.latest_events.length).toBeGreaterThan(0)
    expect(Array.isArray(drift.historical_events)).toBe(true)
    expect(drift.historical_events.length).toBeGreaterThan(0)

    const vendorTrends = JSON.parse(
      readFileSync(path.resolve(__dirname, "fixture-vendor-trends.json"), "utf-8"),
    )
    expect(Array.isArray(vendorTrends.events)).toBe(true)
    expect(vendorTrends.events.length).toBeGreaterThan(0)

    const compare = JSON.parse(readFileSync(path.resolve(__dirname, "fixture-compare.json"), "utf-8"))
    expect(compare.scan_a).toBeTruthy()
    expect(compare.scan_b).toBeTruthy()
    expect(Array.isArray(compare.hardware_drift)).toBe(true)
    expect(compare.hardware_drift.length).toBeGreaterThan(0)

    const scan = JSON.parse(readFileSync(path.resolve(__dirname, "fixture-scan.json"), "utf-8"))
    expect(Array.isArray(scan.hardware_findings)).toBe(true)
    expect(scan.hardware_findings.length).toBeGreaterThanOrEqual(2)
  })
})
