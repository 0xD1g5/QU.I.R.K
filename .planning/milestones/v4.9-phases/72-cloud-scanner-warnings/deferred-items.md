# Phase 72 — Deferred Items

Out-of-scope discoveries found during plan execution. NOT fixed (D-25 do-not-touch).


## 2026-05-15 / Plan 72-05

### Pre-existing failure: tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success

- **Symptom:** `KeyError: 'rabbitmq_version'` at line 217.
- **State:** Fails on parent commit 4a3747d (before any 72-05 work) — confirmed pre-existing.
- **Out of scope:** Phase 72 CLOUD-05 boundary covers cloud/engine modules; broker_scanner_rabbitmq is unrelated.
- **Suggested owner:** Phase 75 (api-cli-core WARNINGs) or a backlog cleanup pass on broker_scanner.
