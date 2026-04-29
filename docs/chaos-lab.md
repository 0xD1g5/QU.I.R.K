# QU.I.R.K. Chaos Lab — Operator Guide

## 1. Overview

The QU.I.R.K. Chaos Lab is a Docker Compose environment that simulates a realistic enterprise network with deliberate cryptographic vulnerabilities. It is the canonical validation tool for scanner behavior:

- **Verify scanner behavior** — confirm QU.I.R.K. detects each class of finding before deploying against a client
- **Reproduce known findings** — reproduce a specific finding to diagnose scanner issues or tune severity thresholds
- **Train new team members** — walk through each vulnerability class hands-on without touching production infrastructure
- **Validate scanner changes** — run the lab after any code change to confirm no regressions

The lab is organized into profiles. The **core** profile is always-on and provides 10 services covering TLS, HTTP, and SSH scenarios. Additional profiles add specialized surfaces covering TLS / SSH / HTTP baseline (core), service inventory + cert chain scenarios (phaseA), cloud storage (cloud), identity (identity + pki), JWT misconfigurations (jwt), container registries (registry), source-code crypto anti-patterns (source), legacy storage (storage), legacy SSH (ssh-weak), LDAPS (ldaps), DNSSEC weakness (dnssec), SAML weakness (saml), Kerberos etype enumeration (kerberos), DAR — databases (database), DAR — object storage (storage-s3), DAR — Vault (vault), email transport (email), and message brokers (broker).

> **For UAT-grade expected scanner findings, see `quantum-chaos-enterprise-lab/expected_results_v4.md`** — the authoritative per-profile oracle used by chaos lab UAT runs and dashboard cross-references.

**Prerequisites:**

- Docker Desktop (macOS/Windows) or Docker Engine + Docker Compose plugin (Linux)
- Docker socket accessible at `/var/run/docker.sock`
- `lab.sh` script in the lab directory (wraps `docker compose` with standard project name `chaoslab`)

---

## 2. Quick Start

```bash
cd quantum-chaos-enterprise-lab

# Start core services (always-on baseline)
./lab.sh up

# Start a specific profile
PROFILE_ARGS="--profile jwt" ./lab.sh up

# Start all Phase 4 profiles
PROFILE_ARGS="--profile jwt --profile registry --profile source --profile storage --profile ssh-weak --profile ldaps" ./lab.sh up

# Stop everything
./lab.sh down
```

---

## 3. Profile Reference

### 3.1 Core Profile (always-on)

No `--profile` flag required. Started by default with `./lab.sh up`.

| Port  | Service              | Expected Protocol | Finding Tag                  |
|-------|----------------------|-------------------|------------------------------|
| 443   | tls-modern           | TLS               | MODERN_TLS                   |
| 8443  | tls-legacy           | TLS               | LEGACY_TLS                   |
| 9443  | tls-expired          | TLS               | CERT_EXPIRED_OR_EXPIRING     |
| 10443 | tls-selfsigned       | TLS               | CERT_SELFSIGNED              |
| 11443 | tls-mtls-required    | TLS               | MTLS_REQUIRED                |
| 12443 | tls-slow-proxy       | TLS               | TLS_SLOW_PROXY               |
| 8444  | http-on-8444         | HTTP              | HTTP_ON_TLS_LIKE_PORT        |
| 8000  | legacy-http          | HTTP              | PLAINTEXT_HTTP               |
| 2222  | ssh-alt              | SSH               | SSH_BANNER                   |
| 5555  | unknown-port         | UNKNOWN           | UNKNOWN_OPEN_PORT            |

**Start:**

```bash
./lab.sh up
```

Run QU.I.R.K. against the core lab:

```yaml
# config-lab-core.yaml
assessment:
  name: "Chaos Lab - Core"
  data_classification: "internal"
  report_owner: "Lab"
  timezone: "UTC"
targets:
  cidrs: [127.0.0.1]
```

```bash
quirk --config config-lab-core.yaml
```

---

### 3.2 phaseA Profile

