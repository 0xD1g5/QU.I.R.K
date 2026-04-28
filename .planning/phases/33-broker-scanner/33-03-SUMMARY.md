---
phase: 33-broker-scanner
plan: "03"
subsystem: broker-scanner-kafka
tags: [phase-33, broker-scanner, kafka, sslyze, struct-01, KAFKA-01, KAFKA-02, KAFKA-03, KAFKA-04]
requirements: [STRUCT-01, BROKER-ARCH, KAFKA-01, KAFKA-02, KAFKA-03, KAFKA-04]

dependency_graph:
  requires:
    - "broker_scan_json column on crypto_endpoints (Plan 01)"
    - "ConnectorsCfg.enable_broker + apply_profile gating (Plan 02)"
  provides:
    - "quirk/scanner/broker_scanner.py module skeleton"
    - "scan_kafka_targets() driver (BROKER-ARCH)"
    - "scan_one_kafka() per-host orchestrator (KAFKA-01..03)"
    - "_detect_kafka_plaintext() TCP probe (KAFKA-02)"
    - "_scan_one_sslyze_kafka() TLS probe (KAFKA-01)"
    - "_enrich_kafka_admin() AdminClient enrichment (KAFKA-04)"
    - "SSLYZE_AVAILABLE / KAFKA_AVAILABLE / REDIS_AVAILABLE module booleans"
    - "AMQP_HEADER constant (Plan 04 RabbitMQ extension point)"
  affects:
    - quirk/scanner/broker_scanner.py
    - tests/test_broker_scanner_kafka.py

tech_stack:
  added: []
  patterns:
    - "Multi-protocol single-file scanner (mirrors db_connector.py)"
    - "4-function-per-protocol shape (mirrors email_scanner.py)"
    - "sslyze cert+cipher parsing block reused from email_scanner.py lines 112-274"
    - "Optional dependency import guards with module-level None for patchability"
    - "SSLYZE_AVAILABLE boolean guard (not SslyzeScanner is None) for testability"
    - "session_start or datetime.now(timezone.utc) pattern (STRUCT-01)"
    - "ConnectionRefusedError silent at DEBUG (D-03 carry-forward)"

key_files:
  created:
    - quirk/scanner/broker_scanner.py
    - tests/test_broker_scanner_kafka.py
  modified: []

decisions:
  - "Used SSLYZE_AVAILABLE boolean guard instead of 'if SslyzeScanner is None' — allows unittest.mock.patch to work cleanly without patching None"
  - "sslyze cert+cipher parsing block reused verbatim from email_scanner.py lines 112-274 (D-10 pattern)"
  - "AMQP_HEADER constant defined at module level for Plan 04 RabbitMQ extension (no Plan 04 code yet)"
  - "Tests patch SSLYZE_AVAILABLE + all sslyze None-initialised symbols for KAFKA-01 test"
  - "Docstrings cleaned of 'datetime.now()' text to keep STRUCT-01 source grep clean"

metrics:
  duration: "~5 minutes"
  completed: "2026-04-28"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 0
  files_created: 2
---

# Phase 33 Plan 03: Broker Scanner Skeleton + Kafka Functions — SUMMARY

**One-liner:** Created `quirk/scanner/broker_scanner.py` with module skeleton, Kafka plaintext probe, sslyze TLS probe, AdminClient enrichment, and parallel-scan driver; verified by 12 green tests covering KAFKA-01..04 + STRUCT-01.

## What Was Built

### Task 1 + 2: broker_scanner.py (382 lines)

**quirk/scanner/broker_scanner.py** — single-file multi-protocol broker scanner module (BROKER-ARCH shape). Mirrors `db_connector.py` (multi-protocol, one file) and `email_scanner.py` (4-function-per-protocol shape).

**Module-level constants:**
- `SSLYZE_AVAILABLE: bool` — sslyze optional import guard
- `KAFKA_AVAILABLE: bool` — kafka-python optional import guard (D-07)
- `REDIS_AVAILABLE: bool` — redis-py optional import guard placeholder (Plan 05)
- `KafkaAdminClient = None`, `ConfigResource = None`, `ConfigResourceType = None` — module-level None for patchability
- `redis_lib = None` — module-level None placeholder
- `AMQP_HEADER = b'AMQP\x00\x00\x09\x01'` — Plan 04 extension point

**Functions defined:**
- `_detect_kafka_plaintext(host, port, timeout=2)` — KAFKA-02: bare TCP connect = plaintext listener
- `_scan_one_sslyze_kafka(host, port, timeout, logger=None)` — KAFKA-01: sslyze direct TLS probe (no STARTTLS). Cert+cipher parsing block reused from `email_scanner.py` lines 112-274.
- `_enrich_kafka_admin(host, port, logger=None)` — KAFKA-04: kafka-python AdminClient `describe_configs(BROKER, '0')` enrichment; returns `{}` on any failure (D-08)
- `scan_one_kafka(host, port, timeout, logger=None, session_start=None)` — port-dispatching orchestrator; 9092 → plaintext detection; 9093/9094 → sslyze + enrichment
- `scan_kafka_targets(hosts, timeout, profile='standard', logger=None, session_start=None)` — KAFKA-03 profile gating: ports [9092, 9093] for quick; [9092, 9093, 9094] for standard/deep; ThreadPoolExecutor parallel

**STRUCT-01 compliance:** Every `datetime.now(timezone.utc)` call is guarded by `session_start or`. Module docstrings contain no bare `datetime.now()` text to keep source-grep clean.

### Task 3: tests/test_broker_scanner_kafka.py (310 lines, 12 tests)

