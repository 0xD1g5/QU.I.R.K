---
phase: 33-broker-scanner
plan: "06"
subsystem: broker-scanner
tags: [phase-33, broker-scanner, integration, run-scan, risk-engine, tdd]
requires: [33-03-SUMMARY.md, 33-04-SUMMARY.md, 33-05-SUMMARY.md]
provides: [BROKER-00-end-to-end, CLI-flags-D01, broker_scan_json-D12-D14, evaluate_broker_endpoints]
affects:
  - run_scan.py
  - quirk/engine/risk_engine.py
  - tests/test_broker_run_integration.py
tech-stack:
  added: []
  patterns:
    - broker-scan-block-after-email-block
    - broker_scan_json-nested-per-protocol-family
    - evaluate_broker_endpoints-plaintext-and-weak-cipher
    - layered-findings-dedupe-survival
key-files:
  modified:
    - run_scan.py
    - quirk/engine/risk_engine.py
  created:
    - tests/test_broker_run_integration.py
decisions:
  - "evaluate_broker_endpoints import deferred to Task 2 because function did not exist during Task 1 — avoids ImportError at --help time before risk_engine is updated"
  - "json module added to top-level imports in run_scan.py (PEP 8 compliance) instead of inline import at aggregation site"
  - "all_broker_eps guarded via 'in dir()' check in broker_findings call to handle the no-broker-enabled path safely"
  - "Layered findings (KAFKA-PLAIN port 9092 + KAFKA-TLS weak-cipher port 9093) survive _dedupe_findings because dedupe key is (host, port, title, recommendation) — different titles ensure both survive (Phase 32 D-11/D-12 carry-forward confirmed)"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-28"
  tasks_completed: 3
  files_changed: 3
---

# Phase 33 Plan 06: run_scan.py Integration + Risk Engine Summary

**One-liner:** Broker scanner wired end-to-end into run_scan.py with CLI flags, broker_scan_json nested aggregation (D-12/D-14), and evaluate_broker_endpoints() emitting four HIGH-severity finding types.

## What Was Built

### Task 1 — CLI flags + broker scan block in run_scan.py

**CLI flags added (D-01)** at argparse setup (run_scan.py lines ~195–208):

```
--azure-servicebus-namespace <name>   action="append", dest="azure_servicebus_namespaces"
--aws-sqs-region <region>             action="append", dest="aws_sqs_regions"
```

Both flags are repeatable (`action="append"`, `default=[]`). After `apply_profile()`, the CLI values are merged into `cfg.connectors.broker_azure_namespaces` / `broker_sqs_regions` using the `list(existing or []) + list(cli_values)` pattern (D-01).

**Top-level imports added:**
- `from quirk.scanner.broker_scanner import scan_kafka_targets, scan_rabbitmq_targets, scan_redis_targets`
- `from quirk.engine.risk_engine import evaluate_broker_endpoints` (added after Task 2)
- `import json` (added to stdlib imports block)

**Broker scan block** (run_scan.py lines ~731–763) inserted after the email scanning block, gated on `cfg.connectors.enable_broker`:

```python
kafka_endpoints = []
rabbit_endpoints = []
redis_endpoints = []
with _phase_timer(run_stats, "broker_scanning"):
    if cfg.connectors.enable_broker:
        broker_hosts = list(dict.fromkeys(h for h, _ in tls_targets))
        if broker_hosts:
            kafka_endpoints = scan_kafka_targets(hosts=broker_hosts, ...)
            rabbit_endpoints = scan_rabbitmq_targets(hosts=broker_hosts, azure_namespaces=..., sqs_regions=..., ...)
            redis_endpoints = scan_redis_targets(hosts=broker_hosts, ...)
            logger.info(f"Broker scan: kafka={...} rabbit={...} redis={...}")
```

Broker endpoints aggregated into the `endpoints` tuple after `email_endpoints`:
```python
+ kafka_endpoints + rabbit_endpoints + redis_endpoints
```

### Task 2 — broker_scan_json aggregation + evaluate_broker_endpoints

**broker_scan_json aggregation** (run_scan.py lines ~766–791) follows the D-12/D-14 spec exactly:

- All broker endpoints combined into `all_broker_eps = kafka_endpoints + rabbit_endpoints + redis_endpoints`
- `rabbit_endpoints` split into `rabbit_self`, `azure_eps`, `sqs_eps` by `ep.protocol`
- Nested `payload` dict built with five protocol-family keys + `session_start`
- `json.dumps(payload, default=str)` set on `all_broker_eps[0]` via `setattr`
- When `all_broker_eps` is empty, no aggregation runs (no endpoint to attach to)

**evaluate_broker_endpoints()** added to `quirk/engine/risk_engine.py` (lines ~520–577). Emits HIGH findings for:

| Finding title | Trigger |
|---|---|
| "Plaintext Kafka listener detected" | `ep.protocol == "KAFKA-PLAIN"` |
| "Plaintext AMQP listener detected" | `ep.protocol == "AMQP-PLAIN"` |
| "Plaintext Redis listener (no auth)" | `ep.protocol == "REDIS-PLAIN"` |
| "Weak cipher suite on broker TLS endpoint" | Broker TLS protocol + RSA/3DES/RC4/non-AEAD cipher |

Weak-cipher detection covers `TLS_RSA_WITH_*`, `AES128-SHA`, `AES256-SHA`, `3DES`, `RC4`, `DES-CBC` and excludes `ECDHE` and `DHE` (PFS). Protocols checked: `KAFKA-TLS`, `AMQPS`, `AMQPS/Azure-ServiceBus`, `HTTPS/AWS-SQS`, `REDIS-TLS`.

**broker_findings merge** in risk_engine block:
```python
broker_findings = evaluate_broker_endpoints(all_broker_eps if 'all_broker_eps' in dir() else [])
if broker_findings:
    findings = (findings or []) + broker_findings
```

### Task 3 — tests/test_broker_run_integration.py (10 tests, all green)

| # | Requirement | Test |
|---|---|---|
| 1 | D-12 | payload has all 5 protocol-family keys + session_start; each is a list |
| 2 | D-14 | broker_scan_json set on first endpoint only; others have None |
| 3 | BROKER-00 | KAFKA-PLAIN -> 1 HIGH "Plaintext Kafka" finding |
| 4 | BROKER-00 | AMQP-PLAIN -> 1 HIGH "Plaintext AMQP" finding |
| 5 | BROKER-00 | REDIS-PLAIN -> 1 HIGH "Plaintext Redis" finding |
| 6 | BROKER-00 | TLS_RSA_WITH_AES_128_CBC_SHA on KAFKA-TLS -> HIGH "Weak cipher" finding |
| 7 | BROKER-00 | DES-CBC3-SHA on AMQPS -> HIGH "Weak cipher" finding |
| 8 | BROKER-00 | ECDHE-RSA-AES256-GCM-SHA384 on KAFKA-TLS -> NO finding (no false positive) |
| 9 | D-11 carry-forward | KAFKA-PLAIN(9092) + KAFKA-TLS weak(9093) both survive _dedupe_findings |
| 10 | BROKER-00 | CryptoEndpoint with broker_scan_json writes to SQLite; SELECT decodes correctly |

Full broker test suite: 58 passed (+ 1 skipped for migration idempotency path).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] evaluate_broker_endpoints import order**
- **Found during:** Task 1 verification
- **Issue:** Plan action for Task 1 included `from quirk.engine.risk_engine import evaluate_broker_endpoints` but that function didn't exist yet — causes ImportError at `--help` time, breaking Task 1's verification criterion
- **Fix:** Import added to top-level only after Task 2 created the function; Task 1 verified with broker scanner imports only
- **Files modified:** run_scan.py
- **Commit:** 17b6bc8

**2. [Rule 2 - Missing critical functionality] PEP 8 json import**
- **Found during:** Task 2 implementation
- **Issue:** `json.dumps()` in aggregation block required json module; used inline `import json as _json` initially
- **Fix:** Added `import json` to stdlib block at top of run_scan.py per PEP 8 and CLAUDE.md code standards
- **Files modified:** run_scan.py
- **Commit:** 17b6bc8

## Known Stubs

None.

## Threat Flags

None. T-33-15 mitigation (`json.dumps(default=str)` — no user input as keys) and T-33-16 (same trust boundary as email_scan_json) are implemented as specified in the threat register.

## Self-Check: PASSED

- [x] `run_scan.py` exists and contains `scan_kafka_targets` at line 28 — FOUND
- [x] `run_scan.py` contains `--azure-servicebus-namespace` at line 195 — FOUND
- [x] `run_scan.py` contains `--aws-sqs-region` at line 200 — FOUND
- [x] `run_scan.py` contains `broker_scan_json` at line 791 — FOUND
- [x] `quirk/engine/risk_engine.py` contains `evaluate_broker_endpoints` — FOUND
- [x] `tests/test_broker_run_integration.py` exists with 319 lines (> 120 min) — FOUND
- [x] `python -m compileall run_scan.py quirk/engine/risk_engine.py` exits 0 — PASSED
- [x] `python run_scan.py --help` lists both new flags — PASSED (grep count: 4)
- [x] Commit 70b94b2 (Task 1 — CLI flags + broker block) — FOUND
- [x] Commit 17b6bc8 (Task 2 — aggregation + risk_engine) — FOUND
- [x] Commit 5d00f8a (Task 3 — integration tests) — FOUND
- [x] 10/10 integration tests green; 58/58 broker suite green — PASSED
