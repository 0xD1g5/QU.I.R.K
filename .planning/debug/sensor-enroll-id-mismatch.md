---
slug: sensor-enroll-id-mismatch
status: resolved
trigger: "v5.4 distributed sensor push fails with HTTP 404 Unknown sensor_id — sensor enroll and console enroll mint independent sensor_ids that never reconcile"
created: 2026-05-26T21:34:38Z
updated: 2026-05-26T21:45:00Z
---

# Debug Session: sensor-enroll-id-mismatch

## Symptoms

- **Expected:** `./quantum-chaos-enterprise-lab/lab.sh distributed e2e` enrolls both sensors, each scans its segment's `crypto.internal:443`, pushes findings to the console with HTTP 200, and the console ingests them for merge into a unified CBOM (UAT-112-03).
- **Actual:** sensor-a push is rejected with `ERROR: push rejected with HTTP 404`. Console log shows `POST /api/sensor/push HTTP/1.1" 404 Not Found` from 10.30.0.3. The request reaches the registered route; the 404 is raised inside the handler at the sensor lookup.
- **Error messages:**
  - `ERROR: push rejected with HTTP 404` (sensor side)
  - `INFO: ... "POST /api/sensor/push HTTP/1.1" 404 Not Found` (console side)
  - `HTTPException(status_code=404, detail="Unknown sensor_id")` at quirk/dashboard/api/routes/sensor.py:312-315
  - Secondary: `WARNING: local scan exited with code 2` during the sensor push step
- **Timeline:** Never worked end-to-end via the real two-command flow. UAT-112-03 was deferred to live human-UAT during v5.4 (Docker unavailable in prior sessions); first live run is today (2026-05-26).
- **Reproduction:** Lab UP (docker compose project `quirk-dist`, file `quantum-chaos-enterprise-lab/docker-compose.distributed.yml`). Run `./quantum-chaos-enterprise-lab/lab.sh distributed e2e` (script: `quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh`).

## Initial Findings (from live UAT investigation)

- `quirk console enroll --segment segment-a --sensor-id sensor-a` (e2e Step 1) provisions a `Sensor` row keyed `sensor-a` in the console DB.
- `quirk sensor enroll <url> --segment segment-a --api-token ...` (e2e Step 2) called `quirk/cli/sensor_cmd.py:230` → `sensor_id = str(uuid.uuid4())`, writing a fresh random UUID into `sensor.yaml`. It had NO `--sensor-id` flag and makes NO HTTP call to the console.
- The push envelope carries the UUID; the console only knows `sensor-a`; lookup at sensor.py:312 fails → 404.
- Phase 109 unit tests passed because they inject matching `Sensor`/`CryptoEndpoint` rows in-memory, never exercising the real two-command enroll handshake.

## Intended Contract (established from design docs)

- 109-CONTEXT.md `<deferred>` FLAGGED the provisioning seam exactly; 109-RESEARCH.md "Provisioning Gap — Resolved Decision" (L739-779) locked **Option (a)**: the console provisions the `sensors` row (`quirk console enroll --sensor-id <uuid>`) and the sensor operator binds the sensor to that SAME `sensor_id` in Step 2. The documented workflow shows the identical `<uuid>` flowing from console Step 1 into sensor Step 2 — which is impossible because `quirk sensor enroll` had no `--sensor-id` flag. The CLI never implemented the documented contract.

## Current Focus

hypothesis: RESOLVED — see Resolution.
next_action: none.
test: `./quantum-chaos-enterprise-lab/lab.sh distributed e2e` completes with both pushes accepted and merge producing two distinct-sensor CryptoEndpoint components.
expecting: HTTP 200 on both pushes; no "Unknown sensor_id"; merge score emitted.

## Evidence

- timestamp: 2026-05-26T21:30Z
  observation: console log confirms POST /api/sensor/push returns 404 (request reached route, handler raised Unknown sensor_id). sensor_cmd.py:230 mints uuid4; no --sensor-id arg in enroll parser; enroll body makes no POST to console.
- timestamp: 2026-05-26T21:40Z
  observation: 109-RESEARCH.md L746-779 documents Option (a) — console provisions sensor_id, sensor binds same id. console_cmd.py enroll accepts --sensor-id; sensor_cmd.py enroll did not. Confirms primary defect = missing --sensor-id on sensor enroll + harness not threading it.
