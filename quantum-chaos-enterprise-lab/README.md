# QU.I.R.K. Chaos Lab

A Docker-Compose-based crypto-misconfiguration playground used by QU.I.R.K. for end-to-end scanner UAT. Eighteen named profiles plus an always-on core baseline cover TLS / SSH / JWT / container / source / cloud / DAR / messaging chaos scenarios — each with an expected-findings oracle in `expected_results_v4.md` and detailed prose in `docs/chaos-lab.md`.

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
| ldaps | ldaps | 636 | [Expected Findings](expected_results_v4.md#profile-ldaps) | v4.1 |
| dnssec | bind9-dnssec | 15353/udp, 15353/tcp | [Expected Findings](expected_results_v4.md#profile-dnssec) | v4.2 |
| saml | simplesamlphp | 8080 | [Expected Findings](expected_results_v4.md#profile-saml) | v4.2; note: port 8080 — avoid running alongside `identity` (Keycloak exposes 8080 internally) |
| kerberos | samba-dc | 88, 389 | [Expected Findings](expected_results_v4.md#profile-kerberos) | v4.2; privileged ports — collides with system DNS/AD if anything else listens on 88/389. **macOS:** `./lab.sh all` skips this profile automatically because the OS-level KDC binds `*:88`. Set `LAB_INCLUDE_KERBEROS=1` to opt in (requires stopping the system KDC first). Tracked for full host-port remap under BACK-89. |
| database | postgres-ssl-off, mysql-ssl-off | 25432, 23306 | [Expected Findings](expected_results_v4.md#profile-database) | v4.3 (DAR) |
| storage-s3 | minio, minio-seed | 29000, 29001 | [Expected Findings](expected_results_v4.md#profile-storage-s3) | v4.3 (DAR) |
| vault | vault-30 (1.17), vault-30-seed | 28200 | [Expected Findings](expected_results_v4.md#profile-vault) | v4.3 (DAR); independent of legacy `storage` profile |
| email | postfix-email, dovecot-email | 30025, 30465, 30587, 30143, 30993, 30110, 30995 | [Expected Findings](expected_results_v4.md#profile-email) | v4.4 |
| broker | kafka-broker, rabbitmq-broker, redis-broker | 29092, 29093, 25672, 25671, 26379, 26380 | [Expected Findings](expected_results_v4.md#profile-broker) | v4.4 |
| tls-cert-defects | tls-cert-expired, tls-cert-selfsigned, tls-cert-untrusted-ca, tls-cert-rsa1024 | 13444, 13445, 13446, 13447 | [Expected Findings](expected_results_v4.md#profile-tls-cert-defects) | v4.6 (Phase 46); single-profile target exercising TLS-FIND-01..05 cert-defect findings end-to-end |

### Image Pin Policy

All services in `docker-compose.yml` carry an explicit version tag because floating tags (`:latest`, `:8`, `:3`) are silently advanced by Docker Hub, which is exactly what broke four services at once and was discovered under Phase 999.83 / BACK-90.

- Major-only tags (e.g. `mysql:8`, `nginx:1`, `postgres:15`) are NOT acceptable — Docker Hub re-points them across breaking minor releases.
- Minor or dated pins ARE acceptable — e.g. `mysql:8.0`, `gitea/gitea:1.21`, `hashicorp/vault:1.17`, `minio/minio:RELEASE.YYYY-MM-DDTHH-MM-SSZ`.
- When upgrading a pin, treat it as a chaos-lab maintenance change per CLAUDE.md: update `lab.sh` / `README.md` / `expected_results_v4.md` together in the same commit if behavior changes.

Pins enforced this phase: `gitea/gitea:1.21` (unchanged), `minio/minio:RELEASE.2025-09-07T16-13-09Z` (newly pinned from `:latest`), `mysql:8.0` (newly pinned from `:8`), and legacy `hashicorp/vault:1.15` deleted along with the deprecated `storage` profile.

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
