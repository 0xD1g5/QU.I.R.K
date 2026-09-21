/**
 * Shared WCAG colour maths for the dashboard's style-audit tests.
 *
 * Not a `*.test.ts` file, so vitest's include glob
 * (`src/** /__tests__/** /*.{test,spec}.{ts,tsx}`) does not collect it as a
 * suite — it is a plain module that the guards import.
 *
 * Extracted in Phase 206 plan 206-11. Before this, `luminance()`,
 * `contrastRatio()` and `hslToHex()` existed as TWO byte-identical copies, in
 * `muted-token-contrast-guard.test.ts` and `executive-tooltip-contrast-guard.
 * test.ts`. 206-11 needed them a third time for the UAT-7-21 audit; a third
 * copy would have been the point at which the set started to drift, so the
 * copies were collapsed here instead.
 */

/** Relative luminance per WCAG 2.1 §Relative luminance. */
export function luminance(hex: string): number {
  const h = hex.replace("#", "")
  const channels = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255)
  const linear = channels.map((c) =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4),
  )
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
}

/** Contrast ratio per WCAG 2.1 §Contrast ratio. */
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

/** Minimal HSL→hex, sufficient for the token values in index.css. */
export function hslToHex(h: number, s: number, l: number): string {
  const sN = s / 100
  const lN = l / 100
  const c = (1 - Math.abs(2 * lN - 1)) * sN
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = lN - c / 2
  const seg = Math.floor(h / 60) % 6
  const [r, g, b] = [
    [c, x, 0],
    [x, c, 0],
    [0, c, x],
    [0, x, c],
    [x, 0, c],
    [c, 0, x],
  ][seg]
  const toHex = (v: number) =>
    Math.round((v + m) * 255)
      .toString(16)
      .padStart(2, "0")
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`
}
