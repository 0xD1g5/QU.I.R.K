// 221 D-04/D-05: pure render-state guard for the a11y fixture variant sweeps. No filesystem
// I/O and no test-runner import, same discipline as baseline-diff.mjs, so it can be driven
// with synthetic input by variant-guard-probe.test.ts.
//
// This is a RENDER-STATE check (is the marker element on the page?), never a baseline-equality
// check: after Phases 217/218 most routes legitimately have `entries: 0` in every variant, so a
// "(rule,count) sets differ across variants" guard would be vacuous.

export const DEFAULT_LOADING_SELECTOR = '.animate-pulse'
// 221 WR-02/WR-13: positive witness for the `empty` leg, symmetric with the loading skeleton,
// BOUND TO AN ENDPOINT. A witness is `[data-a11y-empty="<handler-id>"]`, emitted only by a call
// site that names the handler whose empty response it proves (EmptyStateCard's `emptyFor`, or the
// plain-text page-level empty branches of executive/trends/roadmap). A page-wide "N empty cards"
// count could be satisfied by another panel while the marked endpoint's own panel sat in its
// error branch; a per-endpoint witness cannot. variant-contract.test.ts enforces that no witness
// is emitted on a branch whose condition mentions an error.
export function emptyWitnessSelector(handlerId) {
  return `[data-a11y-empty="${handlerId}"]`
}

// 221 WR-12/WR-13: the witnesses the empty leg requires: exactly one selector per marked
// endpoint. Shared by the guard and the harness's condition wait, so the harness waits for
// exactly what this guard will demand.
export function requiredEmptyWitnesses(markers) {
  return Object.fromEntries(Object.keys(markers ?? {}).map(id => [id, emptyWitnessSelector(id)]))
}

/**
 * @param {object} args
 * @param {string} args.variant   'default' | 'empty' | 'loading'
 * @param {string} args.slug      route slug (for messages)
 * @param {Record<string,string>} args.markers  handlerId -> CSS selector
 * @param {Record<string,boolean>} args.present selector -> found on the page
 * @param {boolean} [args.skeleton]  loading only: loading skeleton selector found
 * @param {string} [args.loadingSelector]
 * @param {Record<string,number>} [args.emptyWitnesses]  empty only: handlerId -> witnesses found
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
  // 221 WR-02/WR-13: one witness PER MARKED ENDPOINT, bound by handler id (a /hardware drift
  // panel stuck in its error branch emits no `hardware-drift` witness and fails by name, however
  // many other empty cards the page renders).
  if (variant === 'empty') {
    if (entries.length === 0) {
      out.push(`${prefix} no marked endpoint to witness — the empty leg cannot prove an empty state`)
    }
    const found = emptyWitnesses ?? {}
    for (const [handler, sel] of Object.entries(requiredEmptyWitnesses(markers))) {
      const n = found[handler]
      if (!(Number.isFinite(n) && n >= 1)) {
        out.push(
          `${prefix} no empty-state witness "${sel}" for marked endpoint ${handler} (found ${Number.isFinite(n) ? n : 'none'}) — no proof that endpoint's empty fixture rendered an empty state`,
        )
      }
    }
  }
  if (variant === 'loading' && skeleton !== true) {
    out.push(`${prefix} loading skeleton "${loadingSelector}" not found — no proof the page was caught mid-load`)
  }
  return out
}
