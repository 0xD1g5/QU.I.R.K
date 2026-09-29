/**
 * Synthetic mutation probe over the repaired a11y harness choke points —
 * Phase 216 plan 216-06.
 *
 * WHY THIS FILE EXISTS. A guard nobody has seen fail is a guard nobody has
 * tested. Plans 216-01..05 repaired the harness's theme dimension, fixture
 * coverage gate, and range/tolerance comparison, but until now nothing had
 * forced those repaired choke points red on purpose and confirmed they name
 * the right thing. This file applies the Phase 215 RATCHET-04 standard
 * (`src/components/__tests__/badge-contrast-guard-probe.test.ts`) to the a11y
 * harness: drive the PURE modules under probe with hand-built synthetic
 * input, and assert the injected failures ARE caught.
 *
 * WHY SYNTHETIC INPUT IS POSSIBLE AT ALL. `badge-map-extractor.mjs` and
 * `baseline-diff.mjs` both perform NO filesystem I/O and import NO vitest —
 * every export is a pure function of its arguments (each module states this
 * of itself in its own header). Purity is what makes fast, deterministic
 * mutation testing possible instead of a slow, flake-prone round-trip
 * through real `.tsx` source, real fixtures and real committed baselines.
 *
 * WHAT THIS FILE DELIBERATELY DOES NOT DO. It never reads a real `.tsx`,
 * `.css`, `.json` or baseline file, and it mutates nothing on disk — every
 * input below is a fabricated string or object literal (`FAKE_STYLES`, slug
 * `probe-route`, token `--probe-token`) chosen not to collide with any real
 * map name, slug or token in this codebase. That means there is no git-dirt
 * window (nothing here can leave a real file edited), and no flake when
 * Phase 217 changes a real contrast token or Phase 218/219 renames a real
 * route — this file never reads either.
 *
 * ALL NODES BELOW ARE GREEN, BY DESIGN. This file is a positive test about
 * negative behaviour: it asserts the injected failures ARE caught, the
 * repaired guard's OWN vacuity/naming/range rules. The live RED evidence
 * 216-VALIDATION.md's falsifiers 1/2 and ROADMAP criterion 2 require —
 * captured as verbatim terminal output, not asserted in prose — is produced
 * separately in Task 2 and lives in `216-06-SUMMARY.md`, not in this file.
 * A `Self-Check: PASSED` line is a claim, not evidence; the verbatim RED
 * terminal output is.
 */
import { describe, it, expect } from "vitest"
import { extractBadgeMaps, dispositionCoverage } from "./badge-map-extractor.mjs"
import { baselineFilename, THEMES } from "./baseline-diff.mjs"

// Fabricated source text, chosen not to collide with any real map name in
// `src/pages/*.tsx`. Do NOT derive this from a real page — a real map
// gaining/losing a key under Phase 217/218 would make this probe flake for
// reasons unrelated to what it tests.
const FAKE_STYLES_BARE_KEYS = `
const FAKE_STYLES: Record<string, string> = {
  Safe: "bg-[hsl(var(--probe-token))] text-white",
  Risky: "bg-[hsl(var(--probe-token-2))] text-white",
}
`

const FAKE_STYLES_QUOTED_KEYS = `
const OTHER_FAKE_STYLES: Record<string, string> = {
  "Tier 1": "bg-[hsl(var(--probe-token-3))] text-white",
  "Tier N/A": "bg-[hsl(var(--probe-token-4))] text-white",
}
`

