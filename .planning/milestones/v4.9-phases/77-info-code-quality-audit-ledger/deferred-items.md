# Phase 77 — Deferred Out-of-Scope Items

These items were discovered during Phase 77 execution but are **NOT** caused by
this phase's changes. Per executor SCOPE BOUNDARY, they are logged here and
left for a future, focused fix.

## Pre-existing test failures (verified via `git stash` on 2026-05-15)

The following tests fail on HEAD `e4e176b` (Phase 77-01 GREEN commit) AND also
fail with the Phase 77-01 changes stashed — confirming they are pre-existing.

1. `tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success`
   — `KeyError: 'rabbitmq_version'`. `_enrich_rabbitmq_mgmt` no longer flattens
   the management-API JSON; the test fixture mocks the older flat-key shape.
   Out of scope for INFO-01.

2. `tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_401`
   — same surface as above.

3. `tests/test_tls_scanner_resource_cleanup.py::test_sslyze_scanner_released_on_exception_path`
   — `AttributeError: module 'quirk.scanner.tls_scanner' has no attribute
   'SslyzeScanner'`. Test patches a symbol that was renamed/removed in a
   prior phase. Out of scope for INFO-01.

4. `tests/test_tls_scanner_resource_cleanup.py::test_sslyze_scanner_released_on_normal_path`
   — same surface as #3.

Recommended owner: whichever future phase touches `quirk/scanner/broker_scanner.py`
RabbitMQ management enrichment or `quirk/scanner/tls_scanner.py` sslyze
attribute surface.

## Pre-existing test failures observed during Phase 77-05 regression sweep (2026-05-15)

The Phase 77-05 (LEDGER-01) full-suite sweep observed 40 test failures. The
same 40 failures exist at commit `900ed0b` (the parent of `f2e24b1` — the
first LEDGER-01 commit), confirming they are inherited from upstream Plans
77-01..04 OR from environmental drift (multiple legacy DB files in cwd noted
in 77-03-SUMMARY). They are explicitly **out of scope** for Plan 77-05 per
the executor scope-boundary rule (LEDGER-01 only touches AUDIT-TASKS.md +
the new test_audit_ledger_zero_open.py module — no production source code
changes).

LEDGER-01 itself ships green:
- `pytest tests/test_audit_ledger_zero_open.py` — 2/2 PASS
- `cd src/dashboard && npm test -- --run` — 70/70 PASS (18 files)
- `cd src/dashboard && npm run build` — exit 0
- `grep -cE "^\| .* \[ \] open\s*\|" AUDIT-TASKS.md` — 0
- `grep -cE "\|\s*\[\s*\]\s*(deferred-\w+|wont-fix)\s*\|\s*$" AUDIT-TASKS.md` — 0

Recommended owners (suite-internal triage):
- `test_cbom_schema_validation` (5 failures) — chaos-lab CBOM emit profiles
- `test_dashboard_theme` (2 failures) — `vendor-charts` / theme drift
- `test_identity_surface` (2 failures), `test_motion_scoring`, `test_scoring_correctness` — QRAMM/scoring landscape drift
- `test_init_db_idempotent`, `test_install_errors` — DB column-helper consolidation aftermath (77-03 D-21)
- `test_qramm_evidence_bridge` (2 failures) — evidence bridge module path
- `test_skip_registry` — unregistered skip in some new test
- `test_cli_correctness`, `test_dashboard_scan_history`, `test_chaos_storage` — misc

These are NOT v4.9 milestone-completion gating because LEDGER-01's invariants
(zero bare-open rows + rationale completeness) are enforced by the new CI
gate module which itself passes. Suggested follow-up: open a "v4.9
post-LEDGER housekeeping" sub-phase.
