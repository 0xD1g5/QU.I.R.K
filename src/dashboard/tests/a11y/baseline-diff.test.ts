import { describe, it, expect } from "vitest"
import {
  buildBaselineEntries,
  compareToBaseline,
  deriveWcagCriteria,
  isPlaceholderJustification,
  SAMPLE_CAP,
  resolveVariant,
  baselineFilename,
} from "./baseline-diff.mjs"

// Phase 165 A11Y-04 / D-01, D-02, D-06, D-13, D-14 — the count-budget baseline comparison
// must be insensitive to selector churn (radix runtime IDs, Tailwind arbitrary values), must
// ratchet (any decrease below baseline fails, not passes silently), must refuse
// `critical`-impact violations regardless of baseline contents, must cap evidence samples,
// and must never synthesize a justification. See 165-CONTEXT.md D-01/D-02/D-06/D-13/D-14.
//
// NOTE ON DECISION-NUMBER COLLISION: the describe block below titled "justification
// carry-forward and" followed by "enforcement" and a "(D-06)" suffix cites 165-CONTEXT.md's
// D-06 (a Phase 165 decision about never synthesizing a justification) — that citation is
// correct in its own frame and the block is NOT renamed. It is unrelated to Phase 185's OWN
// D-06 (the no-tolerance-band,
// exact-integer count-pinning decision) and unrelated to Phase 185's D-05 (regeneration
// merges rather than rewrites, preserving human-written justification text across a
// recompute of counts). Phase 185 D-05 names the exact carry-forward behavior
// `buildBaselineEntries()` already implements below (see the
// `describe("justification carry-forward across regeneration (Phase 185 D-05)")` block) — it
// was verified ALREADY IMPLEMENTED against current `main`, not built new. A future reader must
// not repeat 185-CONTEXT.md's own error of concluding this merge still needs to be written.

function makeViolation({ id, impact = "serious", count = 1, target, tags = [], html }) {
  return {
    id,
    impact,
    tags,
    helpUrl: `https://dequeuniversity.com/rules/axe/4.11/${id}`,
    nodes: Array.from({ length: count }, (_, i) => ({
      target: [target ?? `#node-${i}`],
      html: html ?? `<div id="node-${i}"></div>`,
    })),
  }
}

function makeBaselineEntry({ rule, count, impact = "serious", justification = "" }) {
  return { rule, count, impact, wcag: [], helpUrl: "", justification, samples: [] }
}

describe("deriveWcagCriteria", () => {
  it("derives a three-digit wcag tag", () => {
    expect(deriveWcagCriteria(["cat.color", "wcag2aa", "wcag143"])).toEqual(["1.4.3"])
  })

  it("derives a multi-digit wcag tag using the greedy final group", () => {
    expect(deriveWcagCriteria(["wcag1411"])).toEqual(["1.4.11"])
  })

  it("returns an empty array when no tag matches", () => {
    expect(deriveWcagCriteria(["cat.color"])).toEqual([])
  })
})

describe("isPlaceholderJustification", () => {
  it.each(["", "   ", "pre-existing", "TBD"])(
    "treats %j as a placeholder",
    (value) => {
      expect(isPlaceholderJustification(value)).toBe(true)
    },
  )

  it("accepts a real, sufficiently long justification", () => {
    expect(
      isPlaceholderJustification(
        "Decorative disabled-state text; fixing requires a design system update.",
      ),
    ).toBe(false)
  })
})

describe("compareToBaseline — churn resistance (A11Y-04, D-01)", () => {
  it.each([
    [
      "radix runtime id churn",
      'button[aria-controls="radix-_r_QQ_"]',
      "button-name",
      "critical",
    ],
    [
      "tailwind arbitrary-value churn",
      '.bg-\\[hsl\\(24_95\\%_53\\%\\)\\]',
      "color-contrast",
      "serious",
    ],
  ])("%s produces zero regressions when counts match", (_desc, liveTarget, rule, impact) => {
    const live = [makeViolation({ id: rule, impact, count: 1, target: liveTarget })]
    const baseline = [makeBaselineEntry({ rule, count: 1, impact })]
    const result = compareToBaseline("cbom", live, baseline)
    expect(result.regressions).toHaveLength(0)
  })
})

