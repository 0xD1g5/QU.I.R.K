---
phase: 96-active-rest-fuzzing
plan: "04"
subsystem: chaos-lab
tags: [chaos-lab, fuzz-target, lab-01, docker-compose, rest-fuzzer, alg-confusion, hsts]
dependency_graph:
  requires: [phase-96-02-fuzzer-probes]
  provides: [quantum-chaos-enterprise-lab/fuzz-target, fuzz-target-compose-profile]
  affects: [quantum-chaos-enterprise-lab/docker-compose.yml, quantum-chaos-enterprise-lab/expected_results_v4.md, quantum-chaos-enterprise-lab/README.md]
tech_stack:
  added: [fastapi==0.111.0, uvicorn[standard]==0.29.0 (lab-only python:3.12-slim container)]
  patterns: [deliberately-weak FastAPI service, RS256 JWKS endpoint, alg-confusion acceptance]
key_files:
  created:
    - quantum-chaos-enterprise-lab/fuzz-target/Dockerfile
    - quantum-chaos-enterprise-lab/fuzz-target/main.py
    - quantum-chaos-enterprise-lab/fuzz-target/requirements.txt
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - quantum-chaos-enterprise-lab/README.md
decisions:
  - "lab.sh _derive_all_profiles() discovers fuzz-target dynamically from docker-compose.yml — no ALL_PROFILES hardcoded list edit needed; rationale documented in oracle and README"
  - "Port 20100 chosen — verified conflict-free vs all existing lab host ports (20001-20006, 20022)"
  - "FastAPI openapi_url=None + manual /openapi.json route used to preserve literal http:// server URL in spec (FastAPI auto-gen would not guarantee the URL format)"
  - "No Strict-Transport-Security header achieved by omission (FastAPI/Starlette does not add HSTS by default) — grep -ci strict-transport-security returns 0"
metrics:
  duration: "15 minutes"
  completed: "2026-05-23"
  tasks_completed: 2
  files_changed: 6
  commits: 2
---

# Phase 96 Plan 04: fuzz-target chaos lab profile Summary

Deliberately-weak FastAPI REST service (`fuzz-target` chaos profile) exposing HSTS-missing, http:// server, and alg-confusion acceptance endpoints; plus CLAUDE.md-mandated triple-update of compose + oracle + README.

## What Was Built

### Task 1: Create the fuzz-target service + docker-compose profile

Created `quantum-chaos-enterprise-lab/fuzz-target/` with three files:

**`Dockerfile`** — verbatim copy of `jwt/rs256/Dockerfile` pattern: `python:3.12-slim`, `uvicorn main:app` on port 8000.

**`requirements.txt`** — pinned versions matching jwt/rs256: `fastapi==0.111.0`, `uvicorn[standard]==0.29.0`, `cryptography>=42.0.0`, `PyJWT>=2.8.0`.

**`main.py`** — deliberately-weak FastAPI app with:
- `GET /openapi.json` — manually-served minimal OpenAPI 3.0 spec (FastAPI `openapi_url=None`) with `http://localhost:20100` server URL (HTTP-only credential probe target)
- `GET /.well-known/jwks.json` — exposes RS256 public key generated at startup (JWKS fetch target for alg-confusion probe, mirroring `jwt/rs256/main.py` key-gen)
- `GET /probe` — accepts any `Authorization: Bearer <token>` WITHOUT algorithm verification; always returns 200 OK (alg-confusion probe target)
- No `Strict-Transport-Security` header on any response (HSTS probe target); confirmed by `grep -ci strict-transport-security main.py` → 0

Added `fuzz-target` service block to `docker-compose.yml`:
- `build: context: ./fuzz-target`
- `profiles: ["fuzz-target"]`
- `ports: "20100:8000"` (verified conflict-free — all existing ports: 20001-20006, 20022)
- `restart: unless-stopped`
- Phase 96 / LAB-01 comment header noting dynamic profile discovery rationale

