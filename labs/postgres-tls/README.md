# labs/postgres-tls

**Phase 89 / LAB-01** — PostgreSQL with intentionally weak TLS configuration.

## Purpose

Provides a STARTTLS-negotiated PostgreSQL target that exposes RSA key-exchange
cipher suites (no forward secrecy). The scanner exercises
`sslyze ProtocolWithOpportunisticTlsEnum.POSTGRES` on host port **39432**.

## Intentional Weaknesses (D-02)

| Setting | Value | Why it is weak |
|---------|-------|----------------|
| `ssl_ciphers` | `AES128-SHA:AES256-SHA` | RSA key exchange — no perfect forward secrecy; quantum-vulnerable |
| `ssl_min_protocol_version` | `TLSv1.2` | TLS 1.2 only; TLS 1.3 disabled |
| `ssl_max_protocol_version` | `TLSv1.2` | Locks to TLS 1.2 |
| Cert | RSA-2048 self-signed | RSA-2048 is quantum-vulnerable |

**DO NOT use this configuration in production.**

## Expected Findings

| Finding | Severity | Rule |
|---------|----------|------|
| Weak cipher suite (RSA key exchange, no PFS) | HIGH | TLS-03 |
| RSA-2048 certificate (quantum-vulnerable) | MEDIUM | TLS-02 |

## Cert Generation

```bash
cd labs/postgres-tls
make certs
```

Generates `certs/postgres-tls.crt` and `certs/postgres-tls.key`
(`chmod 640` so postgres uid 999 can read the key via group permission).

## Start

```bash
cd quantum-chaos-enterprise-lab
PROFILE_ARGS="--profile postgres-tls" ./lab.sh up
```

PostgreSQL will be available on `localhost:39432`.
