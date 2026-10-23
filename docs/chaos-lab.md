# QU.I.R.K. Chaos Lab — Operator Guide

## 1. Overview

The QU.I.R.K. Chaos Lab is a Docker Compose environment that simulates a realistic enterprise network with deliberate cryptographic vulnerabilities. It is the canonical validation tool for scanner behavior:

- **Verify scanner behavior** — confirm QU.I.R.K. detects each class of finding before deploying against a client
- **Reproduce known findings** — reproduce a specific finding to diagnose scanner issues or tune severity thresholds
- **Train new team members** — walk through each vulnerability class hands-on without touching production infrastructure
- **Validate scanner changes** — run the lab after any code change to confirm no regressions

The lab is organized into profiles. The **core** profile is always-on and provides 10 services covering TLS, HTTP, SSH and unknown-port scenarios. Additional profiles add specialized surfaces: service inventory and certificate-chain scenarios (`phaseA`), cloud simulators (`cloud`), identity (`identity`, `pki`), JWT misconfigurations (`jwt`), container registries (`registry`), source-code crypto anti-patterns (`source`), legacy SSH (`ssh-weak`), LDAPS (`ldaps`, including the Phase 95 code-signing weak-cert fixture), DNSSEC weakness (`dnssec`), SAML weakness (`saml`), Kerberos etype enumeration (`kerberos`), data-at-rest targets (`database`, `storage-s3`, `vault`), email transport (`email`), message brokers (`broker`), TLS certificate defects (`tls-cert-defects`), a deliberately-weak REST target for active fuzzing (`fuzz-target`), hardware, OT/ICS and segmented-network surfaces (`hwcompat`, `otics`, `segmented-network`), S/MIME and AD CS certificate discovery (`smime`, `adcs`), TLS-wrapped data services (`postgres-tls`, `redis-tls`, `kafka-tls`, `grpc-tls`), a post-quantum TLS endpoint (`oqs-nginx`), and a many-host estate on one subnet (`multihost`). `./lab.sh profiles` prints the profile list your checkout actually defines.

> **For UAT-grade expected scanner findings, see `quantum-chaos-enterprise-lab/expected_results_v4.md`** — the authoritative per-profile oracle for the profiles it covers (`hwcompat`, `otics` and `segmented-network` have their own `expected_results_hwcompat.md`, `expected_results_otics.md` and `expected_results_segmented_network.md`).

**Prerequisites:**

- Docker Desktop (macOS/Windows) or Docker Engine + Docker Compose plugin (Linux).
  On Linux, see [Docker on Linux](installation.md#docker-on-linux-chaos-lab-only) for
  install steps — `docker-compose` (the standalone v1 binary) is **not** the same thing
  as the `docker compose` plugin `lab.sh` calls
- **Plan for ~25 GB of free disk, more if you run several profiles.** When this guide's
  disk figures were taken (`docker system df`, September 2026) the lab's images totalled
  roughly 20 GB and the `multihost` prober alone was ~3.5 GB; they have not been re-measured
  since. On the fresh VM where this was first hit, running out of disk mid-`docker pull`
  showed up as a confusing layer error, not a clear out-of-disk message
- Docker socket accessible at `/var/run/docker.sock`
- `lab.sh` script in the lab directory (wraps `docker compose` with standard project name `chaoslab`)
- For hardware scanning profiles (`hwcompat`): `pip install 'quirk-scanner[hw]'` — installs the SNMP probe libraries (`pysnmp` 7)

---

## 2. Quick Start

```bash
cd quantum-chaos-enterprise-lab

# Start core services (always-on baseline)
./lab.sh up

# Start a specific profile
PROFILE_ARGS="--profile jwt" ./lab.sh up

# Start all Phase 4 profiles
PROFILE_ARGS="--profile jwt --profile registry --profile source --profile ssh-weak --profile ldaps" ./lab.sh up

# Stop everything
./lab.sh down
```

`./lab.sh up`, `./lab.sh all` and `./lab.sh reset` generate the top-level mTLS
CA/client pair and the `email`/`grpc-tls` profiles' certs before starting
containers, when they are missing. Run `./lab.sh certs` to generate the same set
without starting any containers. `lab.sh` does not generate the `broker`,
`postgres-tls`, `redis-tls` or `kafka-tls` certs; run `make -C labs/<profile> certs`
from the repository root before those profiles' first `up` (see each profile's
section).

---

## 3. Profile Reference

**Reading the finding columns.** Upper-case tags such as `MODERN_TLS` or `CERT_SELFSIGNED` are condition
labels from the oracle (`expected_results_v4.md`); the scanner does not output them. Quoted titles such as
`TLS certificate expired` are the scanner's own finding titles. The CLI and the dashboard build their
finding lists separately, so where a result shows up depends on the surface:

- **CLI findings list (`findings-*.json`).** TLS, HTTP, SSH, container and unknown-port rows go through the
  main evaluator, and email, broker, code-signing and SAML rows each have their own evaluator. Kerberos,
  DNSSEC, S/MIME, AD CS, database, S3 and Vault rows have no evaluator there. The one CLI finding such a row
  can produce is an INFO `Informational protocol observation` when it records a scan error.
- **Dashboard Findings page.** The certificate and TLS checks (legacy TLS version, weak ciphers, expiry,
  undersized RSA key, self-signed, untrusted CA, quantum-vulnerable key algorithm) run only on `TLS` rows,
  as in the CLI. S/MIME, AD CS, Vault, cloud, JWT and OpenAPI rows therefore list nothing from those checks,
  even when they carry a certificate or key (surfacing them on both surfaces is tracked as 999.132). Email,
  broker and code-signing rows get the same findings the CLI lists, and Kerberos, SAML and DNSSEC findings
  are added to this page from the identity derivation.
- **Dashboard Identity, Motion and Data at Rest pages.** Kerberos, SAML and DNSSEC findings are on Identity,
  email and broker findings on Motion, and database, S3 and Vault posture on Data at Rest.

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

# REQUIRED — ScanCfg.concurrency and ScanCfg.ports_tls have no defaults.
# ports_tls below is the shipped 17-port CONSULTING_TLS_PORTS default
# (defined in quirk/interactive.py). Port 9443 is the lab's tls-expired service.
scan:
  concurrency: 50
  ports_tls: [443, 8443, 9443, 10443, 4433, 5001, 636, 3269, 993, 995, 465, 6443, 2376, 5432, 3306, 1433, 8200]

output:
  directory: "./quirk-output"
  db_path: "./quirk-output/quirk.db"
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

> **Note:** The pki gateway proxies to the `whoami` service, which only the identity and phaseA profiles define (its certificates are static files under `certs/stepca/`, so it does not call the `step-ca` service at runtime). Start identity first, or start both together:
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
    - "http://localhost:20001"
    - "http://localhost:20002"
    - "http://localhost:20003"
    - "http://localhost:20004"

security:
  allow_internal_targets: true
```

> **Corrected 2026-09-17.** Two defects made this profile unscannable as previously
> documented. First, the targets were written as `.../token`: the connector probes JWKS
> paths by concatenating them onto each target, so `/token` made it request
> `/token/.well-known/jwks.json` and find nothing; the right target is the bare base URL,
> `"http://localhost:20001"`. Second, the JWKS probe runs `validate_external_url()` on every candidate
> URL, and `allow_internal` was never threaded to it, so `localhost` was rejected as
> RC_LOOPBACK regardless of config — the `security` block above is now required, and the
> scanner passes the flag through as of the same change.

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
| 20006 | Gitea   | crypto-antipatterns-go           | Weak algorithms (md5.New, SHA-1, DES, RC4), math/rand |
| 20006 | Gitea   | crypto-antipatterns-java         | Weak algorithm (MD5, DES/ECB), java.util.Random, hardcoded key |

**Start:**

```bash
PROFILE_ARGS="--profile source" ./lab.sh up
```

Gitea admin credentials: username `labadmin`, password `admin123` (Gitea reserves the username `admin`, so the lab provisions `labadmin`)

> **Note:** The `gitea-seed` container waits for Gitea to be healthy before seeding repos. Allow 30–60 seconds on first start. If repos are empty, check `gitea-seed` container logs: `./lab.sh logs gitea-seed`

`connectors.source_targets` takes **local directory paths**, not repository URLs: the source scanner
rejects any entry that is not an existing directory (a URL comes back as an `invalid_input` row and
semgrep never runs). The seeded repos are public, so clone them first and point the config at the clones:

```bash
git clone http://localhost:20006/labadmin/crypto-antipatterns-python
git clone http://localhost:20006/labadmin/crypto-antipatterns-go
git clone http://localhost:20006/labadmin/crypto-antipatterns-java
```

```yaml
connectors:
  enable_source: true
  source_targets:
    - "./crypto-antipatterns-python"
    - "./crypto-antipatterns-go"
    - "./crypto-antipatterns-java"
```

---

### 3.9 Removed: the legacy `storage` profile

The `storage` profile (a LocalStack KMS instance on port 20007, a Vault 1.15 instance on port 20009, and a `postgres-pgcrypto` instance on port 20010) was removed from `docker-compose.yml` (commit `a690e625`, "remove deprecated `storage` profile"). `PROFILE_ARGS="--profile storage"` no longer adds any service beyond the 10 always-on core services, and ports 20007, 20009 and 20010 are not published by any current profile. Use these instead:

- Vault crypto inventory: the `vault` profile (§3.15, port 28200)
- Object storage encryption at rest: the `storage-s3` profile (§3.17, port 29000)
- LocalStack (`SERVICES=s3,sts,iam`, so no KMS) and Azurite behind TLS terminators: the `cloud` profile (§3.3, ports 24566 and 21000-21002)

No current profile offers a KMS or a `pgcrypto` target.

---

### 3.10 ssh-weak Profile (Phase 4 — LAB-05)

| Port  | Service                           | Expected Protocol | Finding Tag          |
|-------|-----------------------------------|-------------------|----------------------|
| 20022 | OpenSSH 7.6p1 (ubuntu:18.04)     | SSH               | SSH_WEAK_ALGORITHMS  |

This service intentionally runs an older OpenSSH version (7.6p1 from Ubuntu 18.04) that supports legacy KEX algorithms (`diffie-hellman-group1-sha1`, `diffie-hellman-group14-sha1`), weak host key types (`ssh-dss`), and deprecated MAC algorithms (`hmac-md5`). Modern OpenSSH disables `diffie-hellman-group1-sha1` and `ssh-dss` by default.

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

### 3.11 ldaps Profile (Phase 4 — LAB-06 / Phase 95 — LAB-01)

| Port | Service                                    | Expected Protocol | Finding Tag |
|------|--------------------------------------------|-------------------|-------------|
| 636  | OpenLDAP over TLS (bitnamilegacy/openldap:2.6.10-debian-12-r4)  | TLS               | CERT_SELFSIGNED |

Standard LDAPS port (636). QU.I.R.K. scans this using sslyze — add port 636 to `ports_tls` to include it in a scan. The service also listens for plaintext LDAP on 389 inside the compose network (the seed sidecar reaches it as `ldap://ldaps:389`), but only 636 is published to the host.

**Phase 95 code-signing fixture (LAB-01):** The `ldaps` profile also seeds an LDAP entry for
`uid=codesign-weak,ou=people,dc=chaos,dc=local` via the `ldaps-codesign-seed` sidecar.  This
entry carries a `userCertificate;binary` attribute containing an RSA-1024 / SHA-1 certificate
with the Code Signing EKU (OID `1.3.6.1.5.5.7.3.3`). Running with `--inventory-code-signing`
against this profile will produce exactly **one HIGH finding in the CLI findings list, `Code-signing certificate uses weak algorithm: <subject>`** (the oracle labels it `CODE-SIGN/weak-algorithm`), with two
weak-algorithm reasons: `weak-rsa-key` (RSA < 2048-bit) and `weak-signing-alg` (SHA-1). The dashboard's
Findings page lists the same HIGH `Code-signing certificate uses weak algorithm: <subject>` (both surfaces use
the shared code-signing evaluator), not `TLS certificate uses undersized RSA key`.

**Start:**

