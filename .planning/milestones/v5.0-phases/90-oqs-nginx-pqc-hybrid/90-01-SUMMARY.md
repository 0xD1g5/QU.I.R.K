---
phase: 90-oqs-nginx-pqc-hybrid
plan: "01"
subsystem: chaos-lab
tags: [pqc, oqs-nginx, tls, lab-sync, chaos-lab, digest-pin]
dependency_graph:
  requires: []
  provides: [oqs-nginx-profile, pqc-hybrid-endpoint, expected-results-anchor]
  affects: [quantum-chaos-enterprise-lab/docker-compose.yml, quantum-chaos-enterprise-lab/README.md, quantum-chaos-enterprise-lab/expected_results_v4.md]
tech_stack:
  added: [openquantumsafe/nginx@sha256:6ca18ac6 (digest-pinned), X25519MLKEM768 hybrid KEM, ML-DSA-65 cert]
  patterns: [chaos-lab-profile, four-file-lab-sync, digest-pin-policy]
key_files:
  created:
    - quantum-chaos-enterprise-lab/oqs-nginx/nginx.conf
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.yml
    - quantum-chaos-enterprise-lab/README.md
    - quantum-chaos-enterprise-lab/expected_results_v4.md
decisions:
  - "Digest-pinned openquantumsafe/nginx (sha256:6ca18ac6…) — oqs-provider renames group names across releases; :latest is permanently forbidden"
  - "Port 39444 confirmed free at planning time and verified before commit (follows 39xxx-for-TLS lab convention)"
  - "nginx.conf pins ssl_ecdh_curve X25519MLKEM768 + TLS 1.3 only; reuses image's bundled ML-DSA-65 cert paths"
  - "lab.sh auto-derives oqs-nginx from docker-compose.yml profiles (Phase 89); no manual ALL_PROFILES edit needed"
  - "expected_results_v4.md ## Profile: oqs-nginx left with TODO marker for Plans 90-02/03/04 — agility contrast finalized in 90-04 D-04 scope"
metrics:
  completed_date: "2026-05-22"
  duration: "~30 min (incl. human-verify checkpoint)"
  tasks_completed: 2
  files_changed: 4
---

# Phase 90 Plan 01: OQS-Nginx PQC Hybrid Profile Summary

**One-liner:** Digest-pinned openquantumsafe/nginx chaos-lab profile serving TLS 1.3 with X25519MLKEM768 hybrid KEM and ML-DSA-65 certificate on port 39444 — the empirical agility-ceiling anchor for Phase 90.

## What Was Built

### Task 1: oqs-nginx service + nginx.conf (commits 6491f35, 223f529)

Added a new `oqs-nginx` Docker Compose profile to the chaos lab:

- **Service:** `openquantumsafe/nginx@sha256:6ca18ac692f347ea9d4c3fdab4231189f2146570cd03c4d8fb486bba208ef870` (digest-pinned, built 2026-05-18)
- **Port:** `127.0.0.1:39444:443` (loopback bind, free port confirmed)
- **Config:** `quantum-chaos-enterprise-lab/oqs-nginx/nginx.conf` — `ssl_protocols TLSv1.3; ssl_ecdh_curve X25519MLKEM768;` mounted read-only; reuses image's bundled ML-DSA-65 cert
- **Healthcheck:** `nc -z 127.0.0.1 443` (IPv4-explicit; IPv6/IPv4 mismatch on `localhost` auto-fixed Rule 1)

**Human-verify checkpoint PASSED:** User confirmed:
- `Negotiated TLS1.3 group: X25519MLKEM768`
- `Peer signature type: mldsa65`

### Task 2: Four-file lab-sync (commit e5c61da)

Completed CLAUDE.md Chaos Lab Maintenance obligations:

- **lab.sh:** Auto-derives `oqs-nginx` from docker-compose.yml profiles (Phase 89 feature, confirmed `./lab.sh profiles` output — no manual ALL_PROFILES edit required)
- **README.md:** Added `oqs-nginx` row to Profile Summary table; bumped count Eighteen → Nineteen; added PQC to scenario list in intro
- **expected_results_v4.md:** Added `## Profile: oqs-nginx` section with full network-listener schema (port, group X25519MLKEM768 / NamedGroup 4588, ML-DSA-65 cert, host-OpenSSL compatibility note, loopback/`--allow-internal-targets` note, TODO markers for Plans 90-02/03/04)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed oqs-nginx healthcheck IPv6/IPv4 mismatch**
- **Found during:** Task 1 container startup
- **Issue:** Healthcheck used `localhost` which on some Docker Linux kernels resolves to `::1` (IPv6); the nginx listener binds IPv4 `0.0.0.0:443` only
- **Fix:** Changed `nc -z localhost 443` to `nc -z 127.0.0.1 443` in the healthcheck
- **Files modified:** `quantum-chaos-enterprise-lab/docker-compose.yml`
- **Commit:** 223f529

## Known Stubs

- `expected_results_v4.md ## Profile: oqs-nginx` — TODO markers for Plans 90-02 and 90-03 (detection + scoring). The genuine CBOM component entry and quantum-readiness score impact are intentionally deferred to Plan 90-04 (D-04 before/after agility contrast). This is planned, not accidental.

## Threat Surface Scan

No new network endpoints beyond what is documented in the plan's threat model. The oqs-nginx container binds loopback only (T-90-02: accepted). Digest pin is the supply-chain control (T-90-01: mitigated).

## Self-Check: PASSED

Files exist:
- quantum-chaos-enterprise-lab/oqs-nginx/nginx.conf: FOUND
- quantum-chaos-enterprise-lab/docker-compose.yml: FOUND (modified)
- quantum-chaos-enterprise-lab/README.md: FOUND (modified)
- quantum-chaos-enterprise-lab/expected_results_v4.md: FOUND (modified)

Commits:
- 6491f35: FOUND (feat: add oqs-nginx chaos-lab profile)
- 223f529: FOUND (fix: healthcheck IPv4/IPv6)
- e5c61da: FOUND (feat: four-file lab-sync)
