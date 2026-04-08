---
phase: 16
slug: v4-1-gap-closure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_cli_version.py tests/test_interactive_output_dir.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_cli_version.py tests/test_interactive_output_dir.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | CLI-04 | unit | `python -m pytest tests/test_cli_version.py -v` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 1 | SCORE-04 | unit | `python -m pytest tests/test_interactive_output_dir.py -v` | ❌ W0 | ⬜ pending |
| 16-02-01 | 02 | 2 | CLI-04 | unit | `python -m pytest tests/test_cli_version.py -v` | ✅ | ⬜ pending |
| 16-02-02 | 02 | 2 | SCORE-04 | unit | `python -m pytest tests/test_interactive_output_dir.py -v` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cli_version.py` — RED test: `importlib.metadata.version("quirk")` returns "4.1.0"
- [ ] `tests/test_interactive_output_dir.py` — RED test: interactive.py output dir default is "quirk-output"

*Wave 0 creates the test files in Plan 16-01.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Flow C: wizard → scan → dashboard with correct profile | SCORE-04 | Requires interactive terminal session | Run `python -m quirk interactive`, accept all defaults, run scan, verify dashboard reads from `quirk-output/` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
