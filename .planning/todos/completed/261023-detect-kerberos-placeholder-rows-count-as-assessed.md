---
type: todo
created: 2026-10-23
source: Phase 230 DETECT-02 (plan 230-02, D-25; orchestrator decision on the 230-02 plan-check warning)
priority: medium
area: quirk/intelligence/scoring.py (_identity_assessed), quirk/intelligence/evidence.py (assessed_crypto_count), quirk/intelligence/confidence.py (coverage_ratio)
status: completed
resolves_phase: 234
resolved: 2026-10-27
owner: "999.120"
---

# Kerberos placeholder rows count as assessed crypto and as identity presence

A Kerberos row that carries no etypes and no `scan_error` is a placeholder: the pre-existing `kerberos-no-preauth`, and
Phase 230's `kerberos-etypes-unavailable-principal-unknown`. Two scoring effects follow, and neither is introduced
by Phase 230 (D-25's "no penalty" is respected: no finding, no weak-etype count):

1. **Identity presence.** The row adds a `KERBEROS` entry to the protocol counts, so
   `quirk/intelligence/scoring.py::_identity_assessed` (`:367-370`, true when any identity protocol count is positive)
   is true. `identity_trust` can then score clean in the headline for a KDC whose crypto was never assessed.
2. **Coverage.** `quirk/intelligence/evidence.py:288-291` increments `assessable_endpoint_count` and
   `assessed_crypto_count` for any non-UNKNOWN protocol without a `scan_error`, so the placeholder raises the
   `coverage_ratio` that `quirk/intelligence/confidence.py` weights at 0.35 (`:7`), reading as coverage for
   an unassessed KDC.

Both are PINNED, not endorsed, by
`tests/test_kerberos_probe_principal_config.py::test_principal_unknown_row_counts_as_assessed_pinned`
(observed 2026-10-23 in plan 230-02: `assessed_crypto_count == 1`, `assessable_endpoint_count == 1`,
`_identity_assessed(...) is True`).

Owner: 999.120 (P2b scan-depth dilution, the row ROADMAP Phases 233 and 234 implement). It should be resolved before or
in Phase 233 so the P2b ladder is not measured on a model that counts unassessed KDCs as assessed. Changing the
behaviour must update the pinned test in the same commit. 999.120 is OPEN and accepts members (read 2026-10-23; it is
the P1 operator-reserved row, so the owner choice here is a recommendation the operator may re-home to 999.131
"score inputs and evidence counters").

- [x] Decide: placeholder rows excluded from `assessed_crypto_count` and from `_identity_assessed`, or counted with a coverage flag.
- [x] Update the pinned test and `docs/report-interpretation.md` / operators guide Kerberos paragraphs (230-05 documents both side effects).

## Feasibility & Effort

- **CONFIRMED**: observed values pinned by the test above; lines `scoring.py:367-370`, `evidence.py:288-291`.
- **LIKELY** effort **S** for the exclusion (a protocol-specific `service_detail` check in two places) but it moves scores,
  so it is a SCORING_VERSION and ladder question: it belongs inside the P2b work, not a standalone patch.
- **UNKNOWN**: how many golden fixtures or ladder rungs carry a Kerberos placeholder (none found in 230-04's fixture grep for bearer; not grepped for Kerberos).
- **Spike**: no; fold into the Phase 233 measurement.

## Phase 233 note (2026-10-27)

None of the five calibration rungs (R1-R5) carries a Kerberos placeholder row. In the Phase 233 row rebuild,
every rung's KERBEROS row has a real etype detail. `tests/test_p2b_instrument.py::test_healthy_rows_are_healthy`
asserts this, and asserts that the row exists, so the check is not vacuous. So the P2b measurement was not taken on
a model that counts an unassessed KDC as assessed.

This todo is **not fixed in Phase 233**: changing the behaviour moves scores, and Phase 233 was measurement-only
(D-15). The wording above, "before or in Phase 233", now means **Phase 234**. Record:
`.planning/decisions/233-p2b-third-instrument-measurement.md` §12.

## Resolution (2026-10-27, Phase 234 plan 234-03, D-11)

Resolved in the scoring 4.0 commit (Phase 234, SCORE-09), which shares the `SCORING_VERSION` bump as D-11 requires.
The decision is **exclusion**, not a coverage flag:

- `quirk/intelligence/evidence.py`: a `KERBEROS` row with no `scan_error` and no `etype:` in `service_detail` is a
  placeholder. It is counted in the new `kerberos_placeholder_count` (evidence schema 1.3.0), stays in
  `assessable_endpoint_count` (the KDC answered), and is excluded from `assessed_crypto_count`. The check was made
  against every `CryptoEndpoint(protocol="KERBEROS", ...)` in `quirk/scanner/kerberos_scanner.py`: the real per-etype
  rows always carry `etype:{id}:{name}:{severity}`, and the placeholders (`kerberos-no-preauth`,
  `kerberos-etypes-unavailable-principal-unknown`, `kerberos-etypes-unavailable-preauth-no-etype-info`, and
  `kerberos-unreachable` when no TCP error was recorded) never do. The rows that carry a `scan_error` were already
  excluded from assessed crypto.
- `quirk/intelligence/scoring.py`: `_identity_assessed(cert_obs, protocol_counts, placeholders=...)` subtracts the
  placeholder count from `KERBEROS` (floored at 0), so a placeholder-only KDC no longer makes `identity_trust` assessed.
  `protocol_counts` is not edited (reports, CBOM and the dashboard read it).
- The pinned test inverted, so it was **renamed** (D-26):
  `tests/test_kerberos_probe_principal_config.py::test_principal_unknown_row_counts_as_assessed_pinned` ->
  `tests/test_kerberos_probe_principal_config.py::test_principal_unknown_placeholder_row_is_not_assessed`. It now
  asserts `assessed_crypto_count == 0`, `assessable_endpoint_count == 1`, `kerberos_placeholder_count == 1` and
  `_identity_assessed(..., placeholders=...) is False`.
- Every citation of the old name moved in the same commit: `docs/UAT-SERIES.md` UAT-230-07 `**Notes:**` (Notes only;
  no `**Result:**` change) and the `.planning/HORIZON.md` 999.120 row. Plan 234-08 cites the commit sha when it closes
  999.120.
- Not done here: the `docs/report-interpretation.md` / operators guide Kerberos paragraphs (230-05 documents the two
  old side effects). They belong to the Phase 234 doc pass (D-17, plan 234-07), whose plan text does not name them
  as of 2026-10-27; flagged in `234-03-SUMMARY.md` so the doc pass picks them up.
