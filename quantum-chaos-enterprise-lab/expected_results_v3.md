# Crypto Chaos Enterprise Lab — Expected Results v3

This file is the **source of truth** (“oracle”) for what the lab should expose and how a scanner should classify it.
Host assumed: `127.0.0.1`

---

## Core — Baseline Chaos Matrix

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 443 | tls-modern | TLS | MODERN_TLS | TLS 1.3 typically negotiates |
| 8443 | tls-legacy | TLS | LEGACY_TLS | May negotiate TLS 1.2 on modern OpenSSL |
| 9443 | tls-expired | TLS | CERT_EXPIRED_OR_EXPIRING | Cert validity failure/near-expiry datapoint |
| 10443 | tls-selfsigned | TLS | CERT_SELFSIGNED | Untrusted/self-signed datapoint |
| 11443 | tls-mtls-required | TLS | MTLS_REQUIRED | Handshake blocked without client cert |
| 12443 | tls-slow-proxy | TLS | TLS_SLOW_PROXY | Useful for timeout/concurrency testing |
| 8444 | http-on-8444 | HTTP | HTTP_ON_TLS_LIKE_PORT | Wrong protocol on “TLS-like” port |
| 8000 | legacy-http | HTTP | PLAINTEXT_HTTP | Hygiene datapoint |
| 2222 | ssh-alt | SSH | SSH_BANNER | Non-standard SSH port |
| 5555 | unknown-port | UNKNOWN | UNKNOWN_OPEN_PORT | Open port with ambiguous protocol |

---

## Phase A1 — Service Inventory Expansion (profile: phaseA)

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 15001 | tls-altport | TLS | TLS_ON_ODD_PORT | TLS listener on non-standard port |
| 18000 | http-redirect | HTTP | HTTP_REDIRECT_302 | Should return 302 Location header |
| 5556 | unknown-port-2 | UNKNOWN | UNKNOWN_OPEN_PORT_2 | Second unknown service |
| 15432 | postgres-plain | UNKNOWN (non-HTTP) | DB_PLAINTEXT_POSTGRES | TCP service, not HTTP/TLS by default |
| 16379 | redis-plain | UNKNOWN (non-HTTP) | DB_PLAINTEXT_REDIS | TCP service, not HTTP/TLS by default |
| 15672 | rabbitmq-mgmt | HTTP | RABBITMQ_MGMT_HTTP | HTTP UI (proxy target for ingress) |

**Notes**
- For DB services (Postgres/Redis) the classifier may label as `UNKNOWN` unless you implement protocol-specific probing. That’s fine — it’s a datapoint for “non-HTTP services in inventory.”

---

## Phase A2 — TLS Chain Scenarios (profile: phaseA)

| Port | Service | Expected protocol | Expected condition / tag | Notes |
|---:|---|---|---|---|
| 13443 | tls-missing-intermediate | TLS | CERT_CHAIN_INCOMPLETE | Leaf presented without required intermediate |
| 14443 | tls-rsa1024 | TLS | CERT_RSA_1024 | Weak RSA key size |
| 15443 | tls-sha1 | TLS | CERT_SHA1_SIG | SHA1-signed cert (legacy) |

**Notes**
- Some clients may treat SHA1 as unacceptable; this is intended for detection.

---

## Phase A3 — Ingress / SNI (multi-vhost behind single TLS port) (profile: phaseA)

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

## Identity Stack (profile: identity)

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

## High-level expectations for a scanner/report
- TLS ports must **never** be misclassified as plaintext HTTP because an HTTPS listener returns an HTTP error (e.g., “plain HTTP request was sent to HTTPS port”).
- `8444` and `8000` should be classified as **HTTP plaintext**.
- mTLS endpoints should be classified as **TLS present, handshake blocked** (not “plain HTTP”).
- Ingress port `24443` should be recognized as **one TLS termination point** servicing multiple hostnames (SNI).

## Phase B — Cloud Simulators (profile: cloud)

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



## Phase 4 — JWT Profile (profile: jwt)

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



## Phase 4 — Registry Profile (profile: registry)

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



## Phase 4 — Source Profile (profile: source)

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



## Phase 4 — Storage Profile (profile: storage)

