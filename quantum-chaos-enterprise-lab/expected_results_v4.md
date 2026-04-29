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

<!-- DAR / messaging profile sections appended by plan 40-03 below this line -->
