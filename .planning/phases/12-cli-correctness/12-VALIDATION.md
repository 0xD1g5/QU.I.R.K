---
phase: 12
slug: cli-correctness
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `python3 -m pytest tests/test_cli_version.py tests/test_cli_init.py tests/test_cli_correctness.py -v` |
| **Full suite command** | `python3 -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_cli_version.py tests/test_cli_init.py tests/test_cli_correctness.py -v`
- **After every plan wave:** Run `python3 -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green (199+ tests)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 0 | CLI-01,02,03,04 | unit/integration | `python3 -m pytest tests/test_cli_correctness.py -v` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | CLI-01 | integration | `python3 -m pytest tests/test_cli_correctness.py::test_init_config_loads_without_error -x` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | CLI-01 | unit | `python3 -m pytest tests/test_cli_correctness.py::test_template_field_alignment -x` | ❌ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | CLI-02 | unit/grep | `python3 -m pytest tests/test_cli_correctness.py::test_no_quirk_scan_references -x` | ❌ W0 | ⬜ pending |
| 12-03-01 | 03 | 1 | CLI-03 | unit | `python3 -m pytest tests/test_cli_correctness.py::test_no_owner_placeholder -x` | ❌ W0 | ⬜ pending |
| 12-04-01 | 04 | 1 | CLI-04 | unit | `python3 -m pytest tests/test_cli_correctness.py::test_version_consistency -x` | ❌ W0 | ⬜ pending |
| 12-04-02 | 04 | 1 | CLI-04 | integration | `python3 -m pytest tests/test_cli_version.py::test_version_flag -x` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli_correctness.py` — new test file covering:
  - CLI-01: `test_init_config_loads_without_error` (integration — runs quirk init, loads YAML, no TypeError)
  - CLI-01: `test_template_field_alignment` (unit — all template keys match ConnectorsCfg/ScanCfg/TargetsCfg attrs)
  - CLI-02: `test_no_quirk_scan_references` (unit/grep — no `quirk scan` in .py/.md/.yaml outside superpowers/specs/)
  - CLI-03: `test_no_owner_placeholder` (unit — no `[owner]` in docs/getting-started.md)
  - CLI-04: `test_version_consistency` (unit — all version constants equal `"4.1.0"`: `__init__.py`, `writer.py` ×2, `builder.py`, `config.py` ×2)

Existing tests (`test_cli_version.py`, `test_cli_init.py`) remain unchanged — regression coverage only.

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
