---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS (fork B4); ledger rows DCL-OPS-B-0412, B-0416, B-0430, B-0432, B-0434, B-0435, B-0444 (docs/operators-guide.md §15-§16)
priority: high
area: quirk/intelligence/remediation_persist.py, quirk/intelligence/closure.py, quirk/intelligence/burndown.py, quirk/intelligence/scope_signature.py (_PROTOCOL_TO_FAMILY)
status: completed
completed: 2026-10-15
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

- [x] Decide the state model: set detected current-scan rows to `open` (at persist or in compute_closure when
      comparable), and decide whether closures should be carried onto the current scan (e.g. a closed row/event
      the burndown counts) so the latest report shows them.
- [x] Give `HTTP` (and bare broker protocols) a probe family, or document plaintext items as non-closable.
- [x] Replace the hand-seeded `open` in `_seed_two_scans` with rows written by `persist_remediation_snapshot`.
- [x] Revisit operators-guide §15-§16 and report-interpretation §16 afterwards.

## Feasibility & Effort

- **CONFIRMED** by both probes and by reading the cited lines.
- **LIKELY** effort **M-L**: the state change is small, but the burndown/VEX/badge semantics and the closure event
  log need a design decision about which scan owns a closure. **UNKNOWN**: whether historical databases need a
  migration of `not_observed` rows. A short design spike (half a day) is recommended before building.

## Resolution (Phase 229, 2026-10-15)

Closed by FIND-11. Fix commits:

- `57453ba2` (229-01): detected remediation rows are written `open`; counter-only items stay `not_observed` (D-01/D-23).
- `41f5cf61` (229-02): HTTP probe family with an opt-in `no_targets` recheck (D-05/D-21).
- `86ad118b` (229-02): a cached fingerprint stage writes no timing key, so a cached run is not a recheck (D-22).
- `648645bd` (229-03): closures are recorded on the observing scan; protocol-set live-row guard (D-03/D-05/D-20).
- `b6376b03` (229-04): end-to-end closure state model on the production writers (D-07).
- Docs: `4ce19f2b` (operators guide), `1f5a120f` (report interpretation).

Proving nodes (UAT-229-01..05, Series 229): `tests/test_closure_state_model_e2e.py::test_scan1_detected_rows_are_open_and_vex_exploitable`, `::test_http_fast_mode_one_fixed_closes_on_scan2`, `::test_http_all_fixed_closes_every_host`, `::test_guardrail_negatives_refuse_and_write_no_closed_row`, `::test_tls_deep_mode_closes_fixed_host`, `::test_tls_fast_mode_refuses_fixed_host`, `::test_rerun_is_idempotent_in_rows_and_events`, `::test_third_scan_does_not_recount_closure`; `tests/test_remediation_persist.py::test_detected_fingerprint_rows_and_item_are_written_open`; `tests/test_fingerprint_cache_recheck.py`; `tests/test_closure_verification.py` (hand-seeded `open` replaced by rows from `persist_remediation_snapshot`).

Item 3 (bare `AMQP`/`KAFKA`/`REDIS`) is a non-issue (D-05). The scanners write `KAFKA-PLAIN`, `AMQP-PLAIN` and `REDIS-PLAIN` (`quirk/scanner/broker_scanner.py` around :501, :624, :917), which the broker family already claims. The bare strings appear only in the `run_scan.py` resume filter (around :3870-3876). Plain `HTTP` did lack a family and now has one.

Documented limits, not defects:

- In the default fast TLS mode the tls probe family is `not_run`, so TLS findings cannot close. Filed as HORIZON 999.138 (operator decision on what fast-mode evidence may count).
- Scans written before this release keep `not_observed` rows; they are not migrated.

The probe the body cites moved to `.planning/milestones/v5.27-phases/224-doc-claim-ledger-verification/work/probes/gc2-ops-b4-closure-states-probe.py` when v5.27 was archived.

**Gap closure (229-12, 2026-10-16).** 229-VERIFICATION gap 1: a finding whose own probe errored, timed out or left no row at its host:port still closed when a co-resident SAML/JWT row there was live (8 of 8 verifier shapes). Fixed by a per-host:port recheck rule: every family that reported the host:port must have a live row there, any CLOSED or scan_error row at it refuses, and a plaintext-HTTP finding closes only on a live HTTP row or a TLS/SSH row whose family was not live there in the detecting scan. The carried path applies the same rule with the detecting scan's families unioned in. RED commit 60864bed, fix commit bbba0339, docs commit d5159287. Proving nodes: `tests/test_closure_state_model_e2e.py::test_finding_probe_failed_beside_live_coresident_refuses_tls_deep`, `::test_finding_probe_failed_beside_live_coresident_refuses_http`, `::test_carried_finding_with_coresident_only_refuses`, `::test_mid_migration_tls_error_then_live_tls_closes`.

**Legacy-chain follow-up (229-12, 2026-10-16).** Residual hole: a carried `not_observed` row with no open/resurfaced detecting row and nothing live at its host:port on the preceding scan fell back to the CURRENT scan protocols, so a co-resident SAML/JWT row closed a plaintext-HTTP finding (4 of 4 legacy-origin shapes). Now refused as `refused_probe` and carried forward. The direct path keeps the fallback (unreachable from the production writer; seeded closure_verification fixtures rely on it). RED commit b7bf8dbd, fix commit 97070300, docs commit recorded in git log as `docs(229-12): legacy-chain closure behaviour (FIND-11)`. Proving node: `tests/test_closure_state_model_e2e.py::test_legacy_origin_carried_chain_refuses_on_empty_probe_basis`.

**Legacy-chain follow-up 2 (229-12, 2026-10-16).** The empty-basis refusal still let a legacy chain close one scan later (co-resident only twice, or a fourth scan: 6 of 6 verifier shapes) because the basis came from an intermediate scan. A carried `not_observed` row with no detecting `open`/`resurfaced` row anywhere in its history is now refused (`refused_probe`) whatever its basis; it closes only after re-detection. Fail-first test 0e06cf82, fix 832b91c8.

**Evidence follow-up (229-12, 2026-10-16).** Residual hole: a deep-scan sslyze-fallback TLS row (live, error-free, no `tls_capabilities_json`) closed a legacy-TLS finding because TLS was healthy elsewhere. A family now counts as rechecked at a host:port only when a live row there also carries the family's evidence field (public `scope_signature.endpoint_has_family_evidence`), direct and carried paths alike; the HTTP-moved-to-TLS/SSH reclassification rule is unchanged. Fail-first test b25cd284, fix f899ee8f, docs ae23b4d6.
