/**
 * Pure badge-contrast extraction, keying and ratchet evaluation —
 * Phase 215 plan 215-03 (RATCHET-01 / RATCHET-02).
 *
 * Not a `*.test.ts` file, so vitest's include glob
 * (`src/** /__tests__/** /*.{test,spec}.{ts,tsx}`) does not collect it as a
 * suite — same idiom as the sibling `color-contrast-helpers.ts` and
 * `audited-files.ts`.
 *
 * This module performs NO filesystem I/O and imports NO vitest — every
 * export below is a pure function of its arguments, the same architecture
 * `tests/a11y/baseline-diff.mjs` states for itself at its own :5-11 ("all
 * reads and writes stay in run-a11y.mjs. Every export here is a pure
 * function of its arguments"). That purity is not stylistic: plan 215-04's
 * mutation probe drives `evaluatePairs` with synthetic input, and if this
 * module reached into the filesystem that design collapses. All reading
 * (source files, `index.css`, the baseline JSON) lives in
 * `badge-contrast-guard.test.ts` instead.
 *
 * Pair extraction (`extractPairs`) is FILE-WIDE per D-03: any double-quoted
 * string anywhere in a stripped-of-comments source file that pairs an
 * arbitrary-value background token with a text-color utility. It is
 * deliberately NOT scoped to a `QS_BADGE`-style const map the way
 * `cbom-badge-contrast-guard.test.ts`'s private `badgePairs()` is — that
 * narrower parse is the cbom guard's own, kept for its own reasons. The
 * broad, file-wide scan here is what reproduces backlog 999.117's measured
 * table (103 pairs / 45 failing occurrences over 11 files), so narrowing it
 * to `className=` attributes only would silently under-count.
 *
 * The baseline key (`pairKey`) carries NO line numbers, per D-06: Phase 217
 * will shift every line number in these files wholesale while fixing badge
 * contrast, and a line-numbered key would invalidate itself on the very
 * commits this ratchet exists to survive.
 */

/** WCAG 2.1 AA for normal-size text. Badges render at `text-xs` (12px), so the
 * normal-text threshold applies, not the large-text one — same rationale
 * `cbom-badge-contrast-guard.test.ts:58` carries for its own identical constant. */
export const AA_NORMAL_TEXT = 4.5

/** A single background/foreground badge-class pairing found in one source file. */
export interface BadgePair {
  file: string
  bgToken: string
  /** "white" | "black" | "--<token-name>" */
  fgSpec: string
}

/** One evaluated ratchet outcome for a pair in a specific theme. */
export interface Failure {
  key: string
  kind: "new" | "worsened" | "fixed" | "unresolvable"
  ratio: number | null
  detail: string
}

// Matches every double-quoted, single-line string in a source file — deliberately not
// scoped to `className="..."` JSX attributes, so a `cn(...)`-composed string or a
// const-map string value (like cbom.tsx's own `QS_BADGE`) is captured too. This breadth
// is what reproduces 999.117's 103/45 figures; see the module docstring above.
const CLASS_STRING_RE = /"([^"\n]*)"/g

// Arbitrary-value background utility naming a CSS custom property, e.g.
// bg-[ hsl(var(--status-warning)) ] (spaces shown here only to keep this comment
// itself from being scanned as a literal Tailwind candidate by the JIT scanner —
// the real regex below has no such spaces, matching real source exactly).
const BG_TOKEN_RE = /bg-\[hsl\(var\(--([\w-]+)\)\)\]/
const FG_TOKEN_RE = /text-\[hsl\(var\(--([\w-]+)\)\)\]/
const FG_WHITE_RE = /\btext-white\b/
const FG_BLACK_RE = /\btext-black\b/

/**
 * Extract every background/foreground badge pairing from one comment-stripped source
 * file. The caller (the guard) is responsible for calling `stripComments()` first —
 * this function does no stripping itself, keeping it a pure function of its arguments.
 */
export function extractPairs(fileText: string, file: string): BadgePair[] {
  const pairs: BadgePair[] = []
  for (const m of fileText.matchAll(CLASS_STRING_RE)) {
    const classString = m[1]
    const bgMatch = classString.match(BG_TOKEN_RE)
    if (!bgMatch) continue

    let fgSpec: string | null = null
    if (FG_WHITE_RE.test(classString)) {
      fgSpec = "white"
    } else if (FG_BLACK_RE.test(classString)) {
      fgSpec = "black"
    } else {
      const fgMatch = classString.match(FG_TOKEN_RE)
      if (fgMatch) fgSpec = `--${fgMatch[1]}`
    }
    if (!fgSpec) continue

    pairs.push({ file, bgToken: bgMatch[1], fgSpec })
  }
  return pairs
}

/** Churn-resistant baseline key. No line numbers (D-06) — Phase 217 will shift them
 * wholesale while fixing badge contrast. */
export function pairKey(pair: BadgePair, theme: string): string {
  return `${pair.file}|${pair.bgToken}|${pair.fgSpec}|${theme}`
}

