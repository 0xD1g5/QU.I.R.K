/**
 * UAT-7-21 ("Dashboard Theme — No Hardcoded Colors") — Phase 206 plan 206-11.
 *
 * CONTEXT D-A1 (operator decision) carves this ONE case out of the phase-wide
 * ban on source-text tests. The ban's own rationale is that grepping source
 * "does not cover a *render* case"; UAT-7-21's claim — "no hardcoded #hex
 * colors in inline styles on major components" — IS a source property, so a
 * source audit covers its actual subject rather than substituting for it.
 * The carve-out is scoped to this file. The ban stands, unchanged, for every
 * other case in Phase 206.
 *
 * SCOPE IS DERIVED AT RUN TIME, NEVER WRITTEN DOWN. The audited page set comes
 * from a `readdirSync` of `src/pages/`, so a page added tomorrow is audited
 * tomorrow. A hand-maintained list of files would silently stop matching the
 * real set — this repository has been bitten by exactly that failure mode
 * repeatedly, and a written list is not a safeguard.
 *
 * ---------------------------------------------------------------------------
 * CURRENT CONTRACT (as of Phase 213 plan 08): this is a PLAIN `it` — the
 * `.fails` modifier a prior phase wrapped it in has been removed. A GREEN
 * run means zero hardcoded colour literals remain across the audited set.
 * A RED run means one was reintroduced, and the failure
 * diff names every offending file, line and literal via `format()` below.
 * Read this before citing the node — its polarity was inverted for six
 * phases (see the historical note at the end of this comment) and a reader
 * skimming an old citation can easily get the direction backwards.
 * ---------------------------------------------------------------------------
 * The detector covers three raw-HSL spellings found live in this codebase,
 * in addition to `#hex`: `RAW_HSL_SPACE_RE` (`hsl(142 71% 45%)`),
 * `RAW_HSL_UNDERSCORE_RE` (Tailwind arbitrary-value form,
 * `hsl(142_71%_45%)`), and `RAW_HSL_COMMA_RE` (legacy comma form,
 * `hsl(0, 72%, 51%)`). The pre-widen predecessor detector had only the
 * whitespace form and was structurally blind to the other two — not merely
 * under-counting them, unable to see them at all.
 *
 * As of Phase 213 plan 08 the pre-fix total, measured by reproducing this
 * file's own scan logic in a standalone Node script (independent of both
 * this file's own vitest runner and the live working tree — it read source
 * via `git show <commit>:<path>` at the phase's starting commit) was
 * **205 hardcoded colour literals across 17 of the 27 audited files**: 67
 * hex, 28 whitespace-HSL, 93 underscore-HSL, 17 comma-HSL. That figure was
 * closer to the eventual truth than D-14's ~188 planning-time hypothesis —
 * the disagreement, and the method used to resolve it, is recorded in
 * `.planning/phases/213-shipped-product-defects/213-COLOUR-COUNT-FINDING.md`.
 * Every one of the 205 has now been tokenised; the same independent
 * instrument, re-run after tokenisation, reports zero. There is no
 * allowlist, no baseline snapshot and no narrowed pattern anywhere in this
 * file or in how the 205 were closed — the assertion below is still the
 * full-strength `toEqual([])`.
 *
 * The whitespace-only predecessor under-reported the true total by more than
 * half (95 of 205 — well under 50%). That is why the `RESIDUAL` guard below
 * re-derives the set of `hsl(`/`hsla(`-opening constructs none of the three
 * named detectors matched, from source, on every run, rather than trusting a
 * written list of forms to stay exhaustive — a written list is exactly what
 * missed the other 110 the first time.
 *
 * HISTORICAL NOTE, kept for readers who find an old citation: this node
 * carried the `.fails` modifier from Phase 206 (plan 206-11, when UAT-7-21
 * was first found failing) until Phase 213 plan 08. While `.fails` was
 * present, a GREEN run meant the OPPOSITE of what green means now — "the
 * dashboard still has hardcoded colours" — and the fix signal was the node
 * going RED with vitest's "Expect test to fail", not green. The `.fails`
 * modifier was chosen over a hard-red node so a documented, expected
 * failure would not take `dashboard-quality.yml` or the UAT citation
 * guard's vitest execution leg down with it. Phase 213 plan 08 proved that
 * RED state verbatim before removing `.fails` — see `213-08-SUMMARY.md`
 * for the captured output — and only then converted this into the plain,
 * honestly-green standing regression guard described above.
 *
 * A known limitation carried over from the `.fails`-modifier era: the
 * module-scope vacuity guards (`AUDITED.length`, the sidebar-presence
 * check, the `RESIDUAL` and `NO_LAUNDERING` throws below) remain at module
 * scope rather than inside the `it(...)` body, because a throw there is a
 * collection error that no wrapper — `it` with `.fails` before, plain `it`
 * now — can silently absorb into a false pass.
 *
 * ---------------------------------------------------------------------------
 * PHASE 215 (RATCHET-03): widened from 27 files (`pages/` + sidebar) to all
 * 76 non-test `.tsx` files under `src/`, via the single derived
 * `auditedFiles()` in `./audited-files` (the local copy formerly here, and
 * its `stripComments()` twin, are deleted — not re-synced). Widening
 * surfaced 11 new hits in the 49 previously-unaudited files, live-measured
 * and reproduced independently during planning:
 *
 *   - 6 are raw `hsl()` literals in `LifecycleEventList.tsx` (2),
 *     `LifecycleEventRow.tsx` (2) and `VendorTrendList.tsx` (2) that
 *     `lifecycle-advisory-guard.test.ts` / `vendor-trend-advisory-guard.test.ts`
 *     PIN as Phase 156/161's deliberate "advisory firewall" — tokenising them
 *     would break those standing guards. These are not debt; they live in
 *     `FOREVER_EXEMPT` below, not the debt baseline.
 *   - 5 are hex literals in `components/ui/chart.tsx` — real, drainable
 *     colour debt. They live in `DEBT_BASELINE` below, a structurally
 *     separate list a later phase is expected to shrink to empty.
 *
 * The two lists are kept apart on purpose: a single list with a `why` field
 * would let a future reader, or a future debt-draining agent, mistake a
 * firewall site for something safe to "fix". Filing deliberate architecture
 * as debt would misreport a correct design as a liability — the exact
 * category error this milestone exists to correct.
 * ---------------------------------------------------------------------------
 */
