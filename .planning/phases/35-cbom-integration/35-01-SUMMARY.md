---
phase: 35-cbom-integration
plan: 01
subsystem: cbom
type: tdd
wave: 1
status: complete
tags: [cbom, tdd, red-phase, motion, email, broker, classifier]
requires: []
provides:
  - tests/test_cbom_motion_endpoints.py
affects:
  - quirk/cbom/builder.py (Plan 02 will turn the 3 RED tests GREEN)
tech-stack:
  added: []
  patterns:
    - synthesized-endpoint-tests
    - parametrized-pytest-cases
    - verify-not-redefine-classifier
key-files:
  created:
    - tests/test_cbom_motion_endpoints.py
  modified: []
decisions:
  - D-01: skip-lists use actual emitted labels (KAFKA-PLAIN/AMQP-PLAIN/REDIS-PLAIN)
  - D-02: all 6 email TLS labels flow uniformly through default-TLS branch
  - D-03: AMQPS/Azure-ServiceBus passes through unchanged (no normalization)
  - D-04: synthesized-endpoint unit tests for fast feedback (golden snapshots come later)
  - D-05: verify quantum-safety classification — do NOT redefine QUANTUM_SAFETY_MAP
metrics:
  duration_seconds: 110
  completed: 2026-04-28
  tasks_completed: 1
  files_changed: 1
  tests_added: 19  # 6 email + 4 broker + 6 plaintext + 3 classifier (parametrized cases)
---

# Phase 35 Plan 01: CBOM Motion Endpoint RED Tests Summary

RED-phase synthesized-endpoint test suite for email + broker TLS endpoints
covering CBOM-01 through CBOM-04. Locks the contract before Plan 02 lands the
Pass 3 skip-list addition that turns the RED failures GREEN.

## What Was Built

`tests/test_cbom_motion_endpoints.py` — 306-line, dependency-free unit test
file with 19 parametrized test cases:

