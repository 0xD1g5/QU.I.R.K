---
phase: 42-cbom-correctness-audit
plan: 05
subsystem: cbom-tests
tags: [cbom, skip-list, parametrized, unit-test, CBOM-04]
type: summary
status: complete
requirements: [CBOM-04]
dependency_graph:
  requires:
    - "quirk.cbom.builder.MOTION_PLAINTEXT_PROTOCOLS (Plan 42-01)"
    - "quirk.cbom.builder.DAR_SKIP_PROTOCOLS (Plan 42-01)"
  provides:
    - "CBOM-04 Pass-2 + Pass-3 skip-list unit gate"
  affects:
    - "tests/test_cbom_skip_lists.py"
tech_stack:
  added: []
  patterns:
    - "Parametrize-off-source-of-truth — no hardcoded label list; drives directly off the imported frozensets so an empty constant collapses the suite (with sanity guard catching that case)"
key_files:
  created:
    - tests/test_cbom_skip_lists.py
  modified: []
decisions:
  - "Drive parametrize off `sorted(MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS)` rather than a literal list — T-42-03 mitigation against constant-vs-test drift"
  - "Add explicit nonempty sanity guard test — defends against T-42-07 (silent zero-coverage if either constant is emptied)"
metrics:
  duration_minutes: 3
  completed_date: 2026-04-30
  tasks_completed: 1
  files_created: 1
  files_modified: 0
---

# Phase 42 Plan 05: Skip-list unit-test gate Summary

Parametrized pytest gate that drives directly off `MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS` to prove every label is skipped by both Pass 2 (cert) and Pass 3 (protocol) of `build_cbom`, with a sanity guard that fails if either constant is emptied.

## What Was Built

- **`tests/test_cbom_skip_lists.py`** (84 lines, 13 tests):
  - `test_skip_list_constants_are_nonempty` — sanity guard against silent zero-coverage if either constant is emptied (T-42-07).
  - `test_skip_protocol_emits_no_cert_or_proto_component[<protocol>]` — parametrized over `sorted(MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS)`. For each label, builds a `CryptoEndpoint` with full TLS+cert metadata (cipher_suite, cert_pubkey_alg, cert_pubkey_size, cert_sig_alg, cert_subject, cert_issuer, tls_version) and asserts the resulting CBOM contains NO `crypto/certificate/{host}:{port}` ref AND NO `crypto/protocol/tls/{host}:{port}` ref. Pass 1 algorithm components are allowed.

## Parametrize Coverage

12 parametrized cases (matches the spec — 3 motion + 9 DAR):

| Source set | Labels |
|------------|--------|
| `MOTION_PLAINTEXT_PROTOCOLS` (3) | AMQP-PLAIN, KAFKA-PLAIN, REDIS-PLAIN |
| `DAR_SKIP_PROTOCOLS` (9) | AZURE_BLOB, CLOUD_SQL, GCP, KUBERNETES, MYSQL, POSTGRESQL, RDS, S3, VAULT |

Total: 13 tests (1 sanity + 12 parametrized).

## Verification

```
$ .venv/bin/pytest tests/test_cbom_skip_lists.py -x -v
collected 13 items

tests/test_cbom_skip_lists.py::test_skip_list_constants_are_nonempty PASSED [  7%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[AMQP-PLAIN] PASSED [ 15%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[AZURE_BLOB] PASSED [ 23%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[CLOUD_SQL] PASSED [ 30%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[GCP] PASSED [ 38%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[KAFKA-PLAIN] PASSED [ 46%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[KUBERNETES] PASSED [ 53%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[MYSQL] PASSED [ 61%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[POSTGRESQL] PASSED [ 69%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[RDS] PASSED [ 76%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[REDIS-PLAIN] PASSED [ 84%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[S3] PASSED [ 92ropriately%]
tests/test_cbom_skip_lists.py::test_skip_protocol_emits_no_cert_or_proto_component[VAULT] PASSED [100%]

============================== 13 passed in 0.16s ==============================
```

Full cbom slice regression check:
```
$ .venv/bin/pytest tests/test_cbom_*.py -x
====================== 114 passed, 1 deselected in 1.31s =======================
```

## Acceptance Criteria

- [x] `tests/test_cbom_skip_lists.py` exists (84 lines, > 50 min).
- [x] Imports `MOTION_PLAINTEXT_PROTOCOLS` and `DAR_SKIP_PROTOCOLS` from `quirk.cbom.builder`.
- [x] Parametrize uses `sorted(MOTION_PLAINTEXT_PROTOCOLS | DAR_SKIP_PROTOCOLS)` (no hardcoded list).
- [x] Sanity guard `test_skip_list_constants_are_nonempty` present.
- [x] Each parametrized case builds a full TLS+cert `CryptoEndpoint` and asserts NO cert ref and NO TLS protocol ref.
- [x] Parametrize ID is the protocol label (failures name the offending entry).
- [x] `pytest tests/test_cbom_skip_lists.py -x -v` exits 0 with 13 passed (≥ 12 parametrized).
- [x] `pytest tests/test_cbom_*.py -x` exits 0 (no regressions: 114 passed).

## Deviations from Plan

None — plan executed exactly as written. The test file matches the plan's `<action>` block verbatim and all acceptance criteria pass on the first run.

## Threat Mitigations

| Threat | Mitigation |
|--------|------------|
| T-42-03 (skip-tuple drift) | Parametrize is driven directly off the source-of-truth frozensets — no literal list to drift from |
| T-42-07 (empty-constant silent coverage loss) | `test_skip_list_constants_are_nonempty` fails loudly if either set is emptied |

## Commits

- `de0449e` — test(42-05): add parametrized Pass-2/Pass-3 skip-list unit gate

## Self-Check: PASSED

- File `tests/test_cbom_skip_lists.py` exists.
- Commit `de0449e` exists in `git log`.
- 13/13 tests pass; 114/114 cbom slice passes.
