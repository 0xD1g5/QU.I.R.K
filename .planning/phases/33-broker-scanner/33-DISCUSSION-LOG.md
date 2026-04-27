# Phase 33: Broker Scanner - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-27
**Phase:** 33-broker-scanner
**Areas discussed:** Cloud broker target plumbing, Optional client libraries (KAFKA-04 / REDIS-03), Profile gating + broker_scan_json schema, Chaos lab base images

---

## Cloud broker target plumbing (RABBIT-04, RABBIT-05)

| Option | Description | Selected |
|--------|-------------|----------|
| CLI flags + config | `--aws-sqs-region` and `--azure-servicebus-namespace`, also config.yaml. broker_scanner stays standalone, no Azure SDK enumeration added. | ✓ |
| Piggyback on cloud connectors | AWS region from aws_connector config; extend azure_connector to enumerate Service Bus namespaces via Azure SDK. Adds Azure SDK surface; requires new Azure RBAC role. | |
| Config.yaml only | No CLI flags. cfg.scanners.broker.{sqs_regions, azure_namespaces} only. Lightest plumbing; matches consulting use case where configs survive across runs. | |

**User's choice:** CLI flags + config (Recommended)
**Notes:** Recommendation accepted directly. Rationale captured in CONTEXT.md D-01/D-02: keeps broker_scanner.py free of Azure SDK / boto3 imports, preserves BROKER-ARCH "three functions, one file" simplicity, and avoids forcing a new Azure RBAC role for Service Bus enumeration.

---

## Optional client libraries (KAFKA-04 kafka-python, REDIS-03 redis-py)

| Option | Description | Selected |
|--------|-------------|----------|
| Sub-extras | `[motion]` empty, `[kafka]=['kafka-python']`, `[redis]=['redis']`. `pip install quirk[motion,kafka,redis]` for full enrichment. Honors "optional" tag in requirements. | ✓ |
| Fold into [motion] | `[motion]=['kafka-python','redis']`. Single install command for everyone. Loses opt-out for email-only consultants. | |
| Defer to v4.5 | `[motion]` empty, KAFKA-04 / REDIS-03 stubbed (no-op or NotImplementedError). Phase 33 ships TLS scanning only; enrichment waits. | |

**User's choice:** Sub-extras (Recommended)
**Notes:** Honors the "optional" tag explicitly used in REQUIREMENTS.md for KAFKA-04 / REDIS-03. STRUCT-02 satisfied by declaring `[motion]` group (empty). Captured in CONTEXT.md D-06 through D-09 — including the silent-on-auth-failure rule for enrichment paths (D-08).

---

## Profile gating + broker_scan_json schema

| Option | Description | Selected |
|--------|-------------|----------|
| Standard+deep, nested schema | Match email profile gating. broker_scan_json shaped {kafka:[], rabbitmq:[], redis:[], azure_servicebus:[], aws_sqs:[]} for direct DASH-03 rendering. | ✓ |
| Standard+deep, flat schema | Same profile gating as email. broker_scan_json flat per-host. Simpler SQL, but dashboard re-buckets at render time. | |
| Deep-only, nested schema | Broker scanning only on --profile deep. Acknowledges plaintext-probe footprint. Nested schema retained. | |
| Deep-only, flat schema | Most conservative footprint, simplest schema. Power-user opt-in only. | |

**User's choice:** Standard+deep, nested schema (Recommended)
**Notes:** Profile gating captured in CONTEXT.md D-10/D-11. Schema shape captured in D-12/D-13/D-14 — driven by Phase 36 DASH-03's "per-broker-type summary" rendering. Footprint concern (RabbitMQ management UI showing `guest:guest` probe; broker connection logs showing plaintext probes) acknowledged but accepted under consulting engagement-letter assumption.

---

## Chaos lab base images (BROKER-LAB-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Bitnami | bitnami/kafka, bitnami/rabbitmq, bitnami/redis. Env-var-driven weak-TLS config; single-purpose images; ecosystem-realistic. | ✓ |
| Official upstream | apache/kafka, rabbitmq:3-management, redis:7. Smaller, but TLS configuration paths differ per image (Compose file becomes inconsistent). | |
| Hand-rolled from ubuntu:22.04 | Custom Dockerfiles install each broker via apt/tarball. Maximum control, but Kafka install from scratch is painful (Java + KRaft/Zookeeper + log dirs). | |

**User's choice:** Bitnami (Recommended)
**Notes:** Bitnami env-var-driven TLS configuration keeps the Compose file readable across all three brokers (Kafka KAFKA_TLS_TYPE, RabbitMQ RABBITMQ_SSL_*, Redis REDIS_TLS_*). Captured in CONTEXT.md D-15 through D-18, including the explicit "do not reuse certs/scenarios/" rule (D-17) carried forward from Phase 32.

---

## Claude's Discretion

- Internal helper organization inside `broker_scanner.py` — whether `scan_rabbitmq_targets()` includes Azure SB + AWS SQS probes inline or via `_scan_azure_servicebus_target` / `_scan_aws_sqs_target` helpers.
- AMQP-header byte sequence handling for plaintext detection (timeout values, response-frame parsing depth, false-positive suppression).
- Whether `kafka-python` `AdminClient.describe_configs()` enrichment runs over the same TLS connection as the sslyze probe or opens fresh.
- Logging verbosity per port-refused / per-fallback event — follow tls_scanner.py / email_scanner.py conventions.
- `--include-broker` / `--no-broker` override flags — only if profile-toggle pattern cleanly exposes scanner-level overrides.

## Deferred Ideas

- Auto-discovery of Azure Service Bus namespaces via Azure SDK (would extend azure_connector.py) — v4.5 candidate.
- AWS SQS auto-region from boto3 Session — v4.5 candidate.
- `--no-broker` opt-out flag — escape hatch for D-11 footprint concern; revisit post-release if needed.
- Active broker auth probing beyond `guest:guest` — explicit auth-attack territory; never implement.
- Folding `kafka-python` / `redis-py` into `[motion]` — rejected D-06; revisit only if sub-extras prove confusing in v4.5.
- DAR dashboard tab (DASH-05 carry-forward from Phase 27) — not in scope for Phase 33.