| Service | Port | Resource | Expected Finding | Notes |
|---------|------|---------|-----------------|-------|
| LocalStack KMS | 20007 | SYMMETRIC_DEFAULT key | AES_256 (quantum-vulnerable via Grover) | KMS key spec maps to AES-256 |
| LocalStack KMS | 20007 | RSA_2048 key | RSA_2048 (quantum-vulnerable) | RSA signing key |
| LocalStack KMS | 20007 | ECC_NIST_P256 key | ECC_P256 (quantum-vulnerable) | ECDSA signing key |
| Vault | 20009 | transit/keys/rsa-2048 | RSA_2048 (quantum-vulnerable) | Vault transit engine key |
| Vault | 20009 | transit/keys/rsa-1024 | RSA_1024 (weak + quantum-vulnerable) | Weak RSA key size |
| Vault | 20009 | transit/keys/aes256 | AES_256 (quantum-vulnerable via Grover) | Symmetric key |
| postgres-pgcrypto | 20010 | encrypted_demo table | pgp_sym_encrypt (weak passphrase) | MD5 salt = finding |

**Scanner validation command:**
```
quirk scan --cloud aws --endpoint http://localhost:20007
```
**Expected:** AWS connector returns >= 3 KMS keys with key spec classifications.



## Phase 4 — SSH-Weak Profile (profile: ssh-weak)

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



## Phase 4 — LDAPS Profile (profile: ldaps)

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



## Phase 25 — DNSSEC Profile (profile: bind9)

| Zone | Algorithm | Algorithm ID | Expected Finding | Severity |
|------|-----------|-------------|-----------------|----------|
| weak.example.com | RSASHA1 | 5 | DNSSEC weak signing algorithm (SHA-1 collision-vulnerable) | CRITICAL |
| weak.example.com | RSASHA1-NSEC3-SHA1 | 7 | DNSSEC weak signing algorithm (SHA-1) | CRITICAL |
| unsigned.example.com | NONE | — | Unsigned zone — DNS responses are unauthenticated | HIGH |
| nsec.example.com | ECDSAP256SHA256 | 13 | NSEC zone enumeration exposure | MEDIUM |

**Scanner validation command:**
```
docker compose --profile bind9 up -d && sleep 5 && quirk scan --targets weak.example.com unsigned.example.com nsec.example.com
```
**Expected:** DNSSEC scanner returns >= 1 CRITICAL finding (RSASHA1) for weak.example.com, 1 HIGH finding (unsigned zone) for unsigned.example.com, and 1 MEDIUM finding (NSEC) for nsec.example.com. ECDSAP256SHA256 zones produce no algorithm severity finding.



## Phase 25 — SAML/OIDC Profile (profile: simpla-samlphp)

| Port | Service | Certificate | Expected Finding | Severity |
|-----:|---------|-------------|-----------------|----------|
| 8880 | simpla-samlphp | RSA-1024 signing cert | Weak SAML signing certificate: RSA-1024 | CRITICAL |
| 8880 | simpla-samlphp | SHA-1 algorithm URI | SHA-1 algorithm URI detected in SAML metadata | HIGH |

**Scanner validation command:**
```
docker compose --profile simpla-samlphp up -d && sleep 10 && quirk scan --targets http://localhost:8880/simplesaml/saml2/idp/metadata.php
```
**Expected:** SAML scanner returns 1 CRITICAL finding for RSA-1024 signing certificate and optionally 1 HIGH finding if SHA-1 algorithm URI is present in metadata. Findings appear in the Identity tab (source="saml"), not the Findings tab.



## Phase 25 — Kerberos Profile (profile: samba-dc)

| Port | Service | Etype ID | Etype Name | Expected Finding | Severity |
|-----:|---------|---------|-----------|-----------------|----------|
| 88 | samba-dc | 23 | rc4-hmac | Kerberos weak etype: rc4-hmac | HIGH |
| 88 | samba-dc | 17 | aes128-cts-hmac-sha1-96 | Kerberos weak etype: aes128-cts-hmac-sha1-96 | HIGH |

**Scanner validation command:**
```
docker compose --profile samba-dc up -d && sleep 15 && quirk scan --targets localhost:88
```
**Expected:** Kerberos scanner returns >= 1 HIGH finding for RC4-HMAC (etype 23). AES-256 (etype 18/20) produces no weakness finding. Findings appear in the Identity tab (source="kerberos").