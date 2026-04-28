---
phase: 33-broker-scanner
plan: "04"
subsystem: broker-scanner-rabbitmq
tags: [phase-33, broker-scanner, rabbitmq, amqp, azure-servicebus, aws-sqs, RABBIT-01, RABBIT-02, RABBIT-03, RABBIT-04, RABBIT-05, STRUCT-01]
requirements: [STRUCT-01, RABBIT-01, RABBIT-02, RABBIT-03, RABBIT-04, RABBIT-05]

dependency_graph:
  requires:
    - "broker_scanner.py module skeleton + _scan_one_sslyze_kafka (Plan 03)"
    - "AMQP_HEADER constant defined at module level (Plan 03)"
  provides:
    - "_scan_one_sslyze_broker() protocol-agnostic TLS probe (renamed from _scan_one_sslyze_kafka)"
    - "_scan_one_sslyze_kafka alias (Plan 03 backward compat)"
    - "_detect_amqp_plaintext() AMQP 0-9-1 header probe, len(data)>0 rule (RABBIT-02)"
    - "_enrich_rabbitmq_mgmt() urllib.request mgmt API probe, 401->rejected_401 (RABBIT-03/D-09)"
    - "scan_one_rabbitmq() per-host orchestrator (RABBIT-01, RABBIT-02)"
    - "scan_rabbitmq_targets() driver with Azure SB + AWS SQS cloud probes (RABBIT-04, RABBIT-05)"
  affects:
    - quirk/scanner/broker_scanner.py
    - tests/test_broker_scanner_rabbitmq.py

tech_stack:
  added: []
  patterns:
    - "len(data)>0 AMQP detection rule (CONTEXT.md 2026-04-27 revision — not b'AMQP' prefix)"
    - "urllib.request for mgmt API — no requests dependency (D-09)"
    - "Cloud-target probes folded into scan_rabbitmq_targets (D-03/D-04)"
    - "_rabbit_mgmt_enrichment attribute on AMQPS endpoint for Plan 06 aggregation"
    - "Backward-compat alias _scan_one_sslyze_kafka = _scan_one_sslyze_broker"

key_files:
  created:
    - tests/test_broker_scanner_rabbitmq.py
  modified:
    - quirk/scanner/broker_scanner.py

decisions:
  - "Renamed _scan_one_sslyze_kafka to _scan_one_sslyze_broker (protocol-agnostic); kept backward-compat alias so Plan 03 tests pass without modification"
  - "AMQP detection rule: len(data)>0 per CONTEXT.md 2026-04-27 revision — original b'AMQP' prefix match would yield false negatives on every real broker (Connection.Start is binary METHOD frame)"
  - "Cloud probes (Azure SB, AWS SQS) folded into scan_rabbitmq_targets per CONTEXT.md Specifics (both speak TLS-only, no separate protocol handshake at our depth)"
  - "scan_one_rabbitmq caller sets ep.protocol via protocol_label kwarg; _scan_one_sslyze_broker returns placeholder 'KAFKA-TLS' that callers always override"
  - "Mgmt enrichment attached as _rabbit_mgmt_enrichment on first AMQPS endpoint per self-hosted host; Plan 06 reads this attribute for broker_scan_json aggregation"

metrics:
  duration: "~6 minutes"
  completed: "2026-04-27"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 1
  files_created: 1
---

# Phase 33 Plan 04: RabbitMQ + Azure Service Bus + AWS SQS Scanner Functions — SUMMARY

**One-liner:** Appended RabbitMQ/AMQPS probe functions to `broker_scanner.py` — AMQP plaintext detection with `len(data)>0` rule, stdlib mgmt API enrichment, and cloud-target probes for Azure Service Bus and AWS SQS folded into `scan_rabbitmq_targets()`; verified by 14 green tests covering RABBIT-01..05.

## What Was Built

### Task 1: sslyze helper rename + _detect_amqp_plaintext + _enrich_rabbitmq_mgmt

**quirk/scanner/broker_scanner.py** — three changes:

1. **`_scan_one_sslyze_kafka` renamed to `_scan_one_sslyze_broker`** — protocol-agnostic helper. Backward-compat alias `_scan_one_sslyze_kafka = _scan_one_sslyze_broker` added so Plan 03 tests import without modification. Internal protocol placeholder set to `"KAFKA-TLS"` (callers always override with their final label).

2. **`_detect_amqp_plaintext(host, port, timeout=2) -> bool`** (RABBIT-02):
   - Sends `AMQP_HEADER` (`b'AMQP\x00\x00\x09\x01'`) and returns `len(data) > 0`
   - `len(data) > 0` rule per CONTEXT.md 2026-04-27 revision — the original `b'AMQP'` prefix match yields false negatives because AMQP 0-9-1 Connection.Start replies are binary METHOD frames, not ASCII-prefixed

3. **`_enrich_rabbitmq_mgmt(host, port=15672, logger=None) -> dict`** (RABBIT-03 / D-09):
   - `urllib.request` GET `/api/overview` with Basic `guest:guest` — no `requests` dependency
   - 401 returns `{"mgmt_auth": "rejected_401"}` (informational, not an error per D-09)
   - URLError/other exceptions return `{}` and log at DEBUG

### Task 2: scan_one_rabbitmq + scan_rabbitmq_targets

**`scan_one_rabbitmq(host, port, timeout, *, protocol_label, logger, session_start)`**:
- Port 5672 → `_detect_amqp_plaintext` → `CryptoEndpoint(protocol="AMQP-PLAIN")` if detected
- Other ports → `_scan_one_sslyze_broker` → sets `ep.protocol = protocol_label`
- `protocol_label` values: `"AMQPS"` (5671 self-hosted), `"AMQPS/Azure-ServiceBus"`, `"HTTPS/AWS-SQS"`