| Test | REQ | Result |
|------|-----|--------|
| test_sslyze_probe_returns_kafka_tls_endpoint | KAFKA-01 | PASSED |
| test_detect_kafka_plaintext_true_on_connect | KAFKA-02 | PASSED |
| test_detect_kafka_plaintext_false_on_refused | KAFKA-02 | PASSED |
| test_scan_one_kafka_9092_returns_plain_endpoint | KAFKA-02 | PASSED |
| test_scan_one_kafka_9092_returns_none_when_no_listener | KAFKA-02 | PASSED |
| test_scan_kafka_targets_standard_profile_includes_9094 | KAFKA-03 | PASSED |
| test_scan_kafka_targets_quick_profile_excludes_9094 | KAFKA-03 | PASSED |
| test_enrich_kafka_admin_returns_empty_when_unavailable | KAFKA-04 | PASSED |
| test_enrich_kafka_admin_returns_dict_when_available | KAFKA-04 | PASSED |
| test_enrich_kafka_admin_swallows_exceptions | D-08 | PASSED |
| test_session_start_propagation | STRUCT-01 | PASSED |
| test_no_naked_datetime_now_in_broker_scanner | STRUCT-01 | PASSED |

**12 / 12 passed. 0 failed.**

## sslyze Block Reuse

The cert+cipher parsing block in `_scan_one_sslyze_kafka()` is a direct adaptation of `email_scanner.py` lines 112–274 (`_scan_one_sslyze_email`). Changes made:
- Removed `tls_opportunistic_encryption` from `ServerNetworkConfiguration` kwargs (Kafka TLS is direct, not STARTTLS)
- Changed `ep = CryptoEndpoint(host=host, port=port, protocol="KAFKA-TLS")` instead of `protocol=""`
- Changed log prefix from `sslyze EMAIL` to `sslyze KAFKA`
- Added `_BROKER_PROTO_MAP` to include TLS 1.0/1.1 probes in addition to 1.2/1.3

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SSLYZE_AVAILABLE boolean guard needed for test patchability**
- **Found during:** Task 3 test execution
- **Issue:** Plan specified `if SslyzeScanner is None` guard inside `_scan_one_sslyze_kafka`. When sslyze is absent, `SslyzeScanner = None` at module level. Patching `SslyzeScanner` via `@patch(...)` replaces the module attribute but the guard `if SslyzeScanner is None` reads the local closure — still evaluates to `True` (None) at function call time because Python closures capture global lookups at call time. Result: test saw `None` return even with mock in place.
- **Fix:** Changed guard to `if not SSLYZE_AVAILABLE:` — patching `SSLYZE_AVAILABLE = True` allows the function to proceed. Updated KAFKA-01 test to also patch `SSLYZE_AVAILABLE`, `ServerNetworkConfiguration`, `ServerNetworkLocation`, `ServerScanRequest`, `ScanCommand` (all None when sslyze absent).
- **Files modified:** `quirk/scanner/broker_scanner.py`, `tests/test_broker_scanner_kafka.py`
- **Commits:** 0084a88, ba74e49

**2. [Rule 1 - Bug] Docstring text triggered STRUCT-01 source grep**
- **Found during:** Task 3 `test_no_naked_datetime_now_in_broker_scanner`
- **Issue:** Module docstring contained "no per-scanner datetime.now() calls" and function docstring contained "no naked datetime.now() in this module" — both matched the grep pattern for bare `datetime.now(` in non-comment lines.
- **Fix:** Rewrote docstring phrases to "no bare now() calls" / "no bare now() calls in this module" — functionally identical documentation without the grep-triggering pattern.
- **Files modified:** `quirk/scanner/broker_scanner.py`
- **Commit:** 0084a88

## Verification Passed

```
python -m compileall quirk/scanner/broker_scanner.py             -> exit 0
python -m pytest tests/test_broker_scanner_kafka.py -v           -> 12 passed, 0 failed
grep -v '^#' broker_scanner.py | grep -c 'datetime.now('        -> 2
grep -v '^#' broker_scanner.py | grep -c 'session_start or'     -> 2  (every call guarded)
```

## Commits

| Hash | Message |
|------|---------|
| 6112e4d | feat(33-03): create broker_scanner.py skeleton with Kafka sslyze probe and plaintext helper |
| 0084a88 | fix(33-03): use SSLYZE_AVAILABLE guard in _scan_one_sslyze_kafka; clean docstrings |
| ba74e49 | test(33-03): add 12 Kafka broker scanner tests for KAFKA-01..04 + STRUCT-01 |

## Known Stubs

None. Module functions are fully implemented. `scan_rabbitmq_targets` and `scan_redis_targets` are not yet defined (Plans 04/05); the module compiles cleanly without them.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: T-33-05 | quirk/scanner/broker_scanner.py | sslyze `network_timeout=timeout` enforced; ConnectionRefusedError caught silently — DoS mitigated |
| threat_flag: T-33-06 | quirk/scanner/broker_scanner.py | `ssl_check_hostname=False, ssl_cafile=None` in `_enrich_kafka_admin` — accepted per D-08; enrichment is opportunistic, not a security signal |
| threat_flag: T-33-07 | quirk/scanner/broker_scanner.py | broker hostname logged at DEBUG in `_enrich_kafka_admin` — accepted; hostname is consultant-supplied target |

## Self-Check: PASSED

- quirk/scanner/broker_scanner.py: FOUND (382 lines)
- tests/test_broker_scanner_kafka.py: FOUND (310 lines)
- Commit 6112e4d: FOUND
- Commit 0084a88: FOUND
- Commit ba74e49: FOUND
- 12/12 tests passing
- SSLYZE_AVAILABLE, KAFKA_AVAILABLE, REDIS_AVAILABLE exported
- scan_kafka_targets, scan_one_kafka, _enrich_kafka_admin all importable
