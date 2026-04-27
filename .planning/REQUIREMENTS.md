# Requirements: QU.I.R.K. v4.4 Data in Motion

**Defined:** 2026-04-27
**Core Value:** Produce a complete, defensible cryptographic inventory with a CBOM deliverable and quantum-readiness score that a consultant can hand to a client in under two hours.

---

## Structural Requirements (carry-forward from v4.3)

These apply to every scanner phase in v4.4:

- **STRUCT-01**: All new scanners accept a `session_start` parameter (shared `datetime` from `run_scan.py`) — no per-scanner `datetime.now()` calls (ISSUE-3 elimination pattern).
- **STRUCT-02**: All new `[motion]` extras group entries must be declared in `pyproject.toml` at plan time — not retroactively added.
- **STRUCT-03**: Each phase plan must include a `pyproject.toml` diff as a required deliverable if any dependencies change.

---

## Email Protocol Scanning

### Schema

- **EMAIL-00**: SQLite `Scan` model gains `email_scan_json` column (TEXT, nullable) following the `kerberos_scan_json` / `dat_scan_json` pattern in `models.py`.

### Scanner Coverage — All 7 Ports

- **EMAIL-01**: Scanner probes SMTP STARTTLS on port 25 and SMTP submission STARTTLS on port 587 using `sslyze` with `ProtocolWithOpportunisticTlsEnum.SMTP`. Returns cert chain, accepted cipher suites, TLS version range. Gracefully handles `CONNECTION_REFUSED` (port 25 commonly blocked on cloud VMs) without crashing.
- **EMAIL-02**: Scanner probes SMTPS implicit TLS on port 465 using existing `_scan_one_sslyze()` path (no `tls_opportunistic_encryption` param needed). Returns same data as EMAIL-01.
- **EMAIL-03**: Scanner probes IMAP STARTTLS on port 143 using `ProtocolWithOpportunisticTlsEnum.IMAP`.
- **EMAIL-04**: Scanner probes IMAPS implicit TLS on port 993 using existing sslyze direct-TLS path.
- **EMAIL-05**: Scanner probes POP3 STARTTLS on port 110 using `ProtocolWithOpportunisticTlsEnum.POP3`.
- **EMAIL-06**: Scanner probes POP3S implicit TLS on port 995 using existing sslyze direct-TLS path.
- **EMAIL-07**: Scanner falls back to stdlib (`smtplib.SMTP`, `imaplib.IMAP4`, `poplib.POP3`) for STARTTLS negotiation when sslyze fails; extracts TLS version, negotiated cipher, and cert from the underlying SSL socket using existing `_pubkey_info()` helpers.

### Findings

- **EMAIL-08**: Port-25 STARTTLS endpoints that successfully negotiate TLS emit an additional static MEDIUM finding: `starttls-downgrade-risk` — noting that STARTTLS is susceptible to stripping attacks that sslyze cannot detect agentlessly. This finding is emitted regardless of cipher strength.
- **EMAIL-09**: Weak cipher suites on email TLS endpoints (`TLS_RSA_WITH_*`, 3DES, RC4) produce HIGH findings. Non-PFS ECDHE without TLS 1.3 produces MEDIUM.
- **EMAIL-10**: Endpoint service_detail format: `"SMTP-STARTTLS:587"`, `"SMTPS:465"`, `"IMAPS:993"`, `"POP3S:995"` etc. for dashboard display and CBOM traceability.

### Chaos Lab

- **EMAIL-11**: New `email` Docker Compose profile — custom Postfix + Dovecot Dockerfile (ubuntu:22.04 base, no docker-mailserver or mailcow) with intentionally weak TLS: TLS 1.1 minimum, non-PFS RSA cipher suites (`AES128-SHA`, `AES256-SHA`), self-signed RSA-2048 cert. Port allocation: 30025 (SMTP), 30465 (SMTPS), 30587 (submission), 30143 (IMAP), 30993 (IMAPS), 30110 (POP3), 30995 (POP3S).
- **EMAIL-12**: `labs/email/expected_results.md` documents expected findings for the chaos lab profile (at minimum: STARTTLS stripping MEDIUM on port 30025, weak cipher HIGH, self-signed cert HIGH).

---

## Message Broker TLS

### Schema

- **BROKER-00**: SQLite `Scan` model gains `broker_scan_json` column (TEXT, nullable) for management API metadata and probe summaries. Follows `dat_scan_json` pattern.