**Acceptance verified:**
- `grep -ci "strict-transport-security" fuzz-target/main.py` → 0
- Three routes present: /openapi.json, /.well-known/jwks.json, /probe
- `http://localhost:20100` in OpenAPI servers array
- `python3 -m compileall fuzz-target/main.py` → exit 0

### Task 2: Update expected_results_v4.md + chaos README for fuzz-target

Added `## Profile: fuzz-target` section to `expected_results_v4.md` with:
- `PROFILE_ARGS="--profile fuzz-target" ./lab.sh up` startup command
- Four-row probe table: HSTS_MISSING (HIGH), HTTP_ONLY_CRED (HIGH), TLS_DOWNGRADE (HIGH), ALG_CONFUSION (CRITICAL)
- Weak-target design description (all four intentional weaknesses documented)
- lab.sh note: `_derive_all_profiles()` discovers fuzz-target dynamically — **no ALL_PROFILES edit needed**
- Scanner validation command: `quirk scan --targets http://localhost:20100 --fuzz --openapi-spec http://localhost:20100/openapi.json`
- Expected: >= 2 findings (HSTS_MISSING HIGH + ALG_CONFUSION CRITICAL)

Added `fuzz-target` row to `README.md` profiles table:
- Port 20100, v5.1 (Phase 96 LAB-01), brief description of intentional weaknesses
- Link to `expected_results_v4.md#profile-fuzz-target`
- Notes: lab.sh ALL_PROFILES needs no edit — dynamic discovery

**CLAUDE.md triple-update complete:** compose profile + oracle + README updated in the same change (two commits, one per task, per CLAUDE.md Chaos Lab Maintenance rule).

## Deviations from Plan

None — plan executed exactly as written.

**lab.sh ALL_PROFILES rationale (as required by plan acceptance criteria):** `_derive_all_profiles()` at line 58 of `lab.sh` parses `docker-compose.yml` dynamically using either `yq` or a `grep` fallback. Adding `profiles: ["fuzz-target"]` to the compose file is sufficient for `./lab.sh profiles` to list `fuzz-target` without any source edit to `lab.sh`. This was verified by inspection of the `_derive_all_profiles` function.

## Known Stubs

None — all probe targets are implemented. The fuzz-target service is intentionally minimal (no auth, no TLS, no HSTS) as its purpose is to be a controlled vulnerable target.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: intentional-vulnerability (T-96-11) | quantum-chaos-enterprise-lab/fuzz-target/main.py | Deliberately-weak service; isolated compose profile (off by default), documented as lab-only, never production |

Note: T-96-11 is covered by the plan's threat model with `accept` disposition. Intentional for lab validation purposes.

## Self-Check: PASSED

- `quantum-chaos-enterprise-lab/fuzz-target/Dockerfile`: FOUND
- `quantum-chaos-enterprise-lab/fuzz-target/main.py`: FOUND (routes: /openapi.json, /.well-known/jwks.json, /probe)
- `quantum-chaos-enterprise-lab/fuzz-target/requirements.txt`: FOUND
- `quantum-chaos-enterprise-lab/docker-compose.yml`: fuzz-target service block FOUND (profiles: fuzz-target, port 20100:8000)
- `expected_results_v4.md` ## Profile: fuzz-target: FOUND (line 587)
- `README.md` fuzz-target row: FOUND (port 20100, v5.1)
- `grep -ci strict-transport-security fuzz-target/main.py` → 0: CONFIRMED
- `python3 -m compileall fuzz-target/main.py` → exit 0: CONFIRMED
- Port 20100 conflict-free: CONFIRMED
- Commit ff6cec1 (Task 1): FOUND
- Commit 8adbc71 (Task 2): FOUND
- No quirk/ source edits: CONFIRMED
- No STATE.md or ROADMAP.md changes: CONFIRMED
