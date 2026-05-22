# labs/kafka-tls

**Phase 89 / LAB-04** — Standalone Apache Kafka with intentionally weak TLS configuration.

## Purpose

Provides an isolated Kafka-TLS target using `apache/kafka:3.9.0` (KRaft mode) that
exposes RSA key-exchange cipher suites (no forward secrecy) and a plaintext listener.
The scanner exercises `broker_scanner.py scan_kafka_targets()` on host ports
**39092** (PLAINTEXT) and **39093** (TLS).

This is a **standalone** profile — it is NOT part of the `broker` profile. The broker
profile's `kafka-broker` service (apache/kafka:3.7.0) is unchanged.

## Intentional Weaknesses (D-02)

| Setting | Value | Why it is weak |
|---------|-------|----------------|
| `ssl.cipher.suites` | `TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA` | RSA key exchange, no forward secrecy; quantum-vulnerable |
| `ssl.enabled.protocols` | `TLSv1.2` | TLS 1.2 only; TLS 1.3 disabled |
| `listeners` | `PLAINTEXT://:9092,SSL://:9093` | Plaintext listener exposed alongside TLS |
| Cert | RSA-2048 self-signed | RSA-2048 is quantum-vulnerable |

**DO NOT use this configuration in production.**

## Expected Findings

| Finding | Severity | Rule |
|---------|----------|------|
| Kafka plaintext listener on port 39092 | HIGH | KAFKA-02 |
| Weak cipher suite (RSA key exchange, no PFS) on TLS port 39093 | HIGH | KAFKA-01 |
| RSA-2048 certificate (quantum-vulnerable) on port 39093 | MEDIUM | TLS-02 |

## PEM Keystore Note

Uses `ssl.keystore.type=PEM` with the two-property form:
- `ssl.keystore.certificate.chain` — cert file path
- `ssl.keystore.key` — key file path

This avoids the combined-PEM ambiguity (RESEARCH Pitfall 2) and is the
recommended form for separate cert + key files with `apache/kafka:3.9.0`.

## Healthcheck

The healthcheck uses the **PLAINTEXT port 9092** to avoid needing a truststore or
client certificate. The SSL port 9093 is reachable but not used for healthchecks.

## Cert Generation

```bash
cd labs/kafka-tls
make certs
```

Generates `certs/kafka-tls.crt` and `certs/kafka-tls.key`.

## Start

```bash
cd quantum-chaos-enterprise-lab
PROFILE_ARGS="--profile kafka-tls" ./lab.sh up
```

Kafka will be available on:
- `localhost:39092` — PLAINTEXT
- `localhost:39093` — TLS (weak ciphers)