import { describe, it, expect } from "vitest"
import { readFileSync, existsSync } from "node:fs"
import path from "node:path"
import { contrastRatio, hslToHex } from "./color-contrast-helpers"
import { SRC_ROOT, auditedFiles, stripComments } from "./audited-files"

/**
 * `#rgb` / `#rrggbb` literals, and raw `hsl(N N% N%)` triples in every spelling this codebase
 * actually uses (not `hsl(var(...))`). A single whitespace-only pattern was blind to two of the
 * three real forms — see the module docstring for how that was found and measured.
 */
const HEX_RE = /#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/g
/** `hsl(142 71% 45%)` — literal whitespace between components. */
const RAW_HSL_SPACE_RE = /hsl\(\s*(?!var\()([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\s*\)/g
/** `hsl(142_71%_45%)` — Tailwind arbitrary-value form, underscore-separated, no whitespace. */
const RAW_HSL_UNDERSCORE_RE = /hsl\(\s*(?!var\()([\d.]+)_([\d.]+)%_([\d.]+)%\s*\)/g
/** `hsl(0, 72%, 51%)` — legacy comma-separated form, optional whitespace after each comma. */
const RAW_HSL_COMMA_RE = /hsl\(\s*(?!var\()([\d.]+)\s*,\s*([\d.]+)%\s*,\s*([\d.]+)%\s*\)/g

interface Violation {
  file: string
  line: number
  literal: string
  hex: string
  /** Contrast against the light-theme page background. */
  onLight: number
}

/** Expand `#abc` to `#aabbcc` so the WCAG maths has six digits to read. */
function normaliseHex(literal: string): string {
  const h = literal.slice(1)
  return h.length === 3 ? `#${h[0]}${h[0]}${h[1]}${h[1]}${h[2]}${h[2]}` : `#${h}`
}

function scan(): Violation[] {
  const found: Violation[] = []
  for (const rel of auditedFiles()) {
    const abs = path.join(SRC_ROOT, rel)
    if (!existsSync(abs)) continue
    const lines = stripComments(readFileSync(abs, "utf8")).split("\n")
    lines.forEach((line, i) => {
      for (const m of line.matchAll(HEX_RE)) {
        const hex = normaliseHex(m[0])
        found.push({
          file: rel,
          line: i + 1,
          literal: m[0],
          hex,
          onLight: Number(contrastRatio(hex, "#ffffff").toFixed(2)),
        })
      }
      // All three raw-HSL spellings are resolved to hex through the same
      // hslToHex/contrastRatio path as HEX_RE, so every form is reported in
      // the same units regardless of which literal punctuation produced it.
      for (const re of [RAW_HSL_SPACE_RE, RAW_HSL_UNDERSCORE_RE, RAW_HSL_COMMA_RE]) {
        for (const m of line.matchAll(re)) {
          const hex = hslToHex(Number(m[1]), Number(m[2]), Number(m[3]))
          found.push({
            file: rel,
            line: i + 1,
            literal: m[0],
            hex,
            onLight: Number(contrastRatio(hex, "#ffffff").toFixed(2)),
          })
        }
      }
    })
  }
  return found
}

function format(v: Violation): string {
  // The contrast figure is the point: a hand-set literal keeps its value when
  // the theme flips, so a colour chosen against the dark surface is reported
  // here with the ratio it will actually render at on the light one.
  return `${v.file}:${v.line}  ${v.literal} -> ${v.hex}  (contrast on light bg: ${v.onLight}:1)`
}

// Module-scope vacuity guard. Deliberately NOT inside the it(...) body: a
// throw here is a collection error, which a `.fails`-modified it cannot absorb, so an
// empty or broken glob can never masquerade as "no violations found".
// Phase 215 (RATCHET-03): floors widened from the 27-file `pages/`+sidebar
// era to the 76-file recursive-walk era. Floors, never exact-count
// equalities — D-04, and HARNESS-03 is the standing example of why an exact
// count flakes across macOS vs CI.
const AUDITED = auditedFiles()
if (AUDITED.length < 60) {
  throw new Error(
    `hardcoded-color-audit: only ${AUDITED.length} files resolved — the recursive walk is broken`,
  )
}
if (!AUDITED.includes(path.join("components", "sidebar.tsx"))) {
  throw new Error("hardcoded-color-audit: components/sidebar.tsx is missing from the audited set")
}
if (AUDITED.filter((f) => f.startsWith("pages/")).length < 20) {
  throw new Error(
    `hardcoded-color-audit: only ${AUDITED.filter((f) => f.startsWith("pages/")).length} ` +
      "pages/ files resolved — src/pages/ has far more than that",
  )
}

/**
 * FOREVER_EXEMPT — Phase 215 (RATCHET-03). Widening the audited set from 27
 * to 76 files surfaced 6 raw `hsl()` literals that TWO OTHER guards —
 * `lifecycle-advisory-guard.test.ts` and `vendor-trend-advisory-guard.test.ts`
 * — pin in their own `FORBIDDEN_PALETTE` as Phase 156 (HWLC-11 / D-07) and
 * Phase 161 (HWLC-19)'s deliberate "advisory firewall": the advisory-only
 * hardware-lifecycle and vendor-PQC-trend sections must never visually
 * resemble the app's scored-finding badge language, so these specific hues
 * are barred from ever becoming design tokens the scored UI also draws from.
 * Tokenising any of the six would break that standing guard.
 *
 * These are NOT debt. They live here, structurally separate from
 * `DEBT_BASELINE` below, so a future debt-draining pass (Phase 217/218) can
 * never mistake deliberate architecture for something to fix. Keyed
 * `file|literal` (no line numbers) for the same churn-resistance reasoning
 * as `THEME_INVARIANT` in the sibling theme-token-vocabulary guard.
 */
const FOREVER_EXEMPT: Record<string, { literal: string; guard: string; decision: string; why: string }> = {
  "components/LifecycleEventList.tsx|hsl(180 37% 47%)": {
    literal: "hsl(180 37% 47%)",
    guard: "lifecycle-advisory-guard.test.ts",
    decision: "Phase 156 HWLC-11 / D-07",
    why:
      "lifecycle-advisory-guard.test.ts pins this hue in FORBIDDEN_PALETTE as Phase 156's deliberate " +
      "advisory firewall, so an advisory-only lifecycle badge can never be mistaken for a scored " +
      "finding; tokenising this literal would let the advisory section draw the same colour the " +
      "scored UI uses, breaking that standing guard.",
  },
  "components/LifecycleEventList.tsx|hsl(180_37%_47%)": {
    literal: "hsl(180_37%_47%)",
    guard: "lifecycle-advisory-guard.test.ts",
    decision: "Phase 156 HWLC-11 / D-07",
    why:
      "Same site as the whitespace-form entry above, in its Tailwind arbitrary-value spelling — " +
      "lifecycle-advisory-guard.test.ts's FORBIDDEN_PALETTE bars this hue for the same advisory-firewall " +
      "reason.",
  },
  "components/LifecycleEventRow.tsx|hsl(172_45%_42%)": {
    literal: "hsl(172_45%_42%)",
    guard: "lifecycle-advisory-guard.test.ts",
    decision: "Phase 156 HWLC-11 / D-07",
    why:
      "lifecycle-advisory-guard.test.ts pins this hue in FORBIDDEN_PALETTE as part of the Phase 156 " +
      "advisory firewall protecting the lifecycle event row's advisory-only status colours from " +
      "resembling the app's scored-finding palette.",
  },
  "components/LifecycleEventRow.tsx|hsl(300_45%_55%)": {
    literal: "hsl(300_45%_55%)",
    guard: "lifecycle-advisory-guard.test.ts",
    decision: "Phase 156 HWLC-11 / D-07",
    why:
      "Second lifecycle-event-row status colour pinned by lifecycle-advisory-guard.test.ts's " +
      "FORBIDDEN_PALETTE under the same Phase 156 advisory-firewall rationale.",
  },
  "components/VendorTrendList.tsx|hsl(180 37% 47%)": {
    literal: "hsl(180 37% 47%)",
    guard: "vendor-trend-advisory-guard.test.ts",
    decision: "Phase 161 HWLC-19",
    why:
      "vendor-trend-advisory-guard.test.ts pins this hue in FORBIDDEN_PALETTE as Phase 161's advisory " +
      "firewall (the HWLC-11 precedent applied to the vendor PQC trend section), so this advisory-only " +
      "badge can never visually resemble a scored finding.",
  },
  "components/VendorTrendList.tsx|hsl(180_37%_47%)": {
    literal: "hsl(180_37%_47%)",
    guard: "vendor-trend-advisory-guard.test.ts",
    decision: "Phase 161 HWLC-19",
    why:
      "Same vendor-trend site as the entry above, in its Tailwind arbitrary-value spelling — pinned by " +
      "vendor-trend-advisory-guard.test.ts's FORBIDDEN_PALETTE for the same Phase 161 advisory-firewall " +
      "reason.",
  },
}

/**
 * DEBT_BASELINE — Phase 215 (RATCHET-03). The 5 remaining newly-surfaced
 * hits, all on one line of `components/ui/chart.tsx` (Recharts CSS-selector
 * fallback colours). Unlike FOREVER_EXEMPT above, this is ordinary,
 * DRAINABLE colour debt: nothing requires these specific hex values to stay
 * raw, and a later phase (217/218) is expected to tokenise them and delete
 * these entries. Do NOT move an entry between this list and FOREVER_EXEMPT —
 * they encode two different claims about a site's future.
 */
const DEBT_BASELINE: Record<string, { justification: string }> = {
  "components/ui/chart.tsx|#ccc": {
    justification:
      "Recharts CSS-selector fallback stroke colour (grid/reference-line/polar-grid stroke='#ccc' " +
      "selectors) on a single shared className string; drainable chart-border debt surfaced by " +
      "Phase 215's audit widening, not yet tokenised.",
  },
  "components/ui/chart.tsx|#fff": {
    justification:
      "Recharts CSS-selector fallback stroke colour (dot/sector stroke='#fff' selectors) on the same " +
      "shared className string as the #ccc entries above; drainable chart-border debt surfaced by " +
      "Phase 215's audit widening, not yet tokenised.",
  },
}

/**
 * RESIDUAL guard. The three named HSL detectors above are a hand-derived list
 * of the forms found at planning time — exactly the kind of artefact that has
 * drifted from the real set here repeatedly (see CLAUDE.md's staleness
 * sections). Rather than trust that list to stay exhaustive, this re-derives
 * the set of `hsl(`/`hsla(`-opening constructs (excluding `hsl(var(...))`)
 * that NONE of the three named detectors matched, at run time, on every run.
 * A fourth spelling — or an `hsla()` call — must fail this loudly rather than
 * silently under-reporting the way the underscore and comma forms did before
 * this plan. Module scope, alongside the other vacuity guards, for the same
 * reason: a throw here is a collection error a `.fails`-modified it cannot absorb.
 */
const ALL_HSL_OPEN_RE = /hsla?\(\s*(?!var\()/g
function findResidualSites(): string[] {
  const residual: string[] = []
  for (const rel of AUDITED) {
    const abs = path.join(SRC_ROOT, rel)
    if (!existsSync(abs)) continue
    const lines = stripComments(readFileSync(abs, "utf8")).split("\n")
    lines.forEach((line, i) => {
      const matchedSpans: Array<[number, number]> = []
      for (const re of [RAW_HSL_SPACE_RE, RAW_HSL_UNDERSCORE_RE, RAW_HSL_COMMA_RE]) {
        for (const m of line.matchAll(re)) {
          matchedSpans.push([m.index as number, (m.index as number) + m[0].length])
        }
      }
      for (const m of line.matchAll(ALL_HSL_OPEN_RE)) {
        const start = m.index as number
        const covered = matchedSpans.some(([s, e]) => start >= s && start < e)
        if (!covered) {
          residual.push(`${rel}:${i + 1}  ${line.trim()}`)
        }
      }
    })
  }
  return residual
}

const RESIDUAL = findResidualSites()
if (RESIDUAL.length > 0) {
  throw new Error(
    `hardcoded-color-audit: RESIDUAL colour construct(s) matched by neither RAW_HSL_SPACE_RE, ` +
      `RAW_HSL_UNDERSCORE_RE nor RAW_HSL_COMMA_RE — a spelling this file does not yet detect has ` +
      `appeared and must be added as a fourth named detector:\n${RESIDUAL.join("\n")}`,
  )
}

/**
 * NO_LAUNDERING guard. Plan 213-07 introduces `src/lib/cytoscape-theme.ts` as
 * a shared colour-resolution helper for the three Cytoscape sites. The
 * premise recorded here originally — "the audited set above is `pages/` plus
 * `components/sidebar.tsx`" — is now FALSE: D-03's deferred "widen the
 * audited set to all of `src/`" decision has landed in Phase 215 (RATCHET-03)
 * via `./audited-files`'s recursive walk, and `cytoscape-theme.ts` would now
 * be scanned by `scan()` directly if it were a `.tsx` file. This guard is
 * retained anyway, as belt-and-braces: `cytoscape-theme.ts` is a `.ts` file,
 * not `.tsx`, and `auditedFiles()`'s walk only collects `.tsx`, so it is
 * still outside the general audit and a hex or raw-HSL literal parked there
 * would still leave `scan()` blind to it — the classic laundering move D-05
 * forbids. `existsSync` keeps it inert until 213-07 actually creates the
 * file.
 */
const CYTOSCAPE_THEME_PATH = path.join(SRC_ROOT, "lib", "cytoscape-theme.ts")
if (existsSync(CYTOSCAPE_THEME_PATH)) {
  const themeSrc = stripComments(readFileSync(CYTOSCAPE_THEME_PATH, "utf8"))
  const laundered: string[] = []
  for (const m of themeSrc.matchAll(HEX_RE)) laundered.push(m[0])
  for (const re of [RAW_HSL_SPACE_RE, RAW_HSL_UNDERSCORE_RE, RAW_HSL_COMMA_RE]) {
    for (const m of themeSrc.matchAll(re)) laundered.push(m[0])
  }
  if (laundered.length > 0) {
    throw new Error(
      `hardcoded-color-audit: NO_LAUNDERING — src/lib/cytoscape-theme.ts contains hardcoded ` +
        `colour literal(s) invisible to the pages/-scoped audit: ${laundered.join(", ")}`,
    )
  }
}

describe("UAT-7-21 — hardcoded colour audit (D-A1 source-audit carve-out)", () => {
  it("finds no hardcoded hex or raw hsl color literals in the major dashboard page and shell components", () => {
    // Restated in-test as well as at module scope, per the plan's acceptance
    // criterion that the glob is asserted non-empty before its contents are.
    expect(AUDITED.length).toBeGreaterThan(0)

    const violations = scan()
    const unexempted = violations.filter((v) => {
      const key = `${v.file}|${v.literal}`
      return !(key in FOREVER_EXEMPT) && !(key in DEBT_BASELINE)
    })
    expect(unexempted.map(format)).toEqual([])
  })

  it("FOREVER_EXEMPT and DEBT_BASELINE carry no stale entries — every key still names a live violation", () => {
    // D-09: a stale entry excuses nothing while reading as a live exemption.
    // Run over BOTH structures — a stale forever-exempt entry is as
    // dangerous as a stale debt entry.
    const liveKeys = new Set(scan().map((v) => `${v.file}|${v.literal}`))
    const stale: string[] = []
    for (const key of Object.keys(FOREVER_EXEMPT)) {
      if (!liveKeys.has(key)) {
        stale.push(`FOREVER_EXEMPT lists "${key}", which no longer matches a live violation — delete it`)
      }
    }
    for (const key of Object.keys(DEBT_BASELINE)) {
      if (!liveKeys.has(key)) {
        stale.push(`DEBT_BASELINE lists "${key}", which no longer matches a live violation — delete it`)
      }
    }
    expect(stale).toEqual([])
  })

  it("FOREVER_EXEMPT and DEBT_BASELINE are mutually disjoint — no site is excused twice", () => {
    const both = Object.keys(FOREVER_EXEMPT).filter((key) => key in DEBT_BASELINE)
    expect(both).toEqual([])
  })
})
