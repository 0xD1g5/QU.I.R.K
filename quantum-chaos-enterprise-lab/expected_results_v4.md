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
git clone http://localhost:20006/admin/crypto-antipatterns-python && cd crypto-antipatterns-python && semgrep --config p/cryptography .
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

## Profile: storage

**Deprecated** — split in v4.3 into `database` (PostgreSQL/MySQL SSL detection), `storage-s3` (MinIO/S3 buckets), and `vault` (Vault transit/PKI/auth audit). Retained for backwards compatibility with v4.1 / v4.2 UAT runs. Predates the clean per-resource split.

```bash
PROFILE_ARGS="--profile storage" ./lab.sh up
```

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|-----:|---------|-------------------|--------------------------|-------|
| 20007 | localstack-kms | HTTPS | LocalStack KMS endpoint | KMS key seed via localstack-kms-seed |
| 20009 | vault (legacy, image 1.15) | HTTPS | Vault dev mode | Predates the v4.3 vault profile on 28200 |
| 20010 | postgres-pgcrypto | POSTGRESQL | pgcrypto extension probe target | DB-side encryption-at-rest demo |

**Config-introspection findings (per `labs/storage/expected_results.md`):**
- LocalStack KMS keys: `RSA_2048`, `RSA_1024`, `AES_256`, `ECC_P256` finding tags (per-key)
- postgres-pgcrypto: `pgp_sym_encrypt (weak passphrase)` finding tag

**Reference:** See `labs/storage/expected_results.md` for full per-resource detail. v4.3 successors give cleaner per-category coverage.

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
