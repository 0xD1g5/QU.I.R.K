---
type: todo
created: 2026-10-27
source: Phase 234 (D-19; decision record §10)
priority: medium
area: quirk/intelligence/evidence.py (scan_error_count), quirk/intelligence/scoring.py (scan-error term)
status: pending
resolves_phase: null
owner: "999.139"
---

# Closed-port and advisory scan-error rows lower the readiness score

**Owner:** 999.139

`build_evidence_summary` counts every endpoint row that carries a `scan_error`
(`quirk/intelligence/evidence.py:300-302`, `scan_error_count += 1`), including rows whose protocol is `CLOSED`
or `ADVISORY`. Scoring 4.0 reads that count against N_REF = 40, so probing more empty ports lowers the score.
The effect is pre-existing: the 3.0 rate-based term had it too (D-03 did not cause it), and 4.0 falls a little
further because `count / 40` exceeds the 3.0 rate.

Measured on R3 plus N rows with `protocol="CLOSED"`, `scan_error="connection refused"` (record §10, from
`234-residuals.md` §3):

| +closed | scan_error.count | 4.0 emitted/computed (hygiene) | 3.0 emitted/computed (hygiene) |
|---------|------------------|--------------------------------|--------------------------------|
| 0 | 0 | 46/85 (22) | 46/85 (22) |
| 20 | 20 | 43/80 (18) | 45/83 (20) |
| 100 | 100 | 42/78 (16) | 43/80 (18) |
| 300 | 300 | 42/78 (16) | 43/79 (17) |

On the real estate (scan `2026-09-14T14:25:49.899977+00:00`) the scan-error rows are 308 CLOSED, 23 ADVISORY and
4 TLS, 335 in all (Phase 234 RESEARCH, open question 6), so nearly all of the term comes from ports with nothing
listening.

## Proposed fix shape

Count only assessable scan errors (a service was reached or expected and the probe failed), excluding `CLOSED`
and `ADVISORY` rows, either in `evidence.py` or as a separate `assessable_scan_error_count` that the scorer
reads. This changes scores, so it needs a scoring-version note and a ladder re-measurement with the P2b
instrument (`python -m scripts.p2b_instrument`), and the closed form in `scripts/p2b_closed_form.py` must change
first (spec-first, as in Phase 234).

## Feasibility & Effort

**CONFIRMED** by the measurement above. Effort **S** for the code; the re-measurement and version note are the
larger part.
