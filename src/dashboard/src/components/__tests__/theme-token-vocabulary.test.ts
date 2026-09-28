/**
 * Theme-token vocabulary guard — Phase 213 plan 213-02.
 *
 * Plans 213-03 through 213-07 substitute the 205 hardcoded colour literals
 * `hardcoded-color-audit.test.tsx` finds (see 213-02-SUMMARY.md for the full
 * value-to-token map) with references to the token vocabulary this plan
 * minted in `src/index.css`. A tokenisation that references a custom
 * property which does not actually exist in `index.css` resolves to nothing
 * and renders NO colour at all — silently, with the colour audit gate none
 * the wiser, because the audit only looks for literals, not broken
 * references. This file is the guard against that failure mode, plus the
 * `.light`-parity check D-10 in 213-CONTEXT.md requires.
 *
 * SCOPE IS DERIVED AT RUN TIME, NEVER WRITTEN DOWN — same discipline as
 * `hardcoded-color-audit.test.tsx`'s own module docstring: a hand-maintained
 * list of token names or audited files would silently stop matching the
 * real set. `auditedFiles()` below is copied verbatim from that file (a
 * `readdirSync` of `src/pages/` plus `components/sidebar.tsx`) so both
 * guards agree on what "the dashboard's pages" means.
 *
 * Three properties are asserted:
 *   1. EXISTENCE — every `var(--x)` / `hsl(var(--x))` reference in the
 *      audited pages names a custom property actually defined in
 *      `index.css`.
 *   2. PARITY — every colour-bearing custom property defined in `:root` is
 *      also defined in `.light`, OR is named in the `THEME_INVARIANT` set
 *      below with a one-line reason. The set is NOT a place to silence a
 *      real gap — see the module comment on `THEME_INVARIANT` itself.
 *   3. VACUITY — the parsed `:root` set, the parsed `.light` set, and the
 *      audited page set are each asserted non-empty at collection time (not
 *      inside `it()`), so a regex that stops matching a future `index.css`
 *      refactor cannot report perfect parity over zero tokens.
 */
import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync, existsSync } from "node:fs"
import path from "node:path"

const SRC_ROOT = path.resolve(__dirname, "../..")

/** Copied verbatim from hardcoded-color-audit.test.tsx's auditedFiles(). */
function auditedFiles(): string[] {
  const pagesDir = path.join(SRC_ROOT, "pages")
  const pages = readdirSync(pagesDir)
    .filter((f) => f.endsWith(".tsx"))
    .map((f) => path.join("pages", f))
  const sidebar = path.join("components", "sidebar.tsx")
  return [...pages, sidebar].sort()
}

/** Same comment-stripping logic as hardcoded-color-audit.test.tsx, so a
 * `var(--x)` mentioned only in prose is never treated as a real reference. */