| Port  | Service                   | Expected Protocol | Finding Tag             |
|-------|---------------------------|-------------------|-------------------------|
| 15001 | tls-altport               | TLS               | TLS_ON_ODD_PORT         |
| 18000 | http-redirect             | HTTP              | HTTP_REDIRECT_302       |
| 5556  | unknown-port-2            | UNKNOWN           | UNKNOWN_OPEN_PORT_2     |
| 15432 | postgres-plain            | UNKNOWN           | DB_PLAINTEXT_POSTGRES   |
| 16379 | redis-plain               | UNKNOWN           | DB_PLAINTEXT_REDIS      |
| 15672 | rabbitmq-mgmt             | HTTP              | RABBITMQ_MGMT_HTTP      |
| 13443 | tls-missing-intermediate  | TLS               | CERT_CHAIN_INCOMPLETE   |
| 14443 | tls-rsa1024               | TLS               | CERT_RSA_1024           |
| 15443 | tls-sha1                  | TLS               | CERT_SHA1_SIG           |
| 24443 | ingress-sni               | TLS               | INGRESS_SNI             |

**Start:**

```bash
PROFILE_ARGS="--profile phaseA" ./lab.sh up
```

---

### 3.3 cloud Profile

| Port  | Service           | Expected Protocol | Finding Tag                 |
|-------|-------------------|-------------------|-----------------------------|
| 24566 | localstack-tls    | TLS               | CLOUD_AWS_LOCALSTACK_TLS    |
| 21000 | azurite-blob-tls  | TLS               | CLOUD_AZURITE_BLOB_TLS      |
| 21001 | azurite-queue-tls | TLS               | CLOUD_AZURITE_QUEUE_TLS     |
| 21002 | azurite-table-tls | TLS               | CLOUD_AZURITE_TABLE_TLS     |

**Start:**

```bash
PROFILE_ARGS="--profile cloud" ./lab.sh up
```

---

### 3.4 identity Profile

| Port  | Service        | Expected Protocol | Finding Tag    |
|-------|----------------|-------------------|----------------|
| 15449 | keycloak-tls   | TLS               | IDP_TLS        |
| 19000 | step-ca        | TLS               | PRIVATE_CA_TLS |
| 13890 | openldap       | UNKNOWN           | LDAP_TCP       |
| 18082 | phpldapadmin   | HTTP              | LDAP_ADMIN_HTTP|
| 16443 | mtls-gateway   | TLS               | MTLS_REQUIRED  |

**Start:**

```bash
PROFILE_ARGS="--profile identity" ./lab.sh up
```

---

### 3.5 pki Profile

| Port  | Service               | Expected Protocol | Finding Tag |
|-------|-----------------------|-------------------|-------------|
| 17443 | mtls-stepca-gateway   | TLS               | MTLS_STEPCA |

**Start:**

```bash
PROFILE_ARGS="--profile pki" ./lab.sh up
```

> **Note:** The pki profile depends on the identity profile (`step-ca` and `whoami` services). Start identity first, or start both together:
> ```bash
> PROFILE_ARGS="--profile identity --profile pki" ./lab.sh up
> ```

---

### 3.6 jwt Profile (Phase 4 — LAB-01)

| Port  | Service       | Algorithm          | Expected Finding              | Key Size           |
|-------|---------------|--------------------|-------------------------------|--------------------|
| 20001 | jwt-rs256     | RS256 (RSA)        | quantum-vulnerable asymmetric | 2048-bit           |
| 20002 | jwt-hs256     | HS256 (HMAC-SHA256)| WEAK_KEY_SIZE                 | 128-bit (16-byte key) |
| 20003 | jwt-rsa1024   | RS256 (RSA)        | WEAK_KEY_SIZE + quantum-vulnerable | 1024-bit      |
| 20004 | jwt-algnone   | none               | CRITICAL_NO_SIGNATURE         | 0 bits             |

**Start:**

```bash
PROFILE_ARGS="--profile jwt" ./lab.sh up
```

Add these targets to your config.yaml to scan JWT endpoints:

```yaml
connectors:
  enable_jwt: true
  jwt_targets:
    - "http://localhost:20001/token"
    - "http://localhost:20002/token"
    - "http://localhost:20003/token"
    - "http://localhost:20004/token"
```

---

### 3.7 registry Profile (Phase 4 — LAB-02)

| Port  | Service             | Content                           | Expected Finding     |
|-------|---------------------|-----------------------------------|----------------------|
| 20005 | Docker Registry v2  | image-old-libssl (openssl 1.0.2n) | OUTDATED_CRYPTO_LIB  |
| 20005 | Docker Registry v2  | image-old-pycrypto (cryptography 2.9.2) | OUTDATED_CRYPTO_LIB |
| 20005 | Docker Registry v2  | image-mixed (both old packages)   | OUTDATED_CRYPTO_LIB  |

**Start:**

```bash
PROFILE_ARGS="--profile registry" ./lab.sh up
```

