// D-08 (WR-09): RFC-2253-aware Distinguished Name parsing for cert Subject/Issuer display.
//
// The legacy inline regex `CN=([^,]+)` truncates CNs containing escaped commas
// (e.g., `CN=Smith\, John,O=Acme` → `Smith\`). RFC-2253 escapes a literal
// comma inside an attribute value with a leading backslash. The regex below
// captures either a non-comma-non-backslash character OR a backslash followed
// by any single character, terminating at an unescaped comma or end-of-string.
// Post-processing strips the backslashes from `\<char>` sequences to recover
// the literal value.

const CN_RE = /CN=((?:[^,\\]|\\.)*)(,|$)/

/**
 * Extract the CN value from an RFC-2253 Distinguished Name string.
 *
 * - Returns `'—'` for null / undefined / empty input.
 * - Returns the input verbatim when no `CN=` segment is present.
 * - Correctly handles escaped commas (`\,`) and escaped backslashes (`\\`).
 */
export function extractCN(dn: string | null | undefined): string {
  if (!dn) return "—"
  const m = dn.match(CN_RE)
  if (!m) return dn
  return m[1].replace(/\\(.)/g, "$1")
}

/**
 * Parse the CN slot from a Distinguished Name into a structured record.
 * Currently exposes only the CN slot; broader DN parsing is deferred per
 * D-12 / RESEARCH Open Q2 (no consumer yet requires O / OU / etc.).
 */
export function parseDistinguishedName(dn: string | null | undefined): Record<string, string> {
  const cn = extractCN(dn)
  return { CN: cn }
}
