---
phase: 33
slug: broker-scanner
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-27
approved: 2026-04-27
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `pytest tests/test_broker_*.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~25 seconds (broker subset) / ~45 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_broker_*.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 33 seconds

---

## Success Criterion → Test Map

These six rows trace each ROADMAP Phase 33 success criterion to a concrete automated check.
Every criterion MUST stay green for the phase to close.

| SC | ROADMAP Success Criterion | Automated Command | File(s) |
|----|---------------------------|-------------------|---------|
| SC-1 | Kafka plaintext + TLS posture detected with weak-cipher findings | `pytest tests/test_broker_scanner_kafka.py -x` | quirk/scanner/broker_scanner.py |
| SC-2 | RabbitMQ AMQP plaintext + AMQPS posture detected (incl. Azure Service Bus host expansion) | `pytest tests/test_broker_scanner_rabbitmq.py -x` | quirk/scanner/broker_scanner.py |
| SC-3 | Redis plaintext-no-auth + TLS posture detected | `pytest tests/test_broker_scanner_redis.py -x` | quirk/scanner/broker_scanner.py |
| SC-4 | broker_scan_json column populated and survives risk-engine layering | `pytest tests/test_broker_db_schema.py tests/test_broker_run_integration.py -x` | quirk/models.py, quirk/db.py, run_scan.py |
| SC-5 | Standard/deep profiles enable broker scan; quick profile leaves it disabled | `pytest tests/test_broker_config_and_profile.py -x` | quirk/config.py |
| SC-6 | Chaos lab profile produces ≥3 plaintext HIGH + ≥2 weak-cipher HIGH end-to-end | Plan 33-08 Task 1 smoke run + jq finding count | labs/broker/, quantum-chaos-enterprise-lab/docker-compose.yml |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 1 | BROKER-00 | T-33-01 | broker_scan_json column added without losing existing rows | unit | `pytest tests/test_broker_db_schema.py -x` | ❌ W0 | ⬜ pending |
| 33-01-02 | 01 | 1 | BROKER-00 | — | schema migration is idempotent | unit | `pytest tests/test_broker_db_schema.py::test_idempotent -x` | ❌ W0 | ⬜ pending |
| 33-02-01 | 02 | 1 | STRUCT-02 | — | enable_broker default False; namespaces hydrate from list | unit | `pytest tests/test_broker_config_and_profile.py::test_config_defaults -x` | ❌ W0 | ⬜ pending |
| 33-02-02 | 02 | 1 | STRUCT-03 | — | quick=False, standard/deep=True | unit | `pytest tests/test_broker_config_and_profile.py::test_profile -x` | ❌ W0 | ⬜ pending |
| 33-02-03 | 02 | 1 | STRUCT-02 | — | optional sub-extras kafka/redis declared | unit | `python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); assert 'kafka' in d['project']['optional-dependencies']"` | ❌ W0 | ⬜ pending |
| 33-03-01 | 03 | 2 | KAFKA-01,KAFKA-02,BROKER-ARCH | T-33-02 | sslyze probe with explicit SNI; no naked datetime.now | unit | `pytest tests/test_broker_scanner_kafka.py -x` | ❌ W0 | ⬜ pending |
| 33-03-02 | 03 | 2 | KAFKA-03,KAFKA-04,STRUCT-01 | — | session_start plumbed; admin enrichment optional | unit | `pytest tests/test_broker_scanner_kafka.py::test_session_start_plumbed -x` | ❌ W0 | ⬜ pending |
| 33-03-03 | 03 | 2 | KAFKA-01..04 | — | grep gate: zero raw datetime.now occurrences in broker_scanner | gate | `grep -v '^#' quirk/scanner/broker_scanner.py \| grep -c 'datetime.now()' \| grep -q '^0$'` | ❌ W0 | ⬜ pending |
| 33-04-01 | 04 | 3 | RABBIT-01,RABBIT-02 | T-33-03 | AMQP plaintext detected via len(data)>0 (not prefix match) | unit | `pytest tests/test_broker_scanner_rabbitmq.py::test_amqp_plaintext_lendata_rule -x` | ❌ W0 | ⬜ pending |
| 33-04-02 | 04 | 3 | RABBIT-03,RABBIT-04,RABBIT-05 | — | Azure Service Bus + AWS SQS hostnames constructed correctly | unit | `pytest tests/test_broker_scanner_rabbitmq.py::test_azure_sqs_host_expansion -x` | ❌ W0 | ⬜ pending |
| 33-04-03 | 04 | 3 | RABBIT-04 | — | management API uses urllib (no requests import) | gate | `grep -E "^import requests\|^from requests" quirk/scanner/broker_scanner.py \| wc -l \| grep -q '^[[:space:]]*0$'` | ❌ W0 | ⬜ pending |
| 33-05-01 | 05 | 4 | REDIS-01,REDIS-02 | T-33-04 | raw ssl.SSLContext.wrap_socket; PING-based plaintext probe | unit | `pytest tests/test_broker_scanner_redis.py -x` | ❌ W0 | ⬜ pending |
| 33-05-02 | 05 | 4 | REDIS-03 | — | AuthenticationError + NoPermissionError handled distinctly | unit | `pytest tests/test_broker_scanner_redis.py::test_redis_auth_branches -x` | ❌ W0 | ⬜ pending |
| 33-05-03 | 05 | 4 | BROKER-ARCH | — | single-file driver test | unit | `pytest tests/test_broker_scanner_redis.py::test_single_file_driver -x` | ❌ W0 | ⬜ pending |
| 33-06-01 | 06 | 5 | BROKER-00 | — | CLI flags accept multi-value namespace/region | integration | `pytest tests/test_broker_run_integration.py::test_cli_flags -x` | ❌ W0 | ⬜ pending |
| 33-06-02 | 06 | 5 | BROKER-00 | — | broker_scan_json attached to first endpoint only (D-14) | integration | `pytest tests/test_broker_run_integration.py::test_first_endpoint_only -x` | ❌ W0 | ⬜ pending |
| 33-06-03 | 06 | 5 | BROKER-00 | — | risk_engine emits 4 expected finding kinds | integration | `pytest tests/test_broker_run_integration.py::test_finding_kinds -x` | ❌ W0 | ⬜ pending |
| 33-07-01 | 07 | 5 | BROKER-LAB-01 | — | Makefile generates RSA-2048 self-signed certs | smoke | `cd labs/broker && make certs && test -f kafka.crt && test -f rabbitmq.crt && test -f redis.crt` | ❌ W0 | ⬜ pending |
| 33-07-02 | 07 | 5 | BROKER-LAB-01 | — | weak-cipher configs reference DES/RSA suites | gate | `grep -q 'DES-CBC3-SHA' labs/broker/rabbitmq.conf && grep -q 'TLS_RSA_WITH_AES_128_CBC_SHA' labs/broker/kafka/server.properties` | ❌ W0 | ⬜ pending |
| 33-07-03 | 07 | 5 | BROKER-LAB-02 | — | compose broker profile uses official images | gate | `grep -E 'image: (apache/kafka:3\.6\|rabbitmq:3\.12-management\|redis:7-alpine)' quantum-chaos-enterprise-lab/docker-compose.yml \| wc -l \| grep -q '^[[:space:]]*3$'` | ❌ W0 | ⬜ pending |
| 33-08-01 | 08 | 6 | All | — | end-to-end smoke produces expected findings | e2e | `python run_scan.py --profile standard --kafka-host localhost:29093 --rabbitmq-host localhost:25671 --redis-host localhost:26380 --output quirk-output/phase33-smoke.json && jq '[.findings[] \| select(.severity=="HIGH")] \| length' quirk-output/phase33-smoke.json \| awk '$1>=5'` | ❌ W0 | ⬜ pending |
| 33-08-02 | 08 | 6 | — | — | UAT-33 series added | gate | `grep -c 'UAT-33-0' docs/UAT-SERIES.md \| awk '$1>=8'` | ✅ | ⬜ pending |
| 33-08-03 | 08 | 6 | — | — | Obsidian phase note exists with status: complete | gate | `test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-33-Broker-Scanner.md" && grep -q 'status: complete' "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-33-Broker-Scanner.md"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

The following test files do not yet exist and MUST be created (as scaffolds with at least
one failing test) by the corresponding plan's Task 1 before subsequent tasks may proceed:

- [ ] `tests/test_broker_db_schema.py` — created in Plan 33-01 Task 2
- [ ] `tests/test_broker_config_and_profile.py` — created in Plan 33-02 Task 3
- [ ] `tests/test_broker_scanner_kafka.py` — created in Plan 33-03 Task 3
- [ ] `tests/test_broker_scanner_rabbitmq.py` — created in Plan 33-04 Task 3
- [ ] `tests/test_broker_scanner_redis.py` — created in Plan 33-05 Task 3
- [ ] `tests/test_broker_run_integration.py` — created in Plan 33-06 Task 3

Each plan's first task that exercises a behavior is paired with the test-creation task in
the same plan, so Wave 0 dependencies are intra-plan rather than a dedicated Wave 0.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Obsidian phase note renders correctly with backlinks resolved | (docs) | Obsidian rendering is a UI concern; backlinks resolve only inside the app | Open Digs vault → 20_Dev-Work/QUIRK/Phases/Phase-33-Broker-Scanner.md and confirm `[[Roadmap]]`, `[[_QUIRK-Hub]]` resolve to existing notes |
| Smoke-run JSON visually inspected for nested broker_scan_json | BROKER-00 | Cross-checking JSON structure against D-12/D-14 expectations is faster by eye | Open quirk-output/phase33-smoke.json and confirm first endpoint has `broker_scan_json.kafka`, `.rabbitmq`, `.redis` keys |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 33s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-27
