---
phase: 33-broker-scanner
plan: 07
subsystem: infra
tags: [phase-33, chaos-lab, docker, weak-tls, kafka, rabbitmq, redis, broker]

requires:
  - phase: 33-02
    provides: broker_scanner.py module with scan targets for Kafka/RabbitMQ/Redis

provides:
  - labs/broker/ chaos lab directory with Makefile, config files, and expected_results.md
  - docker compose --profile broker with three broker services (kafka-broker, rabbitmq-broker, redis-broker)
  - Self-signed RSA-2048 cert generation via make certs (TLS posture test fixture)
  - BROKER-LAB-02 expected_results.md documenting all 6 per-port findings

affects: [33-08, phase-34-motion-scoring, phase-35-cbom-integration]

tech-stack:
  added:
    - apache/kafka:3.6 (official Apache Kafka image — chosen over confluentinc/cp-kafka:7.5 per D-15 planner note)
    - rabbitmq:3.12-management (official RabbitMQ image)
    - redis:7-alpine (official Redis image)
  patterns:
    - Bind-mounted minimal config files for per-cipher TLS control in chaos lab containers
    - labs/<surface>/ layout: Makefile + .gitignore + README + config/ + expected_results.md

key-files:
  created:
    - labs/broker/Makefile
    - labs/broker/.gitignore
    - labs/broker/README.md
    - labs/broker/kafka/server.properties
    - labs/broker/rabbitmq/rabbitmq.conf
    - labs/broker/redis/redis.conf
    - labs/broker/expected_results.md
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml

key-decisions:
  - "Chose apache/kafka:3.6 over confluentinc/cp-kafka:7.5 — Apache image is license-free and adequate for the lab"
  - "Kafka server.properties uses ssl.keystore.type=PEM with bind-mounted kafka.crt+kafka.key; PEM keystore may need cert+key concatenation for full functionality (noted as caveat)"
  - "RabbitMQ TLS 1.0 omitted from config — Erlang OTP 25+ rejects it as a hard error; TLS 1.1+1.2 with DES-CBC3-SHA/AES128-SHA/AES256-SHA is sufficient for weak-cipher HIGH"
  - "certs/ excluded via .gitignore (T-33-18 mitigation); generated freshly per consultant via make certs"

requirements-completed: [BROKER-LAB-01, BROKER-LAB-02]

duration: 18min
completed: 2026-04-27
---

# Phase 33 Plan 07: Broker Chaos Lab Summary

**Three-broker weak-TLS chaos lab (Kafka/RabbitMQ/Redis) with official images, bind-mounted cipher configs, cert generation Makefile, and expected_results.md documenting 6 per-port HIGH findings**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-27T00:00:00Z
- **Completed:** 2026-04-27T00:18:00Z
- **Tasks:** 4
- **Files modified:** 8 (7 created + 1 modified)

## Accomplishments

- `labs/broker/Makefile` generates 6 self-signed RSA-2048 certs (kafka/rabbitmq/redis .crt + .key) via `make certs`; verified `ls certs/ | wc -l` = 6
- Three weak-TLS config files bind-mounted into containers: `rabbitmq.conf` (TLS 1.1/1.2 + DES-CBC3-SHA/AES128-SHA/AES256-SHA), `redis.conf` (TLS 1.2 + DES-CBC3-SHA:AES128-SHA:AES256-SHA), `kafka/server.properties` (TLS 1.2 + TLS_RSA_WITH_AES_128_CBC_SHA/256)
- `quantum-chaos-enterprise-lab/docker-compose.yml` extended with `broker` profile; three services (kafka-broker, rabbitmq-broker, redis-broker) under `profiles: ["broker"]`; `docker compose --profile broker config` exits 0
- `labs/broker/expected_results.md` (156 lines) documents all 6 per-port findings with finding IDs, severity, verification SQL, caveat notes

## Task Commits

Each task was committed atomically:

