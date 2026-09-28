import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, join } from "node:path"

/**
 * Cytoscape draws to <canvas> with its OWN color parser. It does not understand
 * the modern space-separated `hsl(H S% L%)` syntax, and several of this app's
 * design tokens (`--accent`, `--primary`, ...) are stored as RAW COMPONENTS
 * ("180 37% 47%") for Tailwind's benefit. Building `hsl(${...})` from one of
 * those therefore produces a string Cytoscape silently resolves to BLACK.
 *
 * Measured live 2026-09-14 against the running dashboard:
 *
 *   hsl(180 37% 47%)    -> rgb(0,0,0)        <- what the code was passing
 *   hsl(180, 37%, 47%)  -> rgb(76,164,164)
 *   #4ba8a8             -> rgb(75,168,168)   <- the --ds-accent hex token
 *
 * The crown-jewel ring had been broken this way since Phase 195 and nobody saw
 * it, because no scan had ever set `is_crown_jewel: true` — 195-06 recorded the
 * badge as an honest GAP for exactly that reason, so it shipped having never
 * rendered once. `node:selected` shared the same variable and was equally
 * black.
 *
 * UPDATED Phase 213 plan 213-07: this file's own local `cssVar(name) ||
 * "#fallback"` helper (the pattern this suite originally guarded) is gone.
 * Colours now resolve through the shared `resolveToken()` in
 * `src/lib/cytoscape-theme.ts`, which is intentionally FALLBACK-FREE — a hex
 * fallback parked here would itself be a literal in an audited file (D-05),
 * invisible to the pages/-scoped colour-audit gate. `resolveToken()` warns
 * loudly in dev and returns "" instead. This suite now asserts the absence of
 * any local fallback/cssVar helper rather than its presence.
 *
 * A rendering assertion cannot catch this in jsdom — there is no canvas and no
 * Cytoscape color parser — so this guard reads the source instead. It is
 * deliberately a source scan rather than a list of known-bad lines: it
 * regenerates its occurrence set from the file on every run.
 */
const HERE = dirname(fileURLToPath(import.meta.url))
const SOURCE = join(HERE, "..", "exposure-map.tsx")

/**
 * Strip comments before scanning. The first version of this guard matched the
 * explanatory comment in exposure-map.tsx that *describes* the bad pattern, and
 * failed on prose rather than on code — the same false-positive shape this repo
 * has hit before with placeholder greps that match text asserting the absence
 * of placeholders. A guard that fires on its own documentation trains people to
 * ignore it.
 */
function stripComments(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/.*$/gm, "$1")
}

describe("exposure-map Cytoscape colors", () => {
  const src = stripComments(readFileSync(SOURCE, "utf8"))

  it("never builds an hsl() string from a CSS variable for Cytoscape", () => {
    // Matches `hsl(${...})` in any spacing. Cytoscape cannot parse the
    // space-separated form these tokens produce.
    const offenders = src.match(/hsl\(\s*\$\{/g) ?? []
    expect(
      offenders,
      "Cytoscape cannot parse space-separated hsl(). Use a HEX design token " +
        "(e.g. cssVar('--ds-accent')) instead — see this file's module comment.",
    ).toEqual([])
  })

  it("reads its colors from hex --ds-* tokens via the shared resolveToken helper", () => {
    // The five colors fed into the Cytoscape style spec.
    for (const token of [
      "--ds-accent",
      "--ds-high",
      "--ds-medium",
      "--ds-critical",
      "--ds-bg-elevated",
    ]) {
      expect(src, `expected ${token} to be read via resolveToken()`).toContain(
        `resolveToken("${token}")`,
      )
    }
  })

  it("carries no local cssVar helper or hex fallback beside a token read", () => {
    // A fallback here would be a colour literal in an audited file, invisible
    // to the pages/-scoped colour-audit gate (D-05) — the exact anti-pattern
    // this suite used to require. resolveToken() itself is deliberately
    // fallback-free (see src/lib/cytoscape-theme.ts); this file must not
    // reintroduce a local escape hatch around that.
    expect(src, "exposure-map.tsx must not define its own cssVar() helper").not.toMatch(
      /const cssVar\s*=/,
    )
    const fallbackReads = src.match(/resolveToken\("--[a-z-]+"\)\s*\|\|\s*"([^"]*)"/g) ?? []
    expect(
      fallbackReads,
      "a resolveToken() call must not carry a literal hex/colour fallback",
    ).toEqual([])
  })
})
