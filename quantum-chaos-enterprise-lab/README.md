# QU.I.R.K. Chaos Lab

A Docker-Compose-based crypto-misconfiguration playground used by QU.I.R.K. for end-to-end scanner UAT. Nineteen named profiles plus an always-on core baseline cover TLS / SSH / JWT / container / source / cloud / DAR / messaging / PQC chaos scenarios — each with an expected-findings oracle in `expected_results_v4.md` and detailed prose in `docs/chaos-lab.md`.

## Lab certificates

`ca.key`, `ca.crt`, `client.key`, and `client.crt` are **not committed** to the
repository (Phase 120-02, PUBREPO-LAB-KEYS). They are generated on first
`./lab.sh up` (or `./lab.sh all`) by the `ensure_lab_certs` function in
`lab.sh` as self-signed fixtures — functionally equivalent to the prior
committed pair. Regeneration is idempotent: subsequent `up` invocations
re-use the existing files. To force a re-roll, delete the four files (plus
`ca.srl`) and re-run `./lab.sh up`.

These are self-signed lab fixtures only; they have **no production trust
path** and must never be reused outside the chaos lab.

Other scenario keys (`modern.key`, `legacy.key`, `expired.key`, `mtls.key`,
`keycloak.key`, `selfsigned.key`, `scenarios/**/*.key`) remain tracked as
intentional chaos fixtures (weak RSA, expired validity, SHA-1, etc.) with
no real-world security value.

## Quick Start

```bash
# Start the always-on baseline only (10 services: ports 443, 8443, 9443, 10443, 11443, 8444, 8000, 2222, 5555, 12443)
./lab.sh up

# Start every shipped profile (18 named profiles + core)
./lab.sh all

# Start a specific profile
PROFILE_ARGS="--profile identity" ./lab.sh up

# List all available profiles (read live from docker-compose.yml)
./lab.sh profiles
```

## Profile Summary

