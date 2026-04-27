# Phase 33: Broker Scanner - Context

**Gathered:** 2026-04-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver `quirk/scanner/broker_scanner.py` — a single canonical module exposing `scan_kafka_targets()`, `scan_rabbitmq_targets()`, and `scan_redis_targets()` (BROKER-ARCH). Audits TLS posture on Kafka (9092 plaintext / 9093 TLS / 9094 SASL_SSL), RabbitMQ/AMQPS (5672 plaintext / 5671 AMQPS), Redis (6379 plaintext / 6380 TLS), Azure Service Bus (`{namespace}.servicebus.windows.net:5671`), and AWS SQS (`sqs.{region}.amazonaws.com:443`). Persists per-host probe results to a new `broker_scan_json` SQLite column and ships a `labs/broker/` Bitnami-based chaos lab profile. Motion subscore wiring is **Phase 34**; CBOM integration is **Phase 35**; dashboard `/motion` tab is **Phase 36**. Broker scanning develops architecturally parallel to Phase 32 (Email Scanner) but uses three transport mechanics (sslyze for Kafka/RabbitMQ TLS, raw `ssl.SSLContext` for Redis since sslyze cannot speak the Redis handshake, raw TCP+AMQP-header bytes for plaintext detection).

</domain>

<decisions>
## Implementation Decisions

