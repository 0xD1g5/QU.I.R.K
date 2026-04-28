# Broker Chaos Lab (Phase 33)

Kafka + RabbitMQ + Redis lab with intentionally weak TLS for QU.I.R.K. broker scanner validation.

## Images

| Service | Image | Source |
|---------|-------|--------|
| Kafka | `apache/kafka:3.6` | Official Apache image (D-15, 2026-04-27 revision) |
| RabbitMQ | `rabbitmq:3.12-management` | Official Docker Hub image |
| Redis | `redis:7-alpine` | Official Docker Hub image |

Official images are required (not Bitnami) because only official images expose the config-file
hooks needed for cipher-suite control. See CONTEXT.md D-15 for the rationale.

## Port Map

| External | Container | Service | Protocol | Notes |
|----------|-----------|---------|----------|-------|
| 29092 | 29092 | Kafka plaintext | KAFKA-PLAIN | Intentionally listening — fires kafka-plaintext-listener HIGH |
| 29093 | 29093 | Kafka TLS | KAFKA-TLS | Weak ciphers: TLS_RSA_WITH_AES_128_CBC_SHA, TLS_RSA_WITH_AES_256_CBC_SHA |
| 25672 | 5672 | RabbitMQ AMQP | AMQP-PLAIN | Intentionally listening — fires amqp-plaintext-listener HIGH |
| 25671 | 5671 | RabbitMQ AMQPS | AMQPS | Weak ciphers: DES-CBC3-SHA, AES128-SHA, AES256-SHA |
| 26379 | 6379 | Redis plaintext | REDIS-PLAIN | Intentionally listening — fires redis-plaintext-no-auth HIGH |
| 26380 | 6380 | Redis TLS | REDIS-TLS | Weak ciphers: DES-CBC3-SHA, AES128-SHA, AES256-SHA |

## Quick Start

```bash
# 1. Generate self-signed RSA-2048 certs (D-17)
make -C labs/broker certs

# 2. Start all three broker containers
docker compose --profile broker --file quantum-chaos-enterprise-lab/docker-compose.yml up -d

# 3. Wait ~30s for healthchecks to pass
docker compose --profile broker --file quantum-chaos-enterprise-lab/docker-compose.yml ps

# 4. Run the QU.I.R.K. broker scan (standard profile enables broker scanning)
quirk scan --target localhost --profile standard

# 5. Tear down
docker compose --profile broker --file quantum-chaos-enterprise-lab/docker-compose.yml down
```

## TLS Posture (Intentionally Weak)

- TLS 1.2 (TLS 1.1 config present where supported by runtime OpenSSL)
- Non-PFS RSA key exchange — ECDHE/DHE excluded
- Cipher allowlists include 3DES (DES-CBC3-SHA) and RSA-only AES suites
- Self-signed RSA-2048 certs (regenerate via `make certs`)
- Plaintext ports intentionally listening on all three services

## Expected Findings

See `expected_results.md` for the full per-port findings table (BROKER-LAB-02).

Expected finding summary:
- `kafka-plaintext-listener` HIGH on port 29092
- `amqp-plaintext-listener` HIGH on port 25672
- `redis-plaintext-no-auth` HIGH on port 26379
- `weak-cipher` HIGH on at least 2 of: 29093, 25671, 26380
