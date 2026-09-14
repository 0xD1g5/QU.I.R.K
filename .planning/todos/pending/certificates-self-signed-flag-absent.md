---
type: todo
created: 2026-09-13
source: phase-206 plan 05 (COV-04); filed at plan 206-05 close
priority: low
requirement: none (UAT-7-10 partial-coverage input, not itself a requirement)
---

# `certificates.tsx` has no self-signed-certificate flag — UAT-7-10's fourth Pass Criterion is unmet

`docs/UAT-SERIES.md`'s UAT-7-10 ("Certificates Page — Inventory Table") lists "Self-signed certs
flagged" as one of four Pass Criteria bullets. Discovered while writing this case's new vitest
coverage (`src/dashboard/src/pages/__tests__/certificates-inventory-table.test.tsx`,
206-05-SUMMARY.md): reading `certificates.tsx` in full shows no comparison of `cert_subject` against
`cert_issuer` (the standard self-signed definition — a cert is self-signed when its issuer equals
its own subject), no dedicated flag, badge, icon, or column for it anywhere in the component. This
is a second, independently-discovered absent feature alongside UAT-7-12 (tracked separately in
`certificates-expiry-sort-absent.md`) — found by this plan, not by RESEARCH.md, which only flagged
the sort gap.

## Why this matters

Self-signed certificates are a meaningfully different risk profile from CA-issued ones (no chain of
trust, cannot be revoked via CRL/OCSP) — flagging them is a genuine operator-facing signal this
case expects, not cosmetic. Without it, a self-signed cert renders identically to any other row in
the inventory table.

## What a real fix would look like

Compute `const selfSigned = cert.cert_subject && cert.cert_subject === cert.cert_issuer` per row
(after CN-extraction normalization, since raw DN strings may differ in unrelated attributes like
serial-embedded fields while representing the same self-signed relationship — the exact equality
semantics need a design decision, not just a literal string compare) and render an indicator (badge
or icon) in the Issuer or Subject CN cell when true. Consider whether the `cert_subject ==
cert_issuer` heuristic is a reliable enough proxy for true self-signedness, or whether the backend
scanner already has better signal (e.g. from certificate chain length during the TLS handshake)
that should be surfaced as a dedicated API field instead of re-derived client-side.

## Acceptance (for whoever picks this up)

- A defined self-signed detection rule (backend-computed field preferred over client-side DN
  string comparison, to avoid false negatives/positives from DN formatting quirks).
- A visible indicator in the certificates inventory table for self-signed certs.
- A vitest test (extending `certificates-inventory-table.test.tsx` or adding a sibling) asserting
  the indicator appears on self-signed rows and not on CA-issued ones.
- Once built, UAT-7-10 can be re-dispositioned from partial-PASS to full PASS citing the extended
  test.
