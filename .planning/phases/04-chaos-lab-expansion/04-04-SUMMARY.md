---
phase: 04-chaos-lab-expansion
plan: "04"
subsystem: infra
tags: [docker, localstack, vault, hashicorp-vault, postgres, pgcrypto, kms, chaos-lab]

# Dependency graph
requires:
  - phase: 04-chaos-lab-expansion/04-03
    provides: source profile (Gitea + crypto anti-patterns repos) added to docker-compose.yml
  - phase: 03-scanner-coverage/03-04
    provides: AWS cloud connector (aws_connector.py) with KMS_KEY_SPEC_MAP driving key spec expectations
provides:
  - storage Docker Compose profile with 5 services (localstack-kms, localstack-kms-seed, vault, vault-seed, postgres-pgcrypto)
  - kms-seed.sh seeding 4 KMS keys (SYMMETRIC_DEFAULT, RSA_2048, RSA_2048/rsa-1024-fallback, ECC_NIST_P256) in LocalStack on port 20007
  - vault-seed.sh enabling transit engine with 4 key types (rsa-2048, rsa-1024, aes256-gcm96, ecdsa-p256) and KV secrets on port 20009
  - postgres-init.sql creating encrypted_demo + crypto_config tables with pgcrypto examples on port 20010
affects:
  - 04-05 (ssh-weak profile, if present)
  - 04-06 (ldaps profile, if present)
  - aws_connector.py KMS scanning validation
  - chaos lab operator guide

# Tech tracking
tech-stack:
  added:
    - hashicorp/vault:1.15 (dev mode with transit engine)
    - amazon/aws-cli:latest (KMS seed init container)
    - LocalStack KMS (SERVICES=kms, separate from cloud profile)
    - postgres:16 pgcrypto extension
  patterns:
    - sidecar init container pattern with depends_on condition: service_healthy (established in prior plans)
    - restart: "no" for seed containers (established pattern)
    - profile-isolated LocalStack instances (separate from cloud profile)

key-files:
  created:
    - quantum-chaos-enterprise-lab/storage/vault-seed.sh
    - quantum-chaos-enterprise-lab/storage/kms-seed.sh
    - quantum-chaos-enterprise-lab/storage/postgres-init.sql
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml

key-decisions:
  - "RSA_1024 KMS key spec not supported by LocalStack free tier — second RSA_2048 key with rsa-1024-fallback description used instead; plan explicitly documents this fallback"
  - "Storage profile uses its own LocalStack instance (port 20007, SERVICES=kms) independent of cloud profile LocalStack (port 24566, SERVICES=s3,sts,iam) — zero conflict by design"

patterns-established:
  - "Profile isolation: each chaos lab profile gets dedicated infrastructure (ports, volumes, service names)"
  - "Vault dev mode sidecar: vault-seed waits on service_healthy then uses vault CLI to configure transit/KV"

requirements-completed:
  - LAB-04

# Metrics
duration: 3min
completed: 2026-03-30
---

# Phase 04 Plan 04: Storage Profile Summary

**LocalStack KMS + HashiCorp Vault transit engine + postgres-pgcrypto storage profile with 5 Docker Compose services seeded with real crypto key material for scanner validation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-30T18:44:56Z
- **Completed:** 2026-03-30T18:47:43Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Created 3 seed scripts under `quantum-chaos-enterprise-lab/storage/`: vault-seed.sh (transit engine + 4 key types + KV secrets), kms-seed.sh (4 KMS keys for aws_connector.py to enumerate), postgres-init.sql (pgcrypto extension + encrypted_demo + crypto_config tables)
- Added 5 storage-profile services to docker-compose.yml: localstack-kms (port 20007), localstack-kms-seed, vault (port 20009), vault-seed, postgres-pgcrypto (port 20010)
- Storage profile is fully independent of existing cloud profile — different LocalStack instance, different ports, no shared volumes

## Task Commits

Each task was committed atomically:

1. **Task 1: Write vault-seed.sh, kms-seed.sh, and postgres-init.sql** - `d48edca` (feat)
2. **Task 2: Add storage profile services to docker-compose.yml** - `b5cd8ab` (feat)

**Plan metadata:** (see final commit below)

## Files Created/Modified

- `quantum-chaos-enterprise-lab/storage/vault-seed.sh` - Vault sidecar script enabling transit engine (4 key types: rsa-2048, rsa-1024, aes256-gcm96, ecdsa-p256) and KV secrets mount
- `quantum-chaos-enterprise-lab/storage/kms-seed.sh` - AWS CLI init container creating 4 KMS keys in LocalStack (SYMMETRIC_DEFAULT, RSA_2048, RSA_2048/rsa-1024-fallback, ECC_NIST_P256)
- `quantum-chaos-enterprise-lab/storage/postgres-init.sql` - PostgreSQL init SQL: pgcrypto extension, encrypted_demo table with pgp_sym_encrypt/crypt/gen_salt examples, crypto_config reference table
- `quantum-chaos-enterprise-lab/docker-compose.yml` - Added 5 storage-profile services + pgcrypto_data volume

## Decisions Made

- **RSA_1024 LocalStack fallback:** LocalStack free tier does not support RSA_1024 key spec. Plan explicitly documents this — second RSA_2048 key with description "Lab RSA-1024 weak equivalent" used as fallback. Scanner can enumerate all 4 keys; the KMS_KEY_SPEC_MAP in aws_connector.py does not include RSA_1024 anyway so the fallback creates no scanner logic gap.
- **Storage profile isolation:** Dedicated LocalStack instance with `SERVICES=kms` on port 20007 keeps storage profile fully independent of cloud profile's LocalStack (`SERVICES=s3,sts,iam` on 24566). Verified cloud profile unchanged after edit.

## Deviations from Plan

None - plan executed exactly as written. RSA_1024 fallback was explicitly specified in the plan's kms-seed.sh action block.

## Issues Encountered

None - `docker compose config --quiet` validated YAML immediately after both edits.

## User Setup Required

None - no external service configuration required. Storage profile is activated with `docker compose --profile storage up -d`.

## Known Stubs

None - all seed scripts contain actual key material creation commands. The RSA-1024 "fallback" key is intentional per plan specification, not a stub.

## Next Phase Readiness

- Storage profile (LAB-04) complete — LocalStack KMS, Vault transit engine, postgres-pgcrypto all ready for scanner validation
- aws_connector.py can enumerate KMS keys from localhost:20007 using `AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1 aws --endpoint-url=http://localhost:20007`
- Phase 4 Plan 05 (ssh-weak) or Plan 06 (ldaps) can proceed independently
- All 4 Phase 4 lab profiles now complete: jwt (ports 20001-20004), registry (20005), source (20006), storage (20007/20009/20010)

---
*Phase: 04-chaos-lab-expansion*
*Completed: 2026-03-30*
