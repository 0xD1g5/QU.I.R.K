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