function stripComments(src: string): string {
  const noBlocks = src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "))
  return noBlocks
    .split("\n")
    .map((line) => (/^\s*\/\//.test(line) ? "" : line))
    .join("\n")
}

/** Every `var(--token-name` reference (leading text only — we don't need the
 * fallback argument, just the property name). */
const VAR_REF_RE = /var\(\s*--([a-zA-Z0-9-]+)/g

function extractPropertyBlock(css: string, selectorRe: RegExp): string {
  const m = css.match(selectorRe)
  if (!m) {
    throw new Error(`theme-token-vocabulary: selector ${selectorRe} not found in index.css`)
  }
  return m[1]
}

/** Every `--token-name:` DEFINITION inside a block (not a reference). */
function extractDefinedProps(block: string): Set<string> {
  const props = new Set<string>()
  for (const m of block.matchAll(/(?:^|\n)\s*--([a-zA-Z0-9-]+)\s*:/g)) {
    props.add(m[1])
  }
  return props
}

const CSS_PATH = path.join(SRC_ROOT, "index.css")
const CSS_SRC = readFileSync(CSS_PATH, "utf8")

const ROOT_BLOCK = extractPropertyBlock(CSS_SRC, /:root\s*\{([\s\S]*?)\n {2}\}/)
const LIGHT_BLOCK = extractPropertyBlock(CSS_SRC, /\.light\s*\{([\s\S]*?)\n {2}\}/)

const ROOT_PROPS = extractDefinedProps(ROOT_BLOCK)
const LIGHT_PROPS = extractDefinedProps(LIGHT_BLOCK)

const AUDITED = auditedFiles()

/**
 * Tokens deliberately defined ONLY in `:root`, with a stated reason per
 * entry. Seeded from 213-02-PLAN.md's interfaces block (the tokens that
 * pre-date this plan) plus nothing else — this plan's own newly-minted
 * tokens ALL carry `.light` overrides (see index.css), so no new entries
 * were needed here. Do NOT pad this set to make the test green: a token
 * that should have a light value and does not is a finding to fix in
 * index.css, not to allowlist here.
 */
const THEME_INVARIANT: Record<string, string> = {
  radius: "structural (border-radius), not a colour — parity does not apply",
  "ds-accent-dim": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-accent-bdr": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-critical-dim": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-critical-bdr": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-high-dim": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-high-bdr": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-ok-dim": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-ok-bdr": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-medium-dim": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-medium-bdr": "pre-existing gap, not introduced by Phase 213, see 213-02-SUMMARY",
  "ds-font-mono": "a font-family value, not a colour — parity does not apply",
  "risk-badge-high": "deliberately theme-invariant — a high-visibility risk badge accent, same brand hue in both themes, pre-dates Phase 213",
  "risk-badge-high-foreground": "deliberately theme-invariant — paired foreground for risk-badge-high",
  "qs-node-safe": "deliberately theme-invariant — pre-dates Phase 213, same rationale as risk-badge-high",
  "qs-node-safe-foreground": "deliberately theme-invariant — paired foreground for qs-node-safe",
  "quantum-safe-foreground": "deliberately theme-invariant — Phase 165 Wave 5 fixed contrast in both themes with one dark foreground value",
}

// --- VACUITY (module scope, not inside it(), for the same reason
// hardcoded-color-audit.test.tsx hoists its own vacuity guards: a throw here
// is a collection error, which cannot be silently absorbed). ---
if (AUDITED.length === 0) {
  throw new Error("theme-token-vocabulary: the audited file set resolved empty")
}
if (ROOT_PROPS.size === 0) {
  throw new Error("theme-token-vocabulary: :root parsed zero custom properties")
}
if (LIGHT_PROPS.size === 0) {
  throw new Error("theme-token-vocabulary: .light parsed zero custom properties")
}

describe("theme token vocabulary (Phase 213 UIFIX-02)", () => {
  it("index.css parses a non-trivial :root and .light token set", () => {
    // Restated in-test per this plan's own acceptance criterion, alongside
    // the module-scope throws above.
    expect(ROOT_PROPS.size).toBeGreaterThan(40)
    expect(LIGHT_PROPS.size).toBeGreaterThan(40)
  })

  it("every var(--x) reference in the audited pages names a property defined in index.css", () => {
    const missing: string[] = []
    for (const rel of AUDITED) {
      const abs = path.join(SRC_ROOT, rel)
      if (!existsSync(abs)) continue
      const src = stripComments(readFileSync(abs, "utf8"))
      for (const m of src.matchAll(VAR_REF_RE)) {
        const name = m[1]
        if (!ROOT_PROPS.has(name)) {
          missing.push(`${rel}: var(--${name}) has no matching :root definition in index.css`)
        }
      }
    }
    expect(missing).toEqual([])
  })

  it("every colour-bearing :root property has a .light override or a justified THEME_INVARIANT entry", () => {
    const unjustified: string[] = []
    for (const name of ROOT_PROPS) {
      if (LIGHT_PROPS.has(name)) continue
      const reason = THEME_INVARIANT[name]
      if (!reason || reason.trim().length === 0) {
        unjustified.push(
          `--${name} is defined in :root, missing from .light, and has no THEME_INVARIANT reason`,
        )
      }
    }
    expect(unjustified).toEqual([])
  })

  it("THEME_INVARIANT carries no stale entries — every name it lists still exists and is still root-only", () => {
    const stale: string[] = []
    for (const name of Object.keys(THEME_INVARIANT)) {
      if (!ROOT_PROPS.has(name)) {
        stale.push(`THEME_INVARIANT lists --${name}, which no longer exists in :root`)
        continue
      }
      if (LIGHT_PROPS.has(name)) {
        stale.push(
          `THEME_INVARIANT lists --${name}, but it now has a .light override — remove the entry`,
        )
      }
    }
    expect(stale).toEqual([])
  })

  it("every token this plan minted is present in both :root and .light (not just THEME_INVARIANT-exempt)", () => {
    // A direct, named check on top of the general parity scan above — these
    // are the tokens 213-03..213-07 will actually substitute against, so a
    // regression here is the single most consequential thing this file can
    // miss.
    const minted = [
      "status-critical",
      "status-warning",
      "chart-tls",
      "status-neutral",
      "status-safe-deep",
      "chart-data-at-rest",
      "chart-edge-highlight",
      "badge-hardware-device",
      "badge-modbus",
      "badge-bacnet",
      "badge-schedule",
      "chart-slate-dark",
      "chart-slate-mid",
      "chart-slate-light",
      "chart-node-label",
      "print-bg",
      "print-fg",
      "print-fg-inverse",
      "print-fg-on-light",
      "print-border",
      "print-surface",
      "print-muted",
      "print-critical",
      "print-high",
      "print-medium",
      "print-low",
      "print-neutral",
      "print-safe",
    ]
    const missing: string[] = []
    for (const name of minted) {
      if (!ROOT_PROPS.has(name)) missing.push(`--${name} missing from :root`)
      if (!LIGHT_PROPS.has(name)) missing.push(`--${name} missing from .light`)
    }
    expect(missing).toEqual([])
  })
})
