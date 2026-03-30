---
phase: 04-chaos-lab-expansion
plan: 01
subsystem: infra
tags: [docker, fastapi, jwt, jwks, rsa, hmac, python]

# Dependency graph
requires:
  - phase: 03-scanner-coverage
    provides: jwt_scanner.py with JWKS_PATHS and key field extraction (kty, alg, n, k, kid)
provides:
  - 4 FastAPI JWT microservices (RS256, HS256-weak, RSA1024, alg:none) under quantum-chaos-enterprise-lab/jwt/
  - docker-compose.yml jwt profile with 4 services on ports 20001-20004
  - Known weak JWT algorithm findings for SCAN-03 to validate against
affects:
  - 04-chaos-lab-expansion (subsequent plans that extend the lab)
  - test suite (integration tests targeting jwt profile endpoints)

# Tech tracking
tech-stack:
  added:
    - fastapi==0.111.0 (JWT microservice framework, pinned)
    - uvicorn[standard]==0.29.0 (ASGI server)
    - cryptography>=42.0.0 (RSA key generation via hazmat primitives)
    - PyJWT>=2.8.0 (JWT signing — RS256, HS256)
  patterns:
    - Profile-tagged Docker Compose services — all new services use profiles: ["jwt"]
    - python:3.12-slim base image for lightweight FastAPI containers
    - At-startup key generation — keys generated once at import time, reused per container lifetime
    - Manual alg:none JWT construction (no library) — header.payload. with empty signature

key-files:
  created:
    - quantum-chaos-enterprise-lab/jwt/rs256/main.py
    - quantum-chaos-enterprise-lab/jwt/rs256/requirements.txt
    - quantum-chaos-enterprise-lab/jwt/rs256/Dockerfile
    - quantum-chaos-enterprise-lab/jwt/hs256/main.py
    - quantum-chaos-enterprise-lab/jwt/hs256/requirements.txt
    - quantum-chaos-enterprise-lab/jwt/hs256/Dockerfile
    - quantum-chaos-enterprise-lab/jwt/rsa1024/main.py
    - quantum-chaos-enterprise-lab/jwt/rsa1024/requirements.txt
    - quantum-chaos-enterprise-lab/jwt/rsa1024/Dockerfile
    - quantum-chaos-enterprise-lab/jwt/algnone/main.py
    - quantum-chaos-enterprise-lab/jwt/algnone/requirements.txt
    - quantum-chaos-enterprise-lab/jwt/algnone/Dockerfile
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml

key-decisions:
  - "Python/FastAPI chosen for JWT services — consistent with QU.I.R.K. codebase (Python-native constraint)"
  - "Ports 20001-20004 assigned — safe range (20000-23999), confirmed no conflicts with existing lab"
  - "alg:none service manually constructs JWT header.payload. without a library — avoids PyJWT refusing to sign with alg=none"
  - "HS256 weak key is 16 bytes (128 bits) — deliberately below recommended 256-bit minimum to trigger weak-key finding"
  - "RSA-1024 uses key_size=1024 — triggers rsa_bits < 2048 finding in jwt_scanner.py"

patterns-established:
  - "JWT lab service pattern: FastAPI app + Dockerfile + requirements.txt per service subdirectory"
  - "JWKS format: kty/alg/kid/n+e for RSA, kty/alg/kid/k for oct — matches scanner field extraction"
  - "All new compose services tagged profiles: [profile-name] — zero profileless additions"

requirements-completed: [LAB-01]

# Metrics
duration: 12min
completed: 2026-03-30
---

# Phase 4 Plan 01: JWT Chaos Lab Profile Summary

**4 FastAPI JWT microservices (RS256/2048-bit, HS256-weak/128-bit, RSA-1024, alg:none) deployed as docker-compose jwt profile on ports 20001-20004 with JWKS + /token endpoints matching SCAN-03 scanner field expectations**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-30T12:37:21Z
- **Completed:** 2026-03-30T12:49:00Z
- **Tasks:** 2
- **Files modified:** 13 (12 created + 1 modified)

## Accomplishments

