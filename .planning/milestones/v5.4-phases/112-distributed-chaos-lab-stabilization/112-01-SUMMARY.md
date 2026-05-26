---
phase: 112-distributed-chaos-lab-stabilization
plan: "01"
subsystem: chaos-lab
tags: [distributed, docker-compose, topology, lab, sensor, tls, merge-03]
dependency_graph:
  requires: []
  provides:
    - docker-compose.distributed.yml (two-segment topology)
    - sensor.Dockerfile (patch-pinned sensor/console image)
    - distributed-e2e.sh (enroll→push→merge orchestrator)
    - lab.sh distributed arm
    - tests/test_distributed_topology.py (CI floor)
  affects:
    - quantum-chaos-enterprise-lab/lab.sh (distributed arm added)
    - tests/ (topology test added)
tech_stack:
  added: []
  patterns:
    - Docker bridge networking with IPAM subnets
    - Per-network DNS alias (crypto.internal) for host:port reproduction
    - PyYAML compose-parse pytest pattern (test_chaos_lab_image_pinning.py analog)
key_files:
  created:
    - quantum-chaos-enterprise-lab/docker-compose.distributed.yml
    - quantum-chaos-enterprise-lab/sensor.Dockerfile
    - quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh
    - tests/test_distributed_topology.py
  modified:
    - quantum-chaos-enterprise-lab/lab.sh
decisions:
  - "LAB-02 linchpin confirmed: tls_scanner.py:188-189 and :351-352 record CryptoEndpoint(host=host) with the configured string verbatim — not a resolved IP"
  - "crypto.internal alias mechanism: each segment's TLS target carries the alias on its OWN network; per-network Docker DNS resolves to each segment's reachable target independently"
  - "Sensors scan crypto.internal:443 (not a literal IP) so both record identical host:port strings, differing only by sensor_id/segment"
  - "lab.sh distributed arm scopes COMPOSE_FILE + PROJECT_NAME to its own case block — ALL_PROFILES path byte-for-byte unchanged (LAB-03)"
metrics:
  duration: "~3 minutes"
  completed: "2026-05-26"
  tasks_completed: 3
  files_created: 4
  files_modified: 1
---

# Phase 112 Plan 01: Lab Topology Summary

Two-network distributed chaos-lab topology with crypto.internal DNS-alias mechanism, patch-pinned sensor image, enroll→push→merge e2e orchestrator, lab.sh distributed command, and static topology pytest test.

## What Was Built

### Task 1: Distributed Compose Topology + sensor.Dockerfile

**Files:** `quantum-chaos-enterprise-lab/docker-compose.distributed.yml`, `quantum-chaos-enterprise-lab/sensor.Dockerfile`
**Commit:** `158381e`

Built the two-segment distributed topology. Three isolated bridge networks with distinct subnets prevent the Docker "Pool overlaps" error. Each segment's TLS target carries `crypto.internal` as a network alias on its own segment network — Docker per-network embedded DNS resolves `crypto.internal` to each segment's own reachable target so sensor-a and sensor-b can each reach a TLS endpoint at the same hostname.

**LAB-02 linchpin (confirmed before building):**
- `quirk/scanner/tls_scanner.py:188-189`: `ep = CryptoEndpoint(host=host, ...)` — sslyze path
- `quirk/scanner/tls_scanner.py:351-352`: `ep = CryptoEndpoint(host=host, ...)` — fallback path

Both paths record the configured scan-target string verbatim on `CryptoEndpoint.host`. Because both sensors scan `crypto.internal:443`, both record `host=crypto.internal` — the identical host:port string differing only by sensor_id/segment. This is the MERGE-03 reproduction under real Docker networking.

Services:
- `tls-target-a`: nginx:1.28.0, segment-a network, `aliases: [crypto.internal]` on segment-a, `expose: ["443"]`
- `tls-target-b`: nginx:1.28.0, segment-b network, `aliases: [crypto.internal]` on segment-b, `expose: ["443"]`
- `sensor-a`: build from sensor.Dockerfile, networks: [segment-a, console-net], command scans `crypto.internal:443`
- `sensor-b`: build from sensor.Dockerfile, networks: [segment-b, console-net], command scans `crypto.internal:443`
- `console`: build from sensor.Dockerfile, command: `serve --host 0.0.0.0 --port 8512`, healthcheck on `/health`, named volume `console-data`

`sensor.Dockerfile`: `FROM python:3.11.12-slim` (patch-pinned, CHAOS-05), apt installs nmap/curl/ca-certificates, `pip install --no-cache-dir ".[all]"` from repo checkout, ENTRYPOINT `["quirk"]`.

**Verification:** `docker compose -f docker-compose.distributed.yml config -q` exits 0.

### Task 2: distributed-e2e.sh + lab.sh distributed arm

**Files:** `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh`, `quantum-chaos-enterprise-lab/lab.sh`
**Commit:** `5f01a95`

