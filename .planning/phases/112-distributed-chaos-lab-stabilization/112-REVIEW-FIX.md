---
phase: 112-distributed-chaos-lab-stabilization
fixed_at: 2026-05-26T00:00:00Z
review_path: .planning/phases/112-distributed-chaos-lab-stabilization/112-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 112: Code Review Fix Report

**Fixed at:** 2026-05-26
**Source review:** .planning/phases/112-distributed-chaos-lab-stabilization/112-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7
- Fixed: 7
- Skipped: 0

## Fixed Issues

### CR-01: sensor compose command passes non-existent flags

**Files modified:** `quantum-chaos-enterprise-lab/docker-compose.distributed.yml`, `quantum-chaos-enterprise-lab/sensor-config.yaml`, `tests/test_distributed_topology.py`
**Commit:** e5b0dc0
**Applied fix:** Replaced `command: ["sensor", "push", "--target", "crypto.internal:443", "--allow-self-signed"]` with an idle container approach: `entrypoint: []` + `command: ["tail", "-f", "/dev/null"]`. Created `quantum-chaos-enterprise-lab/sensor-config.yaml` with `targets.fqdns: [crypto.internal]` — the scan target is now supplied via config file as required by the `quirk sensor push` contract. Added `cap_add: [NET_RAW]` to both sensor services so nmap works without root. Mounted `./sensor-config.yaml:/quirk/sensor-config.yaml:ro` in both sensor services. Updated `test_both_sensors_scan_crypto_internal` to assert the config.yaml mount exists and contains `crypto.internal`, and assert the command does NOT contain `--target` or literal IPs.

### CR-02: healthcheck URL hits wrong path `/health` instead of `/api/health`

**Files modified:** `quantum-chaos-enterprise-lab/docker-compose.distributed.yml`
**Commit:** e5b0dc0
**Applied fix:** Changed console service healthcheck from `http://localhost:8512/health` to `http://localhost:8512/api/health`. Confirmed in `quirk/dashboard/api/app.py:108` that `application.include_router(health.router, prefix="/api")` — the route is `/api/health`, not `/health`.

### CR-03: SSRF guard blocks internal console URL (real product bug)

**Files modified:** `quirk/cli/sensor_cmd.py`, `tests/test_sensor_cmd.py`, `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh`
**Commit:** 680f94d
**Applied fix:** Added `--allow-internal-console` flag to `quirk sensor enroll` subparser. When set, `_cmd_enroll` calls `validate_external_url(console_url, allow_internal=True)` so RFC1918 console URLs are accepted. The flag is persisted in `sensor.yaml` as `allow_internal_console: true`. `_cmd_push` reads this value from `sensor.yaml` and passes it to `validate_external_url`, so subsequent pushes automatically honour the bypass without requiring the flag to be re-supplied. Cloud metadata service IPs (`169.254.169.254`, `fd00:ec2::254`) remain ALWAYS blocked regardless of the flag. `verify=True` and `follow_redirects=False` on `httpx.Client` are unchanged. Updated `distributed-e2e.sh` to pass `--allow-internal-console` on sensor enroll and `--scan-config /quirk/sensor-config.yaml` on sensor push. Updated `test_enroll_writes_sensor_yaml` to include `allow_internal_console` in the expected key set. Added two new tests: `test_enroll_allow_internal_console_passes_rfc1918` (enroll accepts RFC1918 URL with flag, persists it in sensor.yaml) and `test_enroll_allow_internal_console_persisted_for_push` (push reads allow_internal_console from sensor.yaml and calls validate_external_url with allow_internal=True).

**Note:** Fixed: requires human verification — the logic (allow_internal=True path through validate_external_url) is a conditional bypass; the unit tests confirm it but a live on-prem run should verify the full enroll→push flow with a private console URL.

### WR-01: `test_e2e_script_enroll_push_merge_order` ordering assertion fires on header comment

**Files modified:** `tests/test_distributed_topology.py`
**Commit:** e5b0dc0
**Applied fix:** Replaced `text.index("enroll")` / `text.index("push")` / `text.index("merge")` with a `_first_cmd_pos(keyword)` helper that uses `re.search(r'^\s*(?!\s*#).*quirk\s+.*{keyword}', text, re.MULTILINE)` to find the first actual `quirk ...` invocation rather than the first string occurrence (which was the header comment). The assertion now fires on the executable statements in the script body.

### WR-02: sensor.Dockerfile runs processes as root

**Files modified:** `quantum-chaos-enterprise-lab/sensor.Dockerfile`
**Commit:** 680f94d
**Applied fix:** Added `RUN useradd --create-home --shell /bin/bash quirk` + `USER quirk` + `WORKDIR /home/quirk` after the pip install step. nmap raw-socket access is granted via `cap_add: [NET_RAW]` in `docker-compose.distributed.yml` (added in the CR-01 fix commit) so nmap works without running as root. Added a comment explaining the nmap/cap relationship.

### WR-03: No guard on empty TOKEN_A / TOKEN_B before passing to --api-token

**Files modified:** `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh`
**Commit:** 680f94d
**Applied fix:** Added explicit empty-string guards after token extraction for both TOKEN_A and TOKEN_B:
```bash
if [[ -z "${TOKEN_A}" ]]; then
  echo "ERROR: enrollment failed for sensor-a (empty token — console may not be ready)" >&2
  exit 1
fi
```
Command-substitution failures do not trigger `set -e`; an empty token passed to `--api-token` would silently produce an invalid enrollment that causes sensor push to fail later with an opaque error.

### IN-01: `import re` inside a loop in `test_both_sensors_scan_crypto_internal`

**Files modified:** `tests/test_distributed_topology.py`
**Commit:** e5b0dc0
**Applied fix:** Moved `import re` to module-level alongside `import shutil`, `import subprocess`. Also added the constant `SENSOR_CONFIG = LAB_DIR / "sensor-config.yaml"` at module level.

## Skipped Issues

None — all findings were fixed.

---

**Verification results (post-fix):**
- `python -m compileall quirk run_scan.py`: PASS
- `pytest tests/test_distributed_topology.py tests/test_sensor_cmd.py tests/test_sensor_no_verify_false.py -q`: 40 passed, 0 failed
- `docker compose -f quantum-chaos-enterprise-lab/docker-compose.distributed.yml config -q`: PASS (Docker available)
- `bash -n quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh`: PASS
- `bash -n quantum-chaos-enterprise-lab/lab.sh`: PASS
- `grep verify=False quirk/cli/sensor_cmd.py`: no matches (verify=False gate stays green)

---

_Fixed: 2026-05-26_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
