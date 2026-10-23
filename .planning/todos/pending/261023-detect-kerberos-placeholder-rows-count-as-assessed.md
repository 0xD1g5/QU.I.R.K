---
type: todo
created: 2026-10-23
source: Phase 230 DETECT-02 (plan 230-02, D-25; orchestrator decision on the 230-02 plan-check warning)
priority: medium
area: quirk/intelligence/scoring.py (_identity_assessed), quirk/intelligence/evidence.py (assessed_crypto_count), quirk/intelligence/confidence.py (coverage_ratio)
status: pending
resolves_phase: null
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

- [ ] Decide: placeholder rows excluded from `assessed_crypto_count` and from `_identity_assessed`, or counted with a coverage flag.
- [ ] Update the pinned test and `docs/report-interpretation.md` / operators guide Kerberos paragraphs (230-05 documents both side effects).

## Feasibility & Effort

- **CONFIRMED**: observed values pinned by the test above; lines `scoring.py:367-370`, `evidence.py:288-291`.
- **LIKELY** effort **S** for the exclusion (a protocol-specific `service_detail` check in two places) but it moves scores,
  so it is a SCORING_VERSION and ladder question: it belongs inside the P2b work, not a standalone patch.
- **UNKNOWN**: how many golden fixtures or ladder rungs carry a Kerberos placeholder (none found in 230-04's fixture grep for bearer; not grepped for Kerberos).
- **Spike**: no; fold into the Phase 233 measurement.