> **Note:** The `registry-seed` container seeds test images on startup. Docker socket must be accessible from within the container (`/var/run/docker.sock` mount). Allow 30–60 seconds for seeding to complete before scanning.

Add these targets to your config.yaml to scan container images:

```yaml
connectors:
  enable_container: true
  container_targets:
    - "localhost:20005/image-old-libssl:latest"
    - "localhost:20005/image-old-pycrypto:latest"
    - "localhost:20005/image-mixed:latest"
```

---

### 3.8 source Profile (Phase 4 — LAB-03)

| Port  | Service | Seeded Repos                     | Expected Finding                                      |
|-------|---------|----------------------------------|-------------------------------------------------------|
| 20006 | Gitea   | crypto-antipatterns-python       | Weak algorithm (hashlib.md5), hardcoded key, weak random |
| 20006 | Gitea   | crypto-antipatterns-go           | Weak algorithm (md5.Sum), deprecated TLS config       |
| 20006 | Gitea   | crypto-antipatterns-java         | RC4 usage, static IV, deprecated cipher               |

**Start:**

```bash
PROFILE_ARGS="--profile source" ./lab.sh up
```

Gitea admin credentials: username `admin`, password `admin123`

> **Note:** The `gitea-seed` container waits for Gitea to be healthy before seeding repos. Allow 30–60 seconds on first start. If repos are empty, check `gitea-seed` container logs: `./lab.sh logs gitea-seed`

Add these targets to your config.yaml to scan Gitea repositories:

```yaml
connectors:
  enable_source: true
  source_targets:
    - "http://admin:admin123@localhost:20006/admin/crypto-antipatterns-python"
    - "http://admin:admin123@localhost:20006/admin/crypto-antipatterns-go"
    - "http://admin:admin123@localhost:20006/admin/crypto-antipatterns-java"
```

---

### 3.9 storage Profile (Phase 4 — LAB-04)

| Port  | Service             | Resource                          | Expected Finding                          |
|-------|---------------------|-----------------------------------|-------------------------------------------|
| 20007 | LocalStack KMS      | SYMMETRIC_DEFAULT key             | AES_256 (quantum-vulnerable via Grover)   |
| 20007 | LocalStack KMS      | RSA_2048 key                      | RSA_2048 (quantum-vulnerable)             |
| 20007 | LocalStack KMS      | ECC_NIST_P256 key                 | ECC_P256 (quantum-vulnerable)             |
| 20009 | HashiCorp Vault     | transit/keys/rsa-2048             | RSA_2048 (quantum-vulnerable)             |
| 20009 | HashiCorp Vault     | transit/keys/rsa-1024             | RSA_1024 (weak + quantum-vulnerable)      |
| 20009 | HashiCorp Vault     | transit/keys/aes256               | AES_256 (quantum-vulnerable via Grover)   |
| 20010 | postgres-pgcrypto   | encrypted_demo table              | pgp_sym_encrypt weak passphrase           |

> **Note:** Vault port is **20009** (maps to internal port 8200). LocalStack KMS in this profile is on port **20007** and is a dedicated instance — independent of the cloud profile LocalStack on port 24566 (`SERVICES=s3,sts,iam`). The storage profile LocalStack runs only `SERVICES=kms`.

Credentials:

- Vault root token: `root`
- LocalStack KMS: access key `test`, secret key `test`
- PostgreSQL: default `postgres` superuser (no password in lab config)

**Start:**

```bash
PROFILE_ARGS="--profile storage" ./lab.sh up
```

---

### 3.10 ssh-weak Profile (Phase 4 — LAB-05)

| Port  | Service                           | Expected Protocol | Finding Tag          |
|-------|-----------------------------------|-------------------|----------------------|
| 20022 | OpenSSH 7.6p1 (ubuntu:18.04)     | SSH               | SSH_WEAK_ALGORITHMS  |

This service intentionally runs an older OpenSSH version (7.6p1 from Ubuntu 18.04) that supports legacy KEX algorithms (`diffie-hellman-group1-sha1`, `diffie-hellman-group14-sha1`), weak host key types (`ssh-dss`), and deprecated MAC algorithms. Modern OpenSSH removes these by default.

**Start:**

```bash
PROFILE_ARGS="--profile ssh-weak" ./lab.sh up
```

Add port 20022 to your scan config:

```yaml
scan:
  ports_tls: [443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555, 20022]
```

---

### 3.11 ldaps Profile (Phase 4 — LAB-06)

