// 221 D-04/D-05: pure render-state guard for the a11y fixture variant sweeps. No filesystem
// I/O and no test-runner import, same discipline as baseline-diff.mjs, so it can be driven
// with synthetic input by variant-guard-probe.test.ts.
//
// This is a RENDER-STATE check (is the marker element on the page?), never a baseline-equality
// check: after Phases 217/218 most routes legitimately have `entries: 0` in every variant, so a
// "(rule,count) sets differ across variants" guard would be vacuous.

export const DEFAULT_LOADING_SELECTOR = '.animate-pulse'
// 221 WR-02: positive witness for the `empty` leg, symmetric with the loading skeleton. Emitted by
// EmptyStateCard and by the plain-text page-level empty branches (executive/trends/roadmap); never
// by an error branch, so "every marker absent" from a crash or an error string does not pass.
export const DEFAULT_EMPTY_SELECTOR = '[data-testid="empty-state"]'

// 221 WR-12: the witness count the empty leg requires. Shared by the guard and by the harness's
// wait, so run-a11y.mjs waits for exactly the count this guard will demand (not for the first
// witness, which on a multi-panel route like /hardware appears before its siblings).
export function emptyWitnessesNeeded(markers) {
  return Math.max(1, Object.keys(markers ?? {}).length)
}

/**
 * @param {object} args
 * @param {string} args.variant   'default' | 'empty' | 'loading'
 * @param {string} args.slug      route slug (for messages)
 * @param {Record<string,string>} args.markers  handlerId -> CSS selector
 * @param {Record<string,boolean>} args.present selector -> found on the page
 * @param {boolean} [args.skeleton]  loading only: loading skeleton selector found
 * @param {string} [args.loadingSelector]
 * @param {number} [args.emptyWitnesses]  empty only: how many empty-state witnesses were found
 * @param {string} [args.emptySelector]
 * @returns {string[]} violations, each starting with `render state [<slug>/<variant>]:`
 */
export function renderStateViolations({
  variant,
  slug,
  markers,
  present,
  skeleton,
  loadingSelector = DEFAULT_LOADING_SELECTOR,
  emptyWitnesses,
  emptySelector = DEFAULT_EMPTY_SELECTOR,
}) {
  const out = []
  const prefix = `render state [${slug}/${variant}]:`
  const entries = Object.entries(markers ?? {})
  const seen = present ?? {}
  for (const [handler, selector] of entries) {
    const isPresent = seen[selector] === true
    if (variant === 'default') {
      if (!isPresent) {
        out.push(
          `${prefix} marker "${selector}" (${handler}) is ABSENT under default — a marker never present in default proves nothing by being absent in empty/loading`,
        )
      }
    } else if (variant === 'empty' || variant === 'loading') {
      if (isPresent) {
        out.push(
          `${prefix} marker "${selector}" (${handler}) is present — the ${variant} fixture did not take effect (wrong or stale server?)`,
        )
      }
    }
  }
  // 221 WR-02: one empty-state witness per marked endpoint (a /hardware drift panel stuck in its
  // error branch leaves 2 of 3 witnesses and fails, instead of passing as "absent").
  const needEmpty = emptyWitnessesNeeded(markers)
  if (variant === 'empty' && !(Number.isFinite(emptyWitnesses) && emptyWitnesses >= needEmpty)) {
    out.push(
      `${prefix} found ${Number.isFinite(emptyWitnesses) ? emptyWitnesses : 'no'} empty-state witness(es) "${emptySelector}", need ${needEmpty} (one per marked endpoint) — no proof the empty fixture rendered an empty state`,
    )
  }
  if (variant === 'loading' && skeleton !== true) {
    out.push(`${prefix} loading skeleton "${loadingSelector}" not found — no proof the page was caught mid-load`)
  }
  return out
}
