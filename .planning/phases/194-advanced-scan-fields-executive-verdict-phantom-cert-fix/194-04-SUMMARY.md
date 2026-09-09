---
phase: 194
plan: 04
subsystem: dashboard
tags: [dashboard, certificates, print-pdf, coverage-honesty, DASH-09]
requires:
  - 194-01 (backend: excluded_cert_count field, phantom-cert filter)
provides:
  - "certificates.tsx and print.tsx disclose excluded TLS endpoint counts and show the locked D-14 empty state"
affects:
  - "src/dashboard/src/pages/certificates.tsx"
  - "src/dashboard/src/pages/print.tsx"
tech-stack:
  added: []
  patterns:
    - "honest-absence / coverage-disclosure rendering (Phase 188 SCORE-06 precedent)"
key-files:
  created:
    - src/dashboard/src/pages/__tests__/certificates-phantom-disclosure.test.tsx
    - src/dashboard/src/pages/__tests__/print-cert-disclosure.test.tsx
  modified:
    - src/dashboard/src/pages/certificates.tsx
    - src/dashboard/src/pages/print.tsx
    - quirk/dashboard/static/index.html
    - quirk/dashboard/static/assets/index-r4aZ6eLJ.js
decisions:
  - "EmptyStateCard's single message prop takes only the locked D-14 heading; the longer follow-up sentence ('— verify scan targets include HTTPS or TLS services.') moved to a sibling <p> so the locked phrase stays greppable verbatim rather than concatenated into one string."
  - "PrintCerts was exported (was module-private, like PrintFindings/PrintCbom) so its test file can render the real component directly instead of round-tripping through PrintPage's full data-fetch mocking."
metrics:
  duration: "~35 minutes"
  completed: 2026-09-09
---

# Phase 194 Plan 04: Phantom-Cert Disclosure & Empty-State Fix Summary

Both certificate surfaces (the dashboard `certificates.tsx` page and the `/print` PDF's
`PrintCerts`) now read the server's authoritative `excluded_cert_count` and render an honest
disclosure line ("N TLS endpoints failed handshake and are not shown.") whenever endpoints were
excluded, and both show the D-14-locked empty state ("No TLS certificates discovered in this
scan") even when every TLS endpoint failed handshake — closing the exact 2026-09-05 scenario (5
phantoms, 0 real certs) that previously suppressed the empty state on both surfaces.

## What Was Built

### Task 1 — Certificate inventory page (`certificates.tsx`)

Read `const excluded = data?.excluded_cert_count ?? 0` directly from the `useScanData()` payload
— no client-side re-filtering of `certs` (verified: `grep -c "filter(" certificates.tsx` returns
`0`). A `disclosure` fragment renders `{excluded} TLS endpoints failed handshake and are not
shown.` in small `--ds-medium` (`text-xs text-muted-foreground`) text when `excluded > 0`, placed
directly below the page heading and above the `Table` — matching the Phase 192
`coverage_disclosure` placement precedent (`executive.tsx:413-415`).

The empty-state early return was restructured so the disclosure line survives it: when
`certs.length === 0`, the page now renders the heading, then the disclosure line (if any), then
`EmptyStateCard`. Because `EmptyStateCard` only accepts a single `message` prop, the locked D-14
heading (`"No TLS certificates discovered in this scan"`) is passed as that prop verbatim, and
the existing longer follow-up sentence (`"— verify scan targets include HTTPS or TLS services."`)
is rendered as a sibling `<p>` beneath it rather than concatenated into one string — so the
locked phrase stays byte-greppable on its own line.

New test file `certificates-phantom-disclosure.test.tsx` (4 tests, all passing) covers: (a) 3
certs + `excluded_cert_count: 2` → table renders and the disclosure reads exactly `"2 TLS
endpoints failed handshake and are not shown."`; (b) 3 certs + `excluded_cert_count: 0` → no
disclosure text anywhere; (c) 0 certs + `excluded_cert_count: 5` (the live 2026-09-05 scenario)
→ both the empty-state text and the disclosure line render; (d) 0 certs + `excluded_cert_count:
0` → empty state with no disclosure line.

