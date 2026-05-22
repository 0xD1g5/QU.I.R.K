/**
 * Pure helpers for the Executive page, extracted into a non-component module
 * so executive.tsx exports only its component (react-refresh/only-export-components)
 * while these stay independently unit-testable.
 */

/**
 * D-02 (WR-06): Defensive coercion of an unknown response body to a
 * user-facing string. Guards against raw-string bodies, null/undefined,
 * and non-string `detail` fields — never throws on `body.detail` access.
 */
export function coerceErrorDetail(body: unknown): string {
  if (body && typeof body === "object" && typeof (body as {detail?: unknown}).detail === 'string') {
    return (body as { detail: string }).detail
  }
  return String(body ?? "Unknown error")
}
