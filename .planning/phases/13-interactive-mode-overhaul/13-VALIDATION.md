---
phase: 13
slug: interactive-mode-overhaul
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-06
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini / pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_interactive_mode.py -x -q` |
| **Full suite command** | `python -m pytest -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_interactive_mode.py -x -q`
- **After every plan wave:** Run `python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 0 | INTER-01–10 | unit | `python -m pytest tests/test_interactive_mode.py -x -q` | ❌ W0 | ⬜ pending |
| 13-02-01 | 02 | 1 | INTER-01 | unit | `python -m pytest tests/test_interactive_mode.py::test_no_timezone_prompt -x -q` | ✅ | ⬜ pending |
| 13-02-02 | 02 | 1 | INTER-02 | unit | `python -m pytest tests/test_interactive_mode.py::test_no_sni_prompt -x -q` | ✅ | ⬜ pending |
| 13-02-03 | 02 | 1 | INTER-03 | unit | `python -m pytest tests/test_interactive_mode.py::test_no_adcs_prompt -x -q` | ✅ | ⬜ pending |
| 13-02-04 | 02 | 1 | INTER-04 | unit | `python -m pytest tests/test_interactive_mode.py::test_connector_labels -x -q` | ✅ | ⬜ pending |
| 13-02-05 | 02 | 1 | INTER-05 | unit | `python -m pytest tests/test_interactive_mode.py::test_optional_scanners -x -q` | ✅ | ⬜ pending |
| 13-02-06 | 02 | 1 | INTER-06 | unit | `python -m pytest tests/test_interactive_mode.py::test_profile_selection -x -q` | ✅ | ⬜ pending |
| 13-02-07 | 02 | 1 | INTER-07 | unit | `python -m pytest tests/test_interactive_mode.py::test_no_adcs_in_config -x -q` | ✅ | ⬜ pending |
| 13-02-08 | 02 | 1 | INTER-08 | unit | `python -m pytest tests/test_interactive_mode.py::test_data_classification -x -q` | ✅ | ⬜ pending |
| 13-02-09 | 02 | 1 | INTER-09 | unit | `python -m pytest tests/test_interactive_mode.py::test_timezone_auto_detect -x -q` | ✅ | ⬜ pending |
| 13-02-10 | 02 | 1 | INTER-10 | unit | `python -m pytest tests/test_interactive_mode.py::test_operator_context_integration -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_interactive_mode.py` — stubs for INTER-01 through INTER-10 (RED tests)
- [ ] `tests/conftest.py` — verify shared fixtures exist or add interactive mode fixtures

*If test file exists from Phase 12 scaffold: update to match Phase 13 implementation targets.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Connector labels display "fully implemented" with credential warnings | INTER-04 | UI string rendering depends on terminal output | Run `quirk` interactively, select AWS/Azure connector, verify no "(stub)" label appears |
| Profile selection replaces raw timeout/concurrency fields | INTER-06 | End-to-end interactive flow | Run `quirk`, choose "standard" profile, verify generated config has correct timeout/concurrency values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
