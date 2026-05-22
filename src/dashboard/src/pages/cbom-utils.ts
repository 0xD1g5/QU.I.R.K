/**
 * Pure helpers for the CBOM page, extracted into a non-component module so
 * cbom.tsx exports only its component (react-refresh/only-export-components)
 * while these stay independently unit-testable.
 */

// D-27 (IN-05): representative selector for `compByAlg[alg]` lookups.
// Returns the first component with a non-zero `count` (when the shape
// carries one), falling back to the first entry to preserve the existing
// "any representative" semantic (Researcher recommendation; O(1) at call site).
// Signature is generic-permissive so callers can pass arrays of shapes
// that may or may not carry a `count` field — CbomComponent lacks one and
// falls through to [0], matching the pre-D-27 behavior exactly.
export function firstNonZeroComp<T>(comps: T[] | undefined): T | undefined {
  if (!comps || comps.length === 0) return undefined
  return (
    comps.find((c) => {
      const n = (c as { count?: number }).count
      return typeof n === "number" && n > 0
    }) ?? comps[0]
  )
}