| Port | Service                                    | Expected Protocol | Finding Tag |
|------|--------------------------------------------|-------------------|-------------|
| 636  | OpenLDAP over TLS (osixia/openldap:1.5.0)  | TLS               | LDAPS_TLS   |

Standard LDAPS port (636). QU.I.R.K. scans this using sslyze — add port 636 to `ports_tls` to include it in a scan.

**Start:**

```bash
PROFILE_ARGS="--profile ldaps" ./lab.sh up
```

Add port 636 to your scan config:

```yaml
scan:
  ports_tls: [443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555, 636]
```

---

### 3.12 dnssec Profile (v4.2)

The `dnssec` profile ships a BIND9 authoritative nameserver pre-configured with intentionally weak DNSSEC signing — `RSASHA1` algorithm zones and an unsigned test zone — designed to exercise QU.I.R.K.'s DNS cryptography audit path. It is the canonical chaos lab target for DNSSEC weakness detection.

| Port        | Service      | Protocol | Finding Tag                       |
|-------------|--------------|----------|-----------------------------------|
| 15353/udp   | bind9-dnssec | DNS/UDP  | RSASHA1 weak-algo CRITICAL        |
| 15353/tcp   | bind9-dnssec | DNS/TCP  | unsigned zone HIGH, NSEC MEDIUM   |

**Start:**

```bash
PROFILE_ARGS="--profile dnssec" ./lab.sh up
```

**Expected scanner findings:**

- `RSASHA1` weak-algorithm signing detected — CRITICAL
- Unsigned zone present — HIGH
- `NSEC` (non-authenticated denial of existence) in use — MEDIUM

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-dnssec`

---

### 3.13 saml Profile (v4.2)

The `saml` profile ships a simpleSAMLphp IdP configured with a deliberately weak RSA-1024 signing certificate and SHA-1 algorithm URI, exercising QU.I.R.K.'s SAML metadata inspection path. This is the canonical chaos lab target for SAML signing-certificate weakness.

| Port | Service       | Protocol | Finding Tag                    |
|------|---------------|----------|--------------------------------|
| 8080 | simplesamlphp | HTTP/TLS | RSA-1024 signing cert CRITICAL |
| 8080 | simplesamlphp | HTTP/TLS | SHA-1 algorithm URI HIGH       |

> **Port note:** The compose-authoritative host port is **8080**. Earlier versions of this guide and the v3 oracle incorrectly listed 8880 — 8080 is correct. Keycloak (identity profile) uses `expose: 8080` not `ports:`, so there is no host-level conflict when both profiles run simultaneously.

**Start:**

```bash
PROFILE_ARGS="--profile saml" ./lab.sh up
```

**Expected scanner findings:**

- `RSA-1024 signing cert` detected in SAML metadata — CRITICAL
- `SHA-1 algorithm URI` in SAML signing method — HIGH

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-saml`

---

### 3.14 kerberos Profile (v4.2)

The `kerberos` profile runs a Samba Active Directory Domain Controller configured to advertise weak Kerberos encryption types (`rc4-hmac`, `aes128-cts-hmac-sha1-96`), giving QU.I.R.K.'s Kerberos etype enumeration scanner a realistic target. Both encryption types fall below the FIPS 140-3 / NIST SP 800-131A minimum requirements.

| Port | Service  | Protocol  | Finding Tag                              |
|------|----------|-----------|------------------------------------------|
| 88   | samba-dc | Kerberos  | weak etype: rc4-hmac HIGH                |
| 389  | samba-dc | LDAP/Kerb | weak etype: aes128-cts-hmac-sha1-96 HIGH |

> **Port collision warning:** Ports 88 and 389 are not remapped to a non-standard range. If the lab host is a domain member or has a local Kerberos/LDAP daemon (e.g. `krb5kdc`, Active Directory agent, or system OpenLDAP on port 389), there will be a conflict. Verify with `lsof -i:88 -i:389` before starting this profile.

**Start:**

```bash
PROFILE_ARGS="--profile kerberos" ./lab.sh up
```

**Expected scanner findings:**

