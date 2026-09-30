/**
 * Foreground-derivation guard for roadmap.tsx's two runtime-`style=`
 * detail-panel badges — Phase 218 plan 218-02 (D-07(1)).
 *
 * WHAT THIS PROTECTS. `roadmap.tsx`'s phase badge (`:345`) and closure-state
 * badge (`:352-355`) set their BACKGROUND at runtime via
 * `style={{ background: PHASE_COLORS[selected.phase] }}` /
 * `CLOSURE_STATE_COLOR[selected.closure_state]`. Because that background is
 * a real-DOM inline style, not a static Tailwind class,
 * `badge-contrast-evaluator.ts`'s `BG_TOKEN_RE` (`bg-\[hsl\(var\(--…\)\)\]`)
 * structurally cannot see it — RATCHET-01 is blind to this site by
 * construction, not by oversight. Before this fix both badges paired that
 * runtime background with a STATIC `text-white` class. The 218 planner
 * re-derived every (key, theme) pair (not just the one the P1 todo named):
 * `--status-warning` (NEXT / resurfaced) fails white at 2.13:1 dark;
 * `--status-critical`, `--qs-node-safe` and `--status-neutral` all clear
 * white in both themes. The fix derives the text colour from the SAME map
 * key as the background (`PHASE_FG` / `CLOSURE_STATE_FG`, mirroring
 * `PHASE_TOKEN`/`CLOSURE_STATE_TOKEN`), so a future key added to one map
 * without a matching entry in the other is caught mechanically rather than
 * shipping a silently-white-on-fail badge.
 *
 * SCOPE IS DERIVED AT RUN TIME. Every map (`PHASE_TOKEN`, `PHASE_FG`,
 * `CLOSURE_STATE_TOKEN`, `CLOSURE_STATE_FG`) and every token value is parsed
 * straight out of `roadmap.tsx` and `index.css` on every run, never copied
 * into this file as a hand-maintained literal. The module-scope vacuity
 * checks below throw if any map fails to parse or parses to zero keys, per
 * this project's repeated "a hand-maintained list drifts from the real set"
 * lesson (CLAUDE.md, multiple sections). An unresolvable FG literal is a
 * hard failure here too, never silently skipped.
 *
 * NEVER WRITE AN INTACT ARBITRARY-VALUE CLASS IN THIS FILE. Tailwind's JIT
 * scanner does a static regex pass over raw source text, including comments
 * and string literals, across every file the `content` glob covers,
 * including this directory. This file writes no `bg-[` / `text-[` needle —
 * the sites under test use runtime `style=` and plain `text-white`, not
 * arbitrary-value classes, so none is needed.
 */
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import path from "node:path"
import { contrastRatio, themeBlocks, resolveToken } from "./color-contrast-helpers"

const SRC_ROOT = path.resolve(__dirname, "../..")
const css = readFileSync(path.join(SRC_ROOT, "index.css"), "utf8")
const roadmap = readFileSync(path.join(SRC_ROOT, "pages/roadmap.tsx"), "utf8")

/** WCAG 2.1 AA for normal-size text. */
const AA_NORMAL_TEXT = 4.5

const { dark, light } = themeBlocks(css)

/**
 * Parse `const NAME: Record<string, string> = { key: "value", ... }` out of
 * roadmap.tsx source text. Throws if the const is not found or parses to
 * zero keys — this is the vacuity guard: a rename or refactor that moves
 * this map must fail loudly, not silently protect nothing.
 */
function extractMap(name: string): Record<string, string> {
  const declRe = new RegExp(`const ${name}:\\s*Record<string,\\s*string>\\s*=\\s*\\{([\\s\\S]*?)\\n\\}`)
  const m = roadmap.match(declRe)
  if (!m) {
    throw new Error(`roadmap-badge-foreground-guard: could not find 'const ${name}: Record<string, string> = {...}' in roadmap.tsx — the guard is vacuous`)
  }
  const body = m[1]
  const entries: Record<string, string> = {}
  const entryRe = /(\w+):\s*"([^"]+)"/g
  for (const em of body.matchAll(entryRe)) {
    entries[em[1]] = em[2]
  }
  if (Object.keys(entries).length === 0) {
    throw new Error(`roadmap-badge-foreground-guard: '${name}' parsed to zero keys — the guard is vacuous`)
  }
  return entries
}

const PHASE_TOKEN = extractMap("PHASE_TOKEN")
const PHASE_FG = extractMap("PHASE_FG")
const CLOSURE_STATE_TOKEN = extractMap("CLOSURE_STATE_TOKEN")
const CLOSURE_STATE_FG = extractMap("CLOSURE_STATE_FG")

/** Resolve a background token name (e.g. "--status-warning") to hex for a theme. */
function resolveBgToken(tokenDecl: string, block: string): string {
  const token = tokenDecl.replace(/^--/, "")
  const hex = resolveToken(token, block, dark)
  if (!hex) {
    throw new Error(`roadmap-badge-foreground-guard: background token --${token} unresolvable`)
  }
  return hex
}

/** Resolve an FG map value — a "white"/"#ffffff" literal or an `hsl(var(--x))` reference — to hex. */
function resolveFgValue(fgValue: string, block: string): string {
  if (fgValue === "white" || fgValue.toLowerCase() === "#ffffff") return "#ffffff"
  if (fgValue === "black" || fgValue.toLowerCase() === "#000000") return "#000000"
  const m = fgValue.match(/^hsl\(var\(--([\w-]+)\)\)$/)
  if (m) {
    const hex = resolveToken(m[1], block, dark)
    if (!hex) {
      throw new Error(`roadmap-badge-foreground-guard: FG token --${m[1]} unresolvable`)
    }
    return hex
  }
  throw new Error(`roadmap-badge-foreground-guard: unrecognized FG literal '${fgValue}' — never silently skipped`)
}

