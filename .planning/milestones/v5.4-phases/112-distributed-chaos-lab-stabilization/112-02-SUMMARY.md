---
phase: 112-distributed-chaos-lab-stabilization
plan: "02"
subsystem: docs
tags: [distributed, oracle, chaos-lab, operators-guide, windows, merge-03, lab-03, stab-01]
dependency_graph:
  requires:
    - 112-01 (docker-compose.distributed.yml, sensor.Dockerfile, lab.sh distributed arm)
  provides:
    - quantum-chaos-enterprise-lab/expected_results_distributed.md (LAB-03 oracle)
    - docs/operators-guide.md §8 (STAB-01 distributed + Windows + settings)
  affects:
    - quantum-chaos-enterprise-lab/README.md (distributed section + cross-reference)
    - docs/operators-guide.md (§8 appended)
tech_stack:
  added: []
  patterns:
    - Oracle format mirroring expected_results_v4.md (## Topology: heading, Networks/Services/Outcome tables)
    - Operators-guide numbered §8 pattern (prose intro + numbered subsection runbook)
key_files:
  created:
    - quantum-chaos-enterprise-lab/expected_results_distributed.md
  modified:
    - quantum-chaos-enterprise-lab/README.md
    - docs/operators-guide.md
decisions:
  - "Oracle documents the Docker single-host same-subnet limitation: two bridge networks cannot share a subnet; distinct subnets (10.10/10.20/10.30) are the correct workaround with crypto.internal alias as the shared hostname mechanism"
  - "MERGE-03 rationale written in oracle: tls_scanner.py:188-189 and :351-352 record CryptoEndpoint(host=host) verbatim; both sensors record host=crypto.internal yielding two distinct DB rows differing only by sensor_id"
  - "999.59 gap closed in §8.7 with scan.timeouts.*, output.directory, and sensor_id/segment field reference"
  - "Windows sensor documented with %APPDATA%\\quirk\\sensor.yaml path via platformdirs, PowerShell snippet, SIGTERM guard note (scheduler_cmd.py:283-284)"
  - "Air-gap path documented as §8.6: quirk sensor export-results → transfer .qpush → quirk console import-results"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-26"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
---

# Phase 112 Plan 02: Oracle + Docs Summary

Distributed E2E oracle (`expected_results_distributed.md`), chaos-lab README distributed section, and `operators-guide.md §8` covering the full enroll→push→merge workflow, Windows sensor install, air-gap path, and settings reference (999.59 closed).

## What Was Built

### Task 1: expected_results_distributed.md + README distributed section

**Files:** `quantum-chaos-enterprise-lab/expected_results_distributed.md`, `quantum-chaos-enterprise-lab/README.md`
**Commit:** `44c5c10`

Created `expected_results_distributed.md` mirroring the `expected_results_v4.md` header/scope/status format. Contains:

- **Networks table**: `segment-a` (10.10.0.0/24), `segment-b` (10.20.0.0/24), `console-net` (10.30.0.0/24) with purpose column and Docker distinct-subnet rationale
- **Services table**: `tls-target-a` (nginx:1.28.0 at 10.10.0.10/segment-a, alias `crypto.internal`), `tls-target-b` (10.20.0.10/segment-b, alias `crypto.internal`), `sensor-a`, `sensor-b`, `console` (port 8512)
- **Expected E2E Outcome table**: 2 enrollments, 2 pushes HTTP 200, **2 distinct `CryptoEndpoint` rows** for `crypto.internal:443` differing by `sensor_id`, `coverage_warning=null`
- **MERGE-03 Validation block**: explains crypto.internal alias mechanism, cites `tls_scanner.py:188-189` and `:351-352` as the LAB-02 linchpin, explains why Docker forces distinct subnets, documents the `(sensor_id, host, port)` uniqueness key
- **`lab.sh distributed` commands** reference (up/e2e/down/status/logs)

Added `## Distributed Topology` section to `README.md` after the profile table with network layout, alias mechanism prose, `lab.sh distributed` command reference, and a cross-reference link to `expected_results_distributed.md#topology-distributed`. Confirms `ALL_PROFILES` sweep is unaffected.

### Task 2: operators-guide §8 + 999.59 settings reference

**Files:** `docs/operators-guide.md`
**Commit:** `9b0f58a`

Appended `## 8. Distributed Sensor Deployment` following the §7 numbered-H2 + runbook pattern. Subsections:

- **§8.1 Provision the console**: `quirk serve --host 0.0.0.0 --port 8512` with security note on token one-time-display
- **§8.2 Enroll each sensor**: `quirk console enroll --segment <label>` on console; `quirk sensor enroll <url> --segment <label> --api-token <token>` on sensor; platform `sensor.yaml` paths (Linux/macOS: `~/.config/quirk/sensor.yaml`, Windows: `%APPDATA%\quirk\sensor.yaml`)
- **§8.3 Push findings**: `quirk sensor push [--scan-config ...]` with spool fallback behavior
- **§8.4 Merge into a unified CBOM**: `quirk sensor merge [--stale-days] [--output-dir]`, coverage_warning behavior, MERGE-03 two-component note
- **§8.5 Windows sensor installation**: `pip install "quirk-scanner[all]"`, `%APPDATA%\quirk\sensor.yaml`, PowerShell enroll/push snippet, nmap install note, SIGTERM guard (`scheduler_cmd.py:283-284`)
- **§8.6 Air-gap path**: `quirk sensor export-results` → `.qpush` file transfer → `quirk console import-results`
- **§8.7 Settings reference (999.59)**: full `scan.timeouts.*` table (14 knobs with defaults), `output.directory` default and sensor-node behavior, `sensor_id`/`segment` field descriptions with MERGE-03 note

## Deviations from Plan

None — plan executed exactly as written. The as-built compose names matched the plan's `<interfaces>` section exactly; oracle content sourced from the compose file and 112-01-SUMMARY.md as specified.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The operators-guide examples use placeholder tokens (`<one-time-token>`, `eyJhbGc...`) as required by T-112-04. The oracle notes that `quirk serve --host 0.0.0.0` is lab-network-only per T-112-05.

## Known Stubs

None — all documentation is fully written. The live enroll→push→merge human-UAT remains deferred by design (established in CONTEXT.md / 112-01-SUMMARY.md).

## Self-Check: PASSED

- `quantum-chaos-enterprise-lab/expected_results_distributed.md`: FOUND
- `quantum-chaos-enterprise-lab/README.md` (distributed section): FOUND
- `docs/operators-guide.md` (§8): FOUND
- grep "Topology: distributed" oracle: PASS
- grep "crypto.internal" oracle: PASS
- grep "expected_results_distributed" README: PASS
- grep "## 8. Distributed Sensor Deployment" operators-guide: PASS
- grep "quirk sensor merge" operators-guide: PASS
- grep "APPDATA" operators-guide: PASS
- grep "scan.timeouts" operators-guide: PASS
- Commit `44c5c10`: FOUND
- Commit `9b0f58a`: FOUND