- `weak etype: rc4-hmac` advertised by KDC — HIGH
- `weak etype: aes128-cts-hmac-sha1-96` advertised by KDC — HIGH

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-kerberos`

---

### 3.15 vault Profile (v4.3 — DAR)

The `vault` profile (introduced in Phase 30) ships a standalone HashiCorp Vault 1.17 dev server (`vault-30`) pre-seeded with transit keys, a PKI root CA, and auth method mounts that exercise QU.I.R.K.'s Vault connector. It is intentionally on port **28200** and is independent of the legacy `storage` profile's Vault instance (port 20009, image 1.15).

| Port  | Service   | Resource                       | Expected Finding                      | Severity |
|-------|-----------|--------------------------------|---------------------------------------|----------|
| 28200 | vault-30  | transit/rsa-2048-classification | Classification only                  | (none)   |
| 28200 | vault-30  | transit/rsa-2048-exportable    | Exportable transit key                | MEDIUM   |
| 28200 | vault-30  | PKI/pki                        | RSA<4096 root CA                      | HIGH     |
| 28200 | vault-30  | auth/token                     | Dev-mode root token always enabled    | HIGH     |
| 28200 | vault-30  | auth/userpass                  | Userpass auth method enabled          | MEDIUM   |

Credentials: root token `root` (dev mode — never use in production).

**Start:**

```bash
PROFILE_ARGS="--profile vault" ./lab.sh up
```

**Expected scanner findings:**

- `PKI/<mount>` RSA<4096 root CA detected — HIGH
- `auth/token` always-on in dev mode — HIGH
- `transit/<key_name>` exportable transit key — MEDIUM
- `auth/userpass` method enabled — MEDIUM

See: `labs/vault/expected_results.md`

---

### 3.16 database Profile (v4.3 — DAR)

The `database` profile (introduced in Phase 27) ships a PostgreSQL 15 instance (`postgres-ssl-off`) and a MySQL 8 instance (`mysql-ssl-off`), each with SSL/TLS explicitly disabled, providing QU.I.R.K.'s database connector with clear regression targets for plaintext-connection detection.

| Port  | Service          | Engine     | Expected Finding                                              | Severity |
|-------|------------------|------------|---------------------------------------------------------------|----------|
| 25432 | postgres-ssl-off | PostgreSQL | `PostgreSQL/ssl-off` — SSL disabled at engine level           | HIGH     |
| 25432 | postgres-ssl-off | PostgreSQL | `PostgreSQL/plaintext-connections-allowed` — non-SSL conns    | HIGH     |
| 23306 | mysql-ssl-off    | MySQL      | `MySQL/ssl-off` — SSL disabled at engine level                | HIGH     |

Credentials: PostgreSQL — default `postgres` superuser (no password in lab config); MySQL — root with no password.

**Start:**

```bash
PROFILE_ARGS="--profile database" ./lab.sh up
```

**Expected scanner findings:**

- `PostgreSQL/ssl-off` — SSL parameter is `off` — HIGH
- `PostgreSQL/plaintext-connections-allowed (N non-SSL)` — non-SSL connections present in `pg_stat_ssl` — HIGH
- `MySQL/ssl-off` — `Ssl_cipher` status variable is empty — HIGH

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-database`

---

### 3.17 storage-s3 Profile (v4.3 — DAR)

The `storage-s3` profile (introduced in Phase 28) ships a MinIO S3-compatible object storage server. A seed container creates two buckets on startup: one encrypted (SSE-S3) and one unencrypted, providing QU.I.R.K.'s S3 connector with a clean positive/negative pair for encryption-at-rest detection.

| Port  | Service       | Bucket              | SSE Mode | Expected Finding     | Severity |
|-------|---------------|---------------------|----------|----------------------|----------|
| 29000 | minio         | encrypted-bucket    | SSE-S3   | `S3/sse-s3`          | (none)   |
| 29000 | minio         | unencrypted-bucket  | None     | `S3/unencrypted`     | HIGH     |
| 29001 | minio-console | (admin UI)          | —        | —                    | —        |

Credentials: access key `minioadmin`, secret key `minioadmin`.

**Start:**

```bash
PROFILE_ARGS="--profile storage-s3" ./lab.sh up
```

Add to your config.yaml:

```yaml
connectors:
  enable_s3: true
  aws_region: us-east-1
  aws_endpoint_url: http://localhost:29000
```

**Expected scanner findings:**

- `S3/unencrypted` on `arn:aws:s3:::unencrypted-bucket` — HIGH
- `S3/sse-s3` on `arn:aws:s3:::encrypted-bucket` — no finding (positive control)

See: `labs/storage/expected_results.md`

---

### 3.18 email Profile (v4.4)

