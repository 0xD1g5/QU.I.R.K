---
phase: 63
slug: scheduled-continuous-scanning
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-10
---

# Phase 63 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, `pyproject.toml testpaths = ["tests"]`) |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `pytest tests/test_schedule_cmd.py tests/test_scheduler_cmd.py tests/test_schedules_api.py -x` |
| **Full suite command** | `pytest tests/ -m "not slow and not live_infra"` |
| **Estimated runtime** | ~15 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_schedule_cmd.py tests/test_scheduler_cmd.py tests/test_schedules_api.py -x`
- **After every plan wave:** Run `pytest tests/ -m "not slow and not live_infra"`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds (quick), 60 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 63-01-01 | 01 | 1 | SCHED-01 | — | cron expression validated before persist | unit | `pytest tests/test_schedule_cmd.py::test_schedule_add_persists -x` | ❌ Wave 0 | ⬜ pending |
| 63-01-02 | 01 | 1 | SCHED-01 | — | invalid cron rejected | unit | `pytest tests/test_schedule_cmd.py::test_schedule_add_invalid_cron -x` | ❌ Wave 0 | ⬜ pending |
| 63-01-03 | 01 | 1 | SCHED-01 | — | list shows persisted row | unit | `pytest tests/test_schedule_cmd.py::test_schedule_list_shows_row -x` | ❌ Wave 0 | ⬜ pending |
| 63-02-01 | 02 | 1 | SCHED-02 | — | dispatcher marks run running→completed | unit | `pytest tests/test_scheduler_cmd.py::test_dispatch_lifecycle -x` | ❌ Wave 0 | ⬜ pending |
| 63-02-02 | 02 | 1 | SCHED-02 | — | disabled schedules skipped | unit | `pytest tests/test_scheduler_cmd.py::test_disabled_schedule_skipped -x` | ❌ Wave 0 | ⬜ pending |
| 63-02-03 | 02 | 1 | SCHED-02 | — | stale running rows recovered on startup | unit | `pytest tests/test_scheduler_cmd.py::test_startup_recovery -x` | ❌ Wave 0 | ⬜ pending |
| 63-03-01 | 03 | 2 | SCHED-01 | T-58 | GET /api/schedules returns 200 | unit | `pytest tests/test_schedules_api.py::test_get_schedules_empty -x` | ❌ Wave 0 | ⬜ pending |
| 63-03-02 | 03 | 2 | SCHED-01 | T-58 | POST /api/schedules requires auth+csrf | unit | `pytest tests/test_schedules_api.py::test_post_schedule_creates -x` | ❌ Wave 0 | ⬜ pending |
| 63-03-03 | 03 | 2 | SCHED-03 | T-58 | PATCH toggle requires X-Quirk-Request | unit | `pytest tests/test_schedules_api.py::test_patch_requires_csrf -x` | ❌ Wave 0 | ⬜ pending |
| 63-03-04 | 03 | 2 | SCHED-03 | T-58 | PATCH flips enabled flag | unit | `pytest tests/test_schedules_api.py::test_patch_toggle_enabled -x` | ❌ Wave 0 | ⬜ pending |
| 63-03-05 | 03 | 2 | SCHED-03 | T-58 | GET includes next_run_at field | unit | `pytest tests/test_schedules_api.py::test_get_includes_next_run -x` | ❌ Wave 0 | ⬜ pending |
| 63-03-06 | 03 | 2 | SCHED-03 | T-58 | no unprotected mutating routes | unit | `pytest tests/test_api_auth.py::test_no_unprotected_mutating_routes -x` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_schedule_cmd.py` — stubs for SCHED-01 CLI commands
- [ ] `tests/test_scheduler_cmd.py` — stubs for SCHED-02 dispatcher lifecycle
- [ ] `tests/test_schedules_api.py` — stubs for SCHED-01/03 API routes
- [ ] `tests/conftest.py` — add `in_memory_db` fixture for schedule model tests

*Existing pytest infrastructure covers framework; only new test stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard /schedules page renders, toggle works | SCHED-03 | React UI requires browser | Open dashboard, navigate to /schedules, flip a toggle, confirm it persists on refresh |
| `quirk scheduler run` dispatches a real scan at cron time | SCHED-02 | Long-running process, real subprocess | Set cron to */1 * * * * (every minute), run scheduler, watch for completed run row in DB |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