| Coverage | Tests | Today's State |
|---|---|---|
| CBOM-01 — 6 email TLS labels emit protocol + cert components | 6 | PASS (default-TLS branch already routes these) |
| CBOM-02 — 4 broker TLS labels (incl. AMQPS/Azure-ServiceBus) | 4 | PASS (slash never escapes into bom_ref values, per D-03) |
| CBOM-03 — 3 plaintext labels skipped from cert pass | 3 | PASS today (incidentally — guarded by existing `cert_pubkey_alg` falsy check) |
| CBOM-03 — 3 plaintext labels skipped from protocol pass | 3 | **FAIL (RED)** — Pass 3 has no equivalent guard, leaks bom_refs |
| CBOM-04 — 3 cipher-suite quantum-safety verifications | 3 | PASS (classifier mappings already correct — verify, don't redefine) |
| **TOTAL** | **19** | **16 pass / 3 fail** |

The test file uses two helpers — `_tls_endpoint(**overrides)` (copied verbatim
from `tests/test_cbom_builder.py`) and `_plaintext_broker_endpoint(label, port)`
(new, mirroring the real plaintext shape from `broker_scanner.py`: no cipher,
no cert, no TLS version). A `_bom_refs(bom)` helper extracts the set of
`component.bom_ref.value` strings for assertions.

No production code changed in this plan.

## RED Test Evidence

```
$ python -m pytest tests/test_cbom_motion_endpoints.py -v
...
tests/.../test_plaintext_broker_skipped_from_protocol_pass[kafka-plain] FAILED
tests/.../test_plaintext_broker_skipped_from_protocol_pass[amqp-plain]  FAILED
tests/.../test_plaintext_broker_skipped_from_protocol_pass[redis-plain] FAILED
========================= 3 failed, 16 passed in 0.19s =========================
```

Each failure asserts a specific `crypto/protocol/tls/broker.example.com:{port}`
bom_ref leaked into the BOM despite the endpoint having `protocol="*-PLAIN"`.
The assertion message names the offending label and points to the Pass 3
skip-list as the fix site — exactly the change Plan 02 will land.

## Deviations from Plan

### Auto-discovered: predicted RED split was 6 fails, observed is 3 fails

**Found during:** Task 1 verification (`pytest -v`)
**Issue:** The plan acceptance criteria predicted "13 PASSED and exactly 6 FAILED"
— specifically, all 6 plaintext-broker tests (cert + protocol) were expected to
fail. Observed result: **16 passed / 3 failed**. The 3 cert-pass plaintext tests
pass today.

**Root cause (no code change required):** `quirk/cbom/builder.py` Pass 2 (line
440) has an existing `if not ep.cert_pubkey_alg: continue` guard. Plaintext
broker endpoints have `cert_pubkey_alg=None` (per the broker scanner's real
emit shape, which `_plaintext_broker_endpoint` mirrors), so the cert pass already
correctly skips them via that falsy-cert short-circuit. Pass 3 has no equivalent
guard — the default-TLS branch unconditionally emits a protocol component for
any non-skip-listed protocol value, which is why only the 3 protocol-pass tests
fail (RED).

**Why the tests are still correct:** Both groups of tests assert the *contract*
("plaintext brokers must not emit cert/protocol components"). The cert-pass
contract is already met (by a different mechanism — the falsy guard), so its
tests pass. The protocol-pass contract is not yet met, so its tests fail. After
Plan 02 adds `KAFKA-PLAIN`/`AMQP-PLAIN`/`REDIS-PLAIN` to the Pass 2 + Pass 3
skip tuples:
- Pass 2 tests will continue to pass (now via the explicit skip list, with the
  falsy guard as defense-in-depth).
- Pass 3 tests will turn GREEN.

The contract lock-in for Plan 02 is intact. The plan's success metric — "Plan 02
flips RED tests to GREEN by adding 3 strings to 2 tuples" — still holds; Plan 02's
diff to Pass 2 simply hardens an already-correct behavior, while its diff to
Pass 3 closes the actual leak.

**Action:** Documented here, not "fixed." Adjusting the test file to force RED
in the cert pass (e.g. by setting `cert_pubkey_alg="RSA"` on plaintext fixtures)
would make the fixture diverge from real broker_scanner output and weaken the
contract. The current shape is honest.

**Files modified:** None (no test-file changes needed; behavior is correct).
**Commit:** `d99ddd2`

## Authentication Gates

None.

## Decisions Made

- Used parametrized cases (one parametrized function per group) to keep file
  under 250 logical lines per `must_haves.artifacts.min_lines: 150` while still
  meeting the 19-test count via parametrization (counted as `pytest.param`
  occurrences, per acceptance criteria).
- Added a defensive assertion in the broker-TLS test that `Azure-ServiceBus`
  literal never appears in any bom_ref value (D-03 lock-in: slash is in the
  ref *prefix* `crypto/protocol/tls/`, never the dynamic value).
- Kept all `cert_pubkey_alg=None` on plaintext fixtures to mirror the real
  broker_scanner output. This makes the cert-pass tests pass today (via
  existing falsy guard) — see Deviations above for why this is the correct
  call rather than forcing artificial RED.

## Verification

- [x] `python -m compileall tests/test_cbom_motion_endpoints.py` — no syntax errors
- [x] `python -m pytest tests/test_cbom_motion_endpoints.py -v` — 16 passed, 3 failed (RED state confirmed for Pass 3)
- [x] No changes to `quirk/cbom/builder.py` or `quirk/cbom/classifier.py`
- [x] File line count: 306 (>= 150 min_lines)
- [x] Test function + parametrized case count: 19 (>= 19 acceptance threshold)

## Commits

- `d99ddd2` — test(35-01): add RED synthesized-endpoint CBOM tests for email + broker

## Self-Check: PASSED

Verified files:
- FOUND: tests/test_cbom_motion_endpoints.py
- FOUND commit: d99ddd2

## TDD Gate Compliance

RED gate: `test(35-01): add RED ...` commit `d99ddd2` recorded.
GREEN gate: deferred to Plan 02 (per plan chain — this plan is RED-only).