### Architecture

- **BROKER-ARCH**: All broker scanning lives in a single `quirk/scanner/broker_scanner.py` module exposing `scan_kafka_targets()`, `scan_rabbitmq_targets()`, and `scan_redis_targets()` functions — parallel to `db_connector.py` (PostgreSQL + MySQL + RDS in one file). No per-broker files.

### Kafka

- **KAFKA-01**: Scanner probes Kafka broker TLS on port 9093 via `sslyze ServerScanRequest` (no new dependencies). Returns cert chain, accepted cipher suites, TLS version. Handles connection refused gracefully.
- **KAFKA-02**: Scanner detects plaintext Kafka on port 9092 via raw TCP probe; emits a HIGH finding (`kafka-plaintext-listener`) if port is open.
- **KAFKA-03**: Standard and deep scan profiles additionally probe port 9094 (MSK / SASL_SSL convention).
- **KAFKA-04 (optional)**: When `quirk[kafka]` extras are installed (`kafka-python`), scanner attempts `AdminClient.describe_configs()` for `ssl.enabled.protocols`, `ssl.client.auth`, `ssl.cipher.suites` — used as optional enrichment only. Full graceful degradation when library absent or API access denied (403/auth failure).

### RabbitMQ / AMQP

- **RABBIT-01**: Scanner probes AMQPS on port 5671 via `sslyze ServerScanRequest` (direct TLS, no STARTTLS — identical to port 443 path). Returns cert chain, accepted cipher suites, TLS version range.
- **RABBIT-02**: Scanner detects plaintext AMQP on port 5672 by sending raw AMQP 0-9-1 protocol header (`b'AMQP\x00\x00\x09\x01'`) over bare TCP; emits HIGH finding (`amqp-plaintext-listener`) if port responds with AMQP frame.
- **RABBIT-03**: Scanner probes RabbitMQ management HTTP API on port 15672 with `GET /api/overview` using default `guest:guest` credentials (best-effort only); extracts listener list and Erlang/RabbitMQ version for enrichment. Auth failure (401) emitted as informational data point, not an error.
- **RABBIT-04**: Scanner probes Azure Service Bus namespace AMQP 1.0 TLS on `{namespace}.servicebus.windows.net:5671` via sslyze (no credentials required for TLS layer). Tagged with `ep.protocol = "AMQPS/Azure-ServiceBus"`.
- **RABBIT-05**: Scanner probes AWS SQS TLS on `sqs.{region}.amazonaws.com:443` via sslyze. Tagged with `ep.protocol = "HTTPS/AWS-SQS"`.

### Redis / Valkey

- **REDIS-01**: Scanner probes Redis TLS on port 6380 via raw `ssl.SSLContext` socket wrap (existing `_try_handshake()` pattern from `tls_capabilities.py`). Returns TLS version, negotiated cipher, cert (subject, issuer, expiry, pubkey algorithm). Also supports sslyze deep probe in standard/deep profiles.
- **REDIS-02**: Scanner detects plaintext Redis on port 6379 by attempting a bare TCP connection; emits HIGH finding (`redis-plaintext-no-auth`) if port responds with Redis inline reply. No AUTH required.
- **REDIS-03 (optional)**: Scanner attempts `CONFIG GET tls-*` via `redis-py` (graceful degradation on `NOAUTH` / `NOPERM`); uses result as enrichment for detected TLS settings vs. configured TLS settings.

### Broker Chaos Lab

- **BROKER-LAB-01**: New `broker` Docker Compose profile containing three weak-TLS containers:
  - Kafka: `bitnami/kafka:3.7` (KRaft mode), ports 29092 (plaintext), 29093 (weak TLS — `TLS_RSA_WITH_AES_128_CBC_SHA`, `TLS_RSA_WITH_AES_256_CBC_SHA`, TLS 1.1+1.2 only, RSA-2048 self-signed cert).
  - RabbitMQ: `rabbitmq:3.12-management` (Erlang 25, supports TLS 1.0/1.1), ports 25672 (AMQP plaintext), 25671 (AMQPS weak TLS — 3DES, non-PFS CBC, TLS 1.0/1.1 enabled), 25015672 (management).
  - Redis: `redis:7-alpine` with mounted `redis.conf`, ports 26379 (plaintext, no auth), 26380 (TLS weak — 3DES cipher, TLS 1.2 only, self-signed RSA-2048 cert).