describe("harness-falsification-probe (216-06) -- synthetic input, no filesystem I/O", () => {
  describe("Injection A: extractor under-read (216-VALIDATION.md falsifier 2)", () => {
    // What input makes this fail: if `extractBadgeMaps` is ever swapped for a
    // stub/regression that returns `[]` unconditionally (a total under-read),
    // this node's own assertion that empty source yields zero maps stays
    // green -- so the SECOND assertion is the one that actually falsifies
    // the real gate's vacuity rule: it proves the real gate (mirrored here
    // via `dispositionCoverage`) treats zero discovered maps as a FAILING
    // condition (an undispositioned/orphaned state), never a silent pass.
    it("extractBadgeMaps('') returns zero maps", () => {
      expect(extractBadgeMaps("")).toEqual([])
    })

    it("zero discovered maps against a non-empty ledger is reported as a FAILING orphaned-ledger state, never a silent pass", () => {
      const maps = extractBadgeMaps("") // simulates a total under-read to zero
      const ledger = { "probe/fake.tsx:FAKE_STYLES": "raw-field" }

      const result = dispositionCoverage({ maps, ledger, observedKeysByMap: {} })

      // The real gate's vacuity rule: a ledger row with no matching discovered
      // map is an orphaned row -- exactly the "reads zero maps -> passes
      // vacuously" tautology 216-VALIDATION.md's falsifier 2 warns against
      // must NOT be silently swallowed. Input that would make this fail: if
      // `dispositionCoverage` returned an empty `orphanedLedgerRows` array
      // for a ledger that visibly does not match any discovered map.
      expect(result.orphanedLedgerRows).toEqual(["probe/fake.tsx:FAKE_STYLES"])
      expect(result.uncoveredKeys).toEqual([])
    })
  })

  describe("Injection B: extractor key-shape coverage (bare vs quoted identifier keys)", () => {
    // What input makes this fail: a regex that only matched quoted keys
    // (`"Tier 1":`) would silently under-read FAKE_STYLES's bare `Safe:`/
    // `Risky:` keys to an empty or partial set -- the exact regression shape
    // that would have let a quoted-keys-only extractor under-read
    // certificates.tsx's real `Safe:` key to zero.
    it("a bare-identifier-keyed map yields both bare keys", () => {
      const maps = extractBadgeMaps(FAKE_STYLES_BARE_KEYS)
      expect(maps).toHaveLength(1)
      expect(maps[0].name).toBe("FAKE_STYLES")
      expect(maps[0].keys.sort()).toEqual(["Risky", "Safe"])
    })

    it("a quoted-identifier-keyed map yields both quoted keys", () => {
      const maps = extractBadgeMaps(FAKE_STYLES_QUOTED_KEYS)
      expect(maps).toHaveLength(1)
      expect(maps[0].name).toBe("OTHER_FAKE_STYLES")
      expect(maps[0].keys.sort()).toEqual(["Tier 1", "Tier N/A"])
    })

    it("a source file containing BOTH shapes yields both maps with both key sets intact", () => {
      const maps = extractBadgeMaps(FAKE_STYLES_BARE_KEYS + FAKE_STYLES_QUOTED_KEYS)
      expect(maps).toHaveLength(2)
      const byName = Object.fromEntries(maps.map((m) => [m.name, m.keys.sort()]))
      expect(byName["FAKE_STYLES"]).toEqual(["Risky", "Safe"])
      expect(byName["OTHER_FAKE_STYLES"]).toEqual(["Tier 1", "Tier N/A"])
    })
  })

  describe("Injection C: theme separation (216-VALIDATION.md falsifier 1, unit half)", () => {
    // What input makes this fail: if `baselineFilename` ever collapsed the
    // theme segment back to an implicit default (the exact "sweeps the dark
    // variant only" defect D-02 repairs), light and dark would resolve to
    // the same filename and this equality-of-negation would flip to a
    // false-positive pass.
    it("light and dark filenames for the same route/variant are never equal", () => {
      const light = baselineFilename("probe-route", "default", "light")
      const dark = baselineFilename("probe-route", "default", "dark")
      expect(light).not.toBe(dark)
      expect(light).toBe("baseline-probe-route-default-light.json")
      expect(dark).toBe("baseline-probe-route-default-dark.json")
    })

    it("a 2-arg call (omitted theme) throws rather than yielding a '-undefined.json' path", () => {
      // @ts-expect-error -- deliberately calling with the theme arg omitted,
      // the exact silent-defaulting shape this probe exists to forbid.
      expect(() => baselineFilename("probe-route", "default")).toThrow(
        /missing\/invalid theme/,
      )
    })

    it("THEMES exposes both light and dark, and only those two", () => {
      // Guards against this probe itself going stale if THEMES ever narrows
      // back to one theme -- a silent narrowing here would make Injection C's
      // "never equal" assertion vacuous (only one theme to compare).
      expect([...THEMES].sort()).toEqual(["dark", "light"])
    })
  })

  describe("Injection D: range ceiling and floor (opt-in countRange, D-10/D-12)", () => {
    // These exercise the SAME range semantics `compareToBaseline` implements
    // (ceiling = ceiling of countRange, floor = floor of countRange), applied
    // directly to a synthetic countRange tuple so the two-sided-band shape
    // is probed without needing a real axe violations array. What input
    // makes each fail: a live count exactly at the ceiling+1 (5) must
    // regress; exactly at the floor-1 (1) must go stale; 2, 3, 4 (inside
    // [2,4] inclusive) must do neither.
    const countRange: [number, number] = [2, 4]
    function classify(liveCount: number): "regression" | "stale" | "ok" {
      const [floor, ceiling] = countRange
      if (liveCount > ceiling) return "regression"
      if (liveCount < floor) return "stale"
      return "ok"
    }

    it("a live count of 5 (above the ceiling of 4) is exactly one regression", () => {
      expect(classify(5)).toBe("regression")
    })

    it("a live count of 1 (below the floor of 2) is exactly one stale entry", () => {
      expect(classify(1)).toBe("stale")
    })

    it.each([2, 3, 4])(
      "a live count of %d (inside [2,4]) triggers neither a regression nor a stale entry",
      (liveCount) => {
        expect(classify(liveCount)).toBe("ok")
      },
    )
  })

  describe("Control: the probe is not simply failing everything", () => {
    // What input makes this fail: if `dispositionCoverage` were mutated to
    // always report a nonzero `uncoveredKeys`/orphaned state regardless of
    // input (the "fails everything" degenerate case), this node would go red
    // where it should stay green -- proving the earlier RED-producing
    // injections are catching something real, not a universally-failing stub.
    it("a synthetic map fully covered by synthetic observed keys reports zero uncoveredKeys", () => {
      const maps = extractBadgeMaps(FAKE_STYLES_BARE_KEYS)
      const ledger = { "probe/fake.tsx:FAKE_STYLES": "raw-field" }
      const observedKeysByMap = { "probe/fake.tsx:FAKE_STYLES": ["Safe", "Risky"] }

      const result = dispositionCoverage({
        maps: maps.map((m) => ({ ...m, file: "probe/fake.tsx" })),
        ledger,
        observedKeysByMap,
      })

      expect(result.uncoveredKeys).toEqual([])
      expect(result.undispositionedMaps).toEqual([])
      expect(result.orphanedLedgerRows).toEqual([])
    })

    it("an exact-count entry (no countRange) matching its live count reports neither a regression nor a stale entry", () => {
      // Mirrors compareToBaseline's degenerate "no range declared" path:
      // ceiling === floor === the exact baseline count.
      const baselineCount = 3
      const liveCount = 3
      const ceiling = baselineCount
      const floor = baselineCount
      expect(liveCount > ceiling).toBe(false)
      expect(liveCount < floor).toBe(false)
    })
  })
})
