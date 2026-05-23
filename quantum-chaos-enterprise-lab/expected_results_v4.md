# Expected Scanner Results — v4 Oracle

**Scope:** Every Docker Compose profile shipped through QU.I.R.K. v4.4 (v4.0 baseline + v4.1/4.2 expansions + v4.3 DAR + v4.4 messaging).
**Status:** Authoritative. Supersedes `expected_results_v3.md`.
**Schema:** Per-profile H2 sections (`## Profile: <name>`). Network-listener profiles use `Port | Service | Expected protocol | Expected condition / tag | Notes`. DAR / config-introspection profiles use category-tuned schemas (see plan 40-03 for database / storage-s3 / vault / storage / email / broker).

Use the matching `## Profile: <name>` anchor as the cross-reference target from `README.md` (D-11).

Host assumed: `127.0.0.1`

---

## Profile: core

*The "core" baseline — always-on TLS / HTTP / SSH chaos matrix; present in every `./lab.sh up` regardless of profile selection.*

These services have **no profile tag** in `docker-compose.yml` — Compose brings them up automatically with every `up` invocation regardless of `--profile` flags. No `PROFILE_ARGS` needed; start with:

```bash
./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 443 | tls-modern | TLS | MODERN_TLS | TLS 1.3 typically negotiates |
| 8443 | tls-legacy | TLS | LEGACY_TLS | May negotiate TLS 1.2 on modern OpenSSL |
| 9443 | tls-expired | TLS | CERT_EXPIRED_OR_EXPIRING | Cert validity failure/near-expiry datapoint |
| 10443 | tls-selfsigned | TLS | CERT_SELFSIGNED | Untrusted/self-signed datapoint |
| 11443 | tls-mtls-required | TLS | MTLS_REQUIRED | Handshake blocked without client cert |
| 12443 | tls-slow-proxy | TLS | TLS_SLOW_PROXY | Useful for timeout/concurrency testing |
| 8444 | http-on-8444 | HTTP | HTTP_ON_TLS_LIKE_PORT | Wrong protocol on "TLS-like" port |
| 8000 | legacy-http | HTTP | PLAINTEXT_HTTP | Hygiene datapoint |
| 2222 | ssh-alt | SSH | SSH_BANNER | Non-standard SSH port |
| 5555 | unknown-port | UNKNOWN | UNKNOWN_OPEN_PORT | Open port with ambiguous protocol |

---

## Profile: phaseA

*Service-inventory expansion + TLS chain scenarios + SNI ingress.*

```bash
PROFILE_ARGS="--profile phaseA" ./lab.sh up
```

### Phase A1 — Service Inventory Expansion

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 15001 | tls-altport | TLS | TLS_ON_ODD_PORT | TLS listener on non-standard port |
| 18000 | http-redirect | HTTP | HTTP_REDIRECT_302 | Should return 302 Location header |
| 5556 | unknown-port-2 | UNKNOWN | UNKNOWN_OPEN_PORT_2 | Second unknown service |
| 15432 | postgres-plain | UNKNOWN (non-HTTP) | DB_PLAINTEXT_POSTGRES | TCP service, not HTTP/TLS by default |
| 16379 | redis-plain | UNKNOWN (non-HTTP) | DB_PLAINTEXT_REDIS | TCP service, not HTTP/TLS by default |
| 15672 | rabbitmq-mgmt | HTTP | RABBITMQ_MGMT_HTTP | HTTP UI (proxy target for ingress) |

**Notes**
- For DB services (Postgres/Redis) the classifier may label as `UNKNOWN` unless you implement protocol-specific probing. That's fine — it's a datapoint for "non-HTTP services in inventory."

### Phase A2 — TLS Chain Scenarios

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 13443 | tls-missing-intermediate | TLS | CERT_CHAIN_INCOMPLETE | Leaf presented without required intermediate |
| 14443 | tls-rsa1024 | TLS | CERT_RSA_1024 | Weak RSA key size |
| 15443 | tls-sha1 | TLS | CERT_SHA1_SIG | SHA1-signed cert (legacy) |

**Notes**
- Some clients may treat SHA1 as unacceptable; this is intended for detection.

### Phase A3 — Ingress / SNI (multi-vhost behind single TLS port)

Ingress listener:
- `24443` → TLS terminator with **SNI routing** (multiple hostnames on one port)

| Port | Hostname (SNI) | Expected protocol | Backend | Expected tag |
|---:|---|---|---|---|
| 24443 | app1.chaos.local | TLS | whoami | INGRESS_SNI_APP1 |
| 24443 | app2.chaos.local | TLS | whoami | INGRESS_SNI_APP2 |
| 24443 | legacy.chaos.local | TLS | legacy-http (8000) | INGRESS_SNI_LEGACY |
| 24443 | rabbitmq.chaos.local | TLS | rabbitmq-mgmt (15672) | INGRESS_SNI_RABBITMQ |

**Validation commands**
- `curl -k --resolve app1.chaos.local:24443:127.0.0.1 https://app1.chaos.local:24443/`
- `curl -k --resolve app2.chaos.local:24443:127.0.0.1 https://app2.chaos.local:24443/`
- `curl -k --resolve legacy.chaos.local:24443:127.0.0.1 https://legacy.chaos.local:24443/ | head`
- `curl -k --resolve rabbitmq.chaos.local:24443:127.0.0.1 https://rabbitmq.chaos.local:24443/ | head`

---

## Profile: cloud

*LocalStack S3/STS/IAM + Azurite (Blob/Queue/Table) behind TLS terminators on 21000-21002 and 24566.*

```bash
PROFILE_ARGS="--profile cloud" ./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 24566 | localstack-tls | TLS | CLOUD_AWS_LOCALSTACK_TLS | LocalStack gateway behind TLS; SNI hostname: aws.chaos.local |
| 21000 | azurite-blob-tls | TLS | CLOUD_AZURITE_BLOB_TLS | Azurite Blob behind TLS; SNI hostname: blob.chaos.local |
| 21001 | azurite-queue-tls | TLS | CLOUD_AZURITE_QUEUE_TLS | Azurite Queue behind TLS; SNI hostname: queue.chaos.local |
| 21002 | azurite-table-tls | TLS | CLOUD_AZURITE_TABLE_TLS | Azurite Table behind TLS; SNI hostname: table.chaos.local |

**Validation commands**
- `curl -k --resolve aws.chaos.local:24566:127.0.0.1 https://aws.chaos.local:24566/__tls_ok`
- `curl -k --resolve aws.chaos.local:24566:127.0.0.1 https://aws.chaos.local:24566/_localstack/health`
- `curl -k --resolve blob.chaos.local:21000:127.0.0.1 https://blob.chaos.local:21000/__tls_ok`
- `curl -k --resolve queue.chaos.local:21001:127.0.0.1 https://queue.chaos.local:21001/__tls_ok`
- `curl -k --resolve table.chaos.local:21002:127.0.0.1 https://table.chaos.local:21002/__tls_ok`

---

## Profile: identity

*Keycloak IdP + step-ca + OpenLDAP + mTLS gateway.*

