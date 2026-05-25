---
phase: 108
slug: sensor-push-cli-windows-ci
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-25
---

# Phase 108 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml / pytest.ini (existing) |
| **Quick run command** | `pytest tests/ -k "sensor or no_redirect or posix" -q` |
| **Full suite command** | `pytest tests/ -q && python -m compileall quirk run_scan.py` |
| **Estimated runtime** | ~60 seconds (quick), full suite longer |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Filled by the planner per task. Each requirement below must map to at least one automated test. Windows-only behavior (SENSOR-06) is validated on the `windows-latest` CI runner, not locally.

| Requirement | Secure Behavior | Test Type | Automated Command | Status |
|-------------|-----------------|-----------|-------------------|--------|
| STAB-02 | `_NoRedirectHandler` single source, both callers import it | unit/import | `pytest tests/ -k no_redirect` | ⬜ pending |
| SENSOR-01 | enroll writes bound sensor.yaml, returns one-time token (not persisted) | unit | `pytest tests/ -k sensor_enroll` | ⬜ pending |
| SENSOR-02 | push POSTs over HTTPS with tenacity retry; `verify=False` absent (grep gate) | unit + grep gate | `pytest tests/ -k "sensor_push or verify_gate"` | ⬜ pending |
| SENSOR-03 | offline → spool to bounded dir; retry next push; FIFO; delete on 200/409 | unit | `pytest tests/ -k spool` | ⬜ pending |
| SENSOR-04 | export-results == push payload bytes; console import-results ingests, skips replay window | unit | `pytest tests/ -k "export_results or import_results"` | ⬜ pending |
| SENSOR-05 | POSIX-ism audit: scheduler_cmd path anchored, SIGTERM guarded; platformdirs resolves dirs | unit | `pytest tests/ -k "posix or platformdirs"` | ⬜ pending |
| SENSOR-06 | windows-latest smoke: no backslash paths in serialized payload, clean shutdown | CI (windows) | `.github/workflows/*windows*` job (hard gate) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/sensor/` (or `tests/test_sensor_*.py`) — stub files for SENSOR-01..05
- [ ] Reuse existing conftest `QUIRK_DB_PATH` fixture for any DB-touching enroll tests
- [ ] Add `platformdirs`, `tenacity`, `zstandard` to deps (zstandard is NOT yet present despite arch-doc claim)

*New deps must be declared before tests that import them run.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Windows runtime correctness | SENSOR-06 | Linux chaos lab cannot reproduce Windows path/signal behavior | Validated by the `windows-latest` CI job, not local manual steps; treat CI green as the gate |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