Created `distributed-e2e.sh` orchestrating the enroll → push → merge workflow:
1. `quirk console enroll` per sensor (inside console container, `-T` for clean stdout capture)
2. `quirk sensor enroll <console_url> --segment <label> --api-token "$TOKEN"` per sensor
3. `quirk sensor push` per sensor (scans crypto.internal:443, pushes to console)
4. `quirk sensor merge` on console (unified CBOM + score)

Added `distributed)` case arm to `lab.sh` at line 216. The arm reassigns `COMPOSE_FILE` and `PROJECT_NAME` at entry before any `compose()` call — scoped to the arm only. Subcmds: `up` (with CHAOS-05 gate), `down`, `status`, `logs`, `e2e`. Usage text updated.

**ALL_PROFILES / `all` arm path unchanged** — LAB-03 no-drift guarantee satisfied.

### Task 3: Static Topology Pytest (CI Floor)

**File:** `tests/test_distributed_topology.py`
**Commit:** `663e2a7`

Ten test functions mirroring the `test_chaos_lab_image_pinning.py` PyYAML pattern:

| Test | What it asserts |
|------|-----------------|
| `test_distributed_compose_file_exists` | compose file present |
| `test_config_validates` | `docker compose config` exits 0 (skip if no docker) |
| `test_two_bridge_networks` | >= 2 networks defined |
| `test_segment_networks_have_distinct_subnets` | segment-a=10.10.0.0/24, segment-b=10.20.0.0/24, subnets differ |
| `test_crypto_internal_alias_per_segment` | tls-target-a carries alias on segment-a; tls-target-b on segment-b |
| `test_both_sensors_scan_crypto_internal` | both sensors command includes `crypto.internal:443`; no literal-IP target |
| `test_one_sensor_service_per_segment` | >= 2 sensor services; each on one segment + console-net; no cross-segment |
| `test_one_console_service` | >= 1 console service |
| `test_sensor_dockerfile_base_pinned` | FROM python:3.11.12-slim |
| `test_e2e_script_enroll_push_merge_order` | enroll index < push index < merge index in distributed-e2e.sh |

All 10 tests pass. `test_config_validates` passes because Docker is available on this machine.

## Verification Results

- `docker compose -f quantum-chaos-enterprise-lab/docker-compose.distributed.yml config -q`: **PASS** (Docker available)
- `bash -n quantum-chaos-enterprise-lab/lab.sh`: **PASS**
- `bash -n quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh`: **PASS**
- `pytest tests/test_distributed_topology.py -q`: **10 passed** (Docker available — test_config_validates ran)
- `python -m compileall tests/test_distributed_topology.py`: **PASS**
- ALL_PROFILES / `all` arm unchanged: **CONFIRMED** (grep)

## Deviations from Plan

None — plan executed exactly as written. The crypto.internal alias mechanism from CONTEXT.md was implemented as specified. The LAB-02 linchpin was confirmed before building the oracle-dependency topology.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| threat_flag: information_disclosure | distributed-e2e.sh | Bearer tokens captured via stdout — lab-ephemeral, accepted per T-112-02 |
| threat_flag: network_exposure | docker-compose.distributed.yml | console publishes port 8512 to host for e2e; console-net is isolated bridge — accepted per T-112-03 |

Both flags were pre-analyzed in the plan's threat model with `accept` disposition.

## Plan 02 Oracle Reference

**Service and network names for the Plan 02 expected-results oracle:**
- Networks: `segment-a` (10.10.0.0/24), `segment-b` (10.20.0.0/24), `console-net` (10.30.0.0/24)
- TLS targets: `tls-target-a` (10.10.0.10 on segment-a), `tls-target-b` (10.20.0.10 on segment-b)
- Both targets reachable at alias: `crypto.internal:443`
- Sensors: `sensor-a` (segment-a + console-net), `sensor-b` (segment-b + console-net)
- Console: `console` (console-net, port 8512)
- Expected CBOM outcome: 2 `CryptoEndpoint` components with `host=crypto.internal`, differing only by `sensor_id` (`sensor-a` / `sensor-b`)
- LAB-02 linchpin file:line: `quirk/scanner/tls_scanner.py:188-189` (sslyze path) and `:351-352` (fallback path)

## Known Stubs

None — all topology artifacts are fully wired. The live enroll→push→merge run is human-UAT (deferred by design per CONTEXT.md verification approach decision).

## Self-Check: PASSED

- `quantum-chaos-enterprise-lab/docker-compose.distributed.yml`: FOUND
- `quantum-chaos-enterprise-lab/sensor.Dockerfile`: FOUND
- `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh`: FOUND
- `tests/test_distributed_topology.py`: FOUND
- `quantum-chaos-enterprise-lab/lab.sh` (distributed arm): FOUND at line 216
- Commit `158381e`: FOUND
- Commit `5f01a95`: FOUND
- Commit `663e2a7`: FOUND
