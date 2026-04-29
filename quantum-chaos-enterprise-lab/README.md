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
| storage | localstack-kms, vault (1.15), postgres-pgcrypto | 20007, 20009, 20010 | [Expected Findings](expected_results_v4.md#profile-storage) | v4.1; **deprecated** — see `database` / `storage-s3` / `vault` |
| ssh-weak | ssh-weak | 20022 | [Expected Findings](expected_results_v4.md#profile-ssh-weak) | v4.1 |
| ldaps | ldaps | 636 | [Expected Findings](expected_results_v4.md#profile-ldaps) | v4.1 |
| dnssec | bind9-dnssec | 15353/udp, 15353/tcp | [Expected Findings](expected_results_v4.md#profile-dnssec) | v4.2 |
| saml | simplesamlphp | 8080 | [Expected Findings](expected_results_v4.md#profile-saml) | v4.2; note: port 8080 — avoid running alongside `identity` (Keycloak exposes 8080 internally) |
| kerberos | samba-dc | 88, 389 | [Expected Findings](expected_results_v4.md#profile-kerberos) | v4.2; privileged ports — collides with system DNS/AD if anything else listens on 88/389 |
| database | postgres-ssl-off, mysql-ssl-off | 25432, 23306 | [Expected Findings](expected_results_v4.md#profile-database) | v4.3 (DAR) |
| storage-s3 | minio, minio-seed | 29000, 29001 | [Expected Findings](expected_results_v4.md#profile-storage-s3) | v4.3 (DAR) |
| vault | vault-30 (1.17), vault-30-seed | 28200 | [Expected Findings](expected_results_v4.md#profile-vault) | v4.3 (DAR); independent of legacy `storage` profile |
| email | postfix-email, dovecot-email | 30025, 30465, 30587, 30143, 30993, 30110, 30995 | [Expected Findings](expected_results_v4.md#profile-email) | v4.4 |
| broker | kafka-broker, rabbitmq-broker, redis-broker | 29092, 29093, 25672, 25671, 26379, 26380 | [Expected Findings](expected_results_v4.md#profile-broker) | v4.4 |

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
