/**
 * Shared theme-token resolution for Cytoscape canvas rendering (Phase 213 plan 213-07).
 *
 * Cytoscape draws to a `<canvas>`, which does not participate in the CSS cascade — a
 * `var(--token)` string handed to a Cytoscape style object or `data()` mapper resolves to
 * nothing, not to the token's value (confirmed live, see `exposure-map.tsx`'s own comment
 * trail). Every colour a Cytoscape call site needs must be resolved to a concrete value in JS
 * at graph-build time, and re-resolved whenever the active theme changes.
 *
 * This module intentionally carries NO colour literal of any kind — not even a fallback. The
 * colour audit gate (`hardcoded-color-audit.test.tsx`) scopes its scan to `pages/` +
 * `components/sidebar.tsx`, so a literal parked here would be invisible to that audit and would
 * let a hardcoded colour escape the very scope this phase is measured against (D-05's
 * "no allowlist, no baseline, no narrowing" — a hidden fallback is a baseline in disguise).
 * Plan 213-01's `NO_LAUNDERING` guard fails the build if this file gains a hex or raw-HSL
 * literal. When a token cannot be resolved, this module warns loudly in dev and returns an
 * empty string rather than silently painting the wrong (or no) colour.
 */
import { useEffect, useState } from "react"
import { hslToHex } from "@/components/__tests__/color-contrast-helpers"

/** Matches a raw `H S% L%` custom-property value, e.g. `--status-critical: 0 72% 51%`. */
const HSL_TRIPLE_RE = /^([\d.]+)\s+([\d.]+)%\s+([\d.]+)%$/

/**
 * Resolve a CSS custom property from `document.documentElement` to a value Cytoscape's canvas
 * renderer can actually paint.
 *
 * Two token shapes exist in this codebase's `index.css`:
 *   - The `--ds-*` family stores a concrete resolved hex colour directly — returned as-is.
 *   - Most other tokens (`--status-*`, `--chart-*`, `--qs-node-safe`, `--badge-hardware-device`)
 *     store raw HSL components with no function wrapper, matching Tailwind's own
 *     `hsl(var(--x))` idiom used elsewhere in real DOM. Concatenating those raw components into a
 *     space-separated HSL function-call string and handing it to Cytoscape silently resolves to
 *     BLACK — verified live in `exposure-map.tsx`'s comment trail (2026-09-14: space-separated ->
 *     rgb(0,0,0); comma-separated -> correct; hex -> correct). Rather than rely on remembering the
 *     comma-separated exception, this function converts the HSL triple to hex directly in JS — no
 *     HSL function-call string of any spelling is ever constructed here.
 *
 * Returns an empty string (with a dev-mode console warning naming the token) when the token is
 * missing or resolves empty, so a broken lookup fails loudly rather than painting a silently
 * wrong or absent colour.
 */
export function resolveToken(name: string): string {
  if (typeof document === "undefined") return ""

  const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  if (!raw) {
    if (import.meta.env?.DEV) {
      // eslint-disable-next-line no-console -- deliberate loud failure per plan 213-07 Task 1
      console.warn(`[cytoscape-theme] resolveToken: token "${name}" resolved to an empty value`)
    }
    return ""
  }

  const hslMatch = HSL_TRIPLE_RE.exec(raw)
  if (hslMatch) {
    const [, h, s, l] = hslMatch
    return hslToHex(Number(h), Number(s), Number(l))
  }

  return raw
}

/**
 * Returns a counter that increments whenever `document.documentElement`'s `class` attribute
 * changes, via a `MutationObserver` scoped to that one attribute.
 *
 * `ThemeProvider` toggles a class on `<html>` to switch themes. RESEARCH assumption A2 (reasoned,
 * not verified) is that `ThemeProvider`'s own class-toggle effect is guaranteed to commit before a
 * descendant page's `theme`-dependent effect in the SAME React commit — if that ordering does not
 * hold, a `theme`-dependency-based re-resolution would read the PREVIOUS theme's values on the
 * first toggle, intermittently. A `MutationObserver` fires strictly AFTER the class attribute has
 * actually changed in the DOM, which is exactly the precondition `getComputedStyle` needs — this
 * sidesteps the unverified ordering assumption rather than betting on it (T-213-15: scoped to the
 * `class` attribute only, so an unrelated attribute mutation elsewhere on `<html>` cannot trigger
 * a spurious rebuild).
 */
export function useThemeRevision(): number {
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    if (typeof document === "undefined") return

    const observer = new MutationObserver(() => {
      setRevision((r) => r + 1)
    })
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    })

    return () => observer.disconnect()
  }, [])

  return revision
}