**`scan_rabbitmq_targets(hosts, azure_namespaces, sqs_regions, timeout, logger, session_start)`**:
- Self-hosted: probes ports 5672 (AMQP-PLAIN detection) + 5671 (AMQPS via sslyze)
- Azure SB: `{namespace}.servicebus.windows.net:5671` per namespace (RABBIT-04)
- AWS SQS: `sqs.{region}.amazonaws.com:443` per region (RABBIT-05)
- RABBIT-03 mgmt enrichment: best-effort per self-hosted host, attached as `_rabbit_mgmt_enrichment` on first AMQPS endpoint
- Empty `azure_namespaces` / `sqs_regions` → zero cloud probes
- `ThreadPoolExecutor(max_workers=min(n, 50))` for parallel probe dispatch

### Task 3: tests/test_broker_scanner_rabbitmq.py (14 tests, 405 lines)

| Test | REQ | Result |
|------|-----|--------|
| test_scan_one_rabbitmq_5671_returns_amqps_endpoint | RABBIT-01 | PASSED |
| test_detect_amqp_plaintext_true_on_binary_response | RABBIT-02 | PASSED |
| test_detect_amqp_plaintext_false_on_empty_response | RABBIT-02 | PASSED |
| test_detect_amqp_plaintext_false_on_connection_refused | RABBIT-02 | PASSED |
| test_scan_one_rabbitmq_5672_returns_amqp_plain_endpoint | RABBIT-02 | PASSED |
| test_enrich_rabbitmq_mgmt_success | RABBIT-03 | PASSED |
| test_enrich_rabbitmq_mgmt_401 | RABBIT-03 | PASSED |
| test_enrich_rabbitmq_mgmt_connection_refused | RABBIT-03 | PASSED |
| test_no_requests_dependency | D-09 | PASSED |
| test_azure_servicebus_hostname_construction | RABBIT-04 | PASSED |
| test_aws_sqs_hostname_construction | RABBIT-05 | PASSED |
| test_empty_azure_namespaces_yields_no_cloud_probes | RABBIT-04 | PASSED |
| test_mgmt_enrichment_attached_to_amqps_endpoint | RABBIT-03 | PASSED |
| test_session_start_propagation | STRUCT-01 | PASSED |

**14 / 14 passed. 0 failed.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] sslyze helper placeholder protocol needed to preserve Plan 03 test contract**
- **Found during:** Task 1 implementation
- **Issue:** Plan called for `_scan_one_sslyze_broker` to return `protocol=None` (or placeholder). The Plan 03 test `test_sslyze_probe_returns_kafka_tls_endpoint` imports `_scan_one_sslyze_kafka` by name and asserts `ep.protocol == "KAFKA-TLS"`. Changing the placeholder to `None` or `"BROKER-TLS"` would break that test.
- **Fix:** Kept placeholder as `"KAFKA-TLS"` in the helper. Callers (`scan_one_kafka`, `scan_one_rabbitmq`) always explicitly set `ep.protocol` after the call, satisfying the plan's intent. Added comment in source.
- **Files modified:** `quirk/scanner/broker_scanner.py`
- **Commit:** 90576d4

## Verification Passed

```
python -m compileall quirk/scanner/broker_scanner.py            -> exit 0 (clean)
python -m pytest tests/test_broker_scanner_kafka.py \
                 tests/test_broker_scanner_rabbitmq.py -v       -> 26 passed, 0 failed
grep -v '^#' broker_scanner.py | grep -cE "^import requests|^from requests" -> 0 (D-09)
grep -v '^#' broker_scanner.py | grep -c "len(data) > 0"       -> 2 (RABBIT-02 literal)
```

## Commits

| Hash | Message |
|------|---------|
| 90576d4 | feat(33-04): rename _scan_one_sslyze_kafka to _scan_one_sslyze_broker; add _detect_amqp_plaintext + _enrich_rabbitmq_mgmt |
| 5dfc7f0 | feat(33-04): append scan_one_rabbitmq + scan_rabbitmq_targets with Azure SB and AWS SQS cloud probes |
| f0ed555 | test(33-04): add 14 RabbitMQ broker scanner tests covering RABBIT-01..05 + D-09 + STRUCT-01 |

## Known Stubs

None. All functions are fully implemented and tested. `scan_redis_targets` is not yet defined (Plan 05); the module compiles cleanly without it.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: T-33-08 | quirk/scanner/broker_scanner.py | guest:guest credential transmitted in Basic auth header over plaintext HTTP on port 15672 — accepted per plan threat register |
| threat_flag: T-33-09 | quirk/scanner/broker_scanner.py | AMQP_HEADER byte sequence sent to port 5672; len(data)>0 detection — accepted per plan threat register |
| threat_flag: T-33-10 | quirk/scanner/broker_scanner.py | urllib.request timeout=5 on urlopen mitigates DoS from slow mgmt API |
| threat_flag: T-33-11 | quirk/scanner/broker_scanner.py | namespace/region strings interpolated into hostnames; sslyze rejects malformed hostnames at connectivity test |

## Self-Check: PASSED

- quirk/scanner/broker_scanner.py: FOUND
- tests/test_broker_scanner_rabbitmq.py: FOUND (405 lines, 14 tests)
- Commit 90576d4: FOUND
- Commit 5dfc7f0: FOUND
- Commit f0ed555: FOUND
- 14/14 RabbitMQ tests passing
- 12/12 Kafka tests still passing after rename
- scan_rabbitmq_targets, scan_one_rabbitmq, _detect_amqp_plaintext, _enrich_rabbitmq_mgmt all importable
- D-09: 0 requests imports
- RABBIT-02 len(data)>0 rule: 2 occurrences in source
