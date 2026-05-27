---
phase: 115-live-uat-stabilization-lab-testability
plan: "03"
subsystem: chaos-lab
tags: [lab, distributed, weak-tls, no-drift, uat]
dependency_graph:
  requires: [115-01, 115-02]
  provides: [LAB-01-distributed-weak-tls-segment-b]
  affects: [quantum-chaos-enterprise-lab/docker-compose.distributed.yml, quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh]
tech_stack:
  added: []
  patterns: [tls-legacy-reuse, sensor-config-per-segment, no-drift-rule]
key_files:
  created:
    - quantum-chaos-enterprise-lab/sensor-config-b.yaml
  modified:
    - quantum-chaos-enterprise-lab/docker-compose.distributed.yml
    - quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh
    - quantum-chaos-enterprise-lab/expected_results_distributed.md
    - quantum-chaos-enterprise-lab/README.md
    - docs/UAT-SERIES.md
decisions:
  - "D-09/D-10: tls-weak-b reuses nginx:1.28.0 + nginx/legacy/nginx.conf (no new image or cert)"
  - "D-11: lab.sh + oracle + README updated in same change (no-drift rule satisfied)"
  - "O-Q3: separate sensor-config-b.yaml mounted to sensor-b only (preserves segment-a isolation)"
  - "lab.sh ALL_PROFILES: no change required — distributed arm delegates generically via compose"
metrics:
  duration: "~15 min"
  completed: 2026-05-27
  tasks_completed: 3
  files_modified: 5
  files_created: 1
---

# Phase 115 Plan 03: LAB-01 Weak-TLS Segment-B Distributed Lab Target Summary

## One-liner

Added `tls-weak-b` (nginx:1.28.0 + legacy TLS 1.0/1.1 config) to segment-b with a dedicated `sensor-config-b.yaml` for sensor-b isolation, plus full no-drift docs, oracle, and UAT-115-03.

## What Was Built

### Task 1: tls-weak-b service + sensor-config-b.yaml (LAB-01)

Added `tls-weak-b` to `docker-compose.distributed.yml` on segment-b at `10.20.0.20`, reusing the `nginx/legacy/nginx.conf` and `certs` volumes from the tls-legacy pattern (D-10). Image pinned to `nginx:1.28.0` (CHAOS-05). No host-port binding (`expose: 443` only). No `crypto.internal` alias — distinct from the modern `tls-target-b` at `10.20.0.10`.

Created `sensor-config-b.yaml` copying `sensor-config.yaml` schema, adding `10.20.0.20` to `include_ips` (O-Q3 resolution: separate config, not dual targets in the shared file). Changed the `sensor-b` volume mount from the shared `sensor-config.yaml` to `sensor-config-b.yaml` so only sensor-b scans the weak target. Added `depends_on: tls-weak-b: condition: service_started` to sensor-b.

Segment isolation preserved: sensor-a cannot reach `10.20.0.20` (not on segment-b, shared config unchanged).

**Commit:** `dad59df`

### Task 2: No-drift updates — e2e script, oracle, README (LAB-01/D-11)

Updated `distributed-e2e.sh` to add Test 7 (per-segment weak-TLS filter validation) after the merge step: queries the console SQLite DB via `docker compose exec` to assert sensor-b has `≥1` rows with `host=10.20.0.20` and segment-a has `0` such rows. Best-effort assertion (prints PASS/WARNING/SKIP based on query result).

Updated `expected_results_distributed.md`:
- Added `tls-weak-b` row to Services table (image, network, IP, role)
- Added "LAB-01: Per-Segment Weak-TLS Filter Validation" oracle section with expected findings table (TLS 1.0/1.1, HIGH:MEDIUM ciphers, elevated quantum_risk) and segment isolation assertions

Updated `README.md` distributed section: added `tls-weak-b` to the segment-b network layout table; added v5.5 LAB-01 paragraph explaining the new target and Test 7.

`lab.sh` required no change — the distributed arm delegates to `compose ps/logs` generically; `ALL_PROFILES` is only for the main `docker-compose.yml` (confirmed by RESEARCH).

**Commit:** `0ec6240`

### Task 3: docs/UAT-SERIES.md + Obsidian sync

Updated `docs/UAT-SERIES.md`:
- Bumped `**Last Updated:**` date with Phase 115 Plan 03 entry in the running log
- Updated UAT Series 115 header to reflect full plan coverage (Plans 01–03, all 5 requirements STAB-01..04, LAB-01)
- Added UAT-115-03 (LAB-01 static verification: compose parse, sensor-config-b.yaml parse, sensor-b mount, oracle grep, README grep, e2e bash -n, Test 7 presence)

Synced to Obsidian vault at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` using the printf+cat+cp pattern (file too large for CLI `content=`).

**Commit:** `d804c1a`

## Deviations from Plan

None — plan executed exactly as written.

The RESEARCH and PATTERNS confirmed `lab.sh` needs no ALL_PROFILES change (the distributed arm is entirely generic), which aligned with the plan's note "no ALL_PROFILES change required." No deviation.

## Threat Surface Scan

No new network endpoints or auth paths introduced beyond the tls-weak-b Docker service (intentionally insecure, lab-only, segment-b isolated, no host-port binding). Threat T-115-09 (accept), T-115-10 (mitigated by segment isolation + Test 7), T-115-11 (mitigated by image pin + config reuse) all addressed as planned.

## Known Stubs

None. All oracle rows and test assertions are wired to real service configuration.

## Self-Check: PASSED

Files exist:
- `quantum-chaos-enterprise-lab/sensor-config-b.yaml` — FOUND
- `quantum-chaos-enterprise-lab/docker-compose.distributed.yml` (tls-weak-b present) — FOUND
- `quantum-chaos-enterprise-lab/expected_results_distributed.md` (tls-weak-b rows) — FOUND
- `quantum-chaos-enterprise-lab/README.md` (tls-weak-b) — FOUND
- `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh` (Test 7) — FOUND
- `docs/UAT-SERIES.md` (UAT-115-03) — FOUND

Commits exist:
- `dad59df` feat(115-03): add tls-weak-b service + sensor-config-b.yaml — FOUND
- `0ec6240` feat(115-03): no-drift updates — e2e Test 7 assertion, oracle, README — FOUND
- `d804c1a` docs(115-03): update UAT-SERIES.md — add UAT-115-03 — FOUND