```bash
PROFILE_ARGS="--profile identity" ./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 15449 | keycloak-tls | TLS | IDP_TLS | Keycloak behind TLS proxy |
| 19000 | step-ca | TLS | PRIVATE_CA_TLS | CA health endpoint should be reachable |
| 13890 | openldap | UNKNOWN (non-HTTP) | LDAP_TCP | LDAP service (plaintext unless LDAPS added) |
| 18082 | phpldapadmin | HTTP | LDAP_ADMIN_HTTP | HTTP UI |
| 16443 | mtls-gateway | TLS | MTLS_REQUIRED | Should fail without client cert; succeeds with issued cert later |

**Notes**
- LDAP will likely show as `UNKNOWN` unless you add LDAP probing later (fine for now).
- mTLS gateway should be treated as TLS-associated even if handshake is blocked.

---

## Profile: pki

*step-ca-issued mTLS gateway. Requires `identity` profile to be up first (shared services).*

```bash
PROFILE_ARGS="--profile identity --profile pki" ./lab.sh up
```

> **Dependency:** The `pki` profile's `mtls-stepca-gateway` service depends on `whoami` and `step-ca` from the `identity` profile. Always bring up `identity` alongside `pki`.

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 17443 | mtls-stepca-gateway | TLS 1.2/1.3 | MTLS_STEPCA | step-ca-issued mTLS gateway; depends on identity profile services (whoami, step-ca). |

---

## Profile: jwt

*4 JWT microservices with weak alg configs (LAB-01 / SCAN-03).*

```bash
PROFILE_ARGS="--profile jwt" ./lab.sh up
```

| Port | Service | Algorithm | Expected Finding | Key Size | Notes |
|-----:|---------|-----------|-----------------|----------|-------|
| 20001 | jwt-rs256 | RS256 (RSA) | WEAK_QUANTUM (quantum-vulnerable asymmetric) | 2048-bit | RS256 is classically safe but quantum-vulnerable; scanner should return RSA finding |
| 20002 | jwt-hs256 | HS256 (HMAC-SHA256) | WEAK_KEY_SIZE | 128-bit | 16-byte HMAC key — below minimum 256-bit; scanner flags short symmetric key |
| 20003 | jwt-rsa1024 | RS256 (RSA) | WEAK_KEY_SIZE + WEAK_QUANTUM | 1024-bit | RSA-1024 is classically weak and quantum-vulnerable; scanner flags key size |
| 20004 | jwt-algnone | none | CRITICAL_NO_SIGNATURE | 0 | alg:none = no signature verification; scanner classifies as UNKNOWN/critical |

**Scanner validation command:**
```
quirk scan --targets http://localhost:20001 http://localhost:20002 http://localhost:20003 http://localhost:20004
```
**Expected:** JWT scanner returns >= 2 weak-algorithm findings (HS256-weak + RSA-1024 + alg:none = 3 findings).

---

## Profile: registry

*Docker Registry v2 + 3 seeded images with old crypto libs.*

```bash
PROFILE_ARGS="--profile registry" ./lab.sh up
```

| Image | Package | Version | Expected Finding | Notes |
|-------|---------|---------|-----------------|-------|
| image-old-libssl | openssl | 1.0.2n (ubuntu:18.04) | OUTDATED_CRYPTO_LIB | Syft detects openssl in allowlist |
| image-old-libssl | libssl1.0.0 | 1.0.2n | OUTDATED_CRYPTO_LIB | Additional libssl package |
| image-old-pycrypto | cryptography | 2.9.2 | OUTDATED_CRYPTO_LIB | Syft detects Python cryptography package |
| image-old-pycrypto | pyopenssl | 19.1.0 | OUTDATED_CRYPTO_LIB | Syft detects pyOpenSSL package |
| image-mixed | openssl | 1.0.2n | OUTDATED_CRYPTO_LIB | Combined old libssl + old pycrypto |
| image-mixed | cryptography | 2.9.2 | OUTDATED_CRYPTO_LIB | Combined finding |

**Scanner validation command:**
```
quirk scan --container localhost:20005/image-old-pycrypto localhost:20005/image-old-libssl localhost:20005/image-mixed
```
**Expected:** Container scanner returns at least 4 crypto library findings (cryptography, pyopenssl, openssl per image).

---

## Profile: source

*Gitea + seeded repos with crypto anti-patterns (semgrep target).*

> **Idempotency contract (CHAOS-03 / DEF-999.83-C, 2026-05-16):** The
> `gitea-seed` sidecar is idempotent — re-running `PROFILE_ARGS="--profile source"
> ./lab.sh up` against a persisted `gitea_data` volume is a no-op. A
> sentinel-repo existence probe at the top of `source/seed.sh` checks
> `/api/v1/repos/labadmin/crypto-antipatterns-python`; if present, the script
> logs `[seed] sentinel repo crypto-antipatterns-python already present;
> skipping seed` and exits 0 immediately, avoiding the prior HTTP 409
> duplicate-repo cascade. The per-repo `repo_exists` checks remain as a
> defense-in-depth layer for partial-seed states. Verified live on macOS
> Docker Desktop: two consecutive `up` cycles produced `chaoslab-gitea-seed-1
> Exited (0)` with the skip message and zero 409s. Scanner findings against
> the seeded repos unchanged.

```bash
PROFILE_ARGS="--profile source" ./lab.sh up
```

| Repo | File | Anti-Pattern Category | semgrep Rule Match | Notes |
|------|------|-----------------------|-------------------|-------|
| crypto-antipatterns-python | crypto/weak_algorithms.py | Weak algorithm (MD5/DES/RC4/ECB) | python.cryptography.security.insecure-cipher* | MD5, DES, RC4, ECB mode |
| crypto-antipatterns-python | secrets/hardcoded_keys.py | Hardcoded keys/secrets | secrets.* | RSA key + AES key + API secret literal |
| crypto-antipatterns-python | crypto/weak_random.py | Weak random / custom crypto | python.lang.security.insecure-random | random.random() for security |
| crypto-antipatterns-python | crypto/deprecated_protocols.py | Deprecated protocol usage | python.cryptography.security.ssl* | TLS 1.0 pinning |
| crypto-antipatterns-go | main.go | Weak algorithm (MD5/DES/RC4) | go.crypto.security.* | crypto/md5, crypto/des, crypto/rc4, math/rand |
| crypto-antipatterns-java | src/CryptoAntiPatterns.java | Weak algorithm + hardcoded | java.security.* | MessageDigest MD5, DES cipher, hardcoded key |

**Scanner validation command:**
```
git clone http://localhost:20006/labadmin/crypto-antipatterns-python && cd crypto-antipatterns-python && semgrep --config p/cryptography .
```
**Expected:** At least 1 finding per anti-pattern category (hardcoded keys, weak algorithm, weak random, deprecated protocol).

---

## Profile: ssh-weak

*OpenSSH 7.6p1 with deliberately weak KEX/hostkey/MAC algorithms on port 20022.*

```bash
PROFILE_ARGS="--profile ssh-weak" ./lab.sh up
```

| Port | Service | Algorithm Class | Expected ssh-audit Finding | Severity |
|-----:|---------|----------------|---------------------------|----------|
| 20022 | ssh-weak | KEX | diffie-hellman-group1-sha1 | CRITICAL |
| 20022 | ssh-weak | KEX | diffie-hellman-group14-sha1 | WARNING |
| 20022 | ssh-weak | KEX | diffie-hellman-group-exchange-sha1 | WARNING |
| 20022 | ssh-weak | HostKey | ssh-dss | CRITICAL |
| 20022 | ssh-weak | MAC | hmac-md5 | CRITICAL |
| 20022 | ssh-weak | MAC | hmac-sha1 | WARNING |

**Scanner validation command:**
```
docker compose --profile ssh-weak up -d && sleep 5 && ssh-audit localhost:20022
```
**Expected:** ssh-audit returns >= 3 critical/warning findings for KEX (group1-sha1), hostkey (ssh-dss), and MAC (hmac-md5).

---

## Profile: ldaps

> **Note:** As of 2026-05-15 the `ldaps` service runs on `bitnamilegacy/openldap:2.6.10-debian-12-r4` (was `osixia/openldap:1.5.0`) for macOS Docker Desktop bind-mount compatibility (BACK-91 / DEF-999.83-A). The osixia entrypoint chowns bind-mounted cert files at startup, which fails on macOS where bind-mounts are read-only; bitnami's entrypoint does not. The `bitnamilegacy/*` namespace hosts the post-2025 free images that used to live under `bitnami/*` before Bitnami migrated to paid Secure Images. TLS cert set and crypto findings are unchanged — verified against the same `./certs/modern.{crt,key}` material and CA.
>
> **Phase 82-01 live verification (2026-05-16):** `./lab.sh down && PROFILE_ARGS="--profile ldaps" ./lab.sh up` round-tripped cleanly on macOS Docker Desktop across two consecutive cycles. `LDAPTLS_REQCERT=never ldapsearch -x -H ldaps://localhost:636 -b 'dc=chaos,dc=local' -LLL -s base` returned the base DN (`dn: dc=chaos,dc=local`, `objectClass: dcObject`, `o: example`) on both cycles with no chown errors and no slapd init failures. DEF-999.83-A is closed.

*OpenLDAP over LDAPS on standard port 636 with self-signed cert.*

```bash
PROFILE_ARGS="--profile ldaps" ./lab.sh up
```

| Port | Service | Expected TLS Finding | Notes |
|-----:|---------|---------------------|-------|
| 636 | ldaps | TLS certificate chain | sslyze returns cert chain for modern.crt (self-signed lab cert) |
| 636 | ldaps | CERT_SELFSIGNED | modern.crt is self-signed lab cert — sslyze detects untrusted issuer |
| 636 | ldaps | Protocol support | TLS 1.2/1.3 depending on OpenLDAP version |

**Scanner validation command:**
```
docker compose --profile ldaps up -d && sleep 5 && sslyze --targets localhost:636
```
**Expected:** sslyze returns TLS certificate chain findings including self-signed cert detection.

## Profile: ldaps — Code-Signing Fixture

*Added Phase 95 LAB-01 (CSIGN-01): the `ldaps` service now also carries a user with a
`userCertificate` attribute containing a cert with CodeSigning EKU (OID 1.3.6.1.5.5.7.3.3)
and a weak RSA-1024 / SHA-1 signature — exercises the code-signing scanner HIGH path.*

*The `ldaps-codesign-seed` sidecar seeds `uid=codesign-weak` into `dc=chaos,dc=local` via
an idempotent `ldapadd -c` run (mirrors the smime-seed pattern; swallows exit 68).*

| User DN | Certificate | Expected Finding | Severity |
|---|---|---|---|
| uid=codesign-weak,ou=people,dc=chaos,dc=local | RSA-1024 / SHA-1 + CodeSigning EKU | CODE-SIGN/weak-algorithm | HIGH |

**Scanner validation command:**
```bash
PROFILE_ARGS="--profile ldaps" ./lab.sh up
# Then run with --inventory-code-signing and codesign_targets pointing at ldaps:636
python run_scan.py --target localhost --inventory-code-signing \
  # (configure codesign_targets: ["ldap://localhost:636"] in scan config)
```
**Expected:** CODE_SIGNING scanner returns 1 HIGH `CODE-SIGN/weak-algorithm` finding from the ldaps profile.

---

## Profile: dnssec

*BIND9 with weak DNSSEC zones (RSASHA1) on UDP/TCP 15353.*

```bash
PROFILE_ARGS="--profile dnssec" ./lab.sh up
```

> **Profile name note:** The Docker Compose profile is `dnssec` (compose is the source of truth). The v3 oracle used the service name `bind9` — that was a drift error, corrected here.

| Zone | Algorithm | Algorithm ID | Expected Finding | Severity |
|------|-----------|-------------|-----------------|----------|
| weak.example.com | RSASHA1 | 5 | DNSSEC weak signing algorithm (SHA-1 collision-vulnerable) | CRITICAL |
| weak.example.com | RSASHA1-NSEC3-SHA1 | 7 | DNSSEC weak signing algorithm (SHA-1) | CRITICAL |
| unsigned.example.com | NONE | — | Unsigned zone — DNS responses are unauthenticated | HIGH |
| nsec.example.com | ECDSAP256SHA256 | 13 | NSEC zone enumeration exposure | MEDIUM |

**Scanner validation command:**
```
docker compose --profile dnssec up -d && sleep 5 && quirk scan --targets weak.example.com unsigned.example.com nsec.example.com
```
**Expected:** DNSSEC scanner returns >= 1 CRITICAL finding (RSASHA1) for weak.example.com, 1 HIGH finding (unsigned zone) for unsigned.example.com, and 1 MEDIUM finding (NSEC) for nsec.example.com. ECDSAP256SHA256 zones produce no algorithm severity finding.

**Ports:** 15353/udp, 15353/tcp (service: bind9-dnssec)

---

## Profile: saml

*simpleSAMLphp IdP with weak signing cert (RSA-1024 / SHA-1) on port 8080. Note: shares port 8080 with Keycloak's container-internal port; no host conflict because Keycloak uses `expose:` not `ports:` for 8080.*

```bash
PROFILE_ARGS="--profile saml" ./lab.sh up
```

> **Drift fixes vs v3 oracle:** Profile name corrected from `simpla-samlphp` to `saml`; port corrected from `8880` to `8080` (compose is the source of truth per D-14).

| Port | Service | Certificate | Expected Finding | Severity |
|-----:|---------|-------------|-----------------|----------|
| 8080 | simplesamlphp | RSA-1024 signing cert | Weak SAML signing certificate: RSA-1024 | CRITICAL |
| 8080 | simplesamlphp | SHA-1 algorithm URI | SHA-1 algorithm URI detected in SAML metadata | HIGH |

**Scanner validation command:**
```
docker compose --profile saml up -d && sleep 10 && quirk scan --targets http://localhost:8080/simplesaml/saml2/idp/metadata.php
```
**Expected:** SAML scanner returns 1 CRITICAL finding for RSA-1024 signing certificate and optionally 1 HIGH finding if SHA-1 algorithm URI is present in metadata. Findings appear in the Identity tab (source="saml"), not the Findings tab.

---

## Profile: kerberos

*Samba AD-DC for Kerberos etype enumeration on privileged ports 88 + 389. Warning: These ports collide with system DNS/LDAP if anything else is listening locally.*

```bash
PROFILE_ARGS="--profile kerberos" ./lab.sh up
```

> **Drift fix vs v3 oracle:** Profile name corrected from `samba-dc` to `kerberos` (compose is the source of truth per D-14).

> **Port conflict warning:** Ports 88 and 389 are privileged ports that bind directly (not remapped to a high-numbered range). Do not run this profile if your host system has a local Kerberos KDC or LDAP server, as port conflicts will occur.

| Port | Service | Etype ID | Etype Name | Expected Finding | Severity |
|-----:|---------|---------|-----------|-----------------|----------|
| 88 | samba-dc | 23 | rc4-hmac | Kerberos weak etype: rc4-hmac | HIGH |
| 88 | samba-dc | 17 | aes128-cts-hmac-sha1-96 | Kerberos weak etype: aes128-cts-hmac-sha1-96 | HIGH |
| 389 | samba-dc | — | LDAP | LDAP service exposed on standard port | INFO |

**Scanner validation command:**
```
docker compose --profile kerberos up -d && sleep 15 && quirk scan --targets localhost:88
```
**Expected:** Kerberos scanner returns >= 2 HIGH findings for weak etypes (rc4-hmac, aes128-cts-hmac-sha1-96).

---

<!-- DAR / messaging profile sections appended by plan 40-03 below this line -->

---

## Profile: database

*PostgreSQL + MySQL with SSL explicitly disabled. Phase 27 DAR scanner targets — literal scanner output strings shown in `Expected condition / tag`.*

```bash
PROFILE_ARGS="--profile database" ./lab.sh up
```

| Port | Service | Engine | Expected protocol | TLS in Transit | Encryption-at-Rest | Expected condition / tag | Notes |
|-----:|---------|--------|-------------------|----------------|-------------------|--------------------------|-------|
| 25432 | postgres-ssl-off | PostgreSQL 15 | POSTGRESQL | OFF | none | DB_POSTGRESQL_SSL_OFF → `protocol=POSTGRESQL, service_detail=PostgreSQL/ssl-off` (HIGH) | `SHOW ssl` returns 'off'; db_connector.py L101 |
| 25432 | postgres-ssl-off | PostgreSQL 15 | POSTGRESQL | partial | none | `protocol=POSTGRESQL, service_detail=PostgreSQL/plaintext-connections-allowed (N non-SSL)` (HIGH) | `pg_stat_ssl` shows non-SSL connections; db_connector.py L137 |
| 23306 | mysql-ssl-off | MySQL 8 | MYSQL | OFF | none | DB_MYSQL_SSL_OFF → `protocol=MYSQL, service_detail=MySQL/ssl-off` (HIGH) | `SHOW STATUS LIKE 'Ssl_cipher'` empty; db_connector.py L227 |

**Reference:** Scanner: `quirk/scanner/db_connector.py`. Risk titles via risk_engine `evaluate_db_endpoints`. Oracle aliases (`DB_POSTGRESQL_SSL_OFF`, `DB_MYSQL_SSL_OFF`) used by `docs/UAT-SERIES.md`.

---

## Profile: storage-s3

*MinIO S3-compatible server. Seed creates `encrypted-bucket` (SSE-S3) + `unencrypted-bucket` (no SSE) for STOR-01.*

```bash
PROFILE_ARGS="--profile storage-s3" ./lab.sh up
```

| Port | Service | Provider | Expected protocol | Encryption Mode | Public Access | KMS Key | Versioning | Expected condition / tag | Notes |
|-----:|---------|----------|-------------------|-----------------|---------------|---------|------------|--------------------------|-------|
| 29000 | minio (encrypted-bucket) | MinIO | S3 | SSE-S3 (AES256) | private | S3-managed | n/a | (no finding) → `protocol=S3, service_detail=S3/sse-s3` | aws_connector.py L257 |
| 29000 | minio (unencrypted-bucket) | MinIO | S3 | none | private | none | n/a | `protocol=S3, service_detail=S3/unencrypted` (HIGH) | aws_connector.py L252,263,268 |
| 29001 | minio-console | MinIO Console | HTTP | n/a | local-only | n/a | n/a | not scanned | management UI |

**Reference:** Scanner: `quirk/scanner/aws_connector.py`. Evidence keys: `dar_storage_unencrypted_count`, `dar_storage_aws_managed_count`, `dar_storage_unencrypted_ratio`. Detail in `labs/storage/expected_results.md`.

---

## Profile: vault

*Dedicated Vault dev server (vault-30, image 1.17) on 28200. Independent of the legacy `storage` profile's Vault on 20009. Seeds transit keys, PKI mount, and auth methods for VAULT-01/02/03.*

```bash
PROFILE_ARGS="--profile vault" ./lab.sh up
```

| Port | Service | Mount Type | Seal Type | Auto-Unseal | Expected condition / tag | Notes |
|-----:|---------|------------|-----------|-------------|--------------------------|-------|
| 28200 | vault-30 | transit/rsa-2048-classification | shamir | no | (no finding — exportable=false) → `protocol=VAULT, service_detail=transit/rsa-2048-classification` | vault_connector.py L155 |
| 28200 | vault-30 | transit/rsa-2048-exportable | shamir | no | `protocol=VAULT, service_detail=transit/rsa-2048-exportable` (MEDIUM) | exportable=true; vault_connector.py L158 |
| 28200 | vault-30 | PKI/pki | shamir | no | `protocol=VAULT, service_detail=PKI/pki` (HIGH) | RSA<4096 root CA; vault_connector.py L251 |
| 28200 | vault-30 | auth/token | shamir | no | `protocol=VAULT, service_detail=auth/token` (HIGH) | token auth enabled; vault_connector.py L352 |
| 28200 | vault-30 | auth/userpass | shamir | no | `protocol=VAULT, service_detail=auth/userpass` (MEDIUM) | userpass auth enabled; vault_connector.py L354 |

**Reference:** Scanner: `quirk/scanner/vault_connector.py`. Evidence: `dar_vault_weak_count` (HIGH-only per Phase 30 D-11). Detail in `labs/vault/expected_results.md`.

---

## Profile: email

*Postfix (SMTP / SMTPS / Submission) + Dovecot (IMAP / IMAPS / POP3 / POP3S) with weak RSA-2048 TLS, non-PFS suites, TLS 1.2 floor on Postfix. Dovecot defaults to TLS 1.3 → no weak-cipher finding without explicit pin (caveat). Expected total: 3 HIGH (weak-cipher: 25/465/587) + 1 MEDIUM (STARTTLS-downgrade: 25).*

```bash
PROFILE_ARGS="--profile email" ./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|-----:|---------|-------------------|--------------------------|-------|
| 30025 | postfix-email (smtp) | SMTP-STARTTLS | `protocol=SMTP-STARTTLS, service_detail=SMTP-STARTTLS:25`; risk: "STARTTLS downgrade risk on SMTP" (MEDIUM, EMAIL-08) + "Weak cipher suite on email TLS endpoint" (HIGH, EMAIL-09) | Container port 25 |
| 30465 | postfix-email (smtps) | SMTPS | `protocol=SMTPS, service_detail=SMTPS:465`; risk: "Weak cipher suite on email TLS endpoint" (HIGH, EMAIL-09) | Container port 465 |
| 30587 | postfix-email (submission) | SMTP-STARTTLS | `protocol=SMTP-STARTTLS, service_detail=SMTP-STARTTLS:587`; risk: "Weak cipher suite on email TLS endpoint" (HIGH, EMAIL-09) | Container port 587 |
| 30143 | dovecot-email (imap) | IMAP-STARTTLS | `protocol=IMAP-STARTTLS, service_detail=IMAP-STARTTLS:143`; no weak-cipher finding by default | Container port 143; TLS 1.3 default |
| 30993 | dovecot-email (imaps) | IMAPS | `protocol=IMAPS, service_detail=IMAPS:993`; no weak-cipher finding by default | Container port 993; TLS 1.3 default |
| 30110 | dovecot-email (pop3) | POP3-STARTTLS | `protocol=POP3-STARTTLS, service_detail=POP3-STARTTLS:110`; no weak-cipher finding by default | Container port 110; TLS 1.3 default |
| 30995 | dovecot-email (pop3s) | POP3S | `protocol=POP3S, service_detail=POP3S:995`; no weak-cipher finding by default | Container port 995; TLS 1.3 default |

**Reference:** Scanner: `quirk/scanner/email_scanner.py`. Risk titles from `risk_engine.evaluate_email_endpoints`. Detail + TLS 1.3 caveat in `labs/email/expected_results.md`.

**LAB-03 coverage note (D-01):** Port 30587 (Postfix submission / SMTP STARTTLS) satisfies
requirement LAB-03 ("smtp-starttls coverage"). The scanner emits
`protocol=SMTP-STARTTLS, service_detail=SMTP-STARTTLS:587` (HIGH, EMAIL-09) for this
port when the email profile is running. No standalone `smtp-starttls` service exists —
this coverage is intentional per decision D-01 (already-covered closure). Requirement
LAB-03 is closed as covered by the `email` profile.

---

## Profile: broker

*Kafka + RabbitMQ + Redis with intentional plaintext + weak-cipher TLS listeners. Expected total: 6 HIGH findings.*

```bash
PROFILE_ARGS="--profile broker" ./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|-----:|---------|-------------------|--------------------------|-------|
| 29092 | kafka-broker (plaintext) | KAFKA-PLAIN | `protocol=KAFKA-PLAIN, service_detail=KAFKA-PLAIN:29092`; risk: "Kafka plaintext listener detected" (HIGH, KAFKA-02) | broker_scanner.py L390 |
| 29093 | kafka-broker (TLS) | KAFKA-TLS | `protocol=KAFKA-TLS, service_detail=KAFKA-TLS:29093`; risk: "Weak cipher suite on broker TLS endpoint" (HIGH, KAFKA-01) | broker_scanner.py L401 |
| 25672 | rabbitmq-broker (plaintext) | AMQP-PLAIN | `protocol=AMQP-PLAIN, service_detail=AMQP-PLAIN:25672`; risk: "AMQP plaintext listener detected" (HIGH, RABBIT-02) | broker_scanner.py L472 |
| 25671 | rabbitmq-broker (TLS) | AMQPS | `protocol=AMQPS, service_detail=AMQPS:25671`; risk: "Weak cipher suite on broker TLS endpoint" (HIGH, RABBIT-01) | broker_scanner.py L482 |
| 26379 | redis-broker (plaintext) | REDIS-PLAIN | `protocol=REDIS-PLAIN, service_detail=REDIS-PLAIN:26379`; risk: "Redis plaintext listener (no authentication)" (HIGH, REDIS-02) | broker_scanner.py L674 |
| 26380 | redis-broker (TLS) | REDIS-TLS | `protocol=REDIS-TLS, service_detail=REDIS-TLS:26380`; risk: "Weak cipher suite on broker TLS endpoint" (HIGH, REDIS-01) | broker_scanner.py L683 |

**Reference:** Scanner: `quirk/scanner/broker_scanner.py`. Risk titles from `risk_engine.evaluate_broker_endpoints`. Detail in `labs/broker/expected_results.md`. Expected total: 6 HIGH.

**Idempotency contract (Phase 82-02 / CHAOS-02 / DEF-999.83-B):** `rabbitmq-broker` is idempotent across `./lab.sh down && ./lab.sh up --profile broker` cycles. The Erlang cookie is set deterministically via the `RABBITMQ_ERLANG_COOKIE` env var on the service (lab-only value, not a secret; no `.erlang.cookie` bind-mount exists that could override it). Second-cycle bring-up must reach `Up (healthy)` with no "Connection attempt from disallowed node" or "Cookie file ... must be accessible by owner only" lines in `docker logs chaoslab-rabbitmq-broker-1`. The `[warning] Overriding Erlang cookie using the value set in the environment` log line is expected and confirms the env-var is in effect. Image pinned to `rabbitmq:3.13.7-management` (3.12.x reached EOL 2024-06-26).

---

## Profile: tls-cert-defects

*Phase 46 / TLS-FIND-07. Single-profile target exercising all four cert-defect finding classes (TLS-FIND-01..05) end-to-end. Existing `tls-expired` (port 9443) and `tls-selfsigned` (port 10443) profiles remain unchanged for back-compat — this profile lives on a dedicated port range (13444-13447) so both can coexist.*

```bash
PROFILE_ARGS="--profile tls-cert-defects" ./lab.sh up
```

| Port | Service | Cert source | Expected scanner finding | Severity | Requirement |
|-----:|---------|-------------|--------------------------|----------|-------------|
| 13444 | tls-cert-expired      | `certs/expired.crt` (already past `not_after`) | "TLS certificate expired" | CRITICAL | TLS-FIND-01 |
| 13445 | tls-cert-selfsigned   | `certs/selfsigned.crt` (issuer == subject) | "TLS certificate is self-signed" | HIGH | TLS-FIND-02 |
| 13446 | tls-cert-untrusted-ca | `certs/scenarios/untrusted-ca/leaf.crt` (RSA-2048 leaf signed by `scenario-root` CA, NOT in system trust store) | "TLS certificate issued by untrusted CA" | MEDIUM | TLS-FIND-03 |
| 13447 | tls-cert-rsa1024      | `certs/scenarios/rsa1024/leaf.crt` (RSA-1024 weak key, OpenSSL legacy provider) | "Undersized RSA key" | HIGH | TLS-FIND-04 |

**Live-fire smoke command:**

```bash
quirk scan localhost:13444,localhost:13445,localhost:13446,localhost:13447 --output report.html
```

**Expected:** 4 distinct findings, severities CRITICAL / HIGH / MEDIUM / HIGH, no untrusted-CA finding emitted on the self-signed endpoint (D-04 mutual exclusivity), no rollup (D-02 — one finding per defect class).

**Notes**
- The untrusted-CA leaf is RSA-2048 — strong key — so the untrusted-CA finding is isolated from the RSA-1024 finding (no double-fire on port 13446).
- `tls-cert-rsa1024` requires `OPENSSL_CONF=/etc/nginx/openssl-legacy.cnf` (Pitfall 3) — modern OpenSSL 3 refuses RSA-1024 without the legacy provider.
- `lab.sh` auto-discovers this profile via `_derive_all_profiles()` reading docker-compose.yml at runtime — no manual `ALL_PROFILES` edit was needed.

**Reference:** Risk-engine branches in `quirk/engine/risk_engine.py:343–423`. Cert generation in `scripts/gen_phaseA_certs.sh` (`issue_leaf "untrusted-ca" ...`).

---

## Profile: smime

*OpenLDAP seeded with three users carrying `userSMIMECertificate` attributes — exercises weak-signing, weak-key, and SAFE paths. Plain LDAP on host port **38900 only** (LDAPS deferred per D-79-R9 to a Phase 82 follow-up).*

> **Image:** `bitnamilegacy/openldap:2.6.10-debian-12-r4` (parity with the `ldaps` profile after the 2026-05-15 macOS bind-mount migration; supersedes 79-CONTEXT's osixia:1.5.0 pin per D-79-UPDATE).
>
> **LDIF attribute syntax:** `userSMIMECertificate::` (RFC 2798 base64, no `;binary` suboption). The `userSMIMECertificate` attribute (OID 2.16.840.1.113730.3.1.40) uses SYNTAX 1.3.6.1.4.1.1466.115.121.1.5 (Binary), which already carries octets directly — OpenLDAP rejects `userSMIMECertificate;binary` with "option binary not supported with type". Phase 79-01 deviation, captured in `smime/certs/regen.sh`.

```bash
PROFILE_ARGS="--profile smime" ./lab.sh up
```

| User DN | Certificate | Expected Finding | Severity |
|---|---|---|---|
| uid=alice,ou=people,dc=quirk,dc=lab | RSA-1024 / SHA-1   | Weak S/MIME signing + weak key | HIGH |
| uid=bob,ou=people,dc=quirk,dc=lab   | RSA-1024 / SHA-256 | Weak S/MIME key (RSA-1024)     | HIGH |
| uid=carol,ou=people,dc=quirk,dc=lab | RSA-2048 / SHA-256 | (none — SAFE)                  | —    |

**Scanner validation command** *(Plan 79-02 will wire `--smime-target` / `--smime-base`)*:
```
docker compose --profile smime up -d && sleep 10 && quirk scan --smime-target ldap://localhost:38900 --smime-base dc=quirk,dc=lab
```

**Expected:** SMIME scanner returns **2 HIGH findings** (alice, bob); **0 findings from carol**. Findings appear in the Identity tab (`source="smime"`). **No IMAP traffic, no mailbox access** (privacy invariant, enforced by SMIME-08 AST gate in Plan 79-04). Idempotent — re-running `./lab.sh up --profile smime` must not produce duplicate LDIF entries; the seed sidecar uses `ldapadd -c` and explicitly swallows exit code 68 (`LDAP_ALREADY_EXISTS`) on subsequent runs.

**Ports:** `38900/tcp` (LDAP) — chosen to avoid 636 (`ldaps` profile) and 389 (`kerberos`/samba-DC profile). LDAPS (38901) intentionally **not** exposed in Phase 79; deferred to Phase 82.

**Cert fixtures:** Pre-built DER blobs committed under `quantum-chaos-enterprise-lab/smime/certs/{alice,bob,carol}.der` — regenerated via `regen.sh` (developer tool only, not runtime). 100-year validity window so all three certs are non-expired; the expiry path is exercised by unit-test mocks in Plan 79-04, not by lab fixtures.

**Reference:** `quirk/db.py::_IDENTITY_COLUMNS` (column `smime_scan_json`), compose blocks `smime-openldap` + `smime-seed` (profile `smime`).

---

## Profile: adcs

*OpenLDAP seeded with a deliberately misconfigured AD CS Configuration partition — three certificate templates (one ESC1-category, one ESC4-category, one safe baseline) plus one RSA-1024 / SHA-1 CA signing cert fixture. Plain LDAP on host port **38910 only** (LDAPS deferred per Phase 80 CONTEXT, matching smime D-79-R9). Authenticated SIMPLE bind supported for real-AD parity; anonymous bind is permitted inside the chaos lab.*

> **Image:** `bitnamilegacy/openldap:2.6.10-debian-12-r4` (parity with the `smime` and `ldaps` profiles).
>
> **Schema-load path:** Bitnami-native `LDAP_CUSTOM_SCHEMA_DIR=/schemas` env hook (Plan 80-01 deviation Rule 1, 2026-05-16). The plan's PRIMARY (`ldapadd cn=config` from seed sidecar) returned `Insufficient access (50)` and the D-80-R7 Dockerfile fallback was not auto-loaded by Bitnami's entrypoint; the env-hook activates `slapadd` during initial offline setup, which is the only window cn=config accepts new schemas. `LDAP_EXTRA_SCHEMAS=...,msuser` is also set so the AD-compatible attribute types (`cACertificate`, `nTSecurityDescriptor`, `dNSHostName`, `pKIExtendedKeyUsage`, `pKIKeyUsage`) load before the msPKI overlay's structural classes reference them.
>
> **OID arc:** The msPKI overlay uses a private QU.I.R.K. arc `1.3.6.1.4.1.99999.80.*` because Microsoft's real `1.2.840.113556.1.4.20XX` range collides with the bundled `msuser` schema. The scanner keys off attribute NAMES (not OIDs), so this is functionally equivalent.

```bash
PROFILE_ARGS="--profile adcs" ./lab.sh up
```

| Object | Class | Key attribute | Expected Finding | Severity | Counter |
|---|---|---|---|---|---|
| `CN=QuirkLabCA,CN=Enrollment Services,...` | `pKIEnrollmentService` | `cACertificate;binary::` RSA-1024 SHA-1 | Weak CA signing algorithm | HIGH | `identity_adcs_weak_signing_count` |
| `CN=BadTemplate-ESC1,CN=Certificate Templates,...` | `pKICertificateTemplate` | `msPKI-Certificate-Name-Flag: 1` (ENROLLEE_SUPPLIES_SUBJECT) + client-auth EKU + `msPKI-RA-Signature: 0` | ESC1 misconfig | HIGH | `identity_adcs_weak_template_count` |
| `CN=BadTemplate-ESC4,CN=Certificate Templates,...` | `pKICertificateTemplate` | `nTSecurityDescriptor` present (not parsed) | ADCS-COVERAGE-GAP ESC4 | LOW | `identity_adcs_coverage_gap_count` |
| `CN=SafeTemplate,CN=Certificate Templates,...` | `pKICertificateTemplate` | benign defaults, email-protection EKU only | (none — SAFE) | — | — |
| ESC5 / ESC7 / ESC8 classes | non-LDAP-observable | (no LDAP attribute) | ADCS-COVERAGE-GAP (one per class) | LOW | `identity_adcs_coverage_gap_count` |

**Scanner validation command** *(Plan 80-02 will wire `--adcs-target` / `--adcs-base`)*:
```
docker compose --profile adcs up -d && sleep 12 && quirk scan --adcs-target ldap://localhost:38910 --adcs-base dc=quirk,dc=lab
```

**Expected:** ADCS scanner returns **1 HIGH weak-signing finding** (QuirkLabCA RSA-1024 SHA-1), **1 HIGH ESC1 finding** (BadTemplate-ESC1), **0 from SafeTemplate**, and exactly **4 LOW ADCS-COVERAGE-GAP findings** (one per non-LDAP-observable ESC class: ESC4, ESC5, ESC7, ESC8 per D-80-R8). Findings appear in the Identity tab (`source="adcs"`, `protocol="ADCS"`). **No certificate enrollment, no CSR generation, no LDAP modify/add/delete operations** (privacy invariant, enforced by `tests/test_adcs_no_writes.py` + `tests/test_adcs_ast_gate.py` per ADCS-09). Idempotent — re-running `./lab.sh up --profile adcs` must not error; the seed sidecar uses `ldapadd -c` and explicitly swallows exit code 68 (`LDAP_ALREADY_EXISTS`).

**Ports:** `38910/tcp` (LDAP) — chosen to avoid 38900 (`smime` profile), 636 (`ldaps`), and 389 (`kerberos`). LDAPS intentionally **not** exposed in Phase 80; deferred to a Phase 82 follow-up.

**Fixtures:** Pre-built DER blob committed at `quantum-chaos-enterprise-lab/adcs/certs/ca-weak.der` (RSA-1024, SHA-1, 100-year validity window so it's non-expired; expiry-path detection is exercised by unit-test mocks in Plan 80-04, not by lab fixtures). LDIFs at `adcs/ldif/{00-base,10-ca,20-templates}.ldif`. Regenerate the weak CA via `adcs/certs/regen.sh` (developer tool only, not runtime). D-80-R7 Dockerfile fallback shipped at `adcs/Dockerfile` (preserved per the plan's "ship both branches" contract; not currently active).

**Reference:** `quirk/db.py::_IDENTITY_COLUMNS` (column `adcs_scan_json`), compose blocks `adcs-openldap` + `adcs-seed` (profile `adcs`).

---

## Phase 82 Closure (Chaos Lab Fidelity)

Wave-2 closure summary for Phase 82 — recorded here so the oracle remains the
single source of truth for chaos-lab state across version bumps.

- **CHAOS-01** — `ldaps` profile migrated to `bitnamilegacy/openldap:2.6.10-debian-12-r4`; clean bring-up on macOS Docker Desktop with no chown / Read-only-file-system errors; verified Plan 82-01 (commit `be425f8`).
- **CHAOS-02** — `rabbitmq-broker` pinned to `rabbitmq:3.13.7-management`; `RABBITMQ_ERLANG_COOKIE` deterministic env var; survives `lab.sh down/up` cycles with no Erlang cookie-mismatch log lines; verified Plan 82-02 (commit `e725276`).
- **CHAOS-03** — `gitea` source seed short-circuits when sentinel repo `labadmin/crypto-antipatterns-python` is already present; re-runs exit `0` with no HTTP 409s; verified Plan 82-03 (commit `fdded8e`).
- **CHAOS-04** — Per-profile re-up regression test at `tests/test_chaos_lab_idempotency.py` discovers every profile via `docker compose config --profiles` and runs `./lab.sh up` twice per profile (one parametrized test per profile); marked `@pytest.mark.slow` and skipped cleanly when Docker is unreachable.
- **CHAOS-05** — Image-pin CI gate at `tests/test_chaos_lab_image_pinning.py` (runs in default suite; pure `yaml.safe_load` parse); `lab.sh _validate_pinned_tags()` early-exit installed at the top of both `up)` and `all)` cases so adding `:latest` or a bare-image entry fails before any container is created.
- **CHAOS-06** — `_derive_all_profiles()` enumerates 20 profiles including `smime` and `adcs`; oracle sections for both new profiles present above (Plan 79 + Plan 80 delivered, Plan 82-04 confirmed parity); README Profile Summary table has rows for both with their respective ports (38900, 38910) and links into this oracle.

---

## Profile: postgres-tls

*Phase 89 / LAB-01. PostgreSQL with intentionally weak TLS — RSA key-exchange ciphers (no PFS),
TLS 1.2 only. Scanner probe: sslyze `ProtocolWithOpportunisticTlsEnum.POSTGRES` on host port
**39432**. Expected total: 1 HIGH + 1 MEDIUM finding.*

```bash
PROFILE_ARGS="--profile postgres-tls" ./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|-----:|---------|-------------------|--------------------------|-------|
| 39432 | postgres-tls (STARTTLS) | POSTGRES-TLS | `protocol=POSTGRES-TLS, service_detail=POSTGRES-TLS:5432`; risk: "Weak cipher suite on database TLS endpoint" (HIGH, TLS-03) | sslyze ProtocolWithOpportunisticTlsEnum.POSTGRES; ciphers AES128-SHA:AES256-SHA (RSA-KX, no PFS) |
| 39432 | postgres-tls (cert) | POSTGRES-TLS | `protocol=POSTGRES-TLS`; risk: "RSA-2048 certificate (quantum-vulnerable)" (MEDIUM, TLS-02) | Self-signed RSA-2048 cert CN=postgres-tls.chaos.local |

**Weak TLS knobs (`labs/postgres-tls/postgresql.conf`):**
- `ssl_ciphers = 'AES128-SHA:AES256-SHA'` — RSA key exchange, no forward secrecy
- `ssl_min_protocol_version = 'TLSv1.2'` / `ssl_max_protocol_version = 'TLSv1.2'` — TLS 1.2 only
- RSA-2048 self-signed certificate (`CN=postgres-tls.chaos.local`)

**Cert note:** Key is mounted at `/var/lib/postgresql/postgres-tls.key` (owned by postgres uid 999)
to satisfy PostgreSQL's SSL key ownership requirement (Pitfall 1 in RESEARCH.md).

**Reference:** Scanner: sslyze `ProtocolWithOpportunisticTlsEnum.POSTGRES`. Config: `labs/postgres-tls/postgresql.conf`. Requirement: LAB-01.

---

## Profile: redis-tls

*Phase 89 / LAB-02. Standalone Redis with intentionally weak TLS — 3DES + RSA key-exchange
ciphers, TLS 1.2 only. Separate from the `broker` profile. Scanner probe:
`broker_scanner.py scan_redis_targets()` on host port **39380** (TLS) + **39379** (plaintext).
Expected total: 2 HIGH findings.*

```bash
PROFILE_ARGS="--profile redis-tls" ./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|-----:|---------|-------------------|--------------------------|-------|
| 39380 | redis-tls (TLS port) | REDIS-TLS | `protocol=REDIS-TLS, service_detail=REDIS-TLS:6380`; risk: "Weak cipher suite on broker TLS endpoint" (HIGH, REDIS-01) | 3DES-SHA + RSA-KX; tls-ciphers DES-CBC3-SHA:AES128-SHA:AES256-SHA |
| 39379 | redis-tls (plaintext port) | REDIS-PLAIN | `protocol=REDIS-PLAIN, service_detail=REDIS-PLAIN:6379`; risk: "Redis plaintext listener (no authentication)" (HIGH, REDIS-02) | broker_scanner.py L674 |

**Weak TLS knobs (`labs/redis-tls/redis.conf` — mirrors `labs/broker/redis/redis.conf`):**
- `tls-ciphers "DES-CBC3-SHA:AES128-SHA:AES256-SHA"` — 3DES + RSA key exchange
- `tls-protocols "TLSv1.2"` — TLS 1.2 only
- `tls-auth-clients no` — no client certificate required
- Both plaintext port 6379 and TLS port 6380 exposed

**Note:** The `broker` profile's `redis-broker` service is **unchanged**. This is a standalone
profile providing an isolated Redis-TLS target (D-02).

**Reference:** Scanner: `quirk/scanner/broker_scanner.py`. Config: `labs/redis-tls/redis.conf`. Requirement: LAB-02.

---

## Profile: kafka-tls

*Phase 89 / LAB-04. Standalone Kafka (apache/kafka:3.9.0) with intentionally weak TLS — RSA
key-exchange ciphers, TLS 1.2 only. KRaft mode. Scanner probe:
`broker_scanner.py scan_kafka_targets()` on host port **39092** (PLAINTEXT) and **39093** (TLS).
Expected total: 2 HIGH + 1 MEDIUM finding.*

```bash
PROFILE_ARGS="--profile kafka-tls" ./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|-----:|---------|-------------------|--------------------------|-------|
| 39092 | kafka-tls (PLAINTEXT) | KAFKA-PLAIN | `protocol=KAFKA-PLAIN, service_detail=KAFKA-PLAIN:9092`; risk: "Kafka plaintext listener detected" (HIGH, KAFKA-02) | broker_scanner.py L390 |
| 39093 | kafka-tls (SSL) | KAFKA-TLS | `protocol=KAFKA-TLS, service_detail=KAFKA-TLS:9093`; risk: "Weak cipher suite on broker TLS endpoint" (HIGH, KAFKA-01) | TLS_RSA_WITH_AES_128/256_CBC_SHA (RSA-KX, no PFS) |
| 39093 | kafka-tls (cert) | KAFKA-TLS | `protocol=KAFKA-TLS`; risk: "RSA-2048 certificate (quantum-vulnerable)" (MEDIUM, TLS-02) | Self-signed RSA-2048 cert CN=kafka-tls.chaos.local |

**Weak TLS knobs (`labs/kafka-tls/server.properties`):**
- `ssl.cipher.suites=TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA` — RSA key exchange, no PFS
- `ssl.enabled.protocols=TLSv1.2` — TLS 1.2 only
- `ssl.keystore.type=PEM` — PEM keystore (separate crt + key files)
- Both PLAINTEXT listener (9092) and SSL listener (9093) active

**Healthcheck note:** Uses PLAINTEXT port 9092 — avoids needing truststore or client cert.

**Image upgrade:** `apache/kafka:3.9.0` (vs `3.7.0` in the `broker` profile). The `broker`
profile's `kafka-broker` service is **unchanged**.

**Reference:** Scanner: `quirk/scanner/broker_scanner.py`. Config: `labs/kafka-tls/server.properties`. Requirement: LAB-04.

---

## Profile: grpc-tls

*Phase 89 / LAB-05. Minimal Go gRPC server (grpc-go) with a self-signed RSA-2048 certificate.
grpc-go automatically advertises ALPN `h2` via `NextProtos: ["h2"]` in the TLS config. Direct
TLS on port 443 (no STARTTLS). Scanner probe: sslyze `CERTIFICATE_INFO` + `TLS_1_2_CIPHER_SUITES`
+ `TLS_1_3_CIPHER_SUITES` on host port **39443**.*

```bash
PROFILE_ARGS="--profile grpc-tls" ./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|-----:|---------|-------------------|--------------------------|-------|
| 39443 | grpc-tls | TLS direct | `cert_subject=CN=grpc-tls.chaos.local, key_size=2048`; risk: "RSA-2048 certificate (quantum-vulnerable)" (MEDIUM, TLS-02) | sslyze CERTIFICATE_INFO |
| 39443 | grpc-tls | TLS 1.2 ciphers | `accepted_ciphers=[TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256, TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384, TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256]` — Go TLS defaults (ECDHE-RSA, forward secrecy) | Informational — no HIGH weak-cipher finding (Go's TLS 1.2 defaults are modern) |
| 39443 | grpc-tls | TLS 1.3 ciphers | `accepted_ciphers=[TLS_CHACHA20_POLY1305_SHA256, TLS_AES_256_GCM_SHA384, TLS_AES_128_GCM_SHA256]` | Informational |

**D-03 empirical result (confirmed at execution time, Phase 89 Plan 03):**
sslyze successfully negotiates the TLS handshake against the grpc-go server despite
the server advertising ALPN `h2` only. `scan_status=ServerScanStatusEnum.COMPLETED`.
The ALPN constraint does NOT prevent sslyze cipher/cert enumeration at the TLS record
layer. The openssl s_client fallback (D-03) was NOT needed.

**Expected findings summary:**
- RSA-2048 cert (quantum-vulnerable) — MEDIUM (TLS-02)
- TLS cipher suites — informational (Go TLS defaults are ECDHE-RSA + PFS; no HIGH finding)

**Weak TLS profile note:** The grpc-tls service uses Go's default `tls.Config` — TLS 1.2+
with ECDHE-RSA cipher suites. The intentional weakness is the RSA-2048 key size (D-02
quantum-vulnerable MEDIUM finding). There is no deliberately weak cipher config (unlike
redis-tls / kafka-tls which force 3DES/RSA-KX ciphers).

**ALPN h2 note:** grpc-go sets `NextProtos: ["h2"]` automatically. sslyze does not have an
ALPN ScanCommand but completes the TLS handshake and produces full cipher/cert findings.

**Reference:** Scanner: sslyze direct TLS on port 39443. Lab image: built from
`labs/grpc-tls/Dockerfile` (FROM golang:1.23-alpine). Config: `labs/grpc-tls/main.go`.
Requirement: LAB-05.

---

## Profile: oqs-nginx

*Phase 90 / PQC-01. Digest-pinned `openquantumsafe/nginx` container serving TLS 1.3 with the
X25519MLKEM768 (NIST ML-KEM-768 + X25519 hybrid) key-exchange group and an ML-DSA-65 certificate.
This is the agility ceiling anchor for the v5.0 D-04 consulting before/after demo — the "ideal
PQC-hybrid endpoint" that Plan 90-04 contrasts against the classical baseline.*

```bash
PROFILE_ARGS="--profile oqs-nginx" ./lab.sh up
```

**Image:** `openquantumsafe/nginx@sha256:6ca18ac692f347ea9d4c3fdab4231189f2146570cd03c4d8fb486bba208ef870`
(built 2026-05-18; pinned by digest — oqs-provider renames group names across releases, so `:latest`
is permanently forbidden for this service).

**Config:** `quantum-chaos-enterprise-lab/oqs-nginx/nginx.conf` — pins `ssl_ecdh_curve X25519MLKEM768`
and `ssl_protocols TLSv1.3` on the TLS server block. Mounted read-only into the container.

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|-----:|---------|-------------------|--------------------------|-------|
| 39444 | oqs-nginx | TLS 1.3 direct | Negotiated group: `X25519MLKEM768` (NamedGroup 4588); Peer signature type: `ML-DSA-65` (`mldsa65`) | Host OpenSSL >= 3.5 required for handshake; see advisory note below |
| 39444 | oqs-nginx | TLS 1.3 cert | ML-DSA-65 certificate (post-quantum signature algorithm) | Quantum-safe cert chain — no classical RSA/ECDSA fallback |

**Loopback bind / live scan note:** Like all lab profiles, `oqs-nginx` binds `127.0.0.1:39444`.
Live scanner runs against this profile require `--allow-internal-targets`.

**Host OpenSSL compatibility note (advisory case):** The X25519MLKEM768 handshake requires the
scanning host to have OpenSSL >= 3.5 (or an oqs-provider build) with ML-KEM support compiled in.
On older hosts (OpenSSL < 3.5), `openssl s_client -groups X25519MLKEM768` will fail the
handshake — this is a host-side limitation, not a profile defect. Plan 90-02 (detection) handles
this via the advisory fallback path: when the direct probe fails due to group-name mismatch or
handshake failure, the scanner emits a `PQC_HYBRID_ADVISORY` finding documenting that the endpoint
appears to offer PQC-hybrid but the host client cannot complete the negotiation.

**Expected scanner findings (finalized Plan 90-04 — D-04 before/after agility demo oracle):**

#### Detection outcomes

- **On a host with OpenSSL >= 3.5 (genuine-component path, verified empirically 2026-05-22):**
  - Probe: `openssl s_client -connect 127.0.0.1:39444 -groups X25519MLKEM768 -tls1_3`
    emits `Negotiated TLS1.3 group: X25519MLKEM768` + `Peer signature type: mldsa65`.
  - Scanner endpoint: `protocol="TLS"`, `cipher_suite="X25519MLKEM768"`,
    `service_detail="pqc-hybrid-detected|group=X25519MLKEM768"`.
  - CBOM component: `quantum-safe` KEM — `x25519mlkem768` alias → existing classifier
    entry `mlkem768x25519-sha256` → `(CryptoPrimitive.KEM, NIST Level 3, 192-bit security)`.
  - Evidence counter: `pqc_hybrid_endpoint_count = 1`.

- **On a host with OpenSSL < 3.5 (advisory-fallback path):**
  - Probe: `openssl s_client -groups X25519MLKEM768` fails handshake (no shared groups).
  - Scanner endpoint: `protocol="ADVISORY"`, `scan_error_category="coverage_gap"`,
    `service_detail="pqc-hybrid-detected|advisory=openssl-too-old"`.
  - CBOM: advisory finding documenting that full detection requires OpenSSL >= 3.5 or
    OQS-compiled tooling (non-goal, deferred to v5.1).
  - Evidence counter: `pqc_hybrid_endpoint_count = 1` (D-05 — counter increments on both
    genuine and advisory paths so PQC-03 scoring works regardless of host OpenSSL version).

#### D-04 Agility before/after (consulting deliverable — Plan 90-03 scoring, Plan 90-04 oracle)

The headline claim: **a PQC-hybrid scan scores strictly higher on the agility subscore than an
equivalent classical-TLS-only scan.**  Verified live (2026-05-22, host OpenSSL 3.6.2):

| Scenario | `pqc_hybrid_endpoint_count` | Agility subscore (/25) | Overall score |
|----------|-----------------------------|------------------------|---------------|
| Classical TLS only (baseline) | 0 | 18 | 83 (GOOD) |
| PQC-hybrid endpoint present (oqs-nginx) | 1 | **25** (clamped) | 87 (EXCELLENT) |
| **Delta** | — | **+7 visible** (+8.0 bonus, clamped at /25) | +4 |

> **Live-run footnote (2026-05-22):** The human-verified live scan of the `tls-modern` classical
> baseline measured an agility subscore of **17** (RSA-only TLS posture on that specific scan
> context), whereas the canonical oracle documents **18** (derived from a 50% HIGH finding ratio
> with 4 endpoints in `tests/test_pqc_agility_bonus.py`). The PQC uplift claim holds either way:
> the live oqs-nginx scan returned agility **25**, strictly exceeding both 17 and 18.  The 18 row
> above remains the canonical documented reference for the before/after demo.

Score engine details:
- Bonus weight: `agility_pqc_hybrid_bonus = 8.0` (SCORE_WEIGHTS key #37, Phase 90 PQC-03).
- Invariant: sum=283.0, count=37 (`tests/test_score_weights_invariant.py`).
- Bonus label in report drivers: `"PQC-hybrid key exchange (X25519MLKEM768)"`.
- Clamp: existing `_apply_weighted_impacts(score_cap=25.0)` — no second clamp.
- Orthogonal: five non-agility subscores are identical between the two scenarios.

Evidence dict used for the canonical agility contrast (from `tests/test_pqc_agility_bonus.py`):
```python
# 2 HIGH findings out of 4 endpoints → 50% HIGH ratio → −7 agility penalty → baseline 18/25
_base_evidence = {"finding_severity_counts": {"HIGH": 2}}
```

#### Discriminator (false-positive-free guarantee — Plan 90-04 regression test)

`tests/test_pqc_discriminator.py` asserts:

- **Positive arm (live, skipped when lab down):** `probe_pqc_hybrid("127.0.0.1", 39444)`
  returns `detected=True` + `negotiated_group="X25519MLKEM768"` against the running container.
- **Negative arm (always runs, subprocess mocked):** when `openssl s_client` output contains
  no "Negotiated TLS1.3 group: X25519MLKEM768" line (classical TLS alert / failed handshake),
  the probe returns `detected=False`.  A classical endpoint can never emit that line → zero
  false positives.
- Note: the negative arm uses mock subprocess output (not a Python `ssl.SSLContext` server)
  because host OpenSSL 3.6.2 supports X25519MLKEM768 natively and would make a local Python
  TLS server behaviorally identical to a PQC server.

**Requirements:** PQC-01 (lab profile), PQC-02 (detection), PQC-03 (scoring).
## Profile: fuzz-target

*Deliberately-weak FastAPI REST service for Phase 96 / LAB-01 active REST fuzzer validation. All weaknesses are intentional (T-96-11 — isolated compose profile, off by default, never production).*

```bash
PROFILE_ARGS="--profile fuzz-target" ./lab.sh up
```

| Port | Service | Probe | Expected Finding | Severity | Notes |
|-----:|---------|-------|-----------------|----------|-------|
| 20100 | fuzz-target | HSTS missing | HSTS_MISSING | HIGH | No `Strict-Transport-Security` header on any response — deliberate |
| 20100 | fuzz-target | HTTP-only cred | HTTP_ONLY_CRED | HIGH | OpenAPI spec declares `http://localhost:20100` server URL — deliberate |
| 20100 | fuzz-target | TLS downgrade | TLS_DOWNGRADE | HIGH | Service binds plain HTTP only; TLS downgrade probe fires if TLS later configured |
| 20100 | fuzz-target | JWT alg-confusion | ALG_CONFUSION | CRITICAL | `/probe` accepts forged HS256 token signed with RS256 public key — deliberate |

**Weak-target design:**
- `GET /openapi.json` — minimal OpenAPI 3.0 spec with `http://` server URL (HTTP-only cred probe target); schemathesis can consume this spec to enumerate `/probe`
- `GET /.well-known/jwks.json` — exposes RS256 public key (JWKS fetch for alg-confusion probe)
- `GET /probe` — accepts ANY `Authorization: Bearer <token>` without algorithm verification (alg-confusion probe target — returns `200 OK` for both legitimate RS256 and forged HS256 tokens)
- No `Strict-Transport-Security` header on any response (HSTS probe target)

**lab.sh note:** `_derive_all_profiles()` discovers `fuzz-target` dynamically by parsing `docker-compose.yml` — **no `ALL_PROFILES` edit to `lab.sh` was needed** (LAB-01 rationale: dynamic discovery via `yq` or `grep` fallback, per `_derive_all_profiles` at line 58 of `lab.sh`).

**Scanner validation command:**
```
quirk scan --targets http://localhost:20100 --fuzz --openapi-spec http://localhost:20100/openapi.json
```
**Expected:** REST fuzzer returns >= 2 findings: HSTS_MISSING (HIGH) + ALG_CONFUSION (CRITICAL, when `--fuzz-jwt-alg-confusion` is set and a Bearer RS256 token is supplied via `CredentialContext`).

**Requirements:** LAB-01 (Phase 96 chaos lab fuzz-target profile).
