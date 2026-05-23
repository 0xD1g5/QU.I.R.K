---
phase: 89-chaos-lab-profiles
plan: "03"
subsystem: chaos-lab
tags: [chaos-lab, grpc, tls, alpn-h2, lab-infra, docker-compose, lab-03, lab-05, go]
dependency_graph:
  requires:
    - 89-01 (grpc-tls is the 4th profile in the wave-2 batch; depends on compose/lab-sync patterns established in plan 01)
  provides:
    - grpc-tls chaos-lab profile (LAB-05, port 39443)
    - LAB-03 smtp-starttls already-covered closure (email profile port 30587)
  affects:
    - labs/grpc-tls/ (new)
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/README.md
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - tests/test_phase89_lab_expected_results.py
    - .planning/REQUIREMENTS.md
    - docs/UAT-SERIES.md
tech_stack:
  added:
    - golang:1.23-alpine (grpc-tls multi-stage builder stage — CHAOS-05 satisfied for build-only service)
    - google.golang.org/grpc v1.65.0 (pinned in go.mod/go.sum)
    - alpine:3.20 (grpc-tls runtime stage)
  patterns:
    - Multi-stage Go Dockerfile (builder → minimal alpine runtime)
    - grpc-go credentials.NewServerTLSFromFile auto-sets ALPN NextProtos:["h2"]
    - RSA-2048 self-signed cert-gen via openssl req -x509 (labs/broker/Makefile pattern)
    - D-03 empirical ALPN-h2 gate: sslyze run live against grpc-tls before finalizing oracle
key_files:
  created:
    - labs/grpc-tls/Dockerfile
    - labs/grpc-tls/main.go
    - labs/grpc-tls/go.mod
    - labs/grpc-tls/go.sum
    - labs/grpc-tls/Makefile
    - labs/grpc-tls/README.md
    - labs/grpc-tls/.gitignore
    - labs/grpc-tls/certs/.gitkeep
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/README.md
    - quantum-chaos-enterprise-lab/expected_results_v4.md
    - tests/test_phase89_lab_expected_results.py
    - .planning/REQUIREMENTS.md
    - docs/UAT-SERIES.md
decisions:
  - "D-03 empirical gate result: sslyze ServerScanStatusEnum.COMPLETED against grpc-go ALPN h2 endpoint; ALPN constraint does NOT prevent TLS handshake (cipher/cert findings emitted); openssl s_client fallback NOT needed"
  - "grpc-tls uses Go default TLS config — ECDHE-RSA suites + PFS; intentional weakness is RSA-2048 key size (MEDIUM finding), not cipher weakness (no HIGH weak-cipher expected)"
  - "LAB-03 closed as already-covered by email profile port 30587 per D-01; no standalone smtp-starttls service added"
  - "labs/grpc-tls/.gitignore follows per-lab .gitignore pattern (see labs/broker/.gitignore)"
metrics:
  duration: "~6 minutes"
  completed: "2026-05-22"
  tasks_completed: 2
  files_created: 8
  files_modified: 6
---

# Phase 89 Plan 03: grpc-tls Lab Profile + LAB-03 STARTTLS Closure — Summary

**One-liner:** grpc-tls Go gRPC TLS chaos-lab profile (ALPN h2, port 39443) with empirically-confirmed sslyze ALPN-h2 gate (D-03 PASSED), four-file lab-sync, and LAB-03 smtp-starttls closed as already-covered by the email profile.

## What Was Built

### Task 1: grpc-tls lab profile + D-03 ALPN-h2 blocking gate

