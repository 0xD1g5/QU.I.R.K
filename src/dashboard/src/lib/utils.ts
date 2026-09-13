import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Phase 201-fix (201-UI-C2/E1): the UI-SPEC's locked copywriting contract
// ("N is always a plain integer or one-decimal float ... if the delta is
// fractional, render with one decimal: `+4.2 pts`") — used for the per-item
// score-lift badge and the projected-aggregate stat on BOTH the dashboard
// (roadmap.tsx) and print (print.tsx) surfaces so they cannot diverge.
// Whole numbers render with zero decimals (`4`, not `4.0`); any fractional
// value renders with exactly one decimal (`4.2`), matching the existing
// score display convention post-Phase-199's `Optional[float]` widening.
export function formatScoreNumber(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}