describe("compareToBaseline — ratchet (D-13)", () => {
  it("ratchet up: observed count exceeding baseline yields exactly one regression", () => {
    const live = [makeViolation({ id: "color-contrast", count: 5 })]
    const baseline = [makeBaselineEntry({ rule: "color-contrast", count: 3 })]
    const result = compareToBaseline("cbom", live, baseline)
    expect(result.regressions).toEqual([
      expect.objectContaining({ rule: "color-contrast", baselineCount: 3, observedCount: 5 }),
    ])
    expect(result.staleEntries).toHaveLength(0)
  })

  it("ratchet down: observed count below baseline yields one staleEntries and zero regressions", () => {
    const live = [makeViolation({ id: "color-contrast", count: 1 })]
    const baseline = [makeBaselineEntry({ rule: "color-contrast", count: 3 })]
    const result = compareToBaseline("cbom", live, baseline)
    expect(result.regressions).toHaveLength(0)
    expect(result.staleEntries).toEqual([
      expect.objectContaining({ rule: "color-contrast", baselineCount: 3, observedCount: 1 }),
    ])
  })

  it("ratchet to zero: observed count 0 against a positive baseline yields one staleEntries", () => {
    const baseline = [makeBaselineEntry({ rule: "color-contrast", count: 3 })]
    const result = compareToBaseline("cbom", [], baseline)
    expect(result.staleEntries).toEqual([
      expect.objectContaining({ rule: "color-contrast", baselineCount: 3, observedCount: 0 }),
    ])
  })

  it("new rule: a rule present live with no baseline entry yields one regression with baselineCount 0", () => {
    const live = [makeViolation({ id: "label", count: 2 })]
    const result = compareToBaseline("cbom", live, [])
    expect(result.regressions).toEqual([
      expect.objectContaining({ rule: "label", baselineCount: 0, observedCount: 2 }),
    ])
  })
})

describe("critical refusal (D-14)", () => {
  it("buildBaselineEntries refuses a critical violation at write time but keeps a serious one on the same route", () => {
    const violations = [
      makeViolation({ id: "button-name", impact: "critical", count: 1 }),
      makeViolation({ id: "color-contrast", impact: "serious", count: 4 }),
    ]
    const { entries, refusedCritical } = buildBaselineEntries("cbom", violations)

    expect(refusedCritical).toHaveLength(1)
    expect(refusedCritical[0].rule).toBe("button-name")
    expect(entries.map(e => e.rule)).not.toContain("button-name")
    expect(entries.map(e => e.rule)).toContain("color-contrast")
  })

  it("compareToBaseline reports a live critical violation in criticalViolations even when the count matches baseline", () => {
    const live = [makeViolation({ id: "button-name", impact: "critical", count: 1 })]
    const baseline = [makeBaselineEntry({ rule: "button-name", count: 1, impact: "critical" })]
    const result = compareToBaseline("cbom", live, baseline)
    expect(result.criticalViolations).toEqual([
      expect.objectContaining({ rule: "button-name" }),
    ])
  })
})

describe("evidence samples (D-02)", () => {
  it("caps samples at SAMPLE_CAP, stores node.html, and stores no target field", () => {
    const violation = makeViolation({ id: "color-contrast", count: 190, html: "<span>x</span>" })
    const { entries } = buildBaselineEntries("qramm-assessment", [violation])
    const entry = entries.find(e => e.rule === "color-contrast")

    expect(entry.samples).toHaveLength(SAMPLE_CAP)
    expect(entry.samples.every(s => s === "<span>x</span>")).toBe(true)
    expect(entry).not.toHaveProperty("target")
    expect(JSON.stringify(entry)).not.toContain("target")
  })
})

describe("justification carry-forward and enforcement (D-06)", () => {
  it("preserves a real prior justification across a rebuild", () => {
    const violation = makeViolation({ id: "color-contrast", count: 3 })
    const previousEntries = [
      makeBaselineEntry({
        rule: "color-contrast",
        count: 3,
        justification: "Decorative disabled-state text pending design system update.",
      }),
    ]
    const { entries } = buildBaselineEntries("cbom", [violation], { previousEntries })
    expect(entries[0].justification).toBe(
      "Decorative disabled-state text pending design system update.",
    )
  })

  it("resets a placeholder prior justification to the empty string", () => {
    const violation = makeViolation({ id: "color-contrast", count: 3 })
    const previousEntries = [
      makeBaselineEntry({ rule: "color-contrast", count: 3, justification: "pre-existing" }),
    ]
    const { entries } = buildBaselineEntries("cbom", [violation], { previousEntries })
    expect(entries[0].justification).toBe("")
  })

  it("compareToBaseline reports an empty or placeholder justification in missingJustifications", () => {
    const baseline = [
      makeBaselineEntry({ rule: "color-contrast", count: 3, justification: "" }),
      makeBaselineEntry({ rule: "scrollable-region-focusable", count: 1, justification: "tbd" }),
    ]
    const result = compareToBaseline("cbom", [], baseline)
    expect(result.missingJustifications.map(m => m.rule).sort()).toEqual([
      "color-contrast",
      "scrollable-region-focusable",
    ])
  })
})