function resolveForegroundHex(fgSpec: string, themeTokens: Record<string, string>): string | null {
  if (fgSpec === "white") return "#ffffff"
  if (fgSpec === "black") return "#000000"
  const tokenName = fgSpec.slice(2) // strip leading "--"
  return themeTokens[tokenName] ?? null
}

/**
 * Evaluate every pair, in every theme present in `tokens`, against the baseline. Pure:
 * takes already-resolved hex values, never touches `index.css` or the filesystem.
 *
 * `tokens` shape: theme name -> token name (no leading `--`) -> resolved hex, e.g.
 * `{ dark: { "status-warning": "#9d6607", ... }, light: { ... } }`. `"white"`/`"black"`
 * foregrounds are handled internally as the `#ffffff`/`#000000` constants and do not
 * need entries in `tokens`.
 *
 * `baseline` is keyed by `pairKey(pair, theme)` -> `{ ratio, why }`.
 *
 * Ratchet semantics (D-07), both directions:
 *   - absent from baseline, ratio < AA_NORMAL_TEXT           -> "new" (a fresh violation)
 *   - absent from baseline, ratio >= AA_NORMAL_TEXT           -> no failure
 *   - present, ratio < entry.ratio - 0.01                     -> "worsened" (ceiling broke;
 *     same 0.01 tolerance `cbom-badge-contrast-guard.test.ts:172` uses)
 *   - present, ratio >= AA_NORMAL_TEXT                        -> "fixed" (direction two — the
 *     vitest analogue of `xfail(strict=True)`: good news that demands the entry be deleted,
 *     not a reason to relax the gate)
 *   - present, not worsened, still sub-AA                     -> no failure
 */
export function evaluatePairs(
  pairs: BadgePair[],
  tokens: Record<string, Record<string, string>>,
  baseline: Record<string, { ratio: number; why: string }>,
): Failure[] {
  const failures: Failure[] = []

  for (const pair of pairs) {
    for (const theme of Object.keys(tokens)) {
      const themeTokens = tokens[theme]
      const bgHex = themeTokens[pair.bgToken] ?? null
      const fgHex = resolveForegroundHex(pair.fgSpec, themeTokens)
      const key = pairKey(pair, theme)

      if (bgHex === null || fgHex === null) {
        failures.push({
          key,
          kind: "unresolvable",
          ratio: null,
          detail:
            `${pair.file} (${theme}): could not resolve bg (--${pair.bgToken} -> ` +
            `${bgHex ?? "MISSING"}) or fg (${pair.fgSpec} -> ${fgHex ?? "MISSING"})`,
        })
        continue
      }

      const ratio = contrastRatioOf(bgHex, fgHex)
      const detail = `${pair.file} (${theme}): bg ${bgHex} (--${pair.bgToken}) on fg ${fgHex} = ${ratio.toFixed(2)}:1`
      const entry = baseline[key]

      if (!entry) {
        if (ratio < AA_NORMAL_TEXT) {
          failures.push({ key, kind: "new", ratio, detail: `${detail} — NEW sub-AA pair, not in baseline` })
        }
        continue
      }

      if (ratio < entry.ratio - 0.01) {
        failures.push({
          key,
          kind: "worsened",
          ratio,
          detail: `${detail} — WORSENED below recorded ceiling ${entry.ratio.toFixed(2)}:1. ${entry.why}`,
        })
        continue
      }

      if (ratio >= AA_NORMAL_TEXT) {
        failures.push({
          key,
          kind: "fixed",
          ratio,
          detail: `${detail} — appears FIXED. Delete this baseline entry and let the normal assertion guard it.`,
        })
      }
    }
  }

  return failures
}

/**
 * Local re-implementation of WCAG contrast ratio so this module stays free of any
 * import that could later grow filesystem or vitest dependencies. Mirrors
 * `color-contrast-helpers.ts`'s `contrastRatio`/`luminance` exactly; kept separate
 * (not imported) so `badge-contrast-evaluator.ts` has zero imports at all, the
 * strongest possible form of the "no I/O" guarantee D-17 requires.
 */
function luminanceOf(hex: string): number {
  const h = hex.replace("#", "")
  const channels = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
  const linear = channels.map((c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)))
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
}

function contrastRatioOf(a: string, b: string): number {
  const [hi, lo] = [luminanceOf(a), luminanceOf(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

/**
 * Every baseline key whose `file|bgToken|fgSpec|theme` does not correspond to a live
 * pair/theme combination (D-09). A stale entry excuses nothing while reading as a live
 * exemption, so it must be findable and, per the guard's own suite, rejected.
 */
export function findStaleBaselineKeys(
  baseline: Record<string, { ratio: number; why: string }>,
  livePairs: BadgePair[],
  themes: string[],
): string[] {
  const liveKeys = new Set<string>()
  for (const pair of livePairs) {
    for (const theme of themes) {
      liveKeys.add(pairKey(pair, theme))
    }
  }
  return Object.keys(baseline).filter((key) => !liveKeys.has(key))
}
