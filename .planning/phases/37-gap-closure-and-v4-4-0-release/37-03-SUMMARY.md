---
phase: 37
plan: 03
status: complete
requirements: [INFRA-03, STRUCT-01]
created: 2026-04-29
---

# Plan 37-03 Summary — INFRA-03 Nyquist Coverage Module

## Outcome
INFRA-03 satisfied: a single auditable test module (`tests/test_infra03_nyquist_coverage.py`)
contains 18 explicit test functions — 6 scanner entry points × 3 scenarios
(happy / refused / plaintext-only). All 18 pass on current main.

## Entry-Point Dispatch (Task 1)

`grep '^def scan_' quirk/scanner/broker_scanner.py` returned:
- `scan_one_kafka`, `scan_kafka_targets`
- `scan_one_rabbitmq`, `scan_rabbitmq_targets`
- `scan_one_redis`, `scan_redis_targets`

**Azure Service Bus (RABBIT-04)** and **AWS SQS (RABBIT-05)** are NOT separate
public functions — they are dispatched as parameters to `scan_rabbitmq_targets`:
- Azure: `scan_rabbitmq_targets(hosts=[], azure_namespaces=["myns"])` → probes
  `myns.servicebus.windows.net:5671` with `protocol_label="AMQPS/Azure-ServiceBus"`.
- SQS: `scan_rabbitmq_targets(hosts=[], sqs_regions=["us-east-1"])` → probes
  `sqs.us-east-1.amazonaws.com:443` with `protocol_label="HTTPS/AWS-SQS"`.

Tests 13-15 (Azure SB) and 16-18 (AWS SQS) call `scan_rabbitmq_targets` with the
appropriate parameter set; the protocol label and host pattern uniquely identify
the cloud-broker code path.

## 18 Test Functions

Email (3): `test_scan_email_targets_{happy,refused,plaintext_only}`
Kafka (3): `test_scan_kafka_targets_{happy,refused,plaintext_only}`
RabbitMQ (3): `test_scan_rabbitmq_targets_{happy,refused,plaintext_only}`
Redis (3): `test_scan_redis_targets_{happy,refused,plaintext_only}`
Azure Service Bus (3): `test_azure_servicebus_probe_{happy,refused,plaintext_only}`
AWS SQS (3): `test_aws_sqs_probe_{happy,refused,plaintext_only}`

The Azure SB and AWS SQS plaintext-only cases are intentionally degenerate —
those services have no plaintext port analog (Azure SB is AMQPS-only on 5671;
SQS is HTTPS-only on 443). The tests document the expected absence of any
finding under TLS-refused conditions, satisfying D-03 ("18 explicit functions"
without inventing fake plaintext semantics).

## Mocking Strategy
- **happy**: patch `scan_one_*` to return a `CryptoEndpoint` with `tls_version="TLSv1.3"`.
- **refused**: patch `socket.create_connection` to raise `ConnectionRefusedError`
  AND patch `SSLYZE_AVAILABLE` to `False` — drives the real graceful-degradation
  paths through `_detect_*_plaintext` and `_scan_one_sslyze_*`.
- **plaintext-only**: patch `scan_one_*` to return only the plaintext-port
  endpoint (`KAFKA-PLAIN` / `AMQP-PLAIN` / `REDIS-PLAIN` / `SMTP-STARTTLS` with
  no `tls_version`) and `None` on TLS ports.

STRUCT-01 lock: every test passes `session_start=SESSION_START` (a fixed
`datetime(2026, 1, 1, tzinfo=timezone.utc)`).

## Verification
- `pytest tests/test_infra03_nyquist_coverage.py -v` → **18 passed in 0.14s**
- `grep -c '^def test_' tests/test_infra03_nyquist_coverage.py` → `18`
- `grep -c 'session_start=SESSION_START' tests/test_infra03_nyquist_coverage.py` → `19` (≥18)
- `wc -l tests/test_infra03_nyquist_coverage.py` → `393` (>200 line sanity threshold)
- All 18 named functions present (verified via name-by-name grep)

## Commits
- `test(37-03): INFRA-03 Nyquist coverage — 18 tests, single auditable surface`