```bash
PROFILE_ARGS="--profile ldaps" ./lab.sh up
```

Add port 636 to your scan config:

```yaml
scan:
  ports_tls: [443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555, 636]
```

**Code-signing inventory scan against the ldaps fixture:**

> **Host reachability limit.** The code-signing scanner opens a plaintext, anonymous LDAP connection (it never sets `use_ssl`), but the `ldaps` profile publishes only the TLS port 636 to the host, so there is no host port the example below can reach (host port 389 is published only by the `kerberos` profile, which is a different directory). Run the scan from a container attached to the lab network, or treat the example as the target shape until the lab publishes the plaintext port.

```yaml
# config-lab-ldaps-codesign.yaml
assessment:
  name: "Chaos Lab - ldaps Code-Signing"
  data_classification: "internal"
  report_owner: "Lab"
  timezone: "UTC"
targets:
  cidrs: [127.0.0.1]
scan:
  ports_tls: [443, 8443, 9443, 10443, 11443, 12443, 8444, 8000, 2222, 5555, 636]
connectors:
  codesign_targets:
    - "ldap://ldaps:389"   # reachable only from inside the lab network
  codesign_search_base: "dc=chaos,dc=local"
  codesign_timeout: 10
```

```bash
quirk --config config-lab-ldaps-codesign.yaml --inventory-code-signing
```

**Expected findings:** 1 × HIGH `Code-signing certificate uses weak algorithm: <subject>` (oracle label `CODE-SIGN/weak-algorithm`) for `uid=codesign-weak` (RSA-1024 /
SHA-1 + CodeSigning EKU). The CBOM will contain a `certificate` component with
`bom_ref = crypto/certificate/codesign/<sha256-fingerprint>`.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-ldaps` for the full oracle row.

---

### 3.12 dnssec Profile (first released in 4.10.0)

The `dnssec` profile ships a BIND9 authoritative nameserver pre-configured with intentionally weak DNSSEC signing — `RSASHA1` algorithm zones and an unsigned test zone — designed to exercise QU.I.R.K.'s DNS cryptography audit path. It is the canonical chaos lab target for DNSSEC weakness detection.

| Port        | Service      | Protocol | Finding Tag                       |
|-------------|--------------|----------|-----------------------------------|
| 15353/udp   | bind9-dnssec | DNS/UDP  | all three DNSSEC findings: RSASHA1 weak-algo CRITICAL, unsigned zone HIGH, NSEC MEDIUM |
| 15353/tcp   | bind9-dnssec | DNS/TCP  | no findings of its own: TCP only carries a retry of a truncated UDP reply |

The scanner sends every DNSSEC query (NS, DNSKEY, DS and the NSEC probe) over UDP first and retries over
TCP only when the UDP reply is truncated (dnspython's `udp_with_fallback`). Each finding is recorded
against port 15353 with protocol `DNSSEC`, never against a transport, so the findings cannot be split
by UDP and TCP. `RSASHA1` and `NSEC` both come from the `weak.chaos.local` zone (RSASHA1-signed, with
NSEC records); the unsigned-zone finding comes from `unsigned.chaos.local`. The scanner only reaches
port 15353 when `connectors.dnssec_resolver` is set to `127.0.0.1:15353`; without it, queries go to port 53.

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

### 3.13 saml Profile (first released in 4.10.0)

The `saml` profile ships a simpleSAMLphp IdP configured with a deliberately weak RSA-1024 signing certificate. The scanner also reports a SHA-1 algorithm URI when the IdP's metadata advertises one (the oracle treats that finding as optional). Together these exercise QU.I.R.K.'s SAML metadata inspection path. This is the canonical chaos lab target for SAML signing-certificate weakness.

| Port | Service       | Protocol | Finding Tag                    |
|------|---------------|----------|--------------------------------|
| 8080 | simplesamlphp | HTTP/TLS | RSA-1024 signing cert CRITICAL |
| 8080 | simplesamlphp | HTTP/TLS | SHA-1 algorithm URI HIGH (only if the metadata advertises one) |

> **Port note:** The compose-authoritative host port is **8080**. Earlier versions of this guide and the v3 oracle incorrectly listed 8880 — 8080 is correct. Keycloak (identity profile) uses `expose: 8080` not `ports:`, so there is no host-level conflict when both profiles run simultaneously.

**Start:**

```bash
PROFILE_ARGS="--profile saml" ./lab.sh up
```

**Expected scanner findings:**

- `RSA-1024 signing cert` detected in SAML metadata — CRITICAL
- `SHA-1 algorithm URI` in SAML signing method — HIGH (only if the IdP's metadata advertises one; the oracle treats it as optional)

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-saml`

---

### 3.14 kerberos Profile (first released in 4.10.0)

The `kerberos` profile runs a Samba Active Directory Domain Controller (realm `QUIRK.LAB`), giving QU.I.R.K.'s Kerberos etype enumeration scanner a realistic target. Re-measured 2026-10-23 against the real KDC: probed as the default principal `Administrator` it answers with the etype list [18], `aes256-cts-hmac-sha1-96` only, which the scanner rates SAFE, so the profile as provisioned yields no weak-etype finding. (The scanner would rate `rc4-hmac` and `aes128-cts-hmac-sha1-96` HIGH if a KDC offered them; this lab does not.)

| Port | Service  | Protocol  | Finding Tag                              |
|------|----------|-----------|------------------------------------------|
| 88   | samba-dc | Kerberos  | `etype:18:aes256-cts-hmac-sha1-96` SAFE, no finding (measured) |
| 389  | samba-dc | LDAP      | no LDAP-exposure finding (no scanner code emits one); 389 is not in the default TLS port list |

> **Port collision warning:** Ports 88 and 389 are not remapped to a non-standard range. If the lab host is a domain member or has a local Kerberos/LDAP daemon (e.g. `krb5kdc`, Active Directory agent, or system OpenLDAP on port 389), there will be a conflict. Verify with `lsof -i:88 -i:389` before starting this profile.

**Start:**

```bash
PROFILE_ARGS="--profile kerberos" ./lab.sh up
```

**Expected scanner findings:**

- One `etype:18:aes256-cts-hmac-sha1-96` KERBEROS endpoint, SAFE, no finding (measured 2026-10-23)
- Kerberos targets must be an FQDN (for example `dc.quirk.lab`, with a hosts entry you add); a bare IP such as `127.0.0.1` is used as the realm and the KDC answers principal-unknown, so the scan yields `kerberos-etypes-unavailable-principal-unknown`
- Known issues: the Samba KDC closes about half of its TCP connections with no reply (42 of 90 direct probes across two runs on 2026-10-23); the scanner retries once over TCP, then falls back to UDP, and the UDP answer is checked exactly like a TCP answer, so a UDP failure gives `kerberos-unreachable` and never a false `kerberos-no-preauth` (65 live scans on 2026-10-23: 0 such rows; 17 of them used UDP); the `samba-dc` healthcheck uses `smbclient`, which the image lacks, so the container never reports healthy; and host port 88 conflicts with macOS's own KDC

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-kerberos`

---

### 3.15 vault Profile (first released in 4.10.0 — DAR)

The `vault` profile (introduced in Phase 30) ships a standalone HashiCorp Vault 1.17 dev server (`vault-30`) pre-seeded with transit keys, a PKI root CA, and auth method mounts that exercise QU.I.R.K.'s Vault connector. It is intentionally on port **28200**. An older Vault instance (image 1.15, port 20009) belonged to the `storage` profile, which has been removed (§3.9).

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

**Expected scanner findings** (endpoint severities, which the dashboard's Data at Rest page lists; the
CLI findings list has no Vault evaluator, see the note at the top of §3):

- `PKI/<mount>` RSA<4096 root CA detected — HIGH
- `auth/token` always-on in dev mode — HIGH
- `transit/<key_name>` exportable transit key — MEDIUM
- `auth/userpass` method enabled — MEDIUM

See: `labs/vault/expected_results.md`

---

### 3.16 database Profile (first released in 4.10.0 — DAR)

The `database` profile (introduced in Phase 27) ships a PostgreSQL 15 instance (`postgres-ssl-off`) and a MySQL 8 instance (`mysql-ssl-off`), each with SSL/TLS explicitly disabled, providing QU.I.R.K.'s database connector with clear regression targets for plaintext-connection detection.

| Port  | Service          | Engine     | Expected Finding                                              | Severity |
|-------|------------------|------------|---------------------------------------------------------------|----------|
| 25432 | postgres-ssl-off | PostgreSQL | `PostgreSQL/ssl-off` — SSL disabled at engine level           | HIGH     |
| 25432 | postgres-ssl-off | PostgreSQL | `PostgreSQL/plaintext-connections-allowed` — non-SSL conns    | HIGH     |
| 23306 | mysql-ssl-off    | MySQL      | `MySQL/ssl-off` — SSL disabled at engine level                | HIGH     |

Credentials: both engines use the application user `quirk_scanner` with password `quirk_scanner` (database `quirk_db`). MySQL's root password is `root`.

**Start:**

```bash
PROFILE_ARGS="--profile database" ./lab.sh up
```

**Expected scanner findings** (endpoint severities, which the dashboard's Data at Rest page lists; the
CLI findings list has no database evaluator, see the note at the top of §3):

- `PostgreSQL/ssl-off` — SSL parameter is `off` — HIGH
- `PostgreSQL/plaintext-connections-allowed (N non-SSL)` — non-SSL connections present in `pg_stat_ssl` — HIGH
- `MySQL/ssl-off` — `Ssl_cipher` status variable is empty — HIGH

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-database`

---

### 3.17 storage-s3 Profile (first released in 4.10.0 — DAR)

The `storage-s3` profile (introduced in Phase 28) ships an S3-compatible object storage server: moto since Phase 220, MinIO before. A seed container creates two buckets on startup: one encrypted (SSE-S3) and one unencrypted, providing QU.I.R.K.'s S3 connector with a clean positive/negative pair for encryption-at-rest detection.

**Image source (Phase 220): moto, not MinIO.** `minio` and `minio-seed` run `motoserver/moto:5.2.3` (Apache-2.0, Docker Hub, amd64+arm64). MinIO's pinned images are no longer pullable from the places the lab used to get them: as of 2026-10-12 Docker Hub returns 404 for `minio/minio:RELEASE.2025-09-07T16-13-09Z`, quay.io answers an anonymous manifest request with 401, and dl.min.io returns 410 for the pinned release. The scanner's S3 path needs only three S3 behaviours (`list_buckets`, `get_bucket_encryption`, and the `ServerSideEncryptionConfigurationNotFoundError` for an unencrypted bucket); the lab's compose file records that all three were verified against moto 5.2.3. The endpoint is unchanged (`localhost:29000`, via `MOTO_PORT=9000`). The seed is `storage/s3-seed.py` (boto3, run from the same image). The service names, the `minio` hostname and the `minioadmin` credentials are historical names, kept deliberately. MinIO's admin console (29001) no longer exists. See `quantum-chaos-enterprise-lab/README.md`'s "Phase 220: MinIO replaced by moto" note. The scanner itself still supports real MinIO endpoints as a customer target; only the lab stopped running one.

| Port  | Service       | Bucket              | SSE Mode | Expected Finding     | Severity |
|-------|---------------|---------------------|----------|----------------------|----------|
| 29000 | minio         | encrypted-bucket    | SSE-S3   | `S3/sse-s3`          | (none)   |
| 29000 | minio         | unencrypted-bucket  | None     | `S3/unencrypted`     | HIGH     |

Credentials: access key `minioadmin`, secret key `minioadmin` (historical MinIO-era values, kept so the seed and the scanner configs need no edit).

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

**Expected scanner findings** (endpoint severities, which the dashboard's Data at Rest page lists; the
CLI findings list has no S3 evaluator, see the note at the top of §3):

- `S3/unencrypted` on `arn:aws:s3:::unencrypted-bucket` — HIGH
- `S3/sse-s3` on `arn:aws:s3:::encrypted-bucket` — no severity (positive control; the Data at Rest page
  still lists the bucket, at INFO)

See: `labs/storage/expected_results.md`

---

