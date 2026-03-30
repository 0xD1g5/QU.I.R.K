---
phase: 04-chaos-lab-expansion
plan: 02
subsystem: infra
tags: [docker, registry, crypto, syft, container-scanner, chaos-lab]

# Dependency graph
requires:
  - phase: 04-01
    provides: JWT profile services and docker-compose.yml with jwt services already present
  - phase: 03-scanner-coverage
    provides: container_scanner.py with CRYPTO_LIB_ALLOWLIST (23-entry frozenset, name.lower() exact match)
provides:
  - Docker Registry v2 service on port 20005 under profile "registry"
  - registry-seed service that builds and pushes 3 test images on startup
  - image-old-libssl Dockerfile (ubuntu:18.04 + openssl + libssl1.0.0)
  - image-old-pycrypto Dockerfile (python:3.9-slim + cryptography==2.9.2 + pyOpenSSL==19.1.0)
  - image-mixed Dockerfile (multi-stage golang:1.20 builder + ubuntu:18.04 runtime with old libssl + pycrypto)
  - seed.sh script building and pushing all 3 images to registry:5000
affects: [chaos-lab-operator-guide, container-scanner-validation]

# Tech tracking
tech-stack:
  added: [registry:2, docker:24-dind, ubuntu:18.04, golang:1.20-alpine, python:3.9-slim]
  patterns:
    - "registry profile: Docker Registry v2 + seed sidecar (restart: no + depends_on: service_healthy)"
    - "seed container mounts Docker socket + Dockerfile dirs as read-only volume"
    - "CRYPTO_LIB_ALLOWLIST name.lower() exact match — use 'openssl' (apt), 'cryptography' (pip), 'pyopenssl' (pip)"

key-files:
  created:
    - quantum-chaos-enterprise-lab/registry/image-old-libssl/Dockerfile
    - quantum-chaos-enterprise-lab/registry/image-old-pycrypto/Dockerfile
    - quantum-chaos-enterprise-lab/registry/image-mixed/Dockerfile
    - quantum-chaos-enterprise-lab/registry/seed.sh
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml

key-decisions:
  - "apt package 'openssl' used as primary CRYPTO_LIB_ALLOWLIST match (exact match); 'libssl1.0.0' also installed but does NOT exactly match the frozenset — 'openssl' is the detectable package"
  - "python pip package names 'cryptography' and 'pyOpenSSL' both exact CRYPTO_LIB_ALLOWLIST matches (pyopenssl after .lower())"
  - "registry-seed uses docker:24-dind with socket mount (Pattern 3 from RESEARCH.md) rather than pre-baked images"
  - "port 20005 chosen for registry — safe range per RESEARCH.md Pitfall 7, no conflict with existing lab services"

patterns-established:
  - "Profile sidecar pattern: seed container with restart: no + depends_on: condition: service_healthy"
  - "Registry seed mounts ./registry as /registry-build:ro — Dockerfiles live at /registry-build/{image-name}/"

requirements-completed: [LAB-02]

# Metrics
duration: 15min
completed: 2026-03-30
---

# Phase 04 Plan 02: Registry Profile Summary

**Docker Registry v2 profile on port 20005 with 3 seeded test images containing openssl, cryptography==2.9.2, and pyOpenSSL==19.1.0 that Syft's CRYPTO_LIB_ALLOWLIST will detect**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-30T16:29:24Z
- **Completed:** 2026-03-30T16:44:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- 3 Dockerfiles created with deliberately old crypto library versions matching CRYPTO_LIB_ALLOWLIST exact name.lower() entries
- seed.sh script that builds and pushes all 3 images to the internal registry on startup via Docker socket mount
- docker-compose.yml updated with `registry` and `registry-seed` services under `profiles: ["registry"]` on port 20005
- `registry_data:` named volume added to persist registry storage between restarts

## Task Commits

Each task was committed atomically:

1. **Task 1: Build 3 registry test image Dockerfiles and seed.sh** - `3013b04` (feat)
2. **Task 2: Add registry profile services to docker-compose.yml** - `7bc8a00` (feat)

**Plan metadata:** (docs commit pending)

## Files Created/Modified
- `quantum-chaos-enterprise-lab/registry/image-old-libssl/Dockerfile` - ubuntu:18.04 with openssl + libssl1.0.0 + libssl-dev
- `quantum-chaos-enterprise-lab/registry/image-old-pycrypto/Dockerfile` - python:3.9-slim with cryptography==2.9.2 + pyOpenSSL==19.1.0
- `quantum-chaos-enterprise-lab/registry/image-mixed/Dockerfile` - multi-stage: golang:1.20-alpine builder + ubuntu:18.04 runtime with both old libs
- `quantum-chaos-enterprise-lab/registry/seed.sh` - builds and pushes all 3 images to registry:5000 (internal hostname)
- `quantum-chaos-enterprise-lab/docker-compose.yml` - added registry + registry-seed services and registry_data volume

## Decisions Made
- apt package "openssl" is the exact CRYPTO_LIB_ALLOWLIST match; "libssl1.0.0" installed alongside it but does not match the frozenset entry "libssl1.1" or "libssl" — having both ensures Syft finds "openssl" as a definite hit
- pip packages "cryptography" and "pyOpenSSL" are exact allowlist matches (pyopenssl after .lower()) — these are the primary detectable packages for Python crypto scanning
- registry-seed uses docker:24-dind with /var/run/docker.sock mount; the seed script uses INTERNAL_REGISTRY="registry:5000" (not localhost:20005) because the seed container is inside the compose network
- Multi-stage Go builder in image-mixed adds a Go binary importing crypto/tls, testing that Syft handles multi-stage images

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Registry profile ready for scanner validation: `docker compose --profile registry up -d` starts registry + seed, then `curl http://localhost:20005/v2/_catalog` should return all 3 image names
- container_scanner.py can be pointed at `localhost:20005/image-old-libssl:latest` etc. to validate CRYPTO_LIB_ALLOWLIST detection
- Plan 04-03 (source profile / Gitea) can proceed independently

---
*Phase: 04-chaos-lab-expansion*
*Completed: 2026-03-30*

## Self-Check: PASSED

All files found on disk and all commits verified in git history.
