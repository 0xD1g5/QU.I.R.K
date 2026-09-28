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
 */
import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync, existsSync } from "node:fs"
import path from "node:path"
import { contrastRatio, hslToHex } from "./color-contrast-helpers"

const SRC_ROOT = path.resolve(__dirname, "../..")

/** The audited set: every page component, plus the shell sidebar. */
function auditedFiles(): string[] {
  const pagesDir = path.join(SRC_ROOT, "pages")
  const pages = readdirSync(pagesDir)
    .filter((f) => f.endsWith(".tsx"))
    .map((f) => path.join("pages", f))
  const sidebar = path.join("components", "sidebar.tsx")
  return [...pages, sidebar].sort()
}

/**
 * Blank out comment bodies so a comment that merely *discusses* a colour is
 * not reported as a violation, while keeping line numbering intact.
 * Line comments are only stripped when `//` opens the line, so a `//` inside
 * a string literal (a URL, say) cannot swallow real code.
 */
function stripComments(src: string): string {
  const noBlocks = src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "))
  return noBlocks
    .split("\n")
    .map((line) => (/^\s*\/\//.test(line) ? "" : line))
    .join("\n")
}

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
const AUDITED = auditedFiles()
if (AUDITED.length === 0) {
  throw new Error("hardcoded-color-audit: the audited file set resolved empty — the glob is broken")
}
if (!AUDITED.includes(path.join("components", "sidebar.tsx"))) {
  throw new Error("hardcoded-color-audit: components/sidebar.tsx is missing from the audited set")
}
if (AUDITED.filter((f) => f.startsWith("pages/")).length < 5) {
  throw new Error(
    `hardcoded-color-audit: only ${AUDITED.length} files resolved — src/pages/ has far more than that`,
  )
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
 * a shared colour-resolution helper for the three Cytoscape sites. Because
 * the audited set above is `pages/` plus `components/sidebar.tsx`, a hex or
 * raw-HSL literal parked in that helper (e.g. as a fallback default) would
 * leave this gate green while the product still ships the literal — the
 * classic laundering move D-05 forbids. This guard names ONE file
 * deliberately; widening the audited SET to all of `src/` is the separate,
 * deferred D-03 decision, not this guard's job. `existsSync` keeps it inert
 * until 213-07 actually creates the file.
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
    expect(violations.map(format)).toEqual([])
  })
})