### 3.18 email Profile (first released in 4.10.0)

The `email` profile (introduced in Phase 32) ships a Postfix SMTP server and a Dovecot IMAP/POP3 server. Postfix is hard-capped to TLS 1.2 with non-PFS RSA cipher suites, producing weak-cipher and STARTTLS-downgrade findings. The live capture recorded in the oracle shows Dovecot negotiating TLS 1.3, so its ports do not emit weak-cipher findings under default scan invocation (see caveat below).

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

`lab.sh` materializes `labs/email/certs/{postfix,dovecot}.{crt,key}` on first
`up` — no manual cert-generation step is required.

**Expected scanner findings:**

- `Weak cipher suite on email TLS endpoint` — port 25 — HIGH (EMAIL-09)
- `Weak cipher suite on email TLS endpoint` — port 465 — HIGH (EMAIL-09)
- `Weak cipher suite on email TLS endpoint` — port 587 — HIGH (EMAIL-09)
- `STARTTLS downgrade risk on SMTP` — port 25 — MEDIUM (EMAIL-08)

> **Reachability note.** These findings are what `evaluate_email_endpoints` returns for the 25, 465 and 587 endpoints once the lab's host ports are mapped back to the standard ports (30025 to 25, 30465 to 465, 30587 to 587); the oracle in `labs/email/expected_results.md` records that rewrite. The product's email scan probes only the fixed ports 25, 465, 587, 143, 993, 110 and 995 on each scanned host, so a scan of `127.0.0.1` does not reach this profile's 30xxx ports. For an end-to-end scan use the `multihost` profile (§3.32), whose `mh-postfix` and `mh-dovecot` listen on the standard ports.

> **Dovecot caveat:** Dovecot 2.3.16 (Ubuntu 22.04) negotiates TLS 1.3 when the client offers it, bypassing the TLS 1.2 weak-cipher restriction in the lab's config. Ports 30143/30993/30110/30995 emit **no** weak-cipher findings under the default scan path. To exercise the TLS 1.2 weak-cipher path on Dovecot, pin the client: `openssl s_client -tls1_2 -connect localhost:30143 -starttls imap`. The lab also sets `OPENSSL_CONF` on `dovecot-email` to `labs/email/dovecot/openssl-tls12-only.cnf`, which is meant to cap Dovecot at TLS 1.2 with non-PFS suites; the live capture recorded in `labs/email/expected_results.md` still shows TLS 1.3 on these ports, and this guide has not re-captured it, so treat that file as the reference for Dovecot's behaviour.

See: `labs/email/expected_results.md`

---

### 3.19 broker Profile (first released in 4.10.0)

The `broker` profile (introduced in Phase 33) ships three message brokers — Apache Kafka, RabbitMQ, and Redis — each configured with both a plaintext listener and a TLS listener using deliberately weak non-PFS RSA cipher suites. This exercises QU.I.R.K.'s broker scanner across all three broker types simultaneously.

> **Config required to reproduce this table (Phase 190, TRIAGE-06 — corrected 2026-09-08).**
> The table below was written for QU.I.R.K.'s **hardcoded default broker ports**
> (9092/9093, plus 9094 under the `standard` and `deep` scan profiles; 5672/5671; 6379/6380).
> This lab intentionally remaps the first six to
> 29092/29093, 25672/25671, and 26379/26380 (see the port map), so a stock
> `enable_broker: true` scan with no further config probes only the *default* ports,
> none of which this lab publishes, and finds **zero** broker findings against it.
> **To reproduce the table, set
> `connectors.broker_targets` to this lab's mapped ports** — see
> [`docs/configuration.md`](configuration.md) § "`connectors.broker_targets`":
>
> ```yaml
> connectors:
>   enable_broker: true
>   broker_targets:
>     - "localhost:29092"
>     - "localhost:29093"
>     - "localhost:25671"
>     - "localhost:25672"
>     - "localhost:26379"
>     - "localhost:26380"
> ```

| Host Port | Service         | Protocol   | Expected Finding                              | Severity |
|-----------|-----------------|------------|-----------------------------------------------|----------|
| 29092     | kafka-broker    | KAFKA-PLAIN| Plaintext Kafka listener detected             | HIGH     |
| 29093     | kafka-broker    | KAFKA-TLS  | Weak cipher suite on broker TLS endpoint      | HIGH     |
| 25672     | rabbitmq-broker | AMQP-PLAIN | Plaintext AMQP listener detected              | HIGH     |
| 25671     | rabbitmq-broker | AMQPS      | Weak cipher suite on broker TLS endpoint      | HIGH     |
| 26379     | redis-broker    | REDIS-PLAIN| Plaintext Redis listener (no auth)  | HIGH     |
| 26380     | redis-broker    | REDIS-TLS  | Weak cipher suite on broker TLS endpoint      | HIGH     |

**Start:**

Generate TLS certs before first boot:

```bash
cd labs/broker && make certs && cd ../..
PROFILE_ARGS="--profile broker" ./lab.sh up
```

Allow ~30 seconds for all three healthchecks to pass.

**Expected scanner findings (with `connectors.broker_targets` set as shown above):**

- `Plaintext Kafka listener detected` — port 29092 — HIGH (KAFKA-02)
- `Weak cipher suite on broker TLS endpoint` — port 29093 — HIGH (KAFKA-01)
- `Plaintext AMQP listener detected` — port 25672 — HIGH (RABBIT-02)
- `Weak cipher suite on broker TLS endpoint` — port 25671 — HIGH (RABBIT-01)
- `Plaintext Redis listener (no auth)` — port 26379 — HIGH (REDIS-02)
- `Weak cipher suite on broker TLS endpoint` — port 26380 — HIGH (REDIS-01)

**Total: 6 HIGH findings** (3 plaintext + 3 weak-cipher TLS).

See: `labs/broker/expected_results.md`

> **Why the `broker_targets` run can differ from this table.** `connectors.broker_targets` ports
> are *additive* and are handed as one flat list to all three broker drivers (Kafka, RabbitMQ,
> Redis), and each driver probes every override port that is not one of its own default ports in
> both plaintext and TLS mode, because
> the operator names a port, not a listener type. Reading the scanner source
> (`quirk/scanner/broker_scanner.py`), that has these consequences:
>
> - Kafka's plaintext check is a bare TCP connect, so it reports `KAFKA-PLAIN` on **any** override
>   port that accepts a connection, not only the genuine Kafka listener (29092). Naming this lab's
>   RabbitMQ and Redis ports therefore also yields `KAFKA-PLAIN` rows for them.
> - Redis's raw-TLS probe returns nothing (not an error row) when a speculative override-port
>   probe fails, so foreign-family ports do not produce `REDIS-TLS` error rows.
> - Kafka's `sslyze`-based TLS probe also runs on the other families' TLS ports (25671, 26380),
>   so it can report their weak ciphers under a `KAFKA-TLS` label.
> - This lab's Kafka SSL listener (29093) is configured with `ssl.client.auth=none`, so the lab
>   itself does not require a client certificate.
>
> These are properties of the scanner's additive-override design, not a lab misconfiguration;
> this lab's port map is the fixture. This guide has not re-run the scan, so the counts in the
> table above are the oracle's expectation, not a fresh measurement.

---

### 3.20 tls-cert-defects Profile (first released in 4.10.0)

The `tls-cert-defects` profile (introduced in Phase 46) ships four nginx services, each serving a TLS endpoint with a different certificate defect class. This is the canonical chaos lab target for the four certificate-defect finding types added with this profile (`TLS-FIND-01..05`). Ports 13444–13447 are used; 13443 (phaseA `tls-missing-intermediate`) is preserved for back-compat.

| Port  | Service               | Cert Defect               | Expected Finding                          | Severity |
|-------|-----------------------|---------------------------|-------------------------------------------|----------|
| 13444 | tls-cert-expired      | Expired certificate       | `TLS certificate expired`                 | CRITICAL |
| 13445 | tls-cert-selfsigned   | Self-signed certificate   | `TLS certificate is self-signed`          | HIGH     |
| 13446 | tls-cert-untrusted-ca | Untrusted/private CA      | `TLS certificate issued by untrusted CA`  | MEDIUM   |
| 13447 | tls-cert-rsa1024      | RSA-1024 key (weak size)  | `TLS certificate uses undersized RSA key` | HIGH     |

**Start:**

```bash
PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up
```

**Expected scanner findings:**

- `TLS certificate expired` on port 13444 — CRITICAL
- `TLS certificate is self-signed` on port 13445 — HIGH
- `TLS certificate issued by untrusted CA` on port 13446 — MEDIUM
- `TLS certificate uses undersized RSA key` on port 13447 — HIGH

Ports 13444–13447 are not in the scanner's default TLS port list, so add them to `scan.ports_tls`.

> **Port note:** Ports 13444–13447 do not conflict with any other profile. Port 13443 (`tls-missing-intermediate` in phaseA) is already taken, so this profile starts at 13444.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-tls-cert-defects`

---

### 3.21 fuzz-target Profile (first released in 5.5.0 — Phase 96 LAB-01)

The `fuzz-target` profile is a deliberately-weak FastAPI REST service designed as the
canonical validation target for QU.I.R.K.'s active REST fuzzer (`--fuzz`). It exposes
three intentional weaknesses: missing `Strict-Transport-Security` header (HSTS), an
`http://` server URL in its OpenAPI spec (HTTP-only credential transmission), and a
`/probe` endpoint that accepts JWT tokens **without algorithm verification** (RS256→HS256
alg-confusion acceptance). All weaknesses are intentional and isolated to this profile.

| Port  | Service      | Expected Finding (`service_detail`) | Severity |
|-------|--------------|-------------------------------------|----------|
| 20100 | fuzz-target  | `hsts_missing`                      | HIGH     |
| 20100 | fuzz-target  | `http_creds`                        | HIGH     |
| 20100 | fuzz-target  | `alg_confusion`                     | CRITICAL |

The oracle labels these `HSTS_MISSING`, `HTTP_ONLY_CRED` and `ALG_CONFUSION`. The fuzzer's TLS-downgrade and weak-cipher probes (`tls_downgrade_accepted`, `cipher_weak`) need a TLS listener, and this fixture serves plain HTTP, so they do not fire here.

**Start:**

```bash
PROFILE_ARGS="--profile fuzz-target" ./lab.sh up
```

**Validation scan:** the `quirk` CLI cannot aim `--fuzz` at this fixture. `run_scan.py` builds the fuzzer's base URL as `https://<first configured target host>` (`https://localhost` when none is configured), so a plain-HTTP service on port 20100 is never the fuzz target, and a targets file containing `http://localhost:20100` is rejected as an invalid target because any token containing `/` is parsed as a CIDR. The endpoints below are for a direct `run_fuzz_scan(base_url="http://localhost:20100", ...)` call; this guide has not run one.

When `--fuzz` is used against an HTTPS target, it needs the `[api]` extra (`pip install 'quirk-scanner[api]'`, which brings schemathesis), refuses to run without an interactive terminal, and waits for you to type `CONFIRM` before it sends any request. The fuzzer validates every request URL through the same scope gate as other scanners, so a loopback target needs `--allow-internal-targets`. To exercise the alg-confusion probe, also pass `--fuzz-jwt-alg-confusion` and an RS256 bearer token via `--auth-bearer`.

