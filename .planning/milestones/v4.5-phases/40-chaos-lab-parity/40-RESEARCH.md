# Phase 40: Chaos Lab Parity - Research

**Researched:** 2026-04-29
**Domain:** Documentation parity + bash dynamic profile derivation
**Confidence:** HIGH (filesystem-verified inventory; finding tags read directly from scanner source + per-lab `expected_results.md` files)

## Summary

Phase 40 is documentation + a ~20-line bash refactor in `lab.sh`. The four knowledge gaps are now resolved:

1. **Finding-tag style splits in two**: legacy listener profiles (v3 oracle convention) use SCREAMING_SNAKE oracle-only tags (`MODERN_TLS`, `CERT_RSA_1024`, `LDAP_TCP`, etc.) that are NOT emitted by the scanner — they are oracle labels. The v4.3+v4.4 scanners (DB, S3, Vault, Email, Broker) emit `protocol` + `service_detail` pairs (e.g. `protocol="POSTGRESQL"`, `service_detail="PostgreSQL/ssl-off"`) and risk_engine produces titled findings (e.g. `"Weak cipher suite on broker TLS endpoint"`). The v4 oracle should mix both styles per profile family — this matches what the per-lab `expected_results.md` files already do.
2. **18 profiles in compose**: `phaseA, cloud, identity, pki, jwt, registry, source, storage, ssh-weak, ldaps, dnssec, saml, kerberos, vault, database, storage-s3, email, broker` plus the implicit "core" (no profile = always-on). Lab.sh's hard-coded list is missing `vault, database, storage-s3, email, broker` (5 profiles).
3. **Dynamic parser**: docker-compose.yml uses ONLY the inline-array form `profiles: ["name"]` (verified — no list form exists today). `yq` is not currently a chaos-lab dependency. Recommend `grep+sed+sort -u` as the default; it works with bash + coreutils only and matches what the file actually contains. `yq` becomes a graceful enhancement, not a requirement.
4. **Starting state**: `lab.sh` has `ALL_PROFILES` at lines 63–66, `usage()` heredoc at lines 17–45, `case` block at lines 55–118. README is 28 lines. v3 oracle defines a clean `Port | Service | Expected protocol | Expected condition / tag | Notes` schema for listener rows. `docs/chaos-lab.md` covers profiles up through Phase 4 (v3.9-era) — it is missing all v4.3 and v4.4 profiles.