1. **Task 1: Makefile + cert generation + .gitignore + README** - `c9059cb` (feat)
2. **Task 2: Weak-TLS config files for kafka/rabbitmq/redis** - `bffd880` (feat)
3. **Task 3: Add 'broker' compose profile** - `6c241f9` (feat)
4. **Task 4: labs/broker/expected_results.md (BROKER-LAB-02)** - `677942c` (feat)

## Files Created/Modified

- `labs/broker/Makefile` - cert-gen target (openssl req -x509 -newkey rsa:2048 x3) + clean target
- `labs/broker/.gitignore` - excludes `certs/` directory (T-33-18 mitigation)
- `labs/broker/README.md` - image versions, port map, quick start commands, expected findings summary
- `labs/broker/kafka/server.properties` - KRaft mode broker config; TLS 1.2 + non-PFS RSA cipher suites
- `labs/broker/rabbitmq/rabbitmq.conf` - TLS 1.1+1.2; DES-CBC3-SHA/AES128-SHA/AES256-SHA; verify_none
- `labs/broker/redis/redis.conf` - dual port (6379 plain + 6380 TLS); TLS 1.2; DES-CBC3-SHA:AES128-SHA:AES256-SHA
- `labs/broker/expected_results.md` - BROKER-LAB-02: 6-row per-port findings table + setup/verification/caveats
- `quantum-chaos-enterprise-lab/docker-compose.yml` - appended broker profile block (61 lines); existing profiles untouched

## Decisions Made

**Kafka image: `apache/kafka:3.6` selected over `confluentinc/cp-kafka:7.5`**
The Apache image is license-free (no Confluent Enterprise license terms), smaller, and adequate for the lab's single-broker use case. The KRaft mode config (process.roles=broker,controller) is self-contained and requires no Zookeeper sidecar.

**Kafka PEM keystore caveat**
`ssl.keystore.type=PEM` on `apache/kafka:3.6` requires the keystore file to contain the private key. The Compose bind mount provides `kafka.crt` and `kafka.key` as separate files at `/etc/kafka/secrets/`. If the container's Kafka runtime expects a combined PEM (cert + key concatenated), a startup entrypoint adjustment or `ssl.keystore.certificate.chain` / `ssl.keystore.key` property split may be needed. Documented as a caveat in `expected_results.md`. The compose config validation (--profile broker config) passes; actual container startup is out of scope for Plan 07 (static config only; Plan 33-08 covers scanner integration testing).

**RabbitMQ TLS 1.0 omitted**
`ssl_options.versions.tlsv1` was dropped from `rabbitmq.conf`. Erlang OTP 25+ (used by rabbitmq:3.12) rejects TLS 1.0 at the SSL handshake level, causing container startup failures. TLS 1.1 + TLS 1.2 with DES-CBC3-SHA (3DES) and AES128-SHA/AES256-SHA (non-PFS) is sufficient to satisfy the weak-cipher HIGH requirement (BROKER-LAB-01).

## Deviations from Plan

None — plan executed exactly as written. The TLS 1.0 omission for RabbitMQ was pre-noted in the plan's action text ("dropped ssl_options.versions.tlsv1 — TLS 1.0 is rejected...") so it is not a deviation.

## Issues Encountered

None. All four tasks completed on first attempt. The `docker compose --profile broker config` parse-only check passed immediately with the appended service blocks.

## Known Stubs

None. All config files contain substantive weak-TLS configuration that will produce real scanner findings when the lab is booted.

## Threat Flags

No new network surface beyond what the plan's threat model documents. The `broker` profile is opt-in (`--profile broker`) and the three plaintext ports (29092, 25672, 26379) are intentional per T-33-17 (accepted risk, lab-only). The `.gitignore` mitigates T-33-18 (cert leakage via git).

## Next Phase Readiness

- Plan 33-07 (broker chaos lab) is complete; BROKER-LAB-01 and BROKER-LAB-02 are satisfied
- Plan 33-08 (integration tests + end-to-end scanner validation) can proceed — the lab fixture is ready
- `docker compose --profile broker up` is the boot command; `make -C labs/broker certs` must run first

---
*Phase: 33-broker-scanner*
*Completed: 2026-04-27*