- **BROKER-LAB-02**: `labs/broker/expected_results.md` documents expected findings: at minimum plaintext HIGH (all three brokers), weak cipher HIGH (Kafka RSA key exchange, RabbitMQ 3DES, Redis 3DES), quantum-unsafe HIGH (RSA key exchange).

---

## Evidence Counters and Scoring

### Evidence Counters

- **MOTION-01**: `evidence.py` `EvidenceCounters` dataclass gains the following `motion_` fields:
  - `motion_email_starttls_missing_count` — SMTP without STARTTLS (HIGH)
  - `motion_email_plaintext_count` — IMAP/POP3 without TLS (HIGH)
  - `motion_email_weak_cipher_count` — weak cipher on email TLS (MEDIUM)
  - `motion_broker_plaintext_count` — Kafka/RabbitMQ/Redis plaintext listener (HIGH)
  - `motion_broker_weak_tls_count` — TLS 1.1 or older on broker (HIGH)
  - `motion_broker_weak_cipher_count` — RC4/3DES/non-PFS RSA on broker TLS (CRITICAL/HIGH)

### Scoring

- **MOTION-02**: `SCORE_WEIGHTS` in `scoring.py` gains motion_ ratio entries:
  - `"motion_email_plaintext_ratio": 12.0`
  - `"motion_email_weak_cipher_ratio": 6.0`
  - `"motion_broker_plaintext_ratio": 14.0`
  - `"motion_broker_weak_tls_ratio": 8.0`
  - `"motion_broker_weak_cipher_ratio": 6.0`
- **MOTION-03**: `PROFILE_MULTIPLIERS` gains `"motion_"` prefix key with values `{strict: 1.4, balanced: 1.0, lenient: 0.7}` — parallel to the existing `"identity_"` and `"dar_"` entries.
- **MOTION-04**: `compute_readiness_score()` returns `"data_in_motion"` as a named 6th subscore in the intelligence JSON, alongside `tls`, `ssh`, `api`, `identity`, `data_at_rest`.

---

## CBOM Integration

- **CBOM-01**: Email endpoints produce Pass 1 algorithm component entries (cert pubkey algorithm, negotiated TLS cipher suite) via the existing `cbom/classifier.py` + `cbom/builder.py` pipeline. No changes to `builder.py` required — `ep.protocol` label (`"SMTP-STARTTLS"`, `"SMTPS"`, `"IMAPS"`, `"POP3S"`) distinguishes email from HTTPS endpoints.
- **CBOM-02**: Broker TLS endpoints produce Pass 1 algorithm component entries via the same pipeline. `ep.protocol` set to `"AMQPS"`, `"KAFKA-TLS"`, `"REDIS-TLS"` as appropriate.
- **CBOM-03**: Plaintext-only broker endpoints (`"AMQP"`, `"KAFKA-PLAIN"`, `"REDIS-PLAIN"`) added to Pass 2 and Pass 3 skip lists in `builder.py` to prevent hollow `CertificateProperties` entries for endpoints with no TLS cert.
- **CBOM-04**: Quantum-safety classification for email and broker cipher suites follows the existing `QUANTUM_SAFETY_MAP` in `classifier.py`. `TLS_RSA_WITH_*` suites classified as `quantum-vulnerable` (HIGH); ECDHE as `quantum-vulnerable` (MEDIUM); TLS 1.3 AEAD as `quantum-unknown` (LOW).

---

## Dashboard

- **DASH-01**: New `/motion` React route and "Motion" tab in the dashboard navigation — parallel to the existing `Identity` and `Trends` tabs.
- **DASH-02**: Motion tab — Email surface section: per-port TLS posture summary (port, protocol, TLS version, cipher suite, cert expiry, quantum risk tier). Shows STARTTLS stripping warning badge on port-25 endpoints.
- **DASH-03**: Motion tab — Broker surface section: per-broker type (Kafka / RabbitMQ / Redis) TLS posture summary (endpoint, port, TLS version, cipher, plaintext-exposed flag).
- **DASH-04**: Executive summary card gains a "Data in Motion" score line (6th subscore) alongside the existing TLS, SSH, API, Identity, Data at Rest lines.
- **DASH-05**: FastAPI `/api/scan/latest` response schema gains `motion_findings: list[MotionFinding]` — parallel to `identity_findings`.

---

## Infrastructure