The `email` profile (introduced in Phase 32) ships a Postfix SMTP server and a Dovecot IMAP/POP3 server. Postfix is hard-capped to TLS 1.2 with non-PFS RSA cipher suites, producing weak-cipher and STARTTLS-downgrade findings. Dovecot defaults to TLS 1.3, so its ports do not emit weak-cipher findings under default scan invocation (see caveat below).

| Host Port | Container Port | Service              | Protocol      | Notes                                      |
|-----------|----------------|----------------------|---------------|--------------------------------------------|
| 30025     | 25             | postfix-email (SMTP) | SMTP-STARTTLS | STARTTLS-downgrade MEDIUM + weak-cipher HIGH |
| 30465     | 465            | postfix-email (SMTPS)| SMTPS         | weak-cipher HIGH (implicit TLS)            |
| 30587     | 587            | postfix-email (submission)| SMTP-STARTTLS | weak-cipher HIGH                      |
| 30143     | 143            | dovecot-email (IMAP) | IMAP-STARTTLS | TLS 1.3 — no weak-cipher finding           |
| 30993     | 993            | dovecot-email (IMAPS)| IMAPS         | TLS 1.3 — no weak-cipher finding           |
| 30110     | 110            | dovecot-email (POP3) | POP3-STARTTLS | TLS 1.3 — no weak-cipher finding           |
| 30995     | 995            | dovecot-email (POP3S)| POP3S         | TLS 1.3 — no weak-cipher finding           |

**Start:**

```bash
PROFILE_ARGS="--profile email" ./lab.sh up
```

Allow ~30 seconds for both containers to reach healthy status before scanning.

**Expected scanner findings:**

- `Weak cipher suite on email TLS endpoint` — port 25 — HIGH (EMAIL-09)
- `Weak cipher suite on email TLS endpoint` — port 465 — HIGH (EMAIL-09)
- `Weak cipher suite on email TLS endpoint` — port 587 — HIGH (EMAIL-09)
- `STARTTLS downgrade risk on SMTP` — port 25 — MEDIUM (EMAIL-08)

> **Dovecot caveat:** Dovecot 2.3.16 (Ubuntu 22.04) negotiates TLS 1.3 when the client offers it, bypassing the TLS 1.2 weak-cipher restriction in the lab's config. Ports 30143/30993/30110/30995 emit **no** weak-cipher findings under the default scan path. To exercise the TLS 1.2 weak-cipher path on Dovecot, pin the client: `openssl s_client -tls1_2 -connect localhost:30143 -starttls imap`.

See: `labs/email/expected_results.md`

---

### 3.19 broker Profile (v4.4)

The `broker` profile (introduced in Phase 33) ships three message brokers — Apache Kafka, RabbitMQ, and Redis — each configured with both a plaintext listener and a TLS listener using deliberately weak non-PFS RSA cipher suites. This exercises QU.I.R.K.'s broker scanner across all three broker types simultaneously.

| Host Port | Service         | Protocol   | Expected Finding                              | Severity |
|-----------|-----------------|------------|-----------------------------------------------|----------|
| 29092     | kafka-broker    | KAFKA-PLAIN| Kafka plaintext listener detected             | HIGH     |
| 29093     | kafka-broker    | KAFKA-TLS  | Weak cipher suite on broker TLS endpoint      | HIGH     |
| 25672     | rabbitmq-broker | AMQP-PLAIN | AMQP plaintext listener detected              | HIGH     |
| 25671     | rabbitmq-broker | AMQPS      | Weak cipher suite on broker TLS endpoint      | HIGH     |
| 26379     | redis-broker    | REDIS-PLAIN| Redis plaintext listener (no authentication)  | HIGH     |
| 26380     | redis-broker    | REDIS-TLS  | Weak cipher suite on broker TLS endpoint      | HIGH     |

**Start:**

Generate TLS certs before first boot:

```bash
cd labs/broker && make certs && cd ../..
PROFILE_ARGS="--profile broker" ./lab.sh up
```

Allow ~30 seconds for all three healthchecks to pass.

**Expected scanner findings:**

- `Kafka plaintext listener detected` — port 29092 — HIGH (KAFKA-02)
- `Weak cipher suite on broker TLS endpoint` — port 29093 — HIGH (KAFKA-01)
- `AMQP plaintext listener detected` — port 25672 — HIGH (RABBIT-02)
- `Weak cipher suite on broker TLS endpoint` — port 25671 — HIGH (RABBIT-01)
- `Redis plaintext listener (no authentication)` — port 26379 — HIGH (REDIS-02)
- `Weak cipher suite on broker TLS endpoint` — port 26380 — HIGH (REDIS-01)

