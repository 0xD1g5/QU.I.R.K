---
phase: 10
slug: v39-gap-closure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | CBOM-03 | unit | `python -m pytest tests/test_scan.py -k "quantum_safety" -x -q` | ✅ | ⬜ pending |
| 10-01-02 | 01 | 1 | UI-01, UI-03 | integration | `python -m pytest tests/test_packaging.py -x -q` | ✅ W0 | ⬜ pending |
| 10-01-03 | 01 | 2 | BRAND-04 | unit | `python -m pytest tests/test_cli_init.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_packaging.py` — stub for pip wheel smoke test (PACKAGE-01 / UI-01, UI-03)

*Existing infrastructure covers quantum_safety_label and cli_init tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `pip install --no-editable .` followed by `quirk serve` loads dashboard | UI-01, UI-03 | Requires wheel build + running server | Build wheel, install in venv, run `quirk serve`, open browser, verify no 404s on UI routes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