- **INFRA-01**: `quirk/__init__.py` and `pyproject.toml` version bumped to `4.4.0` at milestone close.
- **INFRA-02**: `pyproject.toml` gains `[motion]` extras group containing any new direct dependencies (e.g., `kafka-python` under `[kafka]` sub-extras if KAFKA-04 is implemented).
- **INFRA-03**: All 6 new scanner functions (`scan_email_targets`, `scan_kafka_targets`, `scan_rabbitmq_targets`, `scan_redis_targets`, and the Azure Service Bus / SQS probe paths) are exercised by Nyquist VALIDATION.md tests covering at minimum: happy path (TLS found), graceful degradation (connection refused), and plaintext-only detection.

---

## Requirements Summary

| Category | Requirements | Count |
|----------|-------------|-------|
| Structural carry-forward | STRUCT-01–03 | 3 |
| Email scanning | EMAIL-00–12 | 13 |
| Broker scanning | BROKER-ARCH, BROKER-00, KAFKA-01–04, RABBIT-01–05, REDIS-01–03, BROKER-LAB-01–02 | 18 |
| Evidence + scoring | MOTION-01–04 | 4 |
| CBOM integration | CBOM-01–04 | 4 |
| Dashboard | DASH-01–05 | 5 |
| Infrastructure | INFRA-01–03 | 3 |
| **Total** | | **50** |

---

## Research Basis

All requirements are grounded in parallel research conducted 2026-04-27:

- `.planning/research/email-tls-research.md` — sslyze STARTTLS API, port conventions, chaos lab options
- `.planning/research/kafka-tls-research.md` — Kafka TLS probe, Admin API, bitnami chaos lab
- `.planning/research/rabbitmq-amqp-research.md` — AMQPS direct TLS, management API, RabbitMQ 3.12 chaos lab
- `.planning/research/redis-broker-architecture-research.md` — Redis TLS probe, CONFIG GET, broker_scanner.py architecture, motion_ counter naming

---

*Requirements defined: 2026-04-27*

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STRUCT-01 | 32, 33, 37 | Complete |
| STRUCT-02 | 32, 33, 37 | Complete |
| STRUCT-03 | 32, 33, 37 | Complete |
| EMAIL-00 | 32 | Complete |
| EMAIL-01 | 32 | Complete |
| EMAIL-02 | 32 | Complete |
| EMAIL-03 | 32 | Complete |
| EMAIL-04 | 32 | Complete |
| EMAIL-05 | 32 | Complete |
| EMAIL-06 | 32 | Complete |
| EMAIL-07 | 32 | Complete |
| EMAIL-08 | 32 | Complete |
| EMAIL-09 | 32 | Complete |
| EMAIL-10 | 32 | Complete |
| EMAIL-11 | 32 | Complete |
| EMAIL-12 | 32 | Complete |
| BROKER-00 | 33 | Pending |
| BROKER-ARCH | 33 | Pending |
| KAFKA-01 | 33 | Pending |
| KAFKA-02 | 33 | Pending |
| KAFKA-03 | 33 | Pending |
| KAFKA-04 | 33 | Pending |
| RABBIT-01 | 33 | Pending |
| RABBIT-02 | 33 | Pending |
| RABBIT-03 | 33 | Pending |
| RABBIT-04 | 33 | Pending |
| RABBIT-05 | 33 | Pending |
| REDIS-01 | 33 | Pending |
| REDIS-02 | 33 | Pending |
| REDIS-03 | 33 | Pending |
| BROKER-LAB-01 | 33 | Pending |
| BROKER-LAB-02 | 33 | Pending |
| MOTION-01 | 34 | Pending |
| MOTION-02 | 34 | Pending |
| MOTION-03 | 34 | Pending |
| MOTION-04 | 34 | Pending |
| CBOM-01 | 35 | Pending |
| CBOM-02 | 35 | Pending |
| CBOM-03 | 35 | Pending |
| CBOM-04 | 35 | Pending |
| DASH-01 | 36 | Pending |
| DASH-02 | 36 | Pending |
| DASH-03 | 36 | Pending |
| DASH-04 | 36 | Pending |
| DASH-05 | 36 | Pending |
| INFRA-01 | 37 | Pending |
| INFRA-02 | 37 | Pending |
| INFRA-03 | 37 | Pending |

**Coverage:** 50/50 requirements mapped (100%) ✓

*Traceability added: 2026-04-27*