**Total: 6 HIGH findings** (3 plaintext + 3 weak-cipher TLS).

See: `labs/broker/expected_results.md`

---

## 4. Starting Multiple Profiles

All profiles can run simultaneously. Phase 4 profiles share a network bridge and do not conflict with each other.

```bash
# Start all Phase 4 profiles together
PROFILE_ARGS="--profile jwt --profile registry --profile source --profile storage --profile ssh-weak --profile ldaps" ./lab.sh up
```

**Port conflict note:** The storage profile uses a dedicated LocalStack instance on port **20007** (`SERVICES=kms`). This is separate from the cloud profile LocalStack on port **24566** (`SERVICES=s3,sts,iam`). Both can run simultaneously without conflict.

To list every profile defined in the compose file (live read — never out of date):

```bash
./lab.sh profiles
```

---

## 5. Complete Port Reference

All lab ports across all profiles, sorted by port number:

| Port  | Service                  | Profile   | Expected Finding                          |
|-------|--------------------------|-----------|-------------------------------------------|
| 443   | tls-modern               | core      | MODERN_TLS                                |
| 636   | ldaps                    | ldaps     | LDAPS_TLS                                 |
| 2222  | ssh-alt                  | core      | SSH_BANNER                                |
| 5555  | unknown-port             | core      | UNKNOWN_OPEN_PORT                         |
| 5556  | unknown-port-2           | phaseA    | UNKNOWN_OPEN_PORT_2                       |
| 8000  | legacy-http              | core      | PLAINTEXT_HTTP                            |
| 8443  | tls-legacy               | core      | LEGACY_TLS                                |
| 8444  | http-on-8444             | core      | HTTP_ON_TLS_LIKE_PORT                     |
| 9443  | tls-expired              | core      | CERT_EXPIRED_OR_EXPIRING                  |
| 10443 | tls-selfsigned           | core      | CERT_SELFSIGNED                           |
| 11443 | tls-mtls-required        | core      | MTLS_REQUIRED                             |
| 12443 | tls-slow-proxy           | core      | TLS_SLOW_PROXY                            |
| 13443 | tls-missing-intermediate | phaseA    | CERT_CHAIN_INCOMPLETE                     |
| 13890 | openldap                 | identity  | LDAP_TCP                                  |
| 14443 | tls-rsa1024              | phaseA    | CERT_RSA_1024                             |
| 15001 | tls-altport              | phaseA    | TLS_ON_ODD_PORT                           |
| 15432 | postgres-plain           | phaseA    | DB_PLAINTEXT_POSTGRES                     |
| 15443 | tls-sha1                 | phaseA    | CERT_SHA1_SIG                             |
| 15449 | keycloak-tls             | identity  | IDP_TLS                                   |
| 15672 | rabbitmq-mgmt            | phaseA    | RABBITMQ_MGMT_HTTP                        |
| 16379 | redis-plain              | phaseA    | DB_PLAINTEXT_REDIS                        |
| 16443 | mtls-gateway             | identity  | MTLS_REQUIRED                             |
| 17443 | mtls-stepca-gateway      | pki       | MTLS_STEPCA                               |
| 18000 | http-redirect            | phaseA    | HTTP_REDIRECT_302                         |
| 18082 | phpldapadmin             | identity  | LDAP_ADMIN_HTTP                           |
| 19000 | step-ca                  | identity  | PRIVATE_CA_TLS                            |
| 20001 | jwt-rs256                | jwt       | JWT quantum-vulnerable asymmetric         |
| 20002 | jwt-hs256                | jwt       | JWT WEAK_KEY_SIZE                         |
| 20003 | jwt-rsa1024              | jwt       | JWT WEAK_KEY_SIZE + quantum-vulnerable    |
| 20004 | jwt-algnone              | jwt       | JWT CRITICAL_NO_SIGNATURE                 |
| 20005 | registry                 | registry  | OUTDATED_CRYPTO_LIB                       |
| 20006 | gitea                    | source    | WEAK_ALGORITHM / HARDCODED_KEY            |
| 20007 | localstack-kms           | storage   | AWS KMS crypto inventory                  |
| 20009 | vault                    | storage   | HashiCorp Vault crypto inventory          |
| 20010 | postgres-pgcrypto        | storage   | pgcrypto weak passphrase                  |
| 20022 | ssh-weak                 | ssh-weak  | SSH_WEAK_ALGORITHMS                       |
| 21000 | azurite-blob-tls         | cloud     | CLOUD_AZURITE_BLOB_TLS                    |
| 21001 | azurite-queue-tls        | cloud     | CLOUD_AZURITE_QUEUE_TLS                   |
| 21002 | azurite-table-tls        | cloud     | CLOUD_AZURITE_TABLE_TLS                   |
| 24443 | ingress-sni              | phaseA    | INGRESS_SNI                               |
| 24566 | localstack-cloud         | cloud     | CLOUD_AWS_LOCALSTACK_TLS                  |
| 25432 | postgres-ssl-off         | database  | PostgreSQL/ssl-off HIGH                   |
| 25671 | rabbitmq-broker (AMQPS)  | broker    | Weak cipher suite on broker TLS endpoint  |
| 25672 | rabbitmq-broker (AMQP)   | broker    | AMQP plaintext listener detected          |
| 26379 | redis-broker (plain)     | broker    | Redis plaintext listener (no auth)        |
| 26380 | redis-broker (TLS)       | broker    | Weak cipher suite on broker TLS endpoint  |
| 28200 | vault-30                 | vault     | PKI/auth/transit DAR audit                |
| 29000 | minio                    | storage-s3| S3/unencrypted HIGH (unencrypted-bucket)  |
| 29001 | minio-console            | storage-s3| MinIO admin UI (no scanner finding)       |
| 29092 | kafka-broker (plain)     | broker    | Kafka plaintext listener detected         |
| 29093 | kafka-broker (TLS)       | broker    | Weak cipher suite on broker TLS endpoint  |
| 30025 | postfix-email (SMTP)     | email     | STARTTLS-downgrade MEDIUM + weak-cipher HIGH |
| 30110 | dovecot-email (POP3)     | email     | POP3-STARTTLS (TLS 1.3 — no weak-cipher) |
| 30143 | dovecot-email (IMAP)     | email     | IMAP-STARTTLS (TLS 1.3 — no weak-cipher) |
| 30465 | postfix-email (SMTPS)    | email     | Weak cipher suite on email TLS endpoint   |
| 30587 | postfix-email (submission)| email    | Weak cipher suite on email TLS endpoint   |
| 30993 | dovecot-email (IMAPS)    | email     | IMAPS (TLS 1.3 — no weak-cipher)          |
| 30995 | dovecot-email (POP3S)    | email     | POP3S (TLS 1.3 — no weak-cipher)          |
| 8080  | simplesamlphp            | saml      | RSA-1024 signing cert CRITICAL            |
| 15353/udp | bind9-dnssec         | dnssec    | RSASHA1 weak-algo CRITICAL                |
| 15353/tcp | bind9-dnssec         | dnssec    | unsigned zone HIGH, NSEC MEDIUM           |
| 23306 | mysql-ssl-off            | database  | MySQL/ssl-off HIGH                        |
| 88    | samba-dc                 | kerberos  | weak etype: rc4-hmac HIGH                 |
| 389   | samba-dc                 | kerberos  | weak etype: aes128-cts-hmac-sha1-96 HIGH  |

