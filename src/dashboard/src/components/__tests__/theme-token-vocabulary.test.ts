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
 * real set. Both guards now import the SAME single derived file set from
 * `./audited-files` (Phase 215 RATCHET-03) rather than each keeping their
 * own copy of `auditedFiles()` — the duplicate this file used to carry (a
 * `readdirSync` of `src/pages/` plus `components/sidebar.tsx`, with a
 * comment describing it as a duplicate of the sibling guard's own function)
 * is what this phase deleted, comment and all. The set now covers all 76
 * non-test `.tsx` files under `src/`, not 27 pages.
 *
 * Four properties are asserted:
 *   1. EXISTENCE — every `var(--x)` / `hsl(var(--x))` reference in the
 *      audited files names a custom property actually defined in
 *      `index.css`, OR its name matches a prefix in `EXTERNAL_VAR_NAMESPACES`
 *      below (Radix-injected runtime custom properties that are absent from
 *      `index.css` by construction and can never be drained).
 *   2. PARITY — every colour-bearing custom property defined in `:root` is
 *      also defined in `.light`, OR is named in the `THEME_INVARIANT` set
 *      below with a one-line reason. The set is NOT a place to silence a
 *      real gap — see the module comment on `THEME_INVARIANT` itself.
 *   3. VACUITY — the parsed `:root` set, the parsed `.light` set, and the
 *      audited file set are each asserted non-empty at collection time (not
 *      inside `it()`), so a regex that stops matching a future `index.css`
 *      refactor cannot report perfect parity over zero tokens.
 *   4. NO STALE EXEMPTIONS — both `THEME_INVARIANT` and
 *      `EXTERNAL_VAR_NAMESPACES` are checked at run time to still name a
 *      live site; a stale entry excuses nothing while reading as a live
 *      exemption (D-09).
 */
import { describe, it, expect } from "vitest"
import { readFileSync, existsSync } from "node:fs"
import path from "node:path"
import { SRC_ROOT, auditedFiles, stripComments } from "./audited-files"

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

/**
 * EXTERNAL_VAR_NAMESPACES — Phase 215 (RATCHET-03). Widening the audited set
 * to 76 files surfaced 2 EXISTENCE misses, both `var(--radix-select-trigger-*)`
 * references in `components/ui/select.tsx`. These are CSS custom properties
 * Radix UI injects at RUNTIME (element-measured trigger height/width); they
 * are, by construction, absent from `index.css` and always will be, so they
 * can never be drained by declaring a token for them — unlike a real missing
 * reference, which is a bug to fix.
 *
 * Structurally SEPARATE from `THEME_INVARIANT` above: that set is about
 * `:root`/`.light` PARITY for tokens that DO exist in `index.css`; this one
 * is about REFERENCES to properties that will never exist in `index.css` at
 * all. Conflating the two would let a future reader silence a real
 * missing-token bug by adding it to this namespace list instead. Keyed by
 * var-name PREFIX (not full name, not file|literal) — `radix-` covers every
 * `--radix-*` property Radix's primitives inject, present or future, without
 * needing an entry per property.
 */
const EXTERNAL_VAR_NAMESPACES: Record<string, string> = {
  "radix-": "Radix UI injects --radix-* custom properties at RUNTIME (e.g. measured trigger " +
    "height/width); application code legitimately reads them via var(--radix-...), they are by " +
    "construction absent from index.css, and this is a permanent property of the Radix primitives, " +
    "not debt to drain.",
}

// --- VACUITY (module scope, not inside it(), for the same reason
// hardcoded-color-audit.test.tsx hoists its own vacuity guards: a throw here
// is a collection error, which cannot be silently absorbed). Phase 215
// (RATCHET-03): floor widened from the 27-file era to the 76-file era, never
// an exact count (D-04). ---
if (AUDITED.length < 60) {
  throw new Error(
    `theme-token-vocabulary: only ${AUDITED.length} files resolved — the recursive walk is broken`,
  )
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
        if (ROOT_PROPS.has(name)) continue
        const exempt = Object.keys(EXTERNAL_VAR_NAMESPACES).some((prefix) => name.startsWith(prefix))
        if (exempt) continue
        missing.push(`${rel}: var(--${name}) has no matching :root definition in index.css`)
      }
    }
    expect(missing).toEqual([])
  })

  it("EXTERNAL_VAR_NAMESPACES carries no stale entries — every prefix still matches a live reference", () => {
    // D-09, modelled on the THEME_INVARIANT stale check below: a prefix
    // matching nothing excuses nothing while reading as a live exemption.
    const liveNames = new Set<string>()
    for (const rel of AUDITED) {
      const abs = path.join(SRC_ROOT, rel)
      if (!existsSync(abs)) continue
      const src = stripComments(readFileSync(abs, "utf8"))
      for (const m of src.matchAll(VAR_REF_RE)) liveNames.add(m[1])
    }
    const stale: string[] = []
    for (const prefix of Object.keys(EXTERNAL_VAR_NAMESPACES)) {
      const matches = [...liveNames].some((name) => name.startsWith(prefix))
      if (!matches) {
        stale.push(
          `EXTERNAL_VAR_NAMESPACES lists prefix "${prefix}", which matches no live var(--...) reference — remove it`,
        )
      }
    }
    expect(stale).toEqual([])
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
      "status-warning-foreground",
      "chart-tls",
      "chart-tls-foreground",
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