- timestamp: 2026-05-26T21:41Z
  observation: After adding --sensor-id (CLI + harness) and rebuilding images, both pushes succeeded (no 404), but merge reported "No endpoints found". Secondary "local scan exited with code 2" persisted.
- timestamp: 2026-05-26T21:42Z
  observation: Root-caused secondary symptom: _run_local_scan invoked `run_scan --output <dir>`, but run_scan.py has NO --output flag → argparse fatal exit 2; scan never ran. run_scan writes its DB to cfg.output.db_path relative to CWD (run_scan.py:923). The lab sensor-config.yaml also lacked the required `output:` block (KeyError 'output'). Lab targets are RFC1918 so the scan needs --allow-internal-targets.
- timestamp: 2026-05-26T21:44Z
  observation: After fixing _run_local_scan (drop --output; cwd=output_dir; forward --allow-internal-targets from allow_internal_console) + adding relative `output:` block to sensor-config.yaml, full e2e exit 0: both pushes complete, merge Score 95 (EXCELLENT), CBOM JSON+XML emitted.
- timestamp: 2026-05-26T21:45Z
  observation: DB verification — crypto.internal:443 present under BOTH sensor-a/segment-a AND sensor-b/segment-b (distinct sensor_ids); 2 sensor_pushes. MERGE-03 invariant satisfied under real Docker networking. 78 sensor/console/topology unit tests pass; new regression test test_enroll_binds_provided_sensor_id added. 3 full-suite failures confirmed PRE-EXISTING on clean main (windows-smoke mock lambda missing allow_internal kwarg; email-wiring) — not caused by this work.

## Eliminated

- DB-path divergence between console enroll CLI and push handler: both use `_default_db_path()` → `./quirk-output/quirk.db` resolved against the same CWD (`/home/quirk`). Rows written by enroll are visible to the handler. Not the cause.
- Auth/HMAC rejection: pushes return 200, not 401/403. Shared-token model works as designed.

## Resolution

root_cause: Two independent defects. (1) PRIMARY 404: the v5.4 enrollment contract (109-RESEARCH Option a) requires the console-minted sensor_id to flow into `quirk sensor enroll`, but that command had no `--sensor-id` flag and always minted its own random UUID — so the push envelope's sensor_id never matched any console `sensors` row → "Unknown sensor_id" 404. (2) SECONDARY scan-exit-2 / empty merge: `_run_local_scan` invoked `run_scan` with a nonexistent `--output` flag (argparse fatal exit 2, scan never ran); the lab `sensor-config.yaml` also lacked the required `output:` block, and RFC1918 lab targets need `--allow-internal-targets`.

fix: (1) Added optional `--sensor-id` to `quirk sensor enroll` (binds to console-provisioned identity; generates+prints a UUID when omitted, preserving backward compat) and threaded `--sensor-id sensor-a/-b` through the e2e harness. (2) Rewrote `_run_local_scan` to drop the unsupported `--output`, run the subprocess with `cwd=output_dir` (run_scan writes to cfg.output.db_path relative to CWD), and forward `--allow-internal-targets` gated on the sensor's persisted `allow_internal_console`; added a relative `output:` block to the lab `sensor-config.yaml`. Added regression test `test_enroll_binds_provided_sensor_id`. Files: quirk/cli/sensor_cmd.py, quantum-chaos-enterprise-lab/scripts/distributed-e2e.sh, quantum-chaos-enterprise-lab/sensor-config.yaml, tests/test_sensor_cmd.py.

verification: `./quantum-chaos-enterprise-lab/lab.sh distributed e2e` exit 0 — both pushes accepted, merge Score 95 (EXCELLENT), CBOM JSON+XML written; DB shows crypto.internal:443 under both sensor-a and sensor-b (MERGE-03 satisfied); 78 targeted unit tests pass.


## Specialist Review

Skill: python-expert-best-practices-code-review (specialist_hint: python)
Result: LOOKS_GOOD.
- `--allow-internal-targets` is gated on the operator's explicit `allow_internal_console` opt-in (not unconditional) — preserves SSRF posture; cloud-metadata IPs still blocked by run_scan.
- subprocess stays list-form, no shell=True (honors T-63-07 + subprocess-only test gate).
- Duplicate `getattr(args, "sensor_id", None)` is intentional defensive style consistent with the file's Args-stub pattern; PEP 8 + minimal-diff respected.
No changes required.