// Fallback pair: both badges fall back to --status-neutral background when
// the lookup key is missing, per `?? "hsl(var(--status-neutral))"` in the
// source. The FG fallback is parsed from the badges' own `?? "..."` literal
// rather than hand-copied.
const BG_FALLBACK_MATCH = roadmap.match(/background:\s*PHASE_COLORS\[selected\.phase\]\s*\?\?\s*"([^"]+)"/)
const PHASE_FG_FALLBACK_MATCH = roadmap.match(/color:\s*PHASE_FG\[selected\.phase\]\s*\?\?\s*"([^"]+)"/)
const CLOSURE_FG_FALLBACK_MATCH = roadmap.match(/color:\s*CLOSURE_STATE_FG\[selected\.closure_state\]\s*\?\?\s*"([^"]+)"/)

if (!BG_FALLBACK_MATCH) {
  throw new Error("roadmap-badge-foreground-guard: could not find the PHASE_COLORS background fallback literal — the guard is vacuous")
}
if (!PHASE_FG_FALLBACK_MATCH) {
  throw new Error("roadmap-badge-foreground-guard: could not find the PHASE_FG foreground fallback literal — the guard is vacuous")
}
if (!CLOSURE_FG_FALLBACK_MATCH) {
  throw new Error("roadmap-badge-foreground-guard: could not find the CLOSURE_STATE_FG foreground fallback literal — the guard is vacuous")
}

const BG_FALLBACK_TOKEN_MATCH = BG_FALLBACK_MATCH[1].match(/--([\w-]+)/)
if (!BG_FALLBACK_TOKEN_MATCH) {
  throw new Error("roadmap-badge-foreground-guard: background fallback literal is not an hsl(var(--x)) reference — the guard is vacuous")
}
const BG_FALLBACK_TOKEN = `--${BG_FALLBACK_TOKEN_MATCH[1]}`
const PHASE_FG_FALLBACK = PHASE_FG_FALLBACK_MATCH[1]
const CLOSURE_FG_FALLBACK = CLOSURE_FG_FALLBACK_MATCH[1]

describe("roadmap detail-panel badge foreground guard (Phase 218 D-07(1))", () => {
  it("PHASE_FG and CLOSURE_STATE_FG cover exactly the keys of their background token maps", () => {
    expect(Object.keys(PHASE_FG).sort()).toEqual(Object.keys(PHASE_TOKEN).sort())
    expect(Object.keys(CLOSURE_STATE_FG).sort()).toEqual(Object.keys(CLOSURE_STATE_TOKEN).sort())
  })

  it("every roadmap badge foreground clears AA on its own background in both themes", () => {
    const ratios: string[] = []
    const allPairs: Array<{ label: string; bgTokenDecl: string; fg: string }> = [
      ...Object.keys(PHASE_TOKEN).map((k) => ({ label: `PHASE.${k}`, bgTokenDecl: PHASE_TOKEN[k], fg: PHASE_FG[k] })),
      ...Object.keys(CLOSURE_STATE_TOKEN).map((k) => ({ label: `CLOSURE.${k}`, bgTokenDecl: CLOSURE_STATE_TOKEN[k], fg: CLOSURE_STATE_FG[k] })),
      { label: "PHASE.fallback", bgTokenDecl: BG_FALLBACK_TOKEN, fg: PHASE_FG_FALLBACK },
      { label: "CLOSURE.fallback", bgTokenDecl: BG_FALLBACK_TOKEN, fg: CLOSURE_FG_FALLBACK },
    ]

    for (const theme of ["dark", "light"] as const) {
      const block = theme === "dark" ? dark : light
      for (const pair of allPairs) {
        const bgHex = resolveBgToken(pair.bgTokenDecl, block)
        const fgHex = resolveFgValue(pair.fg, block)
        const ratio = contrastRatio(fgHex, bgHex)
        ratios.push(`${pair.label} (${theme}): fg=${fgHex} bg=${bgHex} -> ${ratio.toFixed(2)}:1`)
        expect(
          ratio,
          `${pair.label} (${theme}): fg=${pair.fg} (${fgHex}) on bg=${pair.bgTokenDecl} (${bgHex}) = ${ratio.toFixed(2)}:1`,
        ).toBeGreaterThanOrEqual(AA_NORMAL_TEXT)
      }
    }
    console.log("roadmap-badge-foreground-guard ratio table:\n" + ratios.join("\n"))
  })

  it("both detail-panel badges take their text colour from the FG map, not a static class", () => {
    expect(roadmap.includes("color: PHASE_FG[")).toBe(true)
    expect(roadmap.includes("color: CLOSURE_STATE_FG[")).toBe(true)

    const phaseBadgeIdx = roadmap.indexOf("color: PHASE_FG[")
    const phaseWindowStart = roadmap.lastIndexOf("<Badge", phaseBadgeIdx)
    const phaseWindow = roadmap.slice(phaseWindowStart, phaseBadgeIdx + 200)
    expect(phaseWindow.includes("text-white"), "phase badge className still contains text-white").toBe(false)

    const closureBadgeIdx = roadmap.indexOf("color: CLOSURE_STATE_FG[")
    const closureWindowStart = roadmap.lastIndexOf("<Badge", closureBadgeIdx)
    const closureWindow = roadmap.slice(closureWindowStart, closureBadgeIdx + 200)
    expect(closureWindow.includes("text-white"), "closure badge className still contains text-white").toBe(false)
  })
})
