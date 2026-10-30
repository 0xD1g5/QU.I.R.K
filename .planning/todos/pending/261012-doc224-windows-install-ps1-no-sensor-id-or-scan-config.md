---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); plan 224-15 pass over docs/operators-guide.md section 8.8 (Windows zip + Scheduled Task)
priority: high
area: packaging/windows/install.ps1, packaging/windows/uninstall.ps1, quirk/cli/sensor_cmd.py
status: pending
resolves_phase: null
owner: "999.129"
---

# Windows installer cannot produce a working sensor: no -SensorId, no scan config, and reinstall replaces the identity

`packaging/windows/install.ps1` runs `quirk.exe sensor enroll <ConsoleUrl> --segment ... --api-token <EnrollmentToken> --config ...` and
registers a daily task `quirk.exe sensor push --config <sensor.yaml>`. Three consequences follow from reading the script
against `quirk/cli/sensor_cmd.py` and `quirk/dashboard/api/routes/sensor.py`:

1. **Every push is rejected with HTTP 403.** `install.ps1` has no `-SensorId` parameter, so `sensor enroll` invents a random
   UUID (`sensor_cmd.py:244`). The console resolves the sensor from the bearer token and returns 403 `sensor_id mismatch` when the
   envelope's `sensor_id` differs (`routes/sensor.py`, the `sensor_id_mismatch` branch; pinned by
   `tests/test_sensor_auth_per_sensor.py::test_sensor_id_mismatch_returns_403`). The CI Windows E2E job passes `--sensor-id`
   explicitly (`.github/workflows/python-ci.yml:349`), so CI never exercises the installer path.
2. **The task pushes an empty result set.** The task action has no `--scan-config`; the default is a relative `config.yaml`
   (`sensor_cmd.py` `push_p.add_argument("--scan-config", default="config.yaml")`). When it is missing the local scan exits
   non-zero, `_cmd_push` only prints a warning (`sensor_cmd.py:754-755`), builds an envelope with zero endpoints and delivers it,
   so the console shows the sensor as `current` with nothing scanned. Reproduced the same code path with
   `sensor export-results --scan-config /nonexistent.yaml`: `WARNING: local scan exited with code 1`, `Exported 0 finding(s)`.
3. **`uninstall.ps1 -KeepConfig` does not preserve the identity.** `enroll` keeps an existing `sensor.yaml` only when its `sensor_id`
   equals the one being enrolled (`sensor_cmd.py:256`); the installer passes none, so a reinstall writes a new random `sensor_id` and
   HMAC key over the kept file. Reproduced with two consecutive `sensor enroll` calls (second without `--sensor-id`): `sensor_id`
   changed and `console_api_token` was overwritten.

`docs/operators-guide.md` section 8.8 now documents the workarounds (edit `sensor_id` in `sensor.yaml`; repoint the task with
`New-ScheduledTaskAction`/`Set-ScheduledTask` and a full `--scan-config` path).

- [ ] Add `-SensorId` and `-ScanConfig` parameters to `install.ps1`, passed through to `sensor enroll --sensor-id` and `sensor push --scan-config`.
- [ ] Make `-KeepConfig` reinstalls reuse the kept `sensor_id` (read it from the existing file when `-SensorId` is omitted).
- [ ] Decide whether `sensor push` should exit non-zero (or refuse to push) when the local scan fails, instead of delivering an empty envelope.
- [ ] Add a Windows smoke test that drives `install.ps1` and checks that a push is accepted.

## Feasibility & Effort

**CONFIRMED** by reading `install.ps1` (no such parameters), `sensor_cmd.py:206-296`, the 403 branch in `routes/sensor.py`, and a live
reproduction of items 2 and 3 on this host. Item 1 is confirmed by the code path and the passing 403 test but not by a Windows run. Effort **S**
for the script parameters and docs; **M** to add the Windows smoke test. Unknown: whether any deployed Windows sensors were enrolled through
the installer (they would need their `sensor.yaml` edited). No spike needed beyond one Windows VM run.