---

## 6. Troubleshooting

**Services not starting:**

```bash
./lab.sh logs [service-name]   # Check service logs
./lab.sh ps                    # Check container status
```

**Port conflicts:**
If ports conflict with local services, check `docker-compose.yml` host port mappings. All Phase 4 lab ports are in non-standard ranges (20000+) to minimize conflicts with typical development environments.

**registry-seed failures:**
The seed container needs Docker socket access. Confirm `/var/run/docker.sock` is mounted and your user has Docker group membership. Seed timing: allow 30–60 seconds before scanning.

**Gitea seed timing:**
The source profile `gitea-seed` waits for Gitea to be healthy before seeding. Allow 30–60 seconds on first start. If repos are empty:

```bash
./lab.sh logs gitea-seed
```

**Vault not reachable:**
Vault runs on port **20009** (not 20008). Confirm with `curl http://localhost:20009/v1/sys/health`.

**pki profile failing to start:**
The `pki` profile depends on `step-ca` from the identity profile. Always start identity alongside pki:

```bash
PROFILE_ARGS="--profile identity --profile pki" ./lab.sh up
```

---

## 7. Historical Reference

The existing `quantum-chaos-enterprise-lab/CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` in the lab directory is retained as a historical artifact documenting the original lab build decisions (pre-Phase 4). This guide (`docs/chaos-lab.md`) is the authoritative operator reference going forward.
