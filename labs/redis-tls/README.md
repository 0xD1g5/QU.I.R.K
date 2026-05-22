# labs/redis-tls

**Phase 89 / LAB-02** — Standalone Redis with intentionally weak TLS configuration.

## Purpose

Provides an isolated Redis-TLS target that exposes 3DES and RSA key-exchange cipher
suites (no forward secrecy). The scanner exercises `broker_scanner.py scan_redis_targets()`
on host port **39380** (TLS). Plaintext port **39379** is also exposed.

This is a **standalone** profile — it is NOT part of the `broker` profile. The broker
profile's `redis-broker` service is unchanged.

## Intentional Weaknesses (D-02)

| Setting | Value | Why it is weak |
|---------|-------|----------------|
| `tls-ciphers` | `DES-CBC3-SHA:AES128-SHA:AES256-SHA` | 3DES (SWEET32 attack) + RSA key exchange; no PFS; quantum-vulnerable |
| `tls-protocols` | `TLSv1.2` | TLS 1.2 only; TLS 1.3 disabled |
| `tls-auth-clients` | `no` | No mutual TLS |
| Plaintext port | `6379` | Plaintext Redis exposed (no auth) |
| Cert | RSA-2048 self-signed | RSA-2048 is quantum-vulnerable |

**DO NOT use this configuration in production.**

## Expected Findings

| Finding | Severity | Rule |
|---------|----------|------|
| Weak cipher suite (3DES, RSA key exchange, no PFS) on TLS port 39380 | HIGH | REDIS-01 |
| Redis plaintext listener on port 39379 | HIGH | REDIS-02 |

## Cert Generation

```bash
cd labs/redis-tls
make certs
```

Generates `certs/redis-tls.crt` and `certs/redis-tls.key`.

## Start

```bash
cd quantum-chaos-enterprise-lab
PROFILE_ARGS="--profile redis-tls" ./lab.sh up
```

Redis will be available on:
- `localhost:39380` — TLS (weak ciphers)
- `localhost:39379` — plaintext
