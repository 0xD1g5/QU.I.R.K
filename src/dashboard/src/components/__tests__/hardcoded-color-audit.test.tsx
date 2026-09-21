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
 * THIS NODE IS `it.fails` BECAUSE UAT-7-21 CURRENTLY FAILS. READ THIS BEFORE
 * CITING IT.
 * ---------------------------------------------------------------------------
 * As of 2026-09-21 the audit finds 95 hardcoded colour literals across 10 of
 * the audited files. The detector below is NOT weakened to accommodate them:
 * there is no allowlist, no baseline snapshot and no narrowed pattern. The
 * assertion is the full-strength `toEqual([])`, and it genuinely fails.
 *
 * `it.fails` records that verdict instead of hiding it. The alternative —
 * committing a hard-red node — would take `dashboard-quality.yml` and the UAT
 * citation guard's vitest execution leg down with it, which would obscure the
 * finding rather than publish it.
 *
 * Consequences a reader must not get wrong:
 *   - UAT-7-21's recommended disposition is FAIL, not PASS. A green run of
 *     this node means "the dashboard still has hardcoded colours", which is
 *     the opposite of the case passing.
 *   - The day someone fixes the product, this node goes RED with vitest's
 *     "Expect test to fail" — that is the signal to delete `.fails` here and
 *     re-disposition UAT-7-21 to PASS. It is not a regression.
 *   - Known limitation of the `it.fails` shape: a future break in the
 *     preconditions inside the test body would also be absorbed. The
 *     vacuity guard is therefore hoisted to module scope below, where a
 *     throw surfaces as a collection error `it.fails` cannot swallow.
 *   - To read the live violation inventory, change `it.fails` to `it` and
 *     run the file; the failure diff lists every site.
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

/** `#rgb` / `#rrggbb` literals, and raw `hsl(N N% N%)` triples (not `hsl(var(...))`). */
const HEX_RE = /#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/g
const RAW_HSL_RE = /hsl\(\s*(?!var\()([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\s*\)/g

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
      for (const m of line.matchAll(RAW_HSL_RE)) {
        // Resolved to hex so a raw triple is reported in the same units as a
        // hex literal — this is why the shared hslToHex/contrastRatio helpers
        // are reused here rather than re-derived.
        const hex = hslToHex(Number(m[1]), Number(m[2]), Number(m[3]))
        found.push({
          file: rel,
          line: i + 1,
          literal: m[0],
          hex,
          onLight: Number(contrastRatio(hex, "#ffffff").toFixed(2)),
        })
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

// Module-scope vacuity guard. Deliberately NOT inside the it.fails body: a
// throw here is a collection error, which `it.fails` cannot absorb, so an
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

describe("UAT-7-21 — hardcoded colour audit (D-A1 source-audit carve-out)", () => {
  it.fails("finds no hardcoded hex or raw hsl color literals in the major dashboard page and shell components", () => {
    // Restated in-test as well as at module scope, per the plan's acceptance
    // criterion that the glob is asserted non-empty before its contents are.
    expect(AUDITED.length).toBeGreaterThan(0)

    const violations = scan()
    expect(violations.map(format)).toEqual([])
  })
})
