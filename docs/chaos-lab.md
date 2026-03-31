# QU.I.R.K. Chaos Lab — Operator Guide

## 1. Overview

The QU.I.R.K. Chaos Lab is a Docker Compose environment that simulates a realistic enterprise network with deliberate cryptographic vulnerabilities. It is the canonical validation tool for scanner behavior:

- **Verify scanner behavior** — confirm QU.I.R.K. detects each class of finding before deploying against a client
- **Reproduce known findings** — reproduce a specific finding to diagnose scanner issues or tune severity thresholds
- **Train new team members** — walk through each vulnerability class hands-on without touching production infrastructure
- **Validate scanner changes** — run the lab after any code change to confirm no regressions

The lab is organized into profiles. The **core** profile is always-on and provides 10 services covering TLS, HTTP, and SSH scenarios. Additional profiles add specialized surfaces for Phase 4 scanner coverage (JWT, container registry, source code, cloud storage, legacy SSH, and LDAPS).

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

## 4. Starting Multiple Profiles

All profiles can run simultaneously. Phase 4 profiles share a network bridge and do not conflict with each other.

```bash
# Start all Phase 4 profiles together
PROFILE_ARGS="--profile jwt --profile registry --profile source --profile storage --profile ssh-weak --profile ldaps" ./lab.sh up
```

**Port conflict note:** The storage profile uses a dedicated LocalStack instance on port **20007** (`SERVICES=kms`). This is separate from the cloud profile LocalStack on port **24566** (`SERVICES=s3,sts,iam`). Both can run simultaneously without conflict.

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