| Profile | Services / What it ships | Published Ports | Expected Findings | Notes |
|---------|--------------------------|-----------------|-------------------|-------|
| core | tls-modern, tls-legacy, tls-expired, tls-selfsigned, tls-mtls-required, http-on-8444, legacy-http, ssh-alt, unknown-port, tls-slow-proxy | 443, 8443, 9443, 10443, 11443, 8444, 8000, 2222, 5555, 12443 | [Expected Findings](expected_results_v4.md#profile-core) | v4.0; always-on, no `--profile` flag needed |
| phaseA | tls-altport, http-redirect, unknown-port-2, postgres-plain, redis-plain, rabbitmq-mgmt, tls-missing-intermediate, tls-rsa1024, tls-sha1, ingress-sni, whoami | 15001, 18000, 5556, 15432, 16379, 15672, 13443, 14443, 15443, 24443 | [Expected Findings](expected_results_v4.md#profile-phasea) | v4.0 |
| cloud | localstack, localstack-tls, azurite, azurite-blob-tls, azurite-queue-tls, azurite-table-tls | 24566, 21000, 21001, 21002 | [Expected Findings](expected_results_v4.md#profile-cloud) | v4.0 |
| identity | id-postgres, keycloak, keycloak-tls, step-ca, openldap, phpldapadmin, whoami, mtls-gateway | 15449, 19000, 13890, 18082, 16443 | [Expected Findings](expected_results_v4.md#profile-identity) | v4.0 |
| pki | mtls-stepca-gateway | 17443 | [Expected Findings](expected_results_v4.md#profile-pki) | v4.0; depends on `identity` profile |
| jwt | jwt-rs256, jwt-hs256, jwt-rsa1024, jwt-algnone | 20001, 20002, 20003, 20004 | [Expected Findings](expected_results_v4.md#profile-jwt) | v4.1 |
| registry | registry, registry-seed | 20005 | [Expected Findings](expected_results_v4.md#profile-registry) | v4.1 |
| source | gitea, gitea-seed | 20006 | [Expected Findings](expected_results_v4.md#profile-source) | v4.1 |
| ssh-weak | ssh-weak | 20022 | [Expected Findings](expected_results_v4.md#profile-ssh-weak) | v4.1 |
| ldaps | ldaps, ldaps-codesign-seed | 636 | [Expected Findings](expected_results_v4.md#profile-ldaps) | v4.1; bitnamilegacy/openldap:2.6.10-debian-12-r4 (macOS-compat 2026-05-15). v5.1 Phase 95 (LAB-01): code-signing fixture added — `ldaps-codesign-seed` sidecar seeds `uid=codesign-weak` (RSA-1024/SHA-1 + CodeSigning EKU) under `dc=chaos,dc=local`. Idempotent sidecar (`ldapadd -c`, swallows exit 68). Use `--inventory-code-signing` flag to scan. |
| dnssec | bind9-dnssec | 15353/udp, 15353/tcp | [Expected Findings](expected_results_v4.md#profile-dnssec) | v4.2 |
| saml | simplesamlphp | 8080 | [Expected Findings](expected_results_v4.md#profile-saml) | v4.2; note: port 8080 — avoid running alongside `identity` (Keycloak exposes 8080 internally) |
| kerberos | samba-dc | 88, 389 | [Expected Findings](expected_results_v4.md#profile-kerberos) | v4.2; privileged ports — collides with system DNS/AD if anything else listens on 88/389. **macOS:** `./lab.sh all` skips this profile automatically because the OS-level KDC binds `*:88`. Set `LAB_INCLUDE_KERBEROS=1` to opt in (requires stopping the system KDC first). Tracked for full host-port remap under BACK-89. |
| database | postgres-ssl-off, mysql-ssl-off | 25432, 23306 | [Expected Findings](expected_results_v4.md#profile-database) | v4.3 (DAR) |
| storage-s3 | minio, minio-seed | 29000, 29001 | [Expected Findings](expected_results_v4.md#profile-storage-s3) | v4.3 (DAR) |
| vault | vault-30 (1.17), vault-30-seed | 28200 | [Expected Findings](expected_results_v4.md#profile-vault) | v4.3 (DAR); independent of legacy `storage` profile |
| email | postfix-email, dovecot-email | 30025, 30465, 30587, 30143, 30993, 30110, 30995 | [Expected Findings](expected_results_v4.md#profile-email) | v4.4 |
| broker | kafka-broker, rabbitmq-broker, redis-broker | 29092, 29093, 25672, 25671, 26379, 26380 | [Expected Findings](expected_results_v4.md#profile-broker) | v4.4 |
| tls-cert-defects | tls-cert-expired, tls-cert-selfsigned, tls-cert-untrusted-ca, tls-cert-rsa1024 | 13444, 13445, 13446, 13447 | [Expected Findings](expected_results_v4.md#profile-tls-cert-defects) | v4.6 (Phase 46); single-profile target exercising TLS-FIND-01..05 cert-defect findings end-to-end |
| smime | smime-openldap, smime-seed | 38900 | [Expected Findings](expected_results_v4.md#profile-smime) | v4.10 (Phase 79); OpenLDAP seeded with alice/bob/carol userSMIMECertificate fixtures (RSA-1024/SHA-1, RSA-1024/SHA-256, RSA-2048/SHA-256). Plain LDAP only — LDAPS deferred per D-79-R9. Idempotent seed sidecar (`ldapadd -c`, swallows exit 68). |
| adcs | adcs-openldap, adcs-seed | 38910 | [Expected Findings](expected_results_v4.md#profile-adcs) | v4.10 (Phase 80); OpenLDAP seeded with msPKI schema + three certificate template fixtures (BadTemplate-ESC1, BadTemplate-ESC4, SafeTemplate) + a SHA-1-signed RSA-1024 fake CA (QuirkLabCA). Schema loaded via Bitnami `LDAP_CUSTOM_SCHEMA_DIR` (Plan 80-01 deviation; ldapadd cn=config + Dockerfile fallbacks committed but inactive). Plain LDAP only. Authenticated SIMPLE bind for real-AD parity; anonymous bind permitted in lab. Idempotent seed sidecar (`ldapadd -c`, swallows exit 68). Read-only enumeration only — no enrollment, no CSR, no writes (ADCS-09). |
| postgres-tls | postgres-tls | 39432 | [Expected Findings](expected_results_v4.md#profile-postgres-tls) | v5.0 Phase 89 (LAB-01); PostgreSQL STARTTLS with weak RSA key-exchange ciphers (AES128-SHA:AES256-SHA, TLS 1.2 only). sslyze POSTGRES STARTTLS probe on 39432. |
| redis-tls | redis-tls | 39380, 39379 | [Expected Findings](expected_results_v4.md#profile-redis-tls) | v5.0 Phase 89 (LAB-02); Standalone Redis TLS with 3DES+RSA ciphers (DES-CBC3-SHA:AES128-SHA:AES256-SHA, TLS 1.2 only) on TLS port 39380; plaintext port 39379. broker_scanner.py Redis-TLS probe. |
| kafka-tls | kafka-tls | 39093, 39092 | [Expected Findings](expected_results_v4.md#profile-kafka-tls) | v5.0 Phase 89 (LAB-04); Standalone Kafka (apache/kafka:3.9.0) with RSA key-exchange ciphers (TLS_RSA_WITH_AES_128/256_CBC_SHA, TLS 1.2 only) on TLS port 39093; plaintext listener 39092. broker_scanner.py Kafka probe. |
| grpc-tls | grpc-tls | 39443 | [Expected Findings](expected_results_v4.md#profile-grpc-tls) | v5.0 Phase 89 (LAB-05); Minimal Go gRPC server (grpc-go ALPN h2) with RSA-2048 self-signed cert. sslyze direct TLS probe on 39443. D-03 empirical gate PASSED — sslyze negotiates ALPN h2 endpoint successfully. |
| oqs-nginx | oqs-nginx | 39444 | [Expected Findings](expected_results_v4.md#profile-oqs-nginx) | v5.0 Phase 90 (PQC-01); digest-pinned openquantumsafe/nginx serving TLS 1.3 with X25519MLKEM768 hybrid key-exchange and ML-DSA-65 certificate. Agility ceiling anchor for D-04 before/after demo. Needs `--allow-internal-targets` for live scan (loopback bind). |
| fuzz-target | fuzz-target | 20100 | [Expected Findings](expected_results_v4.md#profile-fuzz-target) | v5.1 (Phase 96 LAB-01); Deliberately-weak FastAPI REST service: no HSTS, http:// server URL in OpenAPI spec, /probe accepts forged HS256 JWT (alg-confusion target), /.well-known/jwks.json exposes RS256 public key. lab.sh ALL_PROFILES needs no edit — _derive_all_profiles discovers fuzz-target dynamically. |
| hwcompat | hwcompat-ssh, hwcompat-http | 20221, 20222 | [Expected Findings](expected_results_hwcompat.md) | v5.7 (Phase 127 HWCOMPAT-02); Hardware fingerprinting validation — advisory-only, no score impact (D-01). hwcompat-ssh (port 20221): OpenSSH banner → vendor=Unknown (D-06: never suppressed). hwcompat-http (port 20222): nginx serving X-Device-Model: HPE-iLO5 header + iLO/5.0 Server → vendor=HPE, model=iLO5, confidence=high. Both images pinned (CHAOS-05). lab.sh _derive_all_profiles() auto-discovers — no ALL_PROFILES edit needed (D-15). |

## Distributed Topology

The distributed topology (`docker-compose.distributed.yml`) validates the v5.4 multi-segment
distributed sensor architecture (MERGE-03). It is NOT a named profile in `docker-compose.yml`
and does NOT appear in `ALL_PROFILES` — it is a structurally separate compose file with its
own `lab.sh distributed` command arm.

### Network Layout

Three distinct bridge networks are used. Docker enforces that no two user-defined bridge
networks may share a subnet on a single daemon, so each segment uses a distinct CIDR:

| Network | Subnet | Purpose |
|---------|--------|---------|
| `segment-a` | `10.10.0.0/24` | Segment A — `tls-target-a` + `sensor-a` |
| `segment-b` | `10.20.0.0/24` | Segment B — `tls-target-b` + `tls-weak-b` + `sensor-b` |
| `console-net` | `10.30.0.0/24` | Console management — `console` + sensor push paths |

Each TLS target carries the DNS alias `crypto.internal` on **its own segment network only**.
Docker per-network embedded DNS means `sensor-a` (on segment-a) resolves `crypto.internal`
to `tls-target-a`, and `sensor-b` (on segment-b) resolves it to `tls-target-b` — neither
sensor can reach the other segment's target. Both sensors scan `crypto.internal:443` and
record `host="crypto.internal"` verbatim (`tls_scanner.py:188-189`, `:351-352`), producing
two distinct `CryptoEndpoint` rows in the merged CBOM differing only by `sensor_id`.

**v5.5 LAB-01 addition:** `segment-b` gains a second target, `tls-weak-b` (`10.20.0.20`),
running nginx:1.28.0 with `nginx/legacy/nginx.conf` (TLS 1.0/1.1 + HIGH:MEDIUM ciphers).
sensor-b mounts `sensor-config-b.yaml` which includes `10.20.0.20` in `include_ips`, so
sensor-b scans both the modern (`crypto.internal:443`) and weak-TLS (`10.20.0.20:443`)
targets. sensor-a cannot reach `10.20.0.20` — segment isolation is preserved. This enables
the Phase 111 per-segment score/filter to be exercised end-to-end (Test 7 in `distributed-e2e.sh`).

### Commands

```bash
# Build images and start all distributed services
./lab.sh distributed up

# Run enroll→push→merge end-to-end orchestration
./lab.sh distributed e2e

# Stop and remove distributed containers
./lab.sh distributed down

# Show running distributed container status
./lab.sh distributed status

# Tail logs for a specific service
./lab.sh distributed logs console
./lab.sh distributed logs sensor-a
./lab.sh distributed logs sensor-b
```

### Expected Findings

See the full oracle (service table, E2E outcome, MERGE-03 rationale):
[Expected Findings — Distributed Topology](expected_results_distributed.md#topology-distributed)

The `ALL_PROFILES` sweep in `lab.sh all` is unaffected — it covers only `docker-compose.yml`.

---

### Image Pin Policy

All services in `docker-compose.yml` carry an explicit version tag because floating tags (`:latest`, `:8`, `:3`) are silently advanced by Docker Hub, which is exactly what broke four services at once and was discovered under Phase 999.83 / BACK-90.

- Major-only tags (e.g. `mysql:8`, `nginx:1`, `postgres:15`) are NOT acceptable — Docker Hub re-points them across breaking minor releases.
- Minor or dated pins ARE acceptable — e.g. `mysql:8.0`, `gitea/gitea:1.21`, `hashicorp/vault:1.17`, `minio/minio:RELEASE.YYYY-MM-DDTHH-MM-SSZ`.
- When upgrading a pin, treat it as a chaos-lab maintenance change per CLAUDE.md: update `lab.sh` / `README.md` / `expected_results_v4.md` together in the same commit if behavior changes.

Pins enforced this phase: `gitea/gitea:1.21` (unchanged), `minio/minio:RELEASE.2025-09-07T16-13-09Z` (newly pinned from `:latest`), `mysql:8.0` (newly pinned from `:8`), and legacy `hashicorp/vault:1.15` deleted along with the deprecated `storage` profile.

**Phase 82-01 image-pin sweep (2026-05-16, CHAOS-05):** Every remaining floating tag or bare image reference promoted to a specific minor/patch version. Notable changes: `nginx:stable → 1.28.0`, `httpd:2.4 → 2.4.63`, `postgres:16 → 16.6`, `postgres:15 → 15.10`, `mysql:8.0 → 8.0.40`, `redis:7-alpine → 7.4.1-alpine`, `rabbitmq:3-management → 3.13.7-management`, `haproxy:latest → 3.0.5`, `localstack/localstack:3 → 3.8.1`, `azurite → 3.33.0`, `step-ca → 0.28.1`, `registry:2 → 2.8.3`, `docker:24-dind → 24.0.9-dind`, `gitea/gitea:1.21 → 1.21.11`, `alpine → 3.20`, `simplesamlphp → 1.19.7`, `minio/mc:latest → RELEASE.2024-11-21T17-21-54Z`, `lscr.io/linuxserver/openssh-server → 9.9_p2-r0-ls180`. The identity-profile `osixia/openldap:1.5.0` and `osixia/phpldapadmin:0.9.0` pins were left as-is — both upstreams are unmaintained, and migration is out of scope for v4.10. CI gate (no `:latest`, no bare images) lands in Plan 82-04.

## Documentation

- **Full operator guide:** [`docs/chaos-lab.md`](../docs/chaos-lab.md)
- **Expected scanner findings (UAT oracle):** [`expected_results_v4.md`](./expected_results_v4.md)
- **Historical reference:** [`CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md`](./CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md)

## Phase C (mTLS + step-ca)

Generate and rotate short-lived certs, and restart the Phase C gateway automatically:

```bash
chmod +x scripts/phaseC_stepca_issue.sh
./scripts/phaseC_stepca_issue.sh
# loop:
./scripts/phaseC_stepca_issue.sh --loop --every-min 5
```

## Historical Reference

> **Historical artifact:** `CHAOS_LAB_BUILD_AND_OPERATIONS_text_only.md` in this directory is retained for reference but is no longer updated. The `docs/chaos-lab.md` guide is the authoritative reference.