describe("justification carry-forward across regeneration (Phase 185 D-05)", () => {
  it("carries a real human-written justification forward when the count changes", () => {
    const violation = makeViolation({ id: "color-contrast", count: 7 })
    const previousEntries = [
      makeBaselineEntry({
        rule: "color-contrast",
        count: 3,
        justification:
          "Phase 156 D-07 HWLC-11 advisory firewall raw hsl() literals; see lifecycle-advisory-guard.test.ts.",
      }),
    ]
    const { entries } = buildBaselineEntries("hardware", [violation], { previousEntries })
    const entry = entries.find(e => e.rule === "color-contrast")
    expect(entry.count).toBe(7)
    expect(entry.justification).toBe(
      "Phase 156 D-07 HWLC-11 advisory firewall raw hsl() literals; see lifecycle-advisory-guard.test.ts.",
    )
  })

  it("does not carry a placeholder justification forward across a regeneration", () => {
    const violation = makeViolation({ id: "color-contrast", count: 5 })
    const previousEntries = [
      makeBaselineEntry({ rule: "color-contrast", count: 2, justification: "TBD" }),
    ]
    const { entries } = buildBaselineEntries("hardware", [violation], { previousEntries })
    expect(entries.find(e => e.rule === "color-contrast").justification).toBe("")
  })

  it("drops a rule absent from the new live run rather than carrying it forward as a zero-count entry", () => {
    // Verified, intended behavior per 185-05-PLAN.md <interfaces>: `entries` is built strictly
    // from the live `byRule` map, so a rule present only in `previousEntries` disappears. A
    // decrease to zero is the strongest decrease (D-04) and a `count: 0` placeholder entry
    // would have nothing left to justify. This test locks that so a future "helpful" change
    // to preserve zero-count entries fails loudly.
    const violation = makeViolation({ id: "color-contrast", count: 4 })
    const previousEntries = [
      makeBaselineEntry({ rule: "color-contrast", count: 4, justification: "still present" }),
      makeBaselineEntry({
        rule: "scrollable-region-focusable",
        count: 2,
        justification: "no longer triggered on this route",
      }),
    ]
    const { entries } = buildBaselineEntries("hardware", [violation], { previousEntries })
    expect(entries.map(e => e.rule)).toEqual(["color-contrast"])
    expect(entries.find(e => e.rule === "scrollable-region-focusable")).toBeUndefined()
  })

  it("does not leak a justification across baseline files for different variants of the same route", () => {
    // The (route, rule) carry-forward Map is built fresh from whatever `previousEntries` the
    // caller passes in per call — run-a11y.mjs reads a DIFFERENT baseline file per variant
    // (baseline-hardware-default.json vs baseline-hardware-empty.json), so a justification
    // written on the default-variant file must not appear when regenerating the empty-variant
    // file unless that file's OWN previous entries already carried it.
    const violation = makeViolation({ id: "color-contrast", count: 1 })

    const defaultPrevious = [
      makeBaselineEntry({
        rule: "color-contrast",
        count: 1,
        justification: "Written against baseline-hardware-default.json only.",
      }),
    ]
    const { entries: defaultEntries } = buildBaselineEntries("hardware", [violation], {
      previousEntries: defaultPrevious,
    })
    expect(defaultEntries[0].justification).toBe(
      "Written against baseline-hardware-default.json only.",
    )

    // Regenerating the EMPTY variant's own file passes that file's own (empty) previous
    // entries — the default variant's justification text must not leak in.
    const { entries: emptyEntries } = buildBaselineEntries("hardware", [violation], {
      previousEntries: [],
    })
    expect(emptyEntries[0].justification).toBe("")
  })
})

describe("variant-aware baseline naming (A11Y-04, D-15, D-16)", () => {
  it("resolveVariant({}) returns 'default' — the unsuffixed run is not an empty-string variant", () => {
    expect(resolveVariant({})).toBe("default")
  })

  it("resolveVariant with VITE_A11Y_FIXTURE_VARIANT='empty' returns 'empty'", () => {
    expect(resolveVariant({ VITE_A11Y_FIXTURE_VARIANT: "empty" })).toBe("empty")
  })

  it("resolveVariant with VITE_A11Y_FIXTURE_VARIANT='loading' returns 'loading' — D-16 rides the same code path", () => {
    expect(resolveVariant({ VITE_A11Y_FIXTURE_VARIANT: "loading" })).toBe("loading")
  })

  it("resolveVariant with an empty-string variant falls back to 'default', not 'baseline-cbom-.json'", () => {
    expect(resolveVariant({ VITE_A11Y_FIXTURE_VARIANT: "" })).toBe("default")
  })

  it("baselineFilename('cbom', 'default') returns 'baseline-cbom-default.json'", () => {
    expect(baselineFilename("cbom", "default")).toBe("baseline-cbom-default.json")
  })

  it("baselineFilename('qramm-assessment', 'empty') round-trips a hyphenated slug correctly", () => {
    expect(baselineFilename("qramm-assessment", "empty")).toBe(
      "baseline-qramm-assessment-empty.json",
    )
  })

  it("the default and empty variants produce different filenames for the same slug", () => {
    expect(baselineFilename("cbom", "default")).not.toBe(baselineFilename("cbom", "empty"))
  })
})
