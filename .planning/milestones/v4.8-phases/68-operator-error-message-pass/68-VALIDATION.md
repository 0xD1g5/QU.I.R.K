---
phase: 68
slug: operator-error-message-pass
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-14
---

# Phase 68 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/test_install_errors.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_install_errors.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 68-01-01 | 01 | 1 | UX-01 | — | error registry is read-only (frozen dataclass) | unit | `python -m pytest tests/ -k test_errors -x -q` | ❌ W0 | ⬜ pending |
| 68-01-02 | 01 | 1 | UX-01 | — | format_error returns stable QRK string | unit | `python -m pytest tests/ -k test_format_error -x -q` | ❌ W0 | ⬜ pending |
| 68-02-01 | 02 | 1 | UX-01 | — | quirk errors prints all codes | integration | `python -m pytest tests/ -k test_errors_cmd -x -q` | ❌ W0 | ⬜ pending |
| 68-03-01 | 03 | 2 | UX-01 | — | CLI error paths emit QRK codes | unit | `python -m pytest tests/test_scan_robustness.py -x -q` | ✅ | ⬜ pending |
| 68-04-01 | 04 | 2 | UX-01 | — | dashboard HTTPException uses QRK format | unit | `python -m pytest tests/test_api_auth.py tests/test_jobs_api.py tests/test_qramm_router.py tests/test_schedules_api.py -x -q` | ✅ | ⬜ pending |
| 68-05-01 | 05 | 3 | UX-02 | — | install errors emit QRK-INSTALL-NNN format | smoke | `python -m pytest tests/test_install_errors.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_install_errors.py` — subprocess smoke tests for UX-02 (missing extra, missing nmap, port conflict, unreadable db)
- [ ] `tests/test_errors_cmd.py` — stubs for `quirk errors` command tests

*Existing infrastructure (pytest + conftest.py) covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `quirk errors --dump-md` output matches committed `docs/error-codes.md` | UX-01 | File generation diff check | Run `quirk errors --dump-md > /tmp/codes.md && diff /tmp/codes.md docs/error-codes.md` |
| `quirk doctor` failure messages use QRK format | UX-02 | Requires controlled missing-dependency environment | Run `quirk doctor` with nmap uninstalled; verify `[QRK-INSTALL-NNN]` in output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