### Task 2 — `/print` PDF surface (`print.tsx`)

`PrintCerts`'s signature changed to `{ certs, excludedCount }: { certs: CertItem[]; excludedCount:
number }`, threaded from the call site as `excludedCount={data.excluded_cert_count}` — `data` (the
full `ScanLatestResponse`) was already in scope in `PrintPage` alongside the `certificates` array
it destructures, so no new fetch was needed.

The previous `if (!certs.length) return <p className="meta">No TLS endpoints found.</p>` — a
second, independently-worded empty-state claim that disagreed with `certificates.tsx`'s own copy
— was replaced with the identical D-14 wording (`"No TLS certificates discovered in this scan."`,
period included to match the file's existing `.meta` sentence-punctuation convention) plus the
disclosure line when `excludedCount > 0`. When certs are present and `excludedCount > 0`, the
disclosure line renders above the table, using the byte-identical phrase `"TLS endpoints failed
handshake and are not shown."` (the interpolated count variable name differs — `excludedCount` vs.
`excluded` — but the locked string literal is identical across both files).

`PrintCerts` was changed from module-private to `export function PrintCerts` (matching neither
`PrintFindings` nor `PrintCbom`, which stay private — this is a deliberate, documented deviation,
see below) so its new test file can render the real component directly with fixture props instead
of mocking the entire `PrintPage` data-fetch chain the way `print-pdf-cleanup.test.tsx` does.

New test file `print-cert-disclosure.test.tsx` (4 tests, all passing) mirrors
`certificates-phantom-disclosure.test.tsx`'s four fixture combinations and asserts the identical
copy strings render — the explicit cross-surface consistency guard D-13 requires.

Table markup, column set, `qs-` badge classes, and `formatDateOnly` usage were left untouched.

### Full-suite verification

`npm run build && npm run lint && npm run test` all exit 0: build succeeds (2442 modules,
dashboard statics rebuilt and committed per CLAUDE.md's dashboard-build rule), lint reports 0
errors (1 pre-existing unrelated warning in `ConnectorsPanel.test.tsx`), and the full vitest suite
is 43 files / 304 tests, all green (up from 41 files / 296 tests before this plan — the +2 files /
+8 tests are this plan's own two new test files).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking issue] `PrintCerts` had to be exported to satisfy the plan's own test
requirement**
- **Found during:** Task 2
- **Issue:** The plan's `<action>` instructs "Create ... rendering `PrintCerts` directly," but
  `PrintCerts` (like `PrintFindings`/`PrintCbom`) was a module-private function with no export,
  making direct rendering impossible without either an export or a full-`PrintPage` mock round-trip
  (the heavier pattern `print-pdf-cleanup.test.tsx` uses, which the plan's `read_first` list did
  NOT cite for this task).
- **Fix:** Added `export` to `PrintCerts`'s declaration with an inline comment explaining why it
  differs from its module-private siblings.
- **Files modified:** `src/dashboard/src/pages/print.tsx`
- **Commit:** `041cbb4f`

No other deviations — the rest of the plan executed as written.

## Known Stubs

None. Both surfaces read live data from the existing `ScanLatestResponse` payload; no hardcoded
empty values or placeholder text were introduced.

## Threat Flags

None. Both changes render only an integer count (`excluded_cert_count`) that was already added to
the payload schema by plan 194-01 — no new network endpoints, auth paths, or trust-boundary
changes were introduced by this plan.

## Self-Check: PASSED

- FOUND: `src/dashboard/src/pages/certificates.tsx`
- FOUND: `src/dashboard/src/pages/print.tsx`
- FOUND: `src/dashboard/src/pages/__tests__/certificates-phantom-disclosure.test.tsx`
- FOUND: `src/dashboard/src/pages/__tests__/print-cert-disclosure.test.tsx`
- FOUND commit `64e074d8` (Task 1)
- FOUND commit `041cbb4f` (Task 2)
