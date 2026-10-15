---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS (fork B4); ledger rows DCL-OPS-B-0412, B-0416, B-0430, B-0432, B-0434, B-0435, B-0444 (docs/operators-guide.md §15-§16)
priority: high
area: quirk/intelligence/remediation_persist.py, quirk/intelligence/closure.py, quirk/intelligence/burndown.py, quirk/intelligence/scope_signature.py (_PROTOCOL_TO_FAMILY)
status: pending
resolves_phase: 229
owner: FIND-11
---

# Closure state model: `open` is never written, detected findings read `not_observed`, closures land on the prior scan, and plaintext HTTP can never close

End-to-end probe with the production writers
(`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc2-ops-b4-closure-states-probe.py` and its `-tls`
variant): scan 1 finds an issue on 8 hosts, scan 2 rechecks all 8 and finds it on 7; scope signatures identical,
every probe family healthy.

```
HTTP variant:  closure counters {'refused_probe': 1, 'unchanged': 7}; family_for_protocol('HTTP') -> None
               scan1 states {'not_observed': 8}; scan2 states {'not_observed': 7}
TLS variant:   closure counters {'closed': 1, 'unchanged': 7}
               scan1 states {'not_observed': 7, 'closed': 1}; scan2 states {'not_observed': 7}
both:          burndown(latest scan) open 0, closed 0, not_observed 7
```

1. `persist_remediation_snapshot` writes every detected finding as `DEFAULT_ITEM_STATE = "not_observed"`
   (`quirk/intelligence/remediation.py:136`, `remediation_persist.py:155`, `:267`). No code anywhere writes `"open"`
   (grep for state assignments: only `closure.py:364` closed, `:413` resurfaced, `:451` item closed). So a finding
   the scan FOUND reads "Not Verified" in the report burndown, the CBOM VEX (`in_triage`) and the roadmap badge.
2. `compute_closure` writes `closed` onto the PRIOR scan's rows (`closure.py:321-364`). Reports and the dashboard
   compute the burndown for the CURRENT scan (`quirk/reports/writer.py:175-194`, `routes/scan.py:1345`), which has no
   row for the fixed finding, so `closed` never appears in the latest scan's burndown.
3. `family_for_protocol` has no entry for `HTTP` (or `AMQP`/`KAFKA`/`REDIS` bare protocols); plaintext HTTP findings
   are raised on `protocol == "HTTP"` endpoints (`quirk/engine/findings_evaluator.py:538-543`), so
   `probe_family_status` returns `not_run` and `plaintext-http-exposure` (the docs' own example) can never close.
4. The test suite masks (1): `tests/test_closure_verification.py::_seed_two_scans` seeds the prior row as
   `state="open"` by hand (line ~67), a state production never writes.

The operators-guide §15-§16 now describes this behaviour honestly. The product behaviour defeats the feature's
stated purpose (CLOSE-01/SURF-02: "6 of 8 verified closed" on the report).

- [ ] Decide the state model: set detected current-scan rows to `open` (at persist or in compute_closure when
      comparable), and decide whether closures should be carried onto the current scan (e.g. a closed row/event
      the burndown counts) so the latest report shows them.
- [ ] Give `HTTP` (and bare broker protocols) a probe family, or document plaintext items as non-closable.
- [ ] Replace the hand-seeded `open` in `_seed_two_scans` with rows written by `persist_remediation_snapshot`.
- [ ] Revisit operators-guide §15-§16 and report-interpretation §16 afterwards.

## Feasibility & Effort

- **CONFIRMED** by both probes and by reading the cited lines.
- **LIKELY** effort **M-L**: the state change is small, but the burndown/VEX/badge semantics and the closure event
  log need a design decision about which scan owns a closure. **UNKNOWN**: whether historical databases need a
  migration of `not_observed` rows. A short design spike (half a day) is recommended before building.