**labs/grpc-tls/** directory:
- `main.go` — minimal `grpc.NewServer(grpc.Creds(credentials.NewServerTLSFromFile(...)))` listening on `:443`; grpc-go auto-sets `NextProtos: ["h2"]`
- `Dockerfile` — multi-stage build: `FROM golang:1.23-alpine AS builder` → `go build` → `FROM alpine:3.20` runtime; CHAOS-05 satisfied for build-only service path
- `go.mod` / `go.sum` — `google.golang.org/grpc v1.65.0` pinned; `go.sum` generated via `docker run golang:1.23-alpine go mod tidy`
- `Makefile` — `make certs` generates RSA-2048 self-signed cert (`CN=grpc-tls.chaos.local`, 3650-day validity); `chmod 640` on key
- `README.md` — weakness inventory, D-03 ALPN note, usage
- `.gitignore` — ignores `certs/*.crt` and `certs/*.key`
- `certs/.gitkeep` — directory placeholder (actual certs generated at lab-spin-up time, gitignored)

**docker-compose.yml** grpc-tls service: `build: context: ../labs/grpc-tls`, `profiles: ["grpc-tls"]`, `ports: "39443:443"`, cert bind-mounts, `nc -z localhost 443` healthcheck.

**D-03 BLOCKING GATE — PASSED:**
sslyze ran live against `localhost:39443` after the image built and started:
```
scan_status = ServerScanStatusEnum.COMPLETED
cert_subject = CN=grpc-tls.chaos.local
cert_key_size = 2048
tls12_accepted_ciphers = [TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256,
                           TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
                           TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256]
tls13_accepted_ciphers = [TLS_CHACHA20_POLY1305_SHA256,
                           TLS_AES_256_GCM_SHA384,
                           TLS_AES_128_GCM_SHA256]
```
The ALPN `h2` constraint does NOT prevent sslyze's TLS handshake from completing. Full cipher/cert findings were emitted. The openssl s_client fallback (D-03) was not needed.

Implication: grpc-tls expected findings are RSA-2048 MEDIUM only (no HIGH weak-cipher — Go's TLS 1.2 defaults are modern ECDHE-RSA with PFS).

### Task 2: grpc-tls lab-sync + LAB-03 email STARTTLS closure

**expected_results_v4.md:**
- `## Profile: grpc-tls` section added (port 39443, cert findings, cipher info, D-03 empirical result documented)
- LAB-03 coverage note added under `## Profile: email`:
  ```
  **LAB-03 coverage note (D-01):** Port 30587 (Postfix submission / SMTP STARTTLS) satisfies
  requirement LAB-03... Requirement LAB-03 is closed as covered by the email profile.
  ```

**README.md** Profile Summary table: grpc-tls row added (port 39443, v5.0 Phase 89 LAB-05 note, D-03 gate result referenced).

**REQUIREMENTS.md:**
- LAB-03 flipped to `[x]` with documented "covered-by-email-profile (D-01)" closure rationale
- LAB-05 flipped to `[x]` with D-03 empirical gate result
- Traceability table updated for both

**tests/test_phase89_lab_expected_results.py** extended with:
- `TestGrpcTlsSection` — 2 assertions (section exists + port 39443 present)
- `TestLab03EmailCoverage` — 2 assertions (LAB-03 text + port 30587 in email section)
- `TestReadmeProfileTable.test_grpc_tls_in_readme` — README row assertion
Total: 14 tests, all PASS.

**docs/UAT-SERIES.md:** UAT-89-03-01 (grpc-tls sslyze probe) and UAT-89-03-02 (email 30587 STARTTLS proof) added. Last Updated header updated.

## Verification Results

| Check | Result |
|-------|--------|
| `docker compose config -q` | PASS |
| `pytest test_chaos_lab_image_pinning.py` (CHAOS-05) | PASS — FROM golang:1.23-alpine pinned; build-only service path |
| `pytest test_phase89_lab_expected_results.py` | PASS — 14/14 assertions GREEN |
| `./lab.sh profiles` lists grpc-tls | PASS |
| D-03 BLOCKING GATE: sslyze against localhost:39443 | PASS — COMPLETED, cert CN=grpc-tls.chaos.local, RSA-2048 |
| Lab-sync four-file obligation (grpc-tls) | PASS — compose + lab.sh auto-derive + README + expected_results |
| LAB-03 closure documented in expected_results_v4.md | PASS |
| REQUIREMENTS.md LAB-03 + LAB-05 status updated | PASS |
| `python -m compileall` on modified Python | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added per-lab .gitignore for grpc-tls/certs/**
- **Found during:** Task 1 (git status showed certs/*.crt / *.key as untracked after make certs)
- **Issue:** No .gitignore existed for `labs/grpc-tls/certs/` — generated cert files would be tracked by git
- **Fix:** Created `labs/grpc-tls/.gitignore` (same pattern as `labs/broker/.gitignore` and `labs/email/.gitignore`)
- **Files modified:** `labs/grpc-tls/.gitignore`
- **Commit:** 14c1b90

**2. [Rule 2 - Missing Critical] Extended test_phase89_lab_expected_results.py with grpc-tls + LAB-03 assertions**
- **Found during:** Task 2 — test file from Plan 01 only covered postgres-tls/redis-tls/kafka-tls
- **Issue:** No automated assertions for the grpc-tls profile section or the LAB-03 email coverage note
- **Fix:** Added `TestGrpcTlsSection`, `TestLab03EmailCoverage`, and `test_grpc_tls_in_readme` test classes
- **Files modified:** `tests/test_phase89_lab_expected_results.py`
- **Commit:** 3705189

None of the other plan tasks required deviation.

## Known Stubs

None — grpc-tls has a complete Dockerfile, main.go, go.mod/go.sum, Makefile, and expected_results oracle. The `certs/` directory contains `.gitkeep` (by design — generated certs are gitignored; actual certs are generated at lab-spin-up time via `make certs`).

## Threat Flags

None — no new network endpoints outside the documented lab port (39443); no new auth paths; no schema changes. The grpc-tls image is built from official `golang:1.23-alpine` + `alpine:3.20` (T-89-07 disposition: mitigate via CHAOS-05 pin gate, verified PASS).

## Self-Check: PASSED

Files exist:
- labs/grpc-tls/Dockerfile: FOUND
- labs/grpc-tls/main.go: FOUND
- labs/grpc-tls/go.mod: FOUND
- labs/grpc-tls/go.sum: FOUND
- labs/grpc-tls/Makefile: FOUND
- labs/grpc-tls/README.md: FOUND

Commits exist:
- 14c1b90 (Task 1 — grpc-tls lab files + D-03 gate): FOUND
- 3705189 (Task 2 — lab-sync + LAB-03 closure): FOUND