> **Expected (the oracle's expectation for a direct `run_fuzz_scan` call, not reproduced here):** at minimum 2 findings: `hsts_missing` (HIGH) and `alg_confusion`
> (CRITICAL) when the alg-confusion probe is also enabled with an RS256 bearer token.

**Available endpoints:**

- `GET /openapi.json` — Minimal OpenAPI 3.0 spec with `http://localhost:20100` server URL (HTTP-only credential probe)
- `GET /.well-known/jwks.json` — Exposes RS256 public key for alg-confusion probe
- `GET /probe` — Accepts any `Authorization: Bearer <token>` without algorithm verification (always returns 200 OK)

> **Lab note:** `lab.sh` requires no `ALL_PROFILES` edit for this profile —
> `_derive_all_profiles()` discovers `fuzz-target` dynamically from `docker-compose.yml`
> at runtime via `yq` or the `grep` fallback.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-fuzz-target`

---

### 3.22 hwcompat Profile (first released in 5.8.0 — Phase 127 + Phase 133 LAB-01 + Phase 139 SNMPV3-01..04)

The `hwcompat` profile (introduced in Phase 127, extended in Phase 133) ships three services that
exercise QU.I.R.K.'s agentless hardware fingerprinting capability across all three fingerprint
paths: SSH banner (unknown-vendor fallback), HTTP management headers (HPE positive path), and SNMP
sysDescr (Cisco positive path). Hardware findings are **advisory-only** — they appear in the CBOM
and in the Hardware Inventory table on the dashboard's CBOM page, but do not affect the quantum-readiness score.

> **Prerequisites:** SNMP fingerprinting (the `hwcompat-snmp` row below) requires the `[hw]` extras group; the SSH-banner and HTTP-header
> paths do not. Install before running this profile: `pip install 'quirk-scanner[hw]'`

| Host Port  | Service       | Protocol | Purpose                                  | Expected Finding                                |
|------------|---------------|----------|------------------------------------------|-------------------------------------------------|
| 20221      | hwcompat-ssh  | SSH      | OpenSSH banner → unrecognized pattern    | vendor=Unknown, fingerprint_method=ssh_banner   |
| 20222      | hwcompat-http | HTTP     | nginx with HPE-iLO5 mgmt headers         | vendor=HPE, model=iLO5, fingerprint_method=http_mgmt (only when served on 443/8443/8080/80; see below) |
| 20223/udp (and 161/udp) | hwcompat-snmp | SNMP/UDP | Net-SNMP serving Cisco IOS sysDescr OID  | vendor=Cisco, fingerprint_method=snmp, confidence=medium |

**Start:**

```bash
PROFILE_ARGS="--profile hwcompat" ./lab.sh up
```

**SNMP scan command (v2c):** point a config at `127.0.0.1` (as in §3.1) and add `--enable-snmp`.
`--enable-snmp` probes each scanned host on **UDP 161** — the scanner hardcodes that port — so it reaches
the simulator through the lab's additional `161:161/udp` mapping, not through 20223. The host must
produce at least one TLS, SSH or PQC endpoint to be probed (the core lab will do; without Nmap discovery, as in §3.1's config, `hwcompat-ssh` counts only if `20221` is added to `scan.ports_tls`, which `config-lab-core.yaml` does not list). The
community string comes from `connectors.snmp_community` (default `public`).

```bash
quirk --config config-lab-core.yaml --enable-snmp
```

**SNMPv3 auth+priv scan command (Phase 139):** requires a `connectors.snmp_v3_credentials`
entry for `127.0.0.1` (see `docs/configuration.md`) pointing at env vars holding the lab
passphrases below, then the same `--enable-snmp` flag — the scanner attempts v3 first and
only falls back to v2c/none per host:

```bash
quirk --config config-lab-core.yaml --enable-snmp
```

**hwcompat-snmp container details:**

The `hwcompat-snmp` service is a Net-SNMP container simulating a Cisco IOS device, built locally
from `FROM alpine:3.19` (CHAOS-05 compliant pinned base image). It listens on UDP port 161
(mapped to host ports 20223 and 161) with community string `public` (read-only, lab use only) **and**,
as of Phase 139, a SNMPv3 USM user for live auth+priv scan testing.

SNMP MIB-II OIDs served:
- `sysDescr (1.3.6.1.2.1.1.1.0)`: `"Cisco IOS Software, Version 15.2(4)M3, RELEASE SOFTWARE (fc2)"`
- `sysName (1.3.6.1.2.1.1.5.0)`: `"cisco-sim-hwcompat"`
- `sysObjectID (1.3.6.1.2.1.1.2.0)`: `1.3.6.1.4.1.9.1.1` (Cisco Enterprise OID)

**SNMPv3 USM user (Phase 139 SNMPV3-01..04):** `quirkv3user` — auth protocol `SHA`, priv
protocol `AES` (the scanner also accepts SHA224 to SHA512 and AES192/AES256, but the lab user uses only SHA and AES). Lab passphrases (`quirklabauthpass1` / `quirklabprivpass1`)
are hardcoded in `snmpd.conf` as non-secret test values (same posture as the `public`
community string) — set them as the values of whatever env vars your `snmp_v3_credentials`
config entry names for `auth_key_env`/`priv_key_env`.

**Expected scanner findings:**

- **hwcompat-ssh (port 20221):** `vendor=Unknown`, `fingerprint_method=ssh_banner`, `confidence=low`, `pqc_status=unknown` — the generic OpenSSH banner does not match any vendor pattern in `HARDWARE_MATRIX`; `vendor=Unknown` rows are never suppressed (D-06)
- **hwcompat-http (port 20222):** `vendor=HPE`, `model=iLO5`, `fingerprint_method=http_mgmt`, `confidence=high`, `pqc_status=partial` — nginx serves `X-Device-Model: HPE-iLO5` and `Server: iLO/5.0` headers matching the HPE iLO5 HARDWARE_MATRIX entry. The scanner's HTTP management probe only tries ports 443, 8443, 8080 and 80, so a scan does not reach the simulator on host port 20222; these values appear when the same headers are served on one of those ports. Check the headers directly with `curl -i http://localhost:20222/`
- **hwcompat-snmp (UDP 161, published as 20223 and 161), v2c path:** `vendor=Cisco`, `fingerprint_method=snmp`, `confidence=medium`, `pqc_status=partial`, `snmp_version="v2c"` — the vendor comes from the sysDescr text (`"Cisco IOS Software"`); the sysObjectID is stored in `snmp_sysobjectid` but is not used for the vendor match
- **hwcompat-snmp (UDP 161, published as 20223 and 161), v3 auth+priv path (Phase 139):** same vendor/model match, plus `snmp_version="v3 auth+priv"`, `snmp_auth_protocol="SHA"`, `snmp_priv_protocol="AES"` when a valid `quirkv3user` credential is configured; a scan with wrong v3 credentials against this container yields `snmp_version="v3-failed-fell-back"` (D-03) rather than silently reporting v2c

> **Note (2026-09-13):** the Cisco `pqc_status=partial` value above is the result of the 2026-09-13
> `HARDWARE_MATRIX` re-verification against vendor sources, which changed it from `unsupported`; the HPE `partial` value predates that re-verification, which re-sourced the HPE entry but left its status unchanged. `pqc_status` is copied verbatim from the
> **vendor-scoped** catalog entry by `_apply_entry()` — it is not reasoned per model — so the simulated
> iLO 5 and IOS 15.2 devices inherit the HPE-wide and Cisco-wide verdicts rather than their own. See the
> entries' `notes` in `quirk/scanner/hardware_meta.py` for what each verdict actually rests on.

> **Lab note:** `lab.sh` requires no `ALL_PROFILES` edit for this profile —
> `_derive_all_profiles()` discovers `hwcompat` dynamically from `docker-compose.yml`
> at runtime via `yq` or the `grep` fallback.

See: `quantum-chaos-enterprise-lab/expected_results_hwcompat.md`

---

### 3.23 otics Profile (first released in 5.11.0 — Phase 141 OTICS-04)

The `otics` profile (D-09: a standalone profile, not folded into `hwcompat` — OT/ICS is a
genuinely distinct risk/protocol category) ships two **deliberately fragile** simulators
that validate QU.I.R.K.'s agentless OT/ICS fingerprinting (Modbus/TCP and BACnet/IP) end
to end. Hardware findings are **advisory-only** — they appear in the CBOM and
the Hardware Inventory table on the dashboard's CBOM page, but do not affect the quantum-readiness score.

> **Prerequisites:** OT/ICS scanning requires the `[hw]` extras group. Install before
> running this profile: `pip install 'quirk-scanner[hw]'`
>
> **Risk note:** unlike the other chaos-lab profiles, these two simulators are
> intentionally fragile (D-10) — they enforce single-in-flight-only and
> reset/drop malformed input, mirroring documented real-world PLC/RTU fragility. This is
> by design: it is exactly what lets this profile empirically prove the scanner's D-05
> one-strike circuit breaker keeps a real fragile device healthy. See
> `docs/operators-guide.md` §9.4 for the full OT/ICS risk-warning and authorization
> guidance before pointing `--enable-modbus`/`--enable-bacnet` at anything outside this lab.

| Host Port    | Service       | Protocol    | Purpose                                            | Expected Finding |
|--------------|---------------|-------------|-----------------------------------------------------|-------------------|
| 502          | otics-modbus  | Modbus/TCP  | Fragile Schneider Electric M221 PLC simulator        | modbus_vendor=Schneider Electric, modbus_model=M221, modbus_probe_state=identified |
| 47808/udp    | otics-bacnet  | BACnet/IP   | Fragile Johnson Controls FX16 controller simulator   | bacnet_vendor=5 (Johnson Controls), bacnet_model=FX16, bacnet_probe_state=identified |

**Start:**

```bash
PROFILE_ARGS="--profile otics" ./lab.sh up
```

**Scan command:**

```bash
quirk --config config-lab-core.yaml --enable-modbus --enable-bacnet
```

`--enable-modbus` adds TCP port 502 to the scanned ports itself, and BACnet probes every scanned host
on UDP 47808. Neither OT scanner consults `security.allow_internal_targets` (that flag gates the URL-fetching connectors), so this scan needs no `--allow-internal-targets`.

**Simulator architecture.** Each container runs a small asyncio "gatekeeper" (custom code
that enforces only the D-10 fragility admission policy — single-in-flight tracking and
malformed-header rejection) in front of a real protocol library: `pymodbus`'s
`ModbusTcpServer` handles all actual Modbus/TCP framing and FC 43/14 encode/decode for
`otics-modbus`; a real `bacpypes3` `Application` handles all actual BACnet/IP framing and
Who-Is/I-Am/ReadProperty for `otics-bacnet`. Neither hand-rolls the underlying protocol.

**Expected scanner findings:**

- **otics-modbus (port 502):** `modbus_vendor=Schneider Electric`, `modbus_model=M221`,
  `modbus_firmware=1.6.2.0`, `modbus_probe_state=identified` — FC 43/14 Read Device
  Identification (Basic category) match on the simulator's VendorName/ProductCode/
  MajorMinorRevision objects
- **otics-bacnet (port 47808/udp):** `bacnet_vendor=5`, `bacnet_model=FX16`,
  `bacnet_firmware=9.0.1`, `bacnet_probe_state=identified` — directed-unicast Who-Is/I-Am
  plus ReadProperty(model-name, firmware-revision) on the simulator's Device object
- **Forced concurrent probe (manual verification):** a second connection/datagram sent to
  either simulator while a probe is already in flight is reset/dropped by the simulator;
  if the scanner's own probe observes the resulting anomalous response, it records
  `modbus_probe_state="aborted_anomalous_response"` or
  `bacnet_probe_state="aborted_anomalous_response"` — the distinct D-13 abort state, never
  masquerading as "no response"

> **Lab note:** `lab.sh` requires no `ALL_PROFILES` edit for this profile —
> `_derive_all_profiles()` discovers `otics` dynamically from `docker-compose.yml` at
> runtime via `yq` or the `grep` fallback.

See: `quantum-chaos-enterprise-lab/expected_results_otics.md`

---

### 3.24 segmented-network Profile (first released in 5.12.0 — Phase 152 DISC-09/DISC-10)

The `segmented-network` profile builds a realistic *routed-segment* unreachable-host
environment: two custom Docker bridge networks — a "live" subnet carrying real reused
services (TLS + SSH) and a "dead" subnet with no containers at all — joined by a small
gateway container whose iptables `FORWARD`-chain REJECT rules make every unassigned
dead-subnet address answer with a genuine TCP RST (`closed`) or ICMP host-unreachable,
instead of the silent-timeout behavior that the unassigned-loopback-alias approach of every other chaos-lab profile produces on a macOS host. This gives chunked discovery and
partial-result tolerance (DISC-08/DISC-09) a target that behaves like a real routed
network segment when scanning past its edge, and lets DISC-10 empirically settle the
Phase 144 nmap timing-engine artifact against something real rather than simulated.

| Service | Live Subnet IP | Port | Purpose |
|---------|-----------------|------|---------|
| `segnet-gateway` | 10.70.0.2 (live) / 10.71.0.2 (dead) | — | Routes segnet-live ↔ segnet-dead; REJECTs all forward traffic to the dead subnet |
| `segnet-live-tls` | 10.70.0.10 | 443 | Real TLS 1.2/1.3 service (clones `tls-modern`'s image/config) |
| `segnet-live-ssh` | 10.70.0.11 | 2222 | Real OpenSSH service (clones `hwcompat-ssh`'s image/config) |
| `segnet-prober` | 10.70.0.20 (segnet-live only) | — | In-lab idle container (`sensor.Dockerfile`) that drives all verification via `docker compose exec` |

No host ports are published for this profile — every service is reachable only from
inside the lab network.

**Start:**

```bash
PROFILE_ARGS="--profile segmented-network" ./lab.sh up
```

**Scan command:**

```bash
docker compose -p chaoslab --profile segmented-network exec segnet-prober nmap -sT -Pn -p 443 10.70.0.10   # live TLS host: open
docker compose -p chaoslab --profile segmented-network exec segnet-prober nmap -sT -Pn -p 2222 10.70.0.11  # live SSH host: open
docker compose -p chaoslab --profile segmented-network exec segnet-prober nmap -sT -Pn -p 443 10.71.0.0/26 # dead range: closed/RST (recorded sweep: 0 filtered)
```

`-p chaoslab` is the project name `lab.sh` starts the lab under; without it compose derives the project
name from the directory and does not find the running containers.

> **Risk note (macOS host-routing):** unlike every other profile in this document, this
> profile's scan commands must run with `docker compose ... exec segnet-prober ...` — never
> as a scan of `127.0.0.1` from the host shell. macOS Docker Desktop's
> VM-based networking model cannot route host traffic into custom bridge networks (the lab's compose file records this),
> and no service in this profile publishes a host port, so the host has no path to `segnet-live`/`segnet-dead`;
> `segnet-prober` is the in-lab container this profile's scans run from. This holds on Linux hosts too
> (the in-container pattern works identically there), so no host-OS branching is needed.

**Architecture note.** `segnet-gateway` is attached to both bridge networks with
`cap_add: [NET_ADMIN]` (never `--privileged`) and applies `iptables -A FORWARD -d
<dead-cidr> ... -j REJECT --reject-with tcp-reset` (TCP) and `--reject-with
icmp-host-unreachable` (everything else) inside its own network namespace at container
start, with IP forwarding enabled via compose's `sysctls: [net.ipv4.ip_forward=1]`.
`segnet-prober` deliberately joins **only** `segnet-live` and reaches the dead subnet by
an explicit `ip route add 10.71.0.0/24 via 10.70.0.2` at container start — a container
that is itself a *member* of `segnet-dead` would reach unassigned dead-subnet addresses
via direct L2 bridge delivery, bypassing `segnet-gateway`'s `FORWARD` chain entirely
(confirmed via live smoke test during Phase 152 execution).

The dead-range verification target is `10.71.0.0/26` (62 usable addresses). The gateway's
own `10.71.0.2` is excluded from the automated REJECT-rule sweep in
`compare_discovery.py` — a probe to `.2` is handled by the gateway container's own
`INPUT` chain (ordinary "no listener" TCP RST), not the `FORWARD`-chain `REJECT` rule
this lab exists to verify — leaving 61 addresses genuinely REJECT-verified via the diff
script. A raw `nmap` sweep of the full `/26` CIDR (64 addresses, including the `.0`
network / `.63` broadcast addresses) independently confirmed 63/64 REJECT-rule hits, with
`10.71.0.2` correctly excluded as gateway-self. A **scaled reproduction of the original
~1024-host batch, not a 1:1 replica**. The REJECT rule covers the entire `/24` CIDR, so
this profile adds exactly 4 new containers regardless of range size — no per-dead-host
container is needed.

> **Lab note:** `lab.sh` requires no `ALL_PROFILES` edit for this profile —
> `_derive_all_profiles()` discovers `segmented-network` dynamically from
> `docker-compose.yml` at runtime via `yq` or the `grep` fallback.

See: `quantum-chaos-enterprise-lab/expected_results_segmented_network.md`

---

### 3.25 smime Profile (first released in 4.10.0 — Phase 79)

The `smime` profile ships an OpenLDAP instance (`smime-openldap`) seeded by an idempotent
sidecar (`smime-seed`) with three users carrying `userSMIMECertificate` attributes — alice
(RSA-1024/SHA-1, weak), bob (RSA-1024/SHA-256, weak key size only), and carol (RSA-2048/SHA-256,
safe). Plain LDAP only on host port **38900** — LDAPS is intentionally deferred (D-79-R9).

| Port  | Service        | Image                                   | Expected Finding                | Severity |
|-------|----------------|------------------------------------------|----------------------------------|----------|
| 38900 | smime-openldap | bitnamilegacy/openldap:2.6.10-debian-12-r4 | S/MIME weak cert (alice, RSA-1024/SHA-1) | HIGH |
| 38900 | smime-openldap | bitnamilegacy/openldap:2.6.10-debian-12-r4 | S/MIME weak cert (bob, RSA-1024/SHA-256)  | HIGH |
| 38900 | smime-openldap | bitnamilegacy/openldap:2.6.10-debian-12-r4 | carol — no finding (RSA-2048, safe)       | (none)   |

**Start:**

```bash
PROFILE_ARGS="--profile smime" ./lab.sh up
```

Add to your config.yaml:

```yaml
connectors:
  enable_smime: true
  smime_targets:
    - "ldap://localhost:38900"
  smime_search_base: dc=quirk,dc=lab
```

**Expected scanner findings:** 2 endpoint rows rated HIGH (alice, bob); no row for carol. Both rows carry
an RSA-1024 key, but neither the dashboard Findings page nor the CLI findings list shows them as findings
(see the note at the top of §3; surfacing them is tracked as 999.132). S/MIME
endpoints count toward the Identity scoring domain, and their key algorithm (RSA) is recorded in the CBOM as
an algorithm component. No IMAP traffic, no mailbox access (privacy invariant, enforced
by the SMIME-08 AST gate). Idempotent — the seed sidecar uses `ldapadd -c` and swallows exit code
68 (`LDAP_ALREADY_EXISTS`) on subsequent runs.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-smime`

---

### 3.26 adcs Profile (first released in 4.10.0 — Phase 80)

The `adcs` profile ships an OpenLDAP instance (`adcs-openldap`) seeded by an idempotent sidecar
(`adcs-seed`) with a deliberately misconfigured AD CS Configuration partition: an RSA-1024/SHA-1
CA signing cert (`QuirkLabCA`) plus three certificate templates (`BadTemplate-ESC1`,
`BadTemplate-ESC4`, `SafeTemplate`). Plain LDAP only on host port **38910** (chosen to avoid
`smime`'s 38900, `ldaps`'s 636, and `kerberos`'s 389). Authenticated SIMPLE bind is supported for
real-AD parity; anonymous bind is permitted inside the lab.

| Port  | Service       | Image                                   | Expected Finding                          | Severity |
|-------|---------------|------------------------------------------|--------------------------------------------|----------|
| 38910 | adcs-openldap | bitnamilegacy/openldap:2.6.10-debian-12-r4 | QuirkLabCA weak CA signing algorithm (RSA-1024/SHA-1) | HIGH |
| 38910 | adcs-openldap | bitnamilegacy/openldap:2.6.10-debian-12-r4 | BadTemplate-ESC1 misconfiguration          | HIGH     |
| 38910 | adcs-openldap | bitnamilegacy/openldap:2.6.10-debian-12-r4 | BadTemplate-ESC4 (ADCS-COVERAGE-GAP)       | LOW      |
| 38910 | adcs-openldap | bitnamilegacy/openldap:2.6.10-debian-12-r4 | ESC5/ESC7/ESC8 (ADCS-COVERAGE-GAP, one each) | LOW    |

**Start:**

```bash
PROFILE_ARGS="--profile adcs" ./lab.sh up
```

**Scanner validation:** there is no `--adcs-target` CLI flag; enable the AD CS connector in `config.yaml`
(it needs the `[adcs]` extra, `pip install 'quirk-scanner[adcs]'`, which is also part of `[all]`):

```yaml
connectors:
  enable_adcs: true
  adcs_targets:
    - "ldap://localhost:38910"
  adcs_search_base: dc=quirk,dc=lab
```

The no-write and AST-gate guarantees are also exercised by `tests/test_adcs_no_writes.py` and
`tests/test_adcs_ast_gate.py`.

**Expected findings** (endpoint rows with a severity; see the note at the top
of §3): 1 HIGH weak-signing (QuirkLabCA), 1 HIGH ESC1 (BadTemplate-ESC1), 0 from
SafeTemplate, and exactly 4 LOW ADCS-COVERAGE-GAP findings (one per non-LDAP-observable ESC
class: ESC4, ESC5, ESC7, ESC8). The endpoints (`protocol="ADCS"`) count toward the Identity scoring domain.
Only the CA row carries a key, so only the CA's key algorithm (RSA) reaches the CBOM. No AD CS row is listed
as a finding on the dashboard Findings page or in the CLI findings list (tracked as 999.132). No certificate enrollment, no CSR generation, no LDAP modify/add/delete
operations (privacy invariant, enforced by ADCS-09). Idempotent — the seed sidecar uses
`ldapadd -c` and swallows exit code 68.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-adcs`

---

### 3.27 postgres-tls Profile (first released in 5.0.0 — Phase 89 LAB-01)

The `postgres-tls` profile ships a standalone PostgreSQL 16.6 instance with STARTTLS forced to
weak, non-PFS RSA key-exchange ciphers (`AES128-SHA:AES256-SHA`, TLS 1.2 only) and a self-signed
RSA-2048 certificate — a dedicated target for sslyze's `POSTGRES` STARTTLS probe, separate from
the `database` profile's plaintext-only `postgres-ssl-off` target.

| Port  | Service       | Image        | Expected Finding                                              | Severity |
|-------|---------------|--------------|-----------------------------------------------------------------|----------|
| 39432 | postgres-tls  | postgres:16.6 | With the DB connector configured: a `POSTGRESQL` row, `PostgreSQL/ssl-enforced` or `PostgreSQL/plaintext-connections-allowed (N non-SSL)` — the weak ciphers and RSA-2048 certificate are not observed (see below) | none / HIGH |

**Start:**

```bash
make -C labs/postgres-tls certs
PROFILE_ARGS="--profile postgres-tls" ./lab.sh up
```

`lab.sh` does not generate this profile's certificate (it only generates the mTLS, `email` and `grpc-tls`
certs), so run `make -C labs/postgres-tls certs` before the first `up`; without it Docker turns the
missing bind-mount source into a directory, the failure mode `lab.sh`'s cert helpers exist to prevent.

**What QUIRK observes:** QUIRK has no PostgreSQL STARTTLS probe (its only sslyze STARTTLS use is the email
scanner), so it never sees this profile's cipher suites, protocol version or certificate. With
`connectors.enable_db: true`, `pg_targets: ["127.0.0.1:39432"]` and the lab credentials (`chaos` / `chaos`),
the DB connector records SSL posture only: one `POSTGRESQL` row, `PostgreSQL/ssl-enforced` (no severity) or
`PostgreSQL/plaintext-connections-allowed (N non-SSL)` (HIGH), depending on whether any non-SSL backend exists
when the scan runs. Treat the weak-TLS settings as a fixture for manual probing, for example
`openssl s_client -starttls postgres -connect localhost:39432`.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-postgres-tls`

---

### 3.28 redis-tls Profile (first released in 5.0.0 — Phase 89 LAB-02)

The `redis-tls` profile ships a standalone Redis 7.4.1 instance with a TLS listener forced to
weak 3DES/RSA ciphers (`DES-CBC3-SHA:AES128-SHA:AES256-SHA`, TLS 1.2 only) alongside a plaintext
listener — a dedicated broker-scanner target separate from the `broker` profile's combined
Kafka/RabbitMQ/Redis stack.

| Port  | Service    | Image             | Expected Finding                                     | Severity |
|-------|------------|-------------------|--------------------------------------------------------|----------|
| 39380 | redis-tls  | redis:7.4.1-alpine | Weak cipher suite on broker TLS endpoint (3DES+RSA-KX) | HIGH     |
| 39379 | redis-tls  | redis:7.4.1-alpine | Plaintext Redis listener (no auth)                     | HIGH     |

**Start:**

```bash
make -C labs/redis-tls certs
PROFILE_ARGS="--profile redis-tls" ./lab.sh up
```

`lab.sh` does not generate this profile's certificate; run `make -C labs/redis-tls certs` before the first `up`.

**Expected scanner findings:** `broker_scanner.py`'s Redis-TLS probe returns 1 HIGH weak-cipher
finding on port 39380 and 1 HIGH plaintext-listener finding on port 39379. These ports are not the Redis
defaults (6379/6380), so set `connectors.broker_targets` to `localhost:39380` and `localhost:39379` as in §3.19.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-redis-tls`

---

### 3.29 kafka-tls Profile (first released in 5.0.0 — Phase 89 LAB-04)

The `kafka-tls` profile ships a standalone Kafka broker (`apache/kafka:3.9.0`) with an SSL
listener forced to weak, non-PFS RSA key-exchange ciphers (`TLS_RSA_WITH_AES_128/256_CBC_SHA`,
TLS 1.2 only) and a self-signed RSA-2048 certificate, alongside a plaintext listener — a
dedicated broker-scanner target separate from the `broker` profile's combined stack.

| Port  | Service    | Image              | Expected Finding                                                | Severity |
|-------|------------|--------------------|---------------------------------------------------------------------|----------|
| 39092 | kafka-tls  | apache/kafka:3.9.0 | Plaintext Kafka listener detected                                | HIGH     |
| 39093 | kafka-tls  | apache/kafka:3.9.0 | Weak cipher suite on broker TLS endpoint (RSA-KX, no PFS)        | HIGH     |
| 39093 | kafka-tls  | apache/kafka:3.9.0 | `TLS certificate uses quantum-vulnerable RSA key` (RSA-2048, `CN=kafka-tls.chaos.local`) — oracle target, see below | MEDIUM |

**Start:**

```bash
make -C labs/kafka-tls certs
PROFILE_ARGS="--profile kafka-tls" ./lab.sh up
```

`lab.sh` does not generate this profile's certificate; run `make -C labs/kafka-tls certs` before the first `up`.

**Expected scanner findings:** `broker_scanner.py`'s Kafka probe returns 1 HIGH
plaintext-listener finding on port 39092 and 1 HIGH weak-cipher finding on port 39093. The oracle also expects 1 MEDIUM
RSA-2048-certificate finding on port 39093, but the broker probe does not emit it: the RSA-certificate rule applies only to
endpoints of protocol `TLS`, not `KAFKA-TLS`, so that finding would have to come from the generic TLS scan (`scan.ports_tls`), which this guide has not run against this port.
These ports are not the Kafka defaults (9092/9093), so set
`connectors.broker_targets` to `localhost:39092` and `localhost:39093` as in §3.19.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-kafka-tls`

---

### 3.30 oqs-nginx Profile (first released in 5.0.0 — Phase 90 PQC-01)

The `oqs-nginx` profile ships a digest-pinned `openquantumsafe/nginx` image serving TLS 1.3 with
an X25519MLKEM768 hybrid key-exchange and an ML-DSA-65 certificate — the chaos lab's agility
ceiling anchor, used for the D-04 before/after PQC-readiness demo. Binds `127.0.0.1:39444` only.

| Port  | Service    | Image                                   | Expected Finding                                                        | Severity |
|-------|------------|-------------------------------------------|-----------------------------------------------------------------------------|----------|
| 39444 | oqs-nginx  | openquantumsafe/nginx (sha256-pinned)     | Negotiated group `X25519MLKEM768` (NamedGroup 4588), recorded as a TLS endpoint with `cipher_suite=X25519MLKEM768` | Informational (agility signal) |
| 39444 | oqs-nginx  | openquantumsafe/nginx (sha256-pinned)     | ML-DSA-65 certificate: the server presents it, but no key or signature algorithm is recorded for it (the PQC probe reads only the negotiated group, and the TLS scanner cannot parse an ML-DSA key; see the note below) | none |

**Start:**

```bash
PROFILE_ARGS="--profile oqs-nginx" ./lab.sh up
```

> **Loopback bind note:** `oqs-nginx` publishes only `127.0.0.1:39444`, so scan it from the lab host.
> The TLS scanner and the PQC probe do not consult `security.allow_internal_targets`, so a scan of
> `127.0.0.1` does not need `--allow-internal-targets` (the compose file's comment says the same).
> Host OpenSSL >= 3.5 is required for the hybrid handshake, and 39444 is
> not in the default TLS port list, so add it to `scan.ports_tls`.

> **What the ordinary TLS scanner records here.** Adding 39444 to `scan.ports_tls` also runs the
> regular TLS scanner against it. When Python's `ssl` module is linked against an OpenSSL that
> supports ML-DSA (3.5 or later), the handshake completes and that TLS row keeps the certificate's
> subject and issuer. The `cryptography` library cannot parse the ML-DSA key, so the row has no key
> algorithm or size and carries a `TLS_ERROR: UnsupportedAlgorithm` scan error, which the CLI
> findings list reports as an INFO `Informational protocol observation`.

**Expected scanner findings:** the agility scoring path records this endpoint's hybrid
key-exchange (not its PQC signature, which the scanner cannot parse) as a quantum-readiness positive signal (each scoring domain is clamped
at 25.0; the oracle uses this endpoint as the agility ceiling anchor for the before/after demo).

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-oqs-nginx`

---

### 3.31 grpc-tls Profile (first released in 5.0.0 — Phase 89 LAB-05)

The `grpc-tls` profile ships a minimal Go gRPC server (`grpc-go`, ALPN `h2`) with a self-signed
RSA-2048 certificate and Go's default TLS 1.2+ configuration (modern ECDHE-RSA / forward-secret
cipher suites — no weak-cipher finding expected here, only the RSA-2048 certificate finding).
D-03 empirical gate confirmed sslyze negotiates the ALPN `h2` endpoint successfully via a direct
TLS probe.

| Port  | Service   | Image                                | Expected Finding                                                       | Severity |
|-------|-----------|----------------------------------------|----------------------------------------------------------------------------|----------|
| 39443 | grpc-tls  | build: labs/grpc-tls (golang:1.23-alpine) | `TLS certificate uses quantum-vulnerable RSA key` (RSA-2048, `CN=grpc-tls.chaos.local`) | MEDIUM |
| 39443 | grpc-tls  | build: labs/grpc-tls (golang:1.23-alpine) | TLS 1.2/1.3 ciphers — Go defaults (ECDHE-RSA, forward secrecy)          | Informational |

**Start:**

```bash
PROFILE_ARGS="--profile grpc-tls" ./lab.sh up
```

`labs/grpc-tls/certs/grpc-tls.{key,crt}` are auto-generated on first `up` — no manual
cert-generation step is required (same gitignored-certs shape as the `email` profile).

**Expected scanner findings:** sslyze's direct TLS probe on 39443 returns 1 MEDIUM RSA-2048
certificate finding; TLS 1.2/1.3 cipher enumeration is informational only (Go's defaults are
modern, forward-secret). Port 39443 is not in the default TLS port list, so add it to `scan.ports_tls`.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-grpc-tls`

---

### 3.32 multihost Profile (first released in 5.25.0 — 999.110)

The `multihost` profile is structurally unlike every other profile in this document: it is a whole
**simulated enterprise estate** rather than a single weakness fixture. It brings up **42 containers
on a dedicated `/24`** (`labnet`, `10.80.0.0/24`), all but the one-shot `mh-storage-seed` with a static
address and its own crypto posture, so the scanner sees a realistic topology instead of a pile of
services on `localhost`.

**No published host ports.** No service in the profile publishes a host port, so the subnet is
deliberately unreachable from a macOS Docker Desktop host. Scans run from **`mh-prober`** (`10.80.0.200`), a
container built from this repo — the same in-network vantage point the `segmented-network` profile
established in Phase 152. This is why the profile has no port table like the sections above: there
are no host ports to list, by design.

#### Prerequisite on aarch64 Linux: register amd64 emulation first

**One service in this profile cannot start on a plain aarch64 Linux host without emulation
registered.** `mh-saml-idp` uses `kenchan0130/simplesamlphp:1.19.7`, which upstream publishes for
**amd64 only**. The compose file declares `platform: linux/amd64` so the requirement is
explicit, but the declaration does not supply the emulation.

Register it before bringing the profile up:

```bash
docker run --privileged --rm tonistiigi/binfmt --install amd64

# Persistent across reboots (the command above is NOT):
sudo apt install -y qemu-user-binfmt
```

**This is not needed on Docker Desktop for Apple Silicon, which provides x86_64/amd64 emulation
itself**, which is why the requirement can go unnoticed there.

**How the failure presents if you skip this:** `chaoslab-mh-saml-idp-1` cannot start (Linux reports
`ENOEXEC`, "exec format error", for an executable built for the wrong architecture), and the scan logs
`SAML fetch failed for <url>`, then `SAML: no content fetched from <url>, skipping`, then
`SAML scan: 0 endpoints from 1 targets`. None of these log lines mentions the architecture mismatch (the
first carries only the fetch error), and SAML silently drops out of the Identity domain rather than failing
loudly.

To check an image's architectures yourself, read the image rather than the host — `uname -m`
inside a container on an emulating host reports the *emulated* architecture and will tell you
everything is fine:

```bash
docker inspect kenchan0130/simplesamlphp:1.19.7 --format '{{.Architecture}}'
```

`mh-storage-archive` and `mh-storage-seed` run the same `motoserver/moto:5.2.3` image as the `storage-s3` profile (§3.17), on `10.80.0.50:9000`. See that section's "Image source" note. With no MinIO console on :9001, `.50` carries one plaintext-HTTP HIGH (on :9000) instead of two. That was observed in a scoped scan on 2026-10-01 (`expected_results_v4.md`, `.50` note).

| Host | Service | Posture under test | Finding domain |
|------|---------|--------------------|----------------|
| 10.80.0.10 | mh-edge-legacy | TLS 1.0/1.1 + weak ciphers | data in motion |
| 10.80.0.11 | mh-edge-expired | expired certificate | certificate lifecycle |
| 10.80.0.12–.14 | mh-edge-rsa1024 / -sha1 / -chainbroken | RSA-1024, SHA-1, broken chain | certificate quality |
| 10.80.0.15–.19, .21–.22 | mh-legacy-intranet, mh-intranet-* | plaintext HTTP only | hygiene |
| 10.80.0.20 | mh-app-crownjewel | modern TLS — the healthiest host | in motion (contrast case) |
| 10.80.0.30 | mh-db-finance | PostgreSQL 16.6, no TLS | data at rest (database) |
| 10.80.0.31 | mh-cache-session | Redis 7.4.1, no TLS/auth | in motion (broker/cache) |
| 10.80.0.40 | mh-identity-dc | OpenLDAP, 389 cleartext + 636 | identity |
| 10.80.0.41 | mh-saml-idp | simplesamlphp IdP metadata | identity (federation) |
| 10.80.0.50 | mh-storage-archive | S3 (moto): 1 SSE-S3 + 1 UNENCRYPTED bucket | data at rest (object) |
| 10.80.0.60 | mh-pki-ca | step-ca 0.28.1 | PKI / CA |
| 10.80.0.70 | mh-ssh-jump | OpenSSH jump host | in motion (SSH) |
| 10.80.0.101–.104 | mh-vpn-gateway, mh-mail-relay, mh-vendor-portal, mh-backup-console | expired certificates | certificate lifecycle |
| 10.80.0.105–.107 | mh-devtest-api, mh-staging-web, mh-iot-controller | self-signed certificates | certificate provenance |
| 10.80.0.108–.110 | mh-erp-frontend, mh-hr-portal, mh-payroll | legacy TLS | data in motion |
| 10.80.0.111 | mh-db-hr | MySQL 8.0.40, plaintext | data at rest (database) |
| 10.80.0.42 | mh-kdc | Samba AD DC, realm `QUIRK.LAB` | identity (Kerberos) |
| 10.80.0.61–.62 | mh-vault, mh-vault-seed | Vault 1.17 dev: transit keys, PKI root, auth mounts | data at rest (secrets) |
| 10.80.0.90–.93 | mh-jwt-rs256 / -hs256 / -rsa1024 / -algnone | JWKS: RS256, HS256, RSA-1024, alg=none | API / token signing |
| 10.80.0.120 | mh-postfix | SMTP 25 / SMTPS 465 / submission 587 | in motion (email) |
| 10.80.0.121 | mh-dovecot | IMAP 143 / IMAPS 993 / POP3 110 / POP3S 995, TLS 1.2 cap | in motion (email) |

**Connector coverage (added 2026-09-17).** Nine hosts were added so the profile
exercises the Identity, Data at Rest, Motion and Findings *connectors*, not just TLS and SSH.
Each is a dedicated `mh-*` instance with **no published ports**, mirroring how `mh-db-finance`
is a dedicated Postgres instance on `labnet` rather than the `database` profile's Postgres dual-homed onto it. `multihost-scan-config.yaml`
aims one connector at each:

| Connector | Target in the scan config |
|---|---|
| `enable_vault` | `mh-vault` (10.80.0.61): exportable transit key MEDIUM, PKI root HIGH, token auth HIGH, userpass MEDIUM; needs `quirk-scanner[cloud]` for `hvac` |
| `enable_jwt` | four base URLs, `10.80.0.90`-`.93` on port 8000, one JWKS per algorithm defect |
| `enable_email` | `mh-postfix` and `mh-dovecot`, each probed on the scanner's fixed 7 mail ports (14 endpoints) |
| `enable_db` (MySQL) | `mh-db-hr` through `mysql_targets`: `MySQL/ssl-off`, HIGH |
| `enable_kerberos` | `mh-kdc` (10.80.0.42), realm `QUIRK.LAB` |

Three caveats worth knowing before relying on these:

- **Kerberos needs `quirk-scanner[identity]`**, which `[all]` deliberately excludes. `mh-prober`
  installs `.[all]`, so the prober **cannot** scan `10.80.0.42` without an extra install. The
  connector probes the KDC over TCP first and falls back to UDP only if the TCP probe raises
  (`scan_kerberos_targets`). The compose file records an observation from 2026-09-17 that the UDP
  AS-REQ probe timed out against this container and fell back to TCP, which is the reverse of that
  source order and which this guide has not reproduced, so do not rely on UDP-path enctype enumeration here.
  A UDP timeout no longer reads as `kerberos-no-preauth`: it gives `kerberos-unreachable`, and
  `kerberos-no-preauth` appears only for an AS-REP that answers the probe. `mh-kdc` itself was not
  re-measured; the same Samba image was, through the `kerberos` profile, on 2026-10-23.
- **Email and broker need `sslyze`.** It became a core dependency on 2026-09-17 (commit `15e49e96`);
  prober images built before that lack it, and `run_scan.py` skips the email phase entirely when it
  is missing.
- **Postfix's ports do not negotiate under the stdlib fallback** — it offers RSA-only ciphers that
  `ssl.create_default_context()` excludes. With `sslyze` installed they enumerate normally. This
  is the same behaviour `labs/email/expected_results.md` records for the single-host profile.


**Start and scan:**

```bash
# --build rebuilds the locally-built services: mh-prober, mh-postfix, mh-dovecot,
# mh-kdc and the four mh-jwt-* services. Every other service here is a pinned public image.
PROFILE_ARGS="--profile multihost" ./lab.sh up --build

# Without --build, `up` reuses an existing prober image no matter how far
# quirk/ has moved. `lab.sh` now warns when that image predates the newest
# commit touching quirk/, but the warning depends on docker, git and python3
# all being present — treat --build as the reliable path, not the warning.
# To rebuild the prober alone instead (note `-p chaoslab`, see below):
docker compose -p chaoslab --profile multihost build mh-prober
docker compose -p chaoslab --profile multihost up -d --force-recreate mh-prober

docker exec chaoslab-mh-prober-1 \
  quirk --config /scan-config.yaml --allow-internal-targets --allow-cleartext-broker-probe
# reports land in ./quirk-output (bind-mounted to /out); then, on the host:
quirk serve --port 8512 --no-open
```

**`quirk serve` has no `--db-path` flag** — its only options are `--port`, `--host`, `--no-open`
and `--insecure`; it discovers the canonical `./quirk-output/quirk.db` itself. This section printed
`quirk serve --db-path quirk-output/quirk.db` until 2026-09-14; that command exits 2 with
`unrecognized arguments`.

**The `-p chaoslab` on the rebuild commands is required.** Without it, compose derives the project
name from the directory and tags a different image (`quantum-chaos-enterprise-lab-mh-prober`) that
the running `chaoslab-mh-prober-1` container never picks up — the rebuild appears to succeed and
changes nothing.

`--config` is **required** — `quirk` has no `scan` subcommand and no `--targets` flag, and without
`--config` it drops into the interactive wizard.

**`--allow-internal-targets` is not required with this config.** `10.80.0.0/24` is RFC1918 space,
which the scanner refuses by default (`security.allow_internal_targets` defaults to false), but
`multihost-scan-config.yaml:290` already sets `allow_internal_targets: true`, so the flag is redundant
here. Passing it anyway is harmless.

The flag *is* required when you point `quirk` at RFC1918 space using a config that does **not** set
`allow_internal_targets` — which is why it appears elsewhere in this document.

`--allow-cleartext-broker-probe` is optional; it permits broker management API probes over HTTP
(no TLS).

**Why the scan config targets explicit `/32`s (39 of them) and not `10.80.0.0/24`.** The oracle
records that a full subnet sweep reported **257 hosts and 2572 findings** — 254 phantom addresses at
10 INFO each, plus the Docker bridge gateway at `.1` surfacing a spurious CRITICAL. That buries the
real topology and makes the Exposure Map unreadable. `ports_tls` is likewise retargeted to
`[443,80,389,636,2222,3306,5432,6379,8080,9000,9001,465,993,995]`; the repo-root `config.yaml`'s
list is tuned for the single-host lab's published ports and contains none of
389/636/3306/5432/6379/9000.

`enable_dnssec` is explicitly **false**: this subnet has no DNSSEC resolver, and a connector aimed at
a host that cannot answer yields silence or a misleading finding. `enable_kerberos` is **true** since
2026-09-17, when `mh-kdc` was added.

**Expected scanner findings:** see the oracle. As of 2026-09-14 its per-host table carries 31 targets
(the scan config now lists more), every row derived from a measured run
(`findings-20260914-142606.json`) rather than inferred from the compose file.

**Aggregate recorded in the oracle (2026-09-14 run, scoring v3, 31 targets):** 400 findings — 5 CRITICAL / 14 HIGH /
33 MEDIUM / 16 LOW / 332 INFO across 37 hosts (31 subnet targets + 6 connector pseudo-hosts); 370 endpoints,
38 assessable; readiness **15/100 POOR** (`computed 61, limited to 15 by 5 open CRITICAL findings`). This guide
has not re-run the scan.

**Scoring v3 changed this profile's headline number by 76 points.** The same estate scored 91/100
under the superseded v2 model. If a scan here reports ~91, the prober image is stale — rebuild it
per the commands above and re-check
`docker exec chaoslab-mh-prober-1 python -c "from quirk.intelligence.scoring import SCORING_VERSION; print(SCORING_VERSION)"`.

Since 5.25.0 you no longer have to recognise the number to catch this: the scan summary prints a
**Scoring model** row (read live from `SCORING_VERSION`) and a **Scanner build** row next to
`Platform version`. Check those first — `Platform version` alone cannot distinguish a stale
scanner from a current one, because it names the last released version rather than the code
running, and read `5.21.0` in both the stale and the current case. See
`docs/report-interpretation.md` §27.

**The oracle records three classes of honest gap** — hosts that return INFO only; postures that are
*scored but not in the CLI findings* (the unencrypted S3 bucket and the plaintext Postgres both reach
`evidence_summary` but have no entry in `findings-*.json`; the dashboard's Data at Rest page does list
both); and postures with no distinguishing detection (SHA-1 and
broken-chain hosts are indistinguishable from a generic host). It also records a **CLI-vs-dashboard
score divergence** measured on the same run. Read those sections before quoting any number from this
profile in front of a client.

See: `quantum-chaos-enterprise-lab/expected_results_v4.md#profile-multihost`

---

## 4. Starting Multiple Profiles

Profiles can be combined freely: no two compose services publish the same host port, so there are no port collisions inside the lab. The always-on `tls-modern` (443) and the `kerberos` (88, 389), `ldaps` (636), `otics` (502) and `hwcompat` (161/udp) profiles publish standard ports that can collide with services already running on your host.

```bash
# Start all Phase 4 profiles together
PROFILE_ARGS="--profile jwt --profile registry --profile source --profile ssh-weak --profile ldaps" ./lab.sh up
```

**Port conflict note:** the cloud profile's LocalStack (`SERVICES=s3,sts,iam`) is published only through its TLS terminator on port **24566**. `./lab.sh all` starts every profile except `kerberos` on macOS, because macOS ships its own KDC on port 88 (set `LAB_INCLUDE_KERBEROS=1` to include it).

To list every profile defined in the compose file (live read — never out of date):

```bash
./lab.sh profiles
```

---

## 4.5 Which addresses do I scan?

The lab uses **two different addressing models**, and the one you get depends on the profile.
Knowing which you are in is the difference between a working scan and an empty one.

### `0.0.0.0:9443->443/tcp` is not an address

`docker ps` shows port mappings in Docker's *publishing* notation:

```
0.0.0.0    :9443     ->    443/tcp
   ↑          ↑              ↑
 bind on   HOST port     container's
  all       ← scan        internal
interfaces   THIS           port
```

`0.0.0.0` means "bound on every host interface". **You scan `127.0.0.1` on the host port** — the
number to the *left* of the arrow. The right-hand number is internal to the container and is not
reachable from outside it.

### Model A — most profiles: one address, many ports

```
chaoslab-tls-modern-1       0.0.0.0:443->443/tcp     ->  127.0.0.1:443
chaoslab-tls-legacy-1       0.0.0.0:8443->443/tcp    ->  127.0.0.1:8443
chaoslab-tls-expired-1      0.0.0.0:9443->443/tcp    ->  127.0.0.1:9443
chaoslab-tls-selfsigned-1   0.0.0.0:10443->443/tcp   ->  127.0.0.1:10443
```

Every service is a different **port on the same address**, which is why
`scan-configs/config-lab-core.yaml` reads `cidrs: [127.0.0.1]` and carries a long explicit port
list. In Model A the ports *are* the topology. Section 5 below is the full map.

### Model B — the `multihost` profile: many addresses, standard ports

Look at the port column for these containers and note what is missing:

```
chaoslab-mh-devtest-api-1     80/tcp, 443/tcp      <- NO leading 0.0.0.0:
chaoslab-mh-edge-chainbroken-1  80/tcp, 443/tcp
```

Exposed, but **not published**. They are unreachable from the host. Instead each gets a real
address on a private bridge network:

```
10.80.0.10   mh-edge-legacy
10.80.0.101  mh-vpn-gateway
10.80.0.102  mh-mail-relay
...
10.80.0.200  mh-prober        <- the scan runs from HERE
```

This is why `mh-prober` exists. The lab's compose file records that macOS Docker Desktop cannot
route host traffic into a custom bridge network, so the scan must originate *inside* it — hence
`docker exec chaoslab-mh-prober-1 quirk --config /scan-config.yaml` rather than running `quirk` on
the host. On Linux the bridge may be reachable from the host directly, but the prober is the
path this guide documents and the one the multihost scan config assumes.

### Do not scan `10.80.0.0/24`

`multihost-scan-config.yaml` targets **explicit `/32`s, not the subnet**, and the oracle records
why: a full subnet sweep reported **257 hosts and 2,572 findings** — 254 phantom
addresses with 10 INFO findings each, plus the Docker bridge gateway at `.1` reported as a
CRITICAL. That noise buries the real topology.

Use the shipped config for whichever profile you are running:

| Running | Config | Scans |
|---------|--------|-------|
| core / jwt / registry / source / … | `scan-configs/config-lab-*.yaml` | `127.0.0.1` plus host ports |
| `multihost` | `multihost-scan-config.yaml`, **from inside the prober** | 39 explicit `10.80.0.x/32`s |

To see any running profile's map yourself:

```bash
docker ps --format '{{.Names}}\t{{.Ports}}'
```

---

## 5. Complete Port Reference

Every host port a compose service publishes (80 port/protocol pairs across all profiles), sorted by port number. A port appears here only if `docker-compose.yml` publishes it:

| Port      | Service                    | Profile          | Expected Finding                                                                              |
|-----------|----------------------------|------------------|-----------------------------------------------------------------------------------------------|
| 88        | samba-dc                   | kerberos         | weak etype: rc4-hmac HIGH; weak etype: aes128-cts-hmac-sha1-96 HIGH                           |
| 161/udp   | hwcompat-snmp              | hwcompat         | vendor=Cisco fingerprint_method=snmp (the port the scanner probes; same service as 20223/udp) |
| 389       | samba-dc                   | kerberos         | no LDAP-exposure finding (no scanner code emits one); not in the default TLS port list (see §3.14) |
| 443       | tls-modern                 | core             | MODERN_TLS                                                                                    |
| 502       | otics-modbus               | otics            | modbus_vendor=Schneider Electric, modbus_model=M221                                           |
| 636       | ldaps                      | ldaps            | CERT_SELFSIGNED                                                                               |
| 2222      | ssh-alt                    | core             | SSH_BANNER                                                                                    |
| 5555      | unknown-port               | core             | UNKNOWN_OPEN_PORT                                                                             |
| 5556      | unknown-port-2             | phaseA           | UNKNOWN_OPEN_PORT_2                                                                           |
| 8000      | legacy-http                | core             | PLAINTEXT_HTTP                                                                                |
| 8080      | simplesamlphp              | saml             | RSA-1024 signing cert CRITICAL                                                                |
| 8443      | tls-legacy                 | core             | LEGACY_TLS                                                                                    |
| 8444      | http-on-8444               | core             | HTTP_ON_TLS_LIKE_PORT                                                                         |
| 9443      | tls-expired                | core             | CERT_EXPIRED_OR_EXPIRING                                                                      |
| 10443     | tls-selfsigned             | core             | CERT_SELFSIGNED                                                                               |
| 11443     | tls-mtls-required          | core             | MTLS_REQUIRED                                                                                 |
| 12443     | tls-slow-proxy             | core             | TLS_SLOW_PROXY                                                                                |
| 13443     | tls-missing-intermediate   | phaseA           | CERT_CHAIN_INCOMPLETE                                                                         |
| 13444     | tls-cert-expired           | tls-cert-defects | TLS certificate expired CRITICAL                                                              |
| 13445     | tls-cert-selfsigned        | tls-cert-defects | TLS certificate is self-signed HIGH                                                           |
| 13446     | tls-cert-untrusted-ca      | tls-cert-defects | TLS certificate issued by untrusted CA MEDIUM                                                 |
| 13447     | tls-cert-rsa1024           | tls-cert-defects | TLS certificate uses undersized RSA key HIGH                                                  |
| 13890     | openldap                   | identity         | LDAP_TCP                                                                                      |
| 14443     | tls-rsa1024                | phaseA           | CERT_RSA_1024                                                                                 |
| 15001     | tls-altport                | phaseA           | TLS_ON_ODD_PORT                                                                               |
| 15353/tcp | bind9-dnssec               | dnssec           | none of its own: TCP only retries a truncated UDP reply (see §3.12)                           |
| 15353/udp | bind9-dnssec               | dnssec           | RSASHA1 weak-algo CRITICAL, unsigned zone HIGH, NSEC MEDIUM (needs `dnssec_resolver`)         |
| 15432     | postgres-plain             | phaseA           | DB_PLAINTEXT_POSTGRES                                                                         |
| 15443     | tls-sha1                   | phaseA           | CERT_SHA1_SIG                                                                                 |
| 15449     | keycloak-tls               | identity         | IDP_TLS                                                                                       |
| 15672     | rabbitmq-mgmt              | phaseA           | RABBITMQ_MGMT_HTTP                                                                            |
| 16379     | redis-plain                | phaseA           | DB_PLAINTEXT_REDIS                                                                            |
| 16443     | mtls-gateway               | identity         | MTLS_REQUIRED                                                                                 |
| 17443     | mtls-stepca-gateway        | pki              | MTLS_STEPCA                                                                                   |
| 18000     | http-redirect              | phaseA           | HTTP_REDIRECT_302                                                                             |
| 18082     | phpldapadmin               | identity         | LDAP_ADMIN_HTTP                                                                               |
| 19000     | step-ca                    | identity         | PRIVATE_CA_TLS                                                                                |
| 20001     | jwt-rs256                  | jwt              | JWT quantum-vulnerable asymmetric                                                             |
| 20002     | jwt-hs256                  | jwt              | JWT WEAK_KEY_SIZE                                                                             |
| 20003     | jwt-rsa1024                | jwt              | JWT WEAK_KEY_SIZE + quantum-vulnerable                                                        |
| 20004     | jwt-algnone                | jwt              | JWT CRITICAL_NO_SIGNATURE                                                                     |
| 20005     | registry                   | registry         | OUTDATED_CRYPTO_LIB                                                                           |
| 20006     | gitea                      | source           | semgrep p/cryptography findings (weak algorithms, weak random, hardcoded keys)                |
| 20022     | ssh-weak                   | ssh-weak         | SSH_WEAK_ALGORITHMS                                                                           |
| 20100     | fuzz-target                | fuzz-target      | hsts_missing HIGH / alg_confusion CRITICAL                                                    |
| 20221     | hwcompat-ssh               | hwcompat         | vendor=Unknown (SSH banner)                                                                   |
| 20222     | hwcompat-http              | hwcompat         | vendor=HPE model=iLO5 (HTTP mgmt), only on a probed port (see §3.22)                          |
| 20223/udp | hwcompat-snmp              | hwcompat         | vendor=Cisco fingerprint_method=snmp confidence=medium                                        |
| 21000     | azurite-blob-tls           | cloud            | CLOUD_AZURITE_BLOB_TLS                                                                        |
| 21001     | azurite-queue-tls          | cloud            | CLOUD_AZURITE_QUEUE_TLS                                                                       |
| 21002     | azurite-table-tls          | cloud            | CLOUD_AZURITE_TABLE_TLS                                                                       |
| 23306     | mysql-ssl-off              | database         | MySQL/ssl-off HIGH                                                                            |
| 24443     | ingress-sni                | phaseA           | INGRESS_SNI                                                                                   |
| 24566     | localstack-tls             | cloud            | CLOUD_AWS_LOCALSTACK_TLS                                                                      |
| 25432     | postgres-ssl-off           | database         | PostgreSQL/ssl-off HIGH                                                                       |
| 25671     | rabbitmq-broker (AMQPS)    | broker           | Weak cipher suite on broker TLS endpoint                                                      |
| 25672     | rabbitmq-broker (AMQP)     | broker           | Plaintext AMQP listener detected                                                              |
| 26379     | redis-broker (plain)       | broker           | Plaintext Redis listener (no auth)                                                            |
| 26380     | redis-broker (TLS)         | broker           | Weak cipher suite on broker TLS endpoint                                                      |
| 28200     | vault-30                   | vault            | PKI/auth/transit DAR audit                                                                    |
| 29000     | minio (moto)               | storage-s3       | S3/unencrypted HIGH (unencrypted-bucket)                                                      |
| 29092     | kafka-broker (plain)       | broker           | Plaintext Kafka listener detected                                                             |
| 29093     | kafka-broker (TLS)         | broker           | Weak cipher suite on broker TLS endpoint                                                      |
| 30025     | postfix-email (SMTP)       | email            | STARTTLS-downgrade MEDIUM + weak-cipher HIGH                                                  |
| 30110     | dovecot-email (POP3)       | email            | POP3-STARTTLS (TLS 1.3 — no weak-cipher)                                                      |
| 30143     | dovecot-email (IMAP)       | email            | IMAP-STARTTLS (TLS 1.3 — no weak-cipher)                                                      |
| 30465     | postfix-email (SMTPS)      | email            | Weak cipher suite on email TLS endpoint                                                       |
| 30587     | postfix-email (submission) | email            | Weak cipher suite on email TLS endpoint                                                       |
| 30993     | dovecot-email (IMAPS)      | email            | IMAPS (TLS 1.3 — no weak-cipher)                                                              |
| 30995     | dovecot-email (POP3S)      | email            | POP3S (TLS 1.3 — no weak-cipher)                                                              |
| 38900     | smime-openldap             | smime            | S/MIME weak cert (alice, bob) HIGH                                                            |
| 38910     | adcs-openldap              | adcs             | ADCS weak CA signing / ESC1 HIGH                                                              |
| 39092     | kafka-tls (PLAINTEXT)      | kafka-tls        | Plaintext Kafka listener detected HIGH                                                        |
| 39093     | kafka-tls (SSL)            | kafka-tls        | Weak cipher suite on broker TLS endpoint HIGH                                                 |
| 39379     | redis-tls (plaintext)      | redis-tls        | Plaintext Redis listener (no auth) HIGH                                                       |
| 39380     | redis-tls (TLS)            | redis-tls        | Weak cipher suite on broker TLS endpoint HIGH                                                 |
| 39432     | postgres-tls               | postgres-tls     | oracle target only: weak cipher suite on database TLS endpoint (no current scanner path)      |
| 39443     | grpc-tls                   | grpc-tls         | TLS certificate uses quantum-vulnerable RSA key MEDIUM                                        |
| 39444     | oqs-nginx                  | oqs-nginx        | X25519MLKEM768 hybrid group (agility signal); no key algorithm is recorded for the ML-DSA-65 cert (see §3.30) |
| 47808/udp | otics-bacnet               | otics            | bacnet_vendor=5 (Johnson Controls), bacnet_model=FX16                                         |

---

## 6. Troubleshooting

**Services not starting:**

```bash
./lab.sh logs [service-name]   # Check service logs
./lab.sh status               # Check container status
```

**Port conflicts:**
If ports conflict with local services, check `docker-compose.yml` host port mappings (§5 lists every published port). Most lab ports are in non-standard ranges (66 of the 80 published port/protocol pairs are 10000 or higher), but the always-on `tls-modern` (443) and the `ldaps` (636), `kerberos` (88, 389), `otics` (502, 47808/udp) and `hwcompat` (161/udp) profiles publish standard ports and are the likeliest to collide.

**registry-seed failures:**
The seed container needs Docker socket access. Confirm `/var/run/docker.sock` is mounted and your user has Docker group membership. Seed timing: allow 30–60 seconds before scanning.

**Gitea seed timing:**
The source profile `gitea-seed` waits for Gitea to be healthy before seeding. Allow 30–60 seconds on first start. If repos are empty:

```bash
./lab.sh logs gitea-seed
```

**Vault not reachable:**
The `vault` profile's Vault runs on port **28200**. Confirm with `curl http://localhost:28200/v1/sys/health`.

**pki profile failing to start:**
The `pki` gateway proxies to the `whoami` service, which only the identity and phaseA profiles define. Start identity alongside pki:

```bash
PROFILE_ARGS="--profile identity --profile pki" ./lab.sh up
```

---

## 7. Historical Reference

The existing `quantum-chaos-enterprise-lab/CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` in the lab directory is retained as a historical artifact documenting the original lab build decisions (pre-Phase 4). This guide (`docs/chaos-lab.md`) is the authoritative operator reference going forward.
