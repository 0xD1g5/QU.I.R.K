---
phase: 04-chaos-lab-expansion
plan: 03
subsystem: infra
tags: [gitea, docker-compose, semgrep, crypto-anti-patterns, source-scanner, lab]

# Dependency graph
requires:
  - phase: 04-chaos-lab-expansion
    provides: "docker-compose.yml with jwt + registry profiles from plans 04-01 and 04-02"
provides:
  - "quantum-chaos-enterprise-lab/source/seed.sh: Gitea API seed script creating 3 repos with all 4 D-08 crypto anti-pattern categories"
  - "docker-compose.yml source profile: gitea + gitea-seed services on port 20006"
affects:
  - source_scanner
  - 04-04
  - 04-05

# Tech tracking
tech-stack:
  added: [gitea/gitea:1.21, alpine:3.19]
  patterns: [gitea-api-seeding, compose-profile-isolation, healthcheck-dependency-chain]

key-files:
  created:
    - quantum-chaos-enterprise-lab/source/seed.sh
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml

key-decisions:
  - "Gitea admin user created via entrypoint bash -c with gitea admin user create; INSTALL_LOCK=true prevents setup wizard"
  - "gitea-seed depends_on gitea condition: service_healthy with start_period: 30s to handle cold-start delay"
  - "seed.sh uses printf + base64 | tr -d newlines for reliable file content encoding in alpine sh"

patterns-established:
  - "Pattern: Compose seed containers use restart: no + depends_on service_healthy for one-shot seeding after infra ready"
  - "Pattern: Gitea file creation via POST /api/v1/repos/{owner}/{repo}/contents/{path} with base64-encoded content"

requirements-completed: [LAB-03]

# Metrics
duration: 5min
completed: 2026-03-30
---

# Phase 4 Plan 03: Source Profile (Gitea + Crypto Anti-Patterns) Summary

**Gitea instance seeded with 3 repos (Python/Go/Java) covering all 4 D-08 crypto anti-pattern categories for semgrep p/cryptography validation**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-30T19:34:06Z
- **Completed:** 2026-03-30T19:39:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Created `source/seed.sh` seeding 3 Gitea repos via REST API with all 4 D-08 crypto anti-pattern categories (hardcoded keys, weak algorithms, weak random, deprecated protocols)
- Added `gitea` and `gitea-seed` compose services under `profiles: ["source"]` on port 20006
- Healthcheck chain with `start_period: 30s` ensures seed only runs after Gitea is fully initialized with admin user

## Task Commits

Each task was committed atomically:

1. **Task 1: Write Gitea seed script with all 4 anti-pattern categories** - `2ebb1b4` (feat)
2. **Task 2: Add source profile services to docker-compose.yml** - `6d4f59a` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `quantum-chaos-enterprise-lab/source/seed.sh` - Gitea API seed script: creates 3 repos and uploads Python/Go/Java files with hardcoded keys (HARDCODED_RSA_KEY, AES_KEY), weak algorithms (hashlib.md5, DES, RC4, ECB), weak random (random.choice, math/rand), and deprecated protocols (TLS 1.0 pin, SSLv23)
- `quantum-chaos-enterprise-lab/docker-compose.yml` - Added gitea + gitea-seed services under source profile; added gitea_data volume

## Decisions Made
- Gitea admin user created inside entrypoint command (bash -c with background gitea web process + sleep 10 + user create) rather than a separate init container — avoids needing a custom image while keeping INSTALL_LOCK pattern
- seed.sh uses `put_file` helper function with base64 + tr -d '\n' to avoid newline issues in alpine sh heredoc-free encoding
- start_period: 30s on gitea healthcheck accounts for Gitea's SQLite initialization time before admin user creation completes

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Source profile ready: `docker compose --profile source up -d` starts Gitea on port 20006 and seeds 3 repos
- source_scanner.py can clone repos from `http://localhost:20006` and run `semgrep --config p/cryptography`
- Anti-pattern coverage: all 4 D-08 categories present across crypto-antipatterns-python, crypto-antipatterns-go, crypto-antipatterns-java

---
*Phase: 04-chaos-lab-expansion*
*Completed: 2026-03-30*