### Cloud broker target plumbing (RABBIT-04, RABBIT-05)
- **D-01:** Azure Service Bus namespaces and AWS SQS regions are supplied via **CLI flags + config.yaml**. Flags: `--azure-servicebus-namespace <name>` (repeatable) and `--aws-sqs-region <region>` (repeatable). Config keys: `cfg.scanners.broker.azure_namespaces: [...]` and `cfg.scanners.broker.sqs_regions: [...]`.
- **D-02:** `broker_scanner.py` does **NOT** import or call Azure SDK / boto3 to enumerate namespaces or regions. Inputs come from CLI/config only. Keeps scanner standalone-testable and preserves BROKER-ARCH "three functions, one file" simplicity.
- **D-03:** `scan_rabbitmq_targets()` constructs `{namespace}.servicebus.windows.net:5671` per supplied namespace and probes via sslyze (RABBIT-04). No credentials needed for the TLS layer. `ep.protocol = "AMQPS/Azure-ServiceBus"` per requirement.
- **D-04:** A separate cloud-target probe function (or `scan_rabbitmq_targets()` extension — planner's call) constructs `sqs.{region}.amazonaws.com:443` per supplied region and probes via sslyze (RABBIT-05). `ep.protocol = "HTTPS/AWS-SQS"` per requirement.
- **D-05 (deferred):** Auto-discovery of Azure Service Bus namespaces via Azure SDK (would extend `azure_connector.py`) is **out of scope for v4.4**. Captured as backlog idea.

### Optional client libraries (KAFKA-04, REDIS-03)
- **D-06:** Optional client libraries ship as **sub-extras** under `pyproject.toml`: `[motion]` declared empty (per STRUCT-02), `[kafka] = ["kafka-python>=2.0"]`, `[redis] = ["redis>=5.0"]`. Install via `pip install quirk[motion,kafka,redis]` for full enrichment.
- **D-07:** `kafka-python` and `redis-py` imports inside `broker_scanner.py` MUST be guarded (`try: import kafka` / `try: import redis`). Library-absent path returns the basic sslyze/raw-socket TLS probe results unchanged. Library-present path adds the AdminClient / `CONFIG GET tls-*` enrichment dict to the broker_scan_json payload.
- **D-08:** Auth-failure paths (`NOAUTH`/`NOPERM` for Redis, `403` / Kafka authorizer denial) degrade silently — log at DEBUG, continue with the basic TLS probe. Do NOT emit a finding for "could not enrich" — enrichment is opportunistic, not a security signal.
- **D-09:** RABBIT-03 (RabbitMQ management API `GET /api/overview` with default `guest:guest`) uses stdlib `urllib.request` — no `requests` dependency added. Auth failure (401) is an informational data point, NOT an error or finding (per requirement text).

### Profile gating
- **D-10:** Broker scanning runs in **`standard` and `deep`** profiles only — matches Phase 32 (email) gating. Excluded from `quick`. Adds `cfg.scanners.broker_enabled` flag in `quirk/engine/profiles.py:apply_profile()` (parallel to `email_enabled`).
- **D-11:** Footprint warning (RabbitMQ management UI shows the `guest:guest` probe; broker connection logs show plaintext probes) is acknowledged but accepted — consultants run scans under engagement letters that authorize this. If footprint complaints arise post-release, a `--no-broker` flag becomes the v4.5 escape hatch (not in scope for Phase 33).

### `broker_scan_json` schema shape (BROKER-00)
- **D-12:** `broker_scan_json` payload is **nested per protocol family**, not flat per host. Top-level keys: `kafka`, `rabbitmq`, `redis`, `azure_servicebus`, `aws_sqs`. Each value is a list of per-target probe result dicts.
- **D-13:** Schema design is driven by DASH-03 (Phase 36 Motion tab): "per-broker-type summary" is the natural rendering. Storing nested means the dashboard reads the column shape directly without re-bucketing.
- **D-14:** Aggregation onto a single per-scan row happens at scan-write time in `run_scan.py` (mirrors Phase 32's `email_scan_json` aggregation pattern at `email_scanner.py:550–599`). The first endpoint of the first host carries the full nested payload; other endpoints carry NULL.

### Chaos lab base images (BROKER-LAB-01)
- **D-15:** `labs/broker/` uses **Bitnami images**: `bitnami/kafka:3.6` (or pinned current), `bitnami/rabbitmq:3.12`, `bitnami/redis:7.2`. Env-var-driven weak-TLS configuration (no bind-mounted `server.properties` for Kafka, no custom `rabbitmq.conf` files needed, no Redis `redis.conf` overlay). Compose stays readable.
- **D-16:** Each container exposes both plaintext and TLS ports per BROKER-LAB-01 mapping: Kafka 29092/29093, RabbitMQ 25672/25671, Redis 26379/26380. Plaintext ports are **intentionally listening** so plaintext-detection findings fire.
- **D-17:** Self-signed certs generated freshly per `labs/broker/Makefile` (or labs-level Makefile target). Same pattern as Phase 32 `labs/email/`: TLS 1.1 minimum, RSA non-PFS ciphers (`AES128-SHA`, `AES256-SHA`, at least one 3DES-bearing suite), self-signed RSA-2048 cert. **Do not** reuse `certs/scenarios/` — chaos lab stays decoupled from legacy CA.
- **D-18:** Compose profile name = `broker` per BROKER-LAB-01. Lives in the same compose structure that already powers `--profile email`, `--profile storage`, etc.

### Claude's Discretion
- Internal helper organization inside `broker_scanner.py`: whether `scan_rabbitmq_targets()` includes the cloud probes (Azure SB + AWS SQS) inline or via separate helpers (`_scan_azure_servicebus_target`, `_scan_aws_sqs_target`) — planner decides based on readability.
- Exact AMQP-header byte sequence handling for RABBIT-02 plaintext detection (`b'AMQP\\x00\\x00\\x09\\x01'`) — timeout values, response-frame parsing depth, false-positive suppression. Follow the conservative pattern: 2s timeout, accept any `b'AMQP'` prefix in response as positive.
- Whether the `kafka-python` `AdminClient.describe_configs()` enrichment runs over the same TLS connection as the sslyze probe or opens a fresh connection — planner decides based on connection-reuse cost vs. clean separation.
- Logging verbosity per port-refused / per-fallback event — follow `tls_scanner.py` and `email_scanner.py` conventions.
- Whether `--include-broker` / `--no-broker` override flags are wired — only if existing profile-toggle pattern cleanly exposes scanner-level overrides (mirrors D-07 from Phase 32).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap (locked)
- `.planning/REQUIREMENTS.md` §"Broker Scanning" — BROKER-00, BROKER-ARCH, KAFKA-01–04, RABBIT-01–05, REDIS-01–03, BROKER-LAB-01–02 are LOCKED. Do not redefine.
- `.planning/REQUIREMENTS.md` §"Structural Requirements" — STRUCT-01 (`session_start` parameter), STRUCT-02 (`[motion]` extras at plan time), STRUCT-03 (`pyproject.toml` diff in PLAN.md).
- `.planning/ROADMAP.md` Phase 33 entry — Broker Scanner goal + 6 success criteria.

### Research (validated 2026-04-27 from prior milestone synthesis)
- `.planning/research/SUMMARY.md` — milestone-level synthesis covering email + broker surfaces.
- `.planning/research/email-tls-research.md` — referenced because broker_scanner mirrors `email_scanner.py`'s sslyze-+-fallback shape; the sslyze API conventions documented there transfer.

### Pattern templates (read before writing scanner code)
- `quirk/scanner/db_connector.py` — **architectural precedent for BROKER-ARCH**. Single file, multiple `scan_*_targets()` functions (PostgreSQL + MySQL + RDS in one module). `scan_pg_targets` (line 54), `scan_mysql_targets` (line 170). Mirror this structural pattern.
- `quirk/scanner/email_scanner.py` — Phase 32 implementation reference. 4-function shape per protocol: `_scan_one_sslyze_email` (line 112), `_scan_one_fallback_email` (line 380), `scan_one_email` (line 485), `scan_email_targets` (line 509). Per-host JSON aggregation pattern (line 550–599) is the model for `broker_scan_json` aggregation.
- `quirk/scanner/tls_scanner.py:_pubkey_info()` — extracts `(algorithm, key_size, modulus)` from cert. Redis raw `ssl.SSLContext` path (REDIS-01) calls this directly on the SSLSocket peer cert.
- `quirk/scanner/tls_capabilities.py` — `_try_handshake()` raw-socket pattern is the model for the Redis 6380 probe.
- `quirk/engine/profiles.py:apply_profile()` (line 6) — where D-10 broker_enabled flag wiring lands; lines 75–126 show Phase 32's email_enabled pattern to mirror.
- `quirk/scanner/aws_connector.py:scan_aws_targets(region, ...)` (line 416) — region-input pattern reference. Broker scanner does NOT import this; only the input-shape convention is borrowed.
- `quirk/scanner/azure_connector.py:scan_azure_targets(...)` (line 229) — Azure connector input shape reference. Broker scanner does NOT import this either.

### Configuration & integration
- `quirk/scanner/__init__.py` — broker_scanner registration alongside email_scanner.
- `quirk/db/models.py` — add `broker_scan_json` TEXT NULL column on the `Scan` model, mirroring `email_scan_json` (Phase 32) and `dat_scan_json` (Phase 31).
- `run_scan.py` — Phase 32 added the email integration call site after `scan_tls_targets`. Phase 33 adds broker calls after the email block, gated on `cfg.scanners.broker_enabled`.
- `quirk/cbom/classifier.py` — Phase 35 consumes `ep.protocol` labels from this phase's emitted endpoints (`KAFKA-TLS`, `KAFKA-PLAIN`, `AMQPS`, `AMQP`, `REDIS-TLS`, `REDIS-PLAIN`, `AMQPS/Azure-ServiceBus`, `HTTPS/AWS-SQS`). Phase 33 must produce these labels in the format Phase 35 expects; no Phase 33 changes to classifier.py.

### Carry-forward decisions (from Phase 32 CONTEXT)
- 4-function scanner shape per protocol family (already cited above).
- `session_start` plumbing flows from `run_scan.py` → `scan_*_targets(targets, session_start, ...)` → all per-target work. No `datetime.now()` calls inside the scanner module.
- CONNECTION_REFUSED is silent at DEBUG (carry-forward from v4.2 / Phase 32 D-03).
- Findings are **layered**, not merged — a Kafka 9092 plaintext + 9093 weak-cipher host emits both `kafka-plaintext-listener` HIGH AND `weak-cipher` HIGH (parallel to Phase 32 D-11/D-12).
- Reuse the existing TLS target list verbatim for Kafka/RabbitMQ/Redis self-hosted ports (parallel to Phase 32 D-01/D-02). Cloud broker targets (Azure SB, AWS SQS) are the exception — they require explicit flags/config (D-01 above) because they are managed-service identifiers, not IPs.

### Carry-forward from Phase 32 PATTERNS.md
- `.planning/phases/32-email-scanner/32-PATTERNS.md` — Phase 32's pattern map. Phase 33 planner will produce a parallel PATTERNS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/scanner/db_connector.py` — single-file multi-protocol scanner architecture. Direct precedent for BROKER-ARCH.
- `quirk/scanner/email_scanner.py:550–599` — per-host JSON aggregation onto first endpoint. Reuse this pattern verbatim for `broker_scan_json` aggregation.
- `quirk/scanner/tls_scanner.py:_pubkey_info()` — pubkey metadata extractor. Redis raw-socket path (REDIS-01) calls this directly.
- `quirk/scanner/tls_capabilities.py:_try_handshake()` — raw `ssl.SSLContext.wrap_socket()` pattern. Redis 6380 probe template.
- `sslyze.ServerScanRequest` (already a project dep) — handles Kafka 9093, RabbitMQ 5671, Azure SB 5671, AWS SQS 443. No new direct dep needed for the basic TLS layer.

### Established Patterns
- **Multi-protocol single-file scanner:** db_connector.py exposes 3 protocol-family functions in one file. Broker scanner mirrors this exactly with 3 functions for Kafka / RabbitMQ / Redis (and the Azure SB + AWS SQS probes folded into RabbitMQ since they speak AMQP-over-TLS / HTTPS, not their own protocols at our depth).
- **Optional dependency import guards:** stdlib pattern `try: import kafka except ImportError: kafka = None` then `if kafka is not None: ...` at call sites. No QU.I.R.K.-internal helper exists; planner writes one or duplicates the guard inline.
- **Profile toggling:** `apply_profile(cfg, profile, safe_mode)` mutates `cfg.scanners.*_enabled` flags. Add `broker_enabled = True` for standard/deep, False for quick. Mirror lines 90/107/126 of profiles.py (the email_enabled pattern from Phase 32).
- **Chaos lab layout:** `labs/<surface>/{docker-compose.yml | Dockerfile | certs/ | expected_results.md}`. Match this for `labs/broker/`.

### Integration Points
- `run_scan.py` after the email block — new `scan_kafka_targets`, `scan_rabbitmq_targets`, `scan_redis_targets` call site gated on `cfg.scanners.broker_enabled`.
- `quirk/db/models.py` — add `broker_scan_json` TEXT NULL column on `Scan`.
- `quirk/db/migrations/` (or equivalent migration site) — schema migration adding `broker_scan_json` column. Mirror Phase 32's `email_scan_json` migration shape.
- `quirk/engine/findings.py` (or equivalent) — register finding IDs: `kafka-plaintext-listener`, `amqp-plaintext-listener`, `redis-plaintext-no-auth`, `weak-cipher` (already exists from Phase 32 / earlier).
- `quirk/cli/__init__.py` (or equivalent CLI module) — new flags `--azure-servicebus-namespace` and `--aws-sqs-region` (both repeatable).
- `quirk/config_template.yaml` — add `scanners.broker.{azure_namespaces, sqs_regions}` defaults (empty lists).
- `quirk/cbom/classifier.py` (Phase 35 consumer) — no changes in Phase 33; just produce the right `ep.protocol` strings.

</code_context>

<specifics>
## Specific Ideas

- **Mirror `db_connector.py` exactly** for the multi-protocol single-file shape. Mirror `email_scanner.py` exactly for the per-protocol 4-function shape and per-host JSON aggregation.
- **Bitnami over upstream / hand-rolled** for chaos lab. Env-var-driven weak-TLS config keeps the Compose file readable. Image-size argument doesn't apply on consultant workstations.
- **Cloud-service probes folded into `scan_rabbitmq_targets()`** (Claude's discretion to split) — both Azure SB (AMQPS/5671) and AWS SQS (HTTPS/443) speak TLS-only, no broker-protocol-specific handshake. They fit the AMQPS code path, not their own modules.
- **REDIS-03 enrichment via `redis-py`** uses `CONFIG GET tls-*` (a glob pattern Redis supports). On `NOAUTH`, attempt `AUTH default ""` (empty password) once, fail silently if rejected — no AUTH-attack pattern.
- **KAFKA-04 enrichment** via `AdminClient.describe_configs(ConfigResource(BROKER, '0'))` — broker ID 0 is the convention. Multi-broker clusters: enumerate via `list_topics().brokers` first, then describe one. Planner picks depth.

</specifics>

<deferred>
## Deferred Ideas

- **Auto-discovery of Azure Service Bus namespaces via Azure SDK** — would extend `azure_connector.py` with `ServiceBusManagementClient.namespaces.list()`. Captured as v4.5 backlog idea.
- **AWS SQS auto-region from `boto3` Session** — `session.get_available_regions('sqs')` could populate `--aws-sqs-region` automatically. Out of scope for v4.4 (D-02: scanner stays standalone). v4.5 candidate.
- **`--no-broker` opt-out flag** — D-11 footprint escape hatch. Not in scope for Phase 33; revisit if footprint complaints arise post-release.
- **Active broker auth probing (default credentials beyond `guest:guest`)** — explicit auth-attack territory, not consulting-grade. Document as out-of-scope; never implement.
- **Folding `kafka-python` / `redis-py` into `[motion]`** — rejected (D-06). Revisit only if v4.5 sub-extras prove confusing in practice.
- **`motion_` evidence counters and scoring** — Phase 34.
- **CBOM integration for broker endpoints** — Phase 35.
- **Dashboard `/motion` tab** — Phase 36.
- **DAR dashboard tab (DASH-05 carry-forward from Phase 27)** — separate UI work; not in scope for Phase 33.

</deferred>

---

*Phase: 33-broker-scanner*
*Context gathered: 2026-04-27*