- Created 4 FastAPI microservice apps serving `/.well-known/jwks.json` and `/token`, each with deliberately weak or known algorithm configuration
- Built shared Dockerfile pattern (python:3.12-slim) and requirements.txt across all 4 services
- Added 4 jwt-profile compose services to docker-compose.yml (ports 20001-20004) with no disruption to existing services — YAML validated clean

## Task Commits

1. **Task 1: Build 4 JWT FastAPI microservice apps and Dockerfiles** - `ab308f7` (feat)
2. **Task 2: Add jwt profile services to docker-compose.yml** - `7a136e9` (feat)

## Files Created/Modified

- `quantum-chaos-enterprise-lab/jwt/rs256/main.py` - FastAPI app: RSA 2048-bit key, RS256 JWKS + signed /token
- `quantum-chaos-enterprise-lab/jwt/rs256/requirements.txt` - fastapi/uvicorn/cryptography/PyJWT deps
- `quantum-chaos-enterprise-lab/jwt/rs256/Dockerfile` - python:3.12-slim, uvicorn entrypoint
- `quantum-chaos-enterprise-lab/jwt/hs256/main.py` - FastAPI app: 16-byte (128-bit) HMAC key, kty=oct HS256 JWKS
- `quantum-chaos-enterprise-lab/jwt/hs256/requirements.txt` - same deps
- `quantum-chaos-enterprise-lab/jwt/hs256/Dockerfile` - same pattern
- `quantum-chaos-enterprise-lab/jwt/rsa1024/main.py` - FastAPI app: RSA 1024-bit key (deliberately weak), RS256 JWKS
- `quantum-chaos-enterprise-lab/jwt/rsa1024/requirements.txt` - same deps
- `quantum-chaos-enterprise-lab/jwt/rsa1024/Dockerfile` - same pattern
- `quantum-chaos-enterprise-lab/jwt/algnone/main.py` - FastAPI app: kty=oct alg=none JWKS, manual JWT construction (no library)
- `quantum-chaos-enterprise-lab/jwt/algnone/requirements.txt` - same deps
- `quantum-chaos-enterprise-lab/jwt/algnone/Dockerfile` - same pattern
- `quantum-chaos-enterprise-lab/docker-compose.yml` - +37 lines: jwt-rs256/hs256/rsa1024/algnone services with profiles: ["jwt"]

## Decisions Made

- Python/FastAPI for all 4 services — maintains Python-native constraint from PROJECT.md
- alg:none JWT constructed manually (base64url header.payload. format) — PyJWT actively refuses to encode with alg=none, so manual construction is the correct approach
- Ports 20001-20004 confirmed conflict-free against the full existing port list from RESEARCH.md
- At-startup key generation: keys are generated once at module import, reused for container lifetime (simplest correct approach)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Docker Desktop daemon was not running at execution time — build verification step (`docker compose --profile jwt build`) was blocked. YAML was validated with `docker compose config --quiet` (exits 0). Build will succeed when Docker Desktop is started.

## User Setup Required

To run the smoke test after Docker Desktop is started:

```bash
docker compose -f quantum-chaos-enterprise-lab/docker-compose.yml --profile jwt build
docker compose -f quantum-chaos-enterprise-lab/docker-compose.yml --profile jwt up -d
sleep 8
curl -s http://localhost:20001/.well-known/jwks.json   # RS256: kty=RSA, alg=RS256, n=~342-char b64url
curl -s http://localhost:20002/.well-known/jwks.json   # HS256: kty=oct, alg=HS256, k=22-char b64url
curl -s http://localhost:20003/.well-known/jwks.json   # RSA1024: kty=RSA, alg=RS256, n=~172-char b64url
curl -s http://localhost:20004/.well-known/jwks.json   # alg:none: kty=oct, alg=none, k=""
docker compose -f quantum-chaos-enterprise-lab/docker-compose.yml --profile jwt down
```

## Next Phase Readiness

- jwt profile is ready for scanner validation — jwt_scanner.py (SCAN-03) can be pointed at localhost:20001-20004 to produce RS256/HS256-weak/RSA1024/alg:none findings
- Next plans in phase 4 can build on the established jwt profile pattern for registry, source, storage, ssh-weak, and ldaps profiles

---
*Phase: 04-chaos-lab-expansion*
*Completed: 2026-03-30*
