/**
 * Pure badge-style-map extraction and disposition-coverage set comparison —
 * Phase 216 plan 216-02 (HARNESS-02 / D-08).
 *
 * This module performs NO filesystem I/O and imports NO vitest — every
 * export is a pure function of its arguments, the same architecture
 * `tests/a11y/baseline-diff.mjs` and `src/components/__tests__/
 * badge-contrast-evaluator.ts` both state for themselves. Purity is what
 * lets a future mutation probe (the Phase 215 RATCHET-04 idiom) drive
 * `extractBadgeMaps`/`dispositionCoverage` with hand-built synthetic source
 * text instead of a real `.tsx` file. All reading (globbing `src/pages/*.tsx`,
 * the fixture, the disposition ledger) lives in
 * `badge-variant-coverage.test.ts` instead.
 *
 * `extractBadgeMaps` intentionally does NOT special-case which map names to
 * look for — 216-VALIDATION.md's anti-tautology falsifier 2 requires this
 * to be a real, generic parse of `const NAME: Record<string, string> = {...}`
 * declarations, filtered only by whether the object literal's values look
 * like a Tailwind badge background/foreground pairing
 * (`bg-[hsl(var(--...`). That value-shaped filter is what excludes
 * `TIER_ORDER` (a `Record<string, number>`) and `METHOD_LABEL` (a
 * `Record<string, string>` whose values are plain labels, not badge
 * classes) without ever naming either constant.
 */

/**
 * Extract every badge-style-map declaration from a single file's source text.
 *
 * @param {string} sourceText
 * @returns {{ name: string, keys: string[] }[]}
 */
export function extractBadgeMaps(sourceText) {
  const maps = []
  // Matches `const NAME: Record<string, string> = { ...body... }` where the
  // body is captured non-greedily up to a closing brace that starts its own
  // line — every real badge map in this codebase is a flat object literal
  // with no nested braces in its values, so this bound is safe and avoids
  // needing a full parser.
  const declRe = /const\s+([A-Za-z_$][\w$]*)\s*:\s*Record<\s*string\s*,\s*string\s*>\s*=\s*\{([\s\S]*?)\n\}/g
  let match
  while ((match = declRe.exec(sourceText)) !== null) {
    const [, name, body] = match
    // A badge-style map's values pair a Tailwind arbitrary-value HSL
    // background token with a text-color utility. Anything else (a plain
    // label map, an ordering map) is excluded by this value shape, not by name.
    if (!body.includes("bg-[hsl(var(--")) continue
    maps.push({ name, keys: extractKeys(body) })
  }
  return maps
}

/**
 * Extract the object-literal keys from a captured map body. Handles BOTH
 * quoted keys (`"Tier 1":`) and bare identifier keys (`Safe:` in
 * certificates.tsx's QS_BADGE) — a regex that only handled quoted keys would
 * silently under-read QS_BADGE to a subset of its real keys.
 *
 * @param {string} body
 * @returns {string[]}
 */
function extractKeys(body) {
  const keys = []
  const keyRe = /^\s*(?:"([^"]*)"|'([^']*)'|([A-Za-z_$][\w$]*))\s*:/gm
  let match
  while ((match = keyRe.exec(body)) !== null) {
    keys.push(match[1] ?? match[2] ?? match[3])
  }
  return keys
}

/**
 * Pure set comparison between what was discovered in source, what the
 * disposition ledger claims, and what the fixture actually reaches.
 * This function does NOT decide what is acceptable (e.g. which uncovered
 * keys are legitimately unreachable) — that disposition lives in the test
 * file, which owns an explicit `UNREACHABLE` allowlist with written reasons.
 *
 * @param {object} args
 * @param {{ file: string, name: string, keys: string[] }[]} args.maps
 *   every discovered map, tagged with the file it was found in.
 * @param {Record<string, unknown>} args.ledger
 *   keyed `"<file>:<MAP_NAME>"`.
 * @param {Record<string, string[]>} args.observedKeysByMap
 *   keyed `"<file>:<MAP_NAME>"` -> the keys the fixture actually reaches for
 *   that map, mechanically derived (raw field values, or derived-label
 *   function output).
 * `uncoveredKeys` is the raw, undecided set of `<file>:<MAP_NAME>:<key>`
 * strings for every discovered, dispositioned map key the fixture did not
 * reach. This function deliberately does NOT split that set into "real bug"
 * vs "known dead map key" — that acceptability judgment is the test file's
 * job (it partitions `uncoveredKeys` against its own in-test `UNREACHABLE`
 * allowlist). Keeping that judgment out of this pure module is what keeps
 * it probeable with synthetic input and free of any "acceptable" opinion.
 *
 * @returns {{
 *   uncoveredKeys: string[],
 *   undispositionedMaps: string[],
 *   orphanedLedgerRows: string[],
 * }}
 */
export function dispositionCoverage({ maps, ledger, observedKeysByMap }) {
  const undispositionedMaps = []
  const uncoveredKeys = []

  const discoveredMapIds = new Set()

  for (const map of maps) {
    const id = `${map.file}:${map.name}`
    discoveredMapIds.add(id)
    if (!(id in ledger)) {
      undispositionedMaps.push(id)
      continue
    }
    const observed = new Set(observedKeysByMap[id] ?? [])
    for (const key of map.keys) {
      if (!observed.has(key)) {
        uncoveredKeys.push(`${id}:${key}`)
      }
    }
  }

  const orphanedLedgerRows = Object.keys(ledger).filter((id) => !discoveredMapIds.has(id))

  return { uncoveredKeys, undispositionedMaps, orphanedLedgerRows }
}