**Primary recommendation:** Use `grep -E '^\s*profiles:\s*\[' docker-compose.yml | grep -oE '"[a-z0-9-]+"' | tr -d '"' | sort -u` as the fallback parser. It handles only the inline-array form (which is all that exists). Use the v3 listener-row schema verbatim for v4.0–v4.2 profile sections in the v4 oracle. Use the per-lab `expected_results.md` files (`labs/email/expected_results.md`, `labs/broker/expected_results.md`, `labs/storage/expected_results.md`, `labs/vault/expected_results.md`, plus the v3 oracle's `Phase 27 — Database` section) as the source-of-truth for v4.3+v4.4 oracle sections — copy and reformat into D-06 category-tuned tables.

---

## Scanner Finding Tags

Two distinct conventions are in play. The planner must use the right one per profile family.

### Style A — Oracle-only SCREAMING_SNAKE labels (v4.0 / v4.1 / v4.2 listener profiles)

These tags appear in `expected_results_v3.md` and `docs/chaos-lab.md` Section 5 (Complete Port Reference) but are **not literal scanner output strings**. They are oracle conventions used by consultants to describe the expected scanner *classification*. The actual scanner output is a `CryptoEndpoint` row with `protocol`, `service_detail`, and (sometimes) `severity`. The v4 oracle should keep using these tags verbatim for v4.0–v4.2 sections — they are the de-facto shared vocabulary [VERIFIED: read v3 oracle + chaos-lab.md].

| Profile | Tag examples (carry over verbatim from v3 oracle) |
|---------|--------------------------------------------------|
| (core) | `MODERN_TLS`, `LEGACY_TLS`, `CERT_EXPIRED_OR_EXPIRING`, `CERT_SELFSIGNED`, `MTLS_REQUIRED`, `TLS_SLOW_PROXY`, `HTTP_ON_TLS_LIKE_PORT`, `PLAINTEXT_HTTP`, `SSH_BANNER`, `UNKNOWN_OPEN_PORT` |
| phaseA | `TLS_ON_ODD_PORT`, `HTTP_REDIRECT_302`, `UNKNOWN_OPEN_PORT_2`, `DB_PLAINTEXT_POSTGRES`, `DB_PLAINTEXT_REDIS`, `RABBITMQ_MGMT_HTTP`, `CERT_CHAIN_INCOMPLETE`, `CERT_RSA_1024`, `CERT_SHA1_SIG`, `INGRESS_SNI_*` |
| cloud | `CLOUD_AWS_LOCALSTACK_TLS`, `CLOUD_AZURITE_BLOB_TLS`, `CLOUD_AZURITE_QUEUE_TLS`, `CLOUD_AZURITE_TABLE_TLS` |
| identity | `IDP_TLS`, `PRIVATE_CA_TLS`, `LDAP_TCP`, `LDAP_ADMIN_HTTP`, `MTLS_REQUIRED` |
| pki | `MTLS_STEPCA` |
| jwt | `WEAK_QUANTUM`, `WEAK_KEY_SIZE`, `CRITICAL_NO_SIGNATURE` |
| registry | `OUTDATED_CRYPTO_LIB` |
| source | `WEAK_ALGORITHM`, `HARDCODED_KEY`, `WEAK_RANDOM`, `DEPRECATED_PROTOCOL` (semgrep rule classes) |
| storage (legacy) | (per-resource) `RSA_2048`, `RSA_1024`, `AES_256`, `ECC_P256`, `pgp_sym_encrypt (weak passphrase)` |
| ssh-weak | KEX/Hostkey/MAC algorithm names with `CRITICAL` / `WARNING` severity (e.g., `diffie-hellman-group1-sha1`, `ssh-dss`, `hmac-md5`) |
| ldaps | `CERT_SELFSIGNED` (TLS certificate chain finding via sslyze) |
| dnssec | `RSASHA1` weak-algo CRITICAL, `unsigned zone` HIGH, `NSEC` MEDIUM |
| saml | `RSA-1024 signing cert` CRITICAL, `SHA-1 algorithm URI` HIGH |
| kerberos | `weak etype: rc4-hmac` HIGH, `weak etype: aes128-cts-hmac-sha1-96` HIGH |

**Source files for these:**
- `quantum-chaos-enterprise-lab/expected_results_v3.md` (lines 8–267) [VERIFIED]
- `docs/chaos-lab.md` Section 5 (lines 339–386) [VERIFIED]

### Style B — Real scanner output strings (v4.3 / v4.4 profiles)

These are literal `protocol` + `service_detail` strings emitted by `CryptoEndpoint` rows, plus the `title` strings emitted by the `risk_engine` `evaluate_*_endpoints` functions. The v4 oracle's "Expected condition / tag" cells for these profiles MUST use these verbatim or scanner regression tests will not match.

#### `database` profile (Phase 27)

| Profile | Scanner file | protocol | service_detail | Severity | Triggered when |
|---------|--------------|----------|----------------|----------|----------------|
| database | `quirk/scanner/db_connector.py` L101 | `POSTGRESQL` | `PostgreSQL/ssl-off` | HIGH | `SHOW ssl` returns `'off'` (port 25432) |
| database | `quirk/scanner/db_connector.py` L137 | `POSTGRESQL` | `PostgreSQL/plaintext-connections-allowed (N non-SSL)` | HIGH | `pg_stat_ssl` shows non-SSL connections |
| database | `quirk/scanner/db_connector.py` L147 | `POSTGRESQL` | `PostgreSQL/ssl-enforced` | (none / informational) | All connections SSL |
| database | `quirk/scanner/db_connector.py` L227 | `MYSQL` | `MySQL/ssl-off` | HIGH | `SHOW STATUS LIKE 'Ssl_cipher'` empty (port 23306) |
| database | `quirk/scanner/db_connector.py` L236 | `MYSQL` | `MySQL/<cipher>-weak` | MEDIUM | Ssl_cipher present but weak prefix |
| database | `quirk/scanner/db_connector.py` L245 | `MYSQL` | `MySQL/<cipher>-ok` | (none) | Strong cipher |

**Note:** v3 oracle (lines 277, 287) also uses oracle-tag aliases `DB_POSTGRESQL_SSL_OFF` and `DB_MYSQL_SSL_OFF`. These are not in the scanner — they're aliases used by `docs/UAT-SERIES.md`. Recommend the v4 oracle show **both**: e.g. `DB_POSTGRESQL_SSL_OFF` (oracle alias) → `protocol=POSTGRESQL, service_detail=PostgreSQL/ssl-off` (literal). [VERIFIED via grep]

#### `storage-s3` profile (Phase 28)

| Profile | Scanner file | protocol | service_detail | Severity | Triggered when |
|---------|--------------|----------|----------------|----------|----------------|
| storage-s3 | `quirk/scanner/aws_connector.py` L252,263,268 | `S3` | `S3/unencrypted` | HIGH | Bucket has no SSE configured |
| storage-s3 | `quirk/scanner/aws_connector.py` L257 | `S3` | `S3/sse-s3` | (none) | SSE-S3 (AES256, S3-managed) |
| storage-s3 | `quirk/scanner/aws_connector.py` L260 | `S3` | `S3/sse-kms-aws` | MEDIUM | SSE-KMS with AWS-managed key |
| storage-s3 | `quirk/scanner/aws_connector.py` L261 | `S3` | `S3/sse-kms-cmk` | (none) | SSE-KMS with customer-managed key |

Lab seeds 2 buckets: `encrypted-bucket` (SSE-S3 → no finding) and `unencrypted-bucket` (HIGH `S3/unencrypted`). Evidence keys: `dar_storage_unencrypted_count`, `dar_storage_aws_managed_count`, `dar_storage_unencrypted_ratio`. [VERIFIED: `labs/storage/expected_results.md`]

#### `vault` profile (Phase 30, vault-30 on port 28200)

| Profile | Scanner file | protocol | service_detail | Severity | Triggered when |
|---------|--------------|----------|----------------|----------|----------------|
| vault | `quirk/scanner/vault_connector.py` L155,158 | `VAULT` | `transit/<key_name>` | MEDIUM (if exportable=True), else none | Transit key listed |
| vault | `quirk/scanner/vault_connector.py` L251,254 | `VAULT` | `PKI/<mount>` | HIGH | RSA<4096 root CA |
| vault | `quirk/scanner/vault_connector.py` L288,291 | `VAULT` | `PKI/<mount>:intermediate-N` | HIGH | Intermediate cert weak |
| vault | `quirk/scanner/vault_connector.py` L352,354 | `VAULT` | `auth/<path>` | HIGH (token), MEDIUM (userpass), variable | Auth method enabled |

Seeded resources from `labs/vault/expected_results.md`: `transit/rsa-2048-classification` (none), `transit/rsa-2048-exportable` (MEDIUM), `PKI/pki` (HIGH), `auth/token` (HIGH), `auth/userpass` (MEDIUM). Evidence: `dar_vault_weak_count` (counts only HIGH rows per D-11 of Phase 30). [VERIFIED]

#### `email` profile (Phase 32)

| Profile | Scanner file | protocol | service_detail | Severity | Triggered when |
|---------|--------------|----------|----------------|----------|----------------|
| email | `quirk/scanner/email_scanner.py` L499 | `SMTP-STARTTLS` / `SMTPS` / `IMAP-STARTTLS` / `IMAPS` / `POP3-STARTTLS` / `POP3S` | `<protocol_label>:<port>` | (set by risk_engine) | One row per port (25/465/587/143/993/110/995) |

Risk-engine titles (from `quirk/engine/risk_engine.py::evaluate_email_endpoints`):
- `"STARTTLS downgrade risk on SMTP"` — MEDIUM, only on port 25 (EMAIL-08)
- `"Weak cipher suite on email TLS endpoint"` — HIGH (EMAIL-09), per port with weak cipher
- `"Self-signed certificate"` — HIGH/MEDIUM (generic risk_engine, not email-specific)

Lab map (host:container): 30025:25, 30465:465, 30587:587, 30143:143, 30993:993, 30110:110, 30995:995. Postfix emits weak ciphers on TLSv1.2 (`TLS_RSA_WITH_ARIA_256_GCM_SHA384`, `AES128-SHA`, `AES256-SHA`). Dovecot defaults to TLS 1.3 → no weak-cipher findings without explicit TLS 1.2 pin (caveat documented in `labs/email/expected_results.md`). Expected counts: HIGH=3 weak-cipher (ports 25/465/587), MEDIUM=1 STARTTLS-downgrade (port 25). [VERIFIED]

#### `broker` profile (Phase 33)

| Profile | Scanner file | protocol | service_detail | Severity | Triggered when |
|---------|--------------|----------|----------------|----------|----------------|
| broker | `quirk/scanner/broker_scanner.py` L390 | `KAFKA-PLAIN` | `KAFKA-PLAIN:<port>` | HIGH (via risk_engine) | Plaintext Kafka listener (29092) |
| broker | `quirk/scanner/broker_scanner.py` L401 | `KAFKA-TLS` | `KAFKA-TLS:<port>` | HIGH (weak-cipher) | TLS Kafka with weak cipher (29093) |
| broker | `quirk/scanner/broker_scanner.py` L472 | `AMQP-PLAIN` | `AMQP-PLAIN:<port>` | HIGH | Plaintext RabbitMQ (25672) |
| broker | `quirk/scanner/broker_scanner.py` L482 | `AMQPS` | `AMQPS:<port>` | HIGH | Weak ciphers on AMQPS (25671) |
| broker | `quirk/scanner/broker_scanner.py` L674 | `REDIS-PLAIN` | `REDIS-PLAIN:<port>` | HIGH | Plaintext Redis (26379) |
| broker | `quirk/scanner/broker_scanner.py` L683 | `REDIS-TLS` | `REDIS-TLS:<port>` | HIGH | Weak ciphers on REDIS-TLS (26380) |

Risk-engine titles (from `evaluate_broker_endpoints`):
- `"Kafka plaintext listener detected"` — HIGH (KAFKA-02)
- `"AMQP plaintext listener detected"` — HIGH (RABBIT-02)
- `"Redis plaintext listener (no authentication)"` — HIGH (REDIS-02)
- `"Weak cipher suite on broker TLS endpoint"` — HIGH (KAFKA-01 + RABBIT-01 + REDIS-01)

Expected total: 6 HIGH findings. [VERIFIED: `labs/broker/expected_results.md`]

---

## Docker Compose Profile Inventory

Read directly from `quantum-chaos-enterprise-lab/docker-compose.yml` (1038 lines). Eighteen named profiles plus the implicit "no-profile" core service set. [VERIFIED filesystem 2026-04-29]

| # | Profile | Era | Services | Published Host Ports | One-line description |
|---|---------|-----|----------|---------------------|----------------------|
| 0 | (core, no profile) | v4.0 | tls-modern, tls-legacy, tls-expired, tls-selfsigned, tls-mtls-required, http-on-8444, legacy-http, ssh-alt, unknown-port, tls-slow-proxy | 443, 8443, 9443, 10443, 11443, 8444, 8000, 2222, 5555, 12443 | Always-on baseline TLS / HTTP / SSH chaos matrix |
| 1 | phaseA | v4.0 | tls-altport, http-redirect, unknown-port-2, postgres-plain, redis-plain, rabbitmq-mgmt, tls-missing-intermediate, tls-rsa1024, tls-sha1, ingress-sni, whoami (shared) | 15001, 18000, 5556, 15432, 16379, 15672, 13443, 14443, 15443, 24443 | Service-inventory expansion + TLS chain scenarios + SNI ingress |
| 2 | cloud | v4.0 | localstack (expose 4566), localstack-tls, azurite (expose 10000-10002), azurite-blob-tls, azurite-queue-tls, azurite-table-tls | 24566, 21000, 21001, 21002 | LocalStack S3/STS/IAM + Azurite (Blob/Queue/Table) behind TLS |
| 3 | identity | v4.0 | id-postgres (no host port), keycloak (expose 8080), keycloak-tls, step-ca, openldap, phpldapadmin, whoami, mtls-gateway | 15449, 19000, 13890, 18082, 16443 | Keycloak IdP + step-ca + OpenLDAP + mTLS gateway |
| 4 | pki | v4.0 | mtls-stepca-gateway (depends on identity profile's whoami + step-ca) | 17443 | step-ca-issued mTLS gateway |
| 5 | jwt | v4.1 | jwt-rs256, jwt-hs256, jwt-rsa1024, jwt-algnone | 20001, 20002, 20003, 20004 | 4 JWT microservices with weak alg configs (LAB-01 / SCAN-03) |
| 6 | registry | v4.1 | registry, registry-seed (init container) | 20005 | Docker Registry v2 + 3 seeded images with old crypto libs |
| 7 | source | v4.1 | gitea, gitea-seed (init) | 20006 | Gitea + seeded repos with crypto anti-patterns (semgrep target) |
| 8 | storage (legacy) | v4.1 | localstack-kms, localstack-kms-seed, vault (image hashicorp/vault:1.15), vault-seed, postgres-pgcrypto | 20007, 20009, 20010 | Legacy bucket: LocalStack KMS + dev-Vault + pgcrypto. **Predates the v4.3 split into clean `database`/`storage-s3`/`vault` profiles.** |
| 9 | ssh-weak | v4.1 | ssh-weak (custom build) | 20022 | OpenSSH 7.6p1 with deliberately weak KEX/hostkey/MAC algorithms |
| 10 | ldaps | v4.1 | ldaps (osixia/openldap with TLS enabled) | 636 | OpenLDAP over LDAPS on standard port 636 |
| 11 | dnssec | v4.2 | bind9-dnssec | 15353/udp, 15353/tcp | BIND9 with weak DNSSEC zones (RSASHA1) |
| 12 | saml | v4.2 | simplesamlphp | 8080 | simpleSAMLphp IdP with weak signing cert. **NOTE drift:** v3 oracle says port 8880 but compose binds 8080 — flag for the v4 oracle. |
| 13 | kerberos | v4.2 | samba-dc | 88, 389 | Samba AD-DC for Kerberos etype enumeration. **NOTE:** binds privileged 88 + 389 directly — collides with system DNS/LDAP if anything else listens. |
| 14 | vault | v4.3 (DAR) | vault-30 (image hashicorp/vault:1.17), vault-30-seed | 28200 | Dedicated Vault dev server for VAULT-01/02/03; intentionally on 28200 to NOT collide with legacy `storage`/vault on 20009 |
| 15 | database | v4.3 (DAR) | postgres-ssl-off, mysql-ssl-off | 25432, 23306 | PostgreSQL + MySQL with SSL explicitly disabled (DB-01, DB-02) |
| 16 | storage-s3 | v4.3 (DAR) | minio, minio-seed | 29000, 29001 | MinIO S3-compatible server; seed creates `encrypted-bucket` + `unencrypted-bucket` (STOR-01) |
| 17 | email | v4.4 | postfix-email, dovecot-email | 30025, 30465, 30587, 30143, 30993, 30110, 30995 | Postfix + Dovecot with weak RSA-2048 TLS / non-PFS / TLS 1.2 floor |
| 18 | broker | v4.4 | kafka-broker, rabbitmq-broker, redis-broker | 29092, 29093, 25672, 25671, 26379, 26380 | Kafka + RabbitMQ + Redis with intentional plaintext + weak-cipher TLS listeners |

**Drift / sharp edges to call out in the planner notes:**
- `whoami` is in **both** `identity` and `phaseA` profiles (line 473) — it's the only service with multiple profiles. Both profiles share the `phpldapadmin → openldap` and `mtls-gateway` topology assumption.
- `pki` profile depends on services from `identity` (step-ca, whoami) — must be brought up together. `docs/chaos-lab.md` line 415 already documents this.
- The legacy `storage` profile (v4.1) and the new `vault` profile (v4.3) BOTH ship a Vault container, but on different ports (20009 vs 28200) and different image versions (1.15 vs 1.17). Oracle should note both, with `storage` annotated "deprecated — see `database`/`storage-s3`/`vault`".
- SAML port mismatch (compose: 8080; v3 oracle: 8880) — v4 oracle must use **8080** (compose is the source of truth per D-14).
- `kerberos` uses unmapped privileged ports (88, 389) — not remapped to a 2xxxx range like everything else.

---

## Dynamic Profile Parser Recommendation

### What's actually in the compose file

Verified: every `profiles:` line in `docker-compose.yml` uses the inline-array form `profiles: ["name"]`. There are **zero** instances of the YAML list form (`profiles:\n  - name`). Several services declare two profiles: `profiles: ["identity", "phaseA"]` (line 473). [VERIFIED via direct file read]

### `yq` availability

`yq` is **not** referenced anywhere in the chaos lab tooling, current `lab.sh`, README, `docs/chaos-lab.md`, or any project skill / CLAUDE.md rule. Adding a `yq` requirement would be a new install burden on consultants. Recommend: **default to the grep parser; do not require yq**. Optionally add a `yq`-preferred branch if it's already on `$PATH`.

### Recommended bash snippet

```bash
# Derive ALL profiles from docker-compose.yml. Output: alphabetized, deduped, one per line.
# Preserves set -euo pipefail (no unbound vars; pipefail-safe — sort never fails on empty input).
_derive_all_profiles() {
  if command -v yq >/dev/null 2>&1; then
    # yq path: works for both inline-array and list forms (future-proof)
    yq eval '.. | select(has("profiles")) | .profiles[]' "${COMPOSE_FILE}" 2>/dev/null \
      | sort -u
  else
    # Fallback: only handles the inline-array form, which is all the file currently uses.
    # Pattern matches:  profiles: ["name"]   or   profiles: ["a", "b"]
    grep -E '^\s*profiles:\s*\[' "${COMPOSE_FILE}" \
      | grep -oE '"[a-z0-9_-]+"' \
      | tr -d '"' \
      | sort -u
  fi
}
```

### Usage in `all` and new `profiles` subcommand

```bash
all)
  mapfile -t _profiles < <(_derive_all_profiles)
  if [[ ${#_profiles[@]} -eq 0 ]]; then
    echo "❌ Could not derive profiles from ${COMPOSE_FILE}" >&2
    exit 1
  fi
  ALL_PROFILES=""
  for p in "${_profiles[@]}"; do ALL_PROFILES+=" --profile $p"; done
  echo "🔥 Starting ALL profiles: ${_profiles[*]}"
  PROFILE_ARGS="${ALL_PROFILES}" compose up -d
  echo "✅ Full chaos lab started."
  compose ps
  ;;
profiles)
  _derive_all_profiles
  ;;
```

### Portability notes

- `mapfile -t` requires bash 4+. macOS ships bash 3.2 by default but `lab.sh`'s shebang is `#!/usr/bin/env bash`, so users with Homebrew bash get 5.x. Existing lab.sh already assumes bash 4+ via heredoc patterns — no new constraint added. If macOS-stock-bash compatibility is required, replace `mapfile` with `while read` loop.
- `set -euo pipefail` is in effect (line 2). The snippet is safe: `command -v` cannot fail, `grep` returning no matches inside the pipeline does not break the pipeline (sort handles empty input).
- `sort -u` is POSIX, available everywhere.
- `grep -oE` is GNU/BSD compatible.

### Verification command for the planner

```bash
# Should print: broker, cloud, database, dnssec, email, identity, jwt, kerberos, ldaps,
#               phaseA, pki, registry, saml, source, ssh-weak, storage, storage-s3, vault
cd quantum-chaos-enterprise-lab
grep -E '^\s*profiles:\s*\[' docker-compose.yml | grep -oE '"[a-z0-9_-]+"' | tr -d '"' | sort -u
```

Expected: 18 lines. Note "core" services do not appear because they have no `profiles:` line (Compose treats no-profile services as always-on; they ship with every `up`).

---

## Starting-State Summary

### `quantum-chaos-enterprise-lab/lab.sh` (118 lines)

| Lines | Content | Edit needed |
|------:|---------|-------------|
| 1–9 | Shebang, `set -euo pipefail`, `.env` loader | Preserve |
| 11–14 | Config: `PROJECT_NAME`, `COMPOSE_FILE`, `PROFILE_ARGS` | Preserve |
| 17–45 | `usage()` heredoc (Commands, Options, Examples blocks) | **Edit:** add `profiles    Print all known profiles (one per line)` to Commands section, around line 26 |
| 47–50 | `compose()` wrapper | Preserve |
| 52–53 | `cmd="${1:-}"; shift \|\| true` | Preserve |
| 55–118 | `case "${cmd}"` block | **Edit:** rewrite `all` arm (lines 62–72) to use `_derive_all_profiles`; insert new `profiles)` arm before `down)` |
| (new) | Insert `_derive_all_profiles()` helper between line 50 and line 52 | **Add** |

The hard-coded `ALL_PROFILES=" --profile phaseA --profile cloud --profile identity --profile pki --profile jwt --profile registry --profile source --profile storage --profile ssh-weak --profile ldaps --profile dnssec --profile saml --profile kerberos"` at lines 63–66 is the broken list missing `vault, database, storage-s3, email, broker`. Replacing it with derivation eliminates the drift root cause (per D-14).

### `quantum-chaos-enterprise-lab/README.md` (28 lines)

| Lines | Content | Disposition |
|------:|---------|-------------|
| 1 | H1 title | Preserve |
| 3 | One-paragraph intro | Preserve / lightly edit |
| 5–10 | Quick Start docker compose example | Replace with cleaner Quick Start (D-08 §2) |
| 12–14 | Documentation pointer to docs/chaos-lab.md | Move into the new "Link block" (D-08 §4) |
| 16 | "Historical artifact" pointer to CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md | **Preserve verbatim** (D-08 §6) |
| 19–28 | Phase C (mTLS + step-ca) section with helper script invocations | **Preserve verbatim** (D-08 §5) |

**New sections to insert between the new Quick Start and the link block:** Profile Summary Table per D-09. Order: core → v4.0 (phaseA, cloud, identity, pki) → v4.1 (jwt, registry, source, storage, ssh-weak, ldaps) → v4.2 (dnssec, saml, kerberos) → v4.3 (database, storage-s3, vault) → v4.4 (email, broker).

### `quantum-chaos-enterprise-lab/expected_results_v3.md` (293 lines)

| Section | Lines | Use for v4 oracle |
|---------|------:|-------------------|
| Header | 1–4 | Schema reference; will get a top-of-file "superseded by expected_results_v4.md" note |
| Core baseline | 8–22 | **Copy verbatim** as the v4 oracle's "core" section |
| Phase A1/A2/A3 | 25–70 | **Copy verbatim** as `## Profile: phaseA` |
| Identity | 74–88 | **Copy verbatim** as `## Profile: identity` |
| (no pki section) | — | **Add new** — v3 oracle does not have a `pki` section. Use port 17443 / `MTLS_STEPCA` from `docs/chaos-lab.md` line 367. |
| Phase B (cloud) | 96–110 | **Copy verbatim** as `## Profile: cloud` |
| JWT | 114–127 | **Copy verbatim** as `## Profile: jwt` |
| Registry | 131–146 | **Copy verbatim** as `## Profile: registry` |
| Source | 150–165 | **Copy verbatim** as `## Profile: source` |
| Storage (legacy) | 169–185 | **Copy + add deprecation note** per D-06 hybrid schema |
| ssh-weak | 189–204 | **Copy verbatim** |
| ldaps | 208–220 | **Copy verbatim** |
| DNSSEC | 224–237 | **Copy verbatim** (note profile name in v3 oracle says `bind9` but compose name is `dnssec` — use `dnssec`) |
| SAML | 241–252 | **Copy + fix port (8880 → 8080) + fix profile name (`simpla-samlphp` → `saml`)** |
| Kerberos | 256–266 | **Copy + fix profile name (`samba-dc` → `kerberos`)** |
| Database (Phase 27) | 270–293 | **Reformat into D-06 category-tuned schema** (Port \| Service \| Engine \| Expected protocol \| TLS in Transit \| Encryption-at-Rest \| Expected condition / tag \| Notes) |
| (no storage-s3, vault, email, broker) | — | **NET-NEW** sections from `labs/storage/expected_results.md`, `labs/vault/expected_results.md`, `labs/email/expected_results.md`, `labs/broker/expected_results.md` |

Schema for listener rows (D-05) is already proven: `Port | Service | Expected protocol | Expected condition / tag | Notes`. Reuse verbatim.

### `docs/chaos-lab.md` (425 lines)

| Section | Lines | Edit needed |
|---------|------:|-------------|
| 1. Overview | 3–18 | Light edit: §1 still says "Phase 4 scanner coverage (JWT, container registry, source code, cloud storage, legacy SSH, and LDAPS)" — outdated. Add v4.2/v4.3/v4.4 categories |
| 1. Overview (intro) | line 5 area | **Add D-12 pointer:** "For UAT-grade expected scanner findings, see `quantum-chaos-enterprise-lab/expected_results_v4.md`." |
| 2. Quick Start | 22–38 | Light edit: the "all Phase 4 profiles" example (line 32) should be replaced with `./lab.sh all` reference |
| 3.1–3.11 | 44–324 | Existing per-profile sections, well-formatted. Keep as-is |
| (new) 3.12 dnssec | — | **Add** (currently missing) |
| (new) 3.13 saml | — | **Add** (currently missing — fix port 8080 vs 8880 here too) |
| (new) 3.14 kerberos | — | **Add** (currently missing) |
| (new) 3.15 vault (v4.3) | — | **Add** — point at `labs/vault/expected_results.md` |
| (new) 3.16 database (v4.3) | — | **Add** — point at `expected_results_v3.md` Phase 27 section (or new v4 oracle once written) |
| (new) 3.17 storage-s3 (v4.3) | — | **Add** — point at `labs/storage/expected_results.md` |
| (new) 3.18 email (v4.4) | — | **Add** — point at `labs/email/expected_results.md` |
| (new) 3.19 broker (v4.4) | — | **Add** — point at `labs/broker/expected_results.md` |
| 4. Starting Multiple Profiles | 326–336 | Light edit: add example using new `./lab.sh profiles` subcommand |
| 5. Complete Port Reference | 339–386 | **Append rows** for the missing 9 profiles' worth of ports (28200, 25432, 23306, 29000, 29001, 30025-30995, 29092-29093, 25672, 25671, 26379, 26380, 88, 389, 15353, 8080, and the dnssec UDP ports) |
| 6. Troubleshooting | 389–420 | Preserve. Optionally add v4.3+v4.4 entries (vault-30 on 28200, MinIO console on 29001, etc.) |
| 7. Historical Reference | 423–425 | Preserve |

Also note: `docs/chaos-lab.md` Section 5 line 366 has `MTLS_REQUIRED` listed for both `mtls-gateway` (port 16443, identity) and `tls-mtls-required` (port 11443, core). Same tag, two services — that's accurate; don't "fix" it.

---

## Open Questions for Planner

1. **`storage` (legacy) profile annotation wording.** D-06 + Claude's-Discretion both flag this. Recommend: a top-of-section note saying "**Deprecated** — split in v4.3 into `database` (PostgreSQL/MySQL SSL detection), `storage-s3` (MinIO/S3 buckets), and `vault` (Vault transit/PKI/auth audit). Retained for backwards compatibility with v4.1 / v4.2 UAT runs." Planner can refine.
2. **Whether to add a v4 oracle "core (no profile)" section.** D-02 lists v4.0 baseline as `phaseA, cloud, identity, pki` but the v3 oracle's "Core — Baseline Chaos Matrix" (10 always-on services) is not in that list. The planner should clarify with the user — strictly per D-02 the core baseline isn't in the v4 oracle, but operationally consultants will look for `tls-modern` etc. Recommend: include core as an unnamed-profile section at the top with `Profile: (core / always-on)`.
3. **Profile Summary Table anchor format.** D-11 says README rows link to `## Profile: <name>` anchors. GitHub renders `## Profile: storage-s3` as `#profile-storage-s3` — confirm the planner uses GitHub's anchor convention (lowercase, dashes for non-alphanumeric, colons stripped) and tests one link.
4. **Whether the `kerberos` profile's privileged-port binding (88, 389) is OK as-is or should be remapped.** This is out-of-scope per "no compose changes" but the oracle/README should explicitly call it out so consultants don't try to run it alongside system DNS/AD.
5. **SAML port drift (compose: 8080, v3 oracle: 8880).** Treating compose as source of truth (correct per D-14). But if 8080 collides with the user's local Keycloak (which uses 8080 internally — though Keycloak is `expose: 8080` not `ports:`), there could be a real conflict. Planner should verify by booting `--profile saml` alongside `--profile identity` and noting the result.

---

## Sources

### Primary (HIGH confidence — filesystem-verified 2026-04-29)
- `quantum-chaos-enterprise-lab/docker-compose.yml` (1038 lines) — profile / service / port ground truth
- `quantum-chaos-enterprise-lab/lab.sh` (118 lines) — current state of script being edited
- `quantum-chaos-enterprise-lab/README.md` (28 lines) — current stub being rewritten
- `quantum-chaos-enterprise-lab/expected_results_v3.md` (293 lines) — schema source + v4.0–v4.2 content to carry forward
- `docs/chaos-lab.md` (425 lines) — full prose authority being extended
- `quirk/scanner/db_connector.py` (260 lines) — POSTGRESQL/MYSQL service_detail strings
- `quirk/scanner/email_scanner.py` (608 lines) — SMTP/IMAP/POP3 protocol labels
- `quirk/scanner/broker_scanner.py` (719 lines) — KAFKA/AMQP/REDIS service_detail strings
- `quirk/scanner/vault_connector.py` (466 lines) — VAULT transit/PKI/auth service_detail strings
- `quirk/scanner/aws_connector.py` (S3/* service_detail strings)
- `labs/storage/expected_results.md`, `labs/vault/expected_results.md`, `labs/email/expected_results.md`, `labs/broker/expected_results.md` — authoritative v4.3+v4.4 finding tables

### Project rules (HIGH)
- `CLAUDE.md` §"Chaos Lab Maintenance" — the rule this phase implements structurally
- `CLAUDE.md` §"Mandatory Phase Completion Steps" — Obsidian + UAT-SERIES sync requirements
- `.planning/REQUIREMENTS.md` LAB-01..04 (lines 60–63) — phase requirement source statements
- `.planning/phases/40-chaos-lab-parity/40-CONTEXT.md` (D-01 through D-19) — locked decisions

## Metadata

**Confidence breakdown:**
- Scanner finding tags: HIGH — read directly from scanner source + per-lab oracle files
- Profile inventory: HIGH — direct compose file enumeration
- Bash parser: HIGH — verified inline-array form is the only form present
- Starting-state summary: HIGH — line numbers verified

**Research date:** 2026-04-29
**Valid until:** Until docker-compose.yml changes (which under D-14 will trigger structural drift in lab.sh — but README + oracle will need a manual sync trigger per CLAUDE.md "Chaos Lab Maintenance")

## RESEARCH COMPLETE
