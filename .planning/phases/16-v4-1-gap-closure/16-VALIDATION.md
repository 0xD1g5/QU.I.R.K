---
phase: 16
slug: v4-1-gap-closure
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 16 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_v41_gap_closure.py -v` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_v41_gap_closure.py -v`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 1 | CLI-04 | unit | `python -m pytest tests/test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0 tests/test_v41_gap_closure.py::TestV41GapClosure::test_pyproject_version_field_is_4_1_0 -v` | W0 | pending |
| 16-01-02 | 01 | 1 | SCORE-04 | unit | `python -m pytest tests/test_v41_gap_closure.py::TestV41GapClosure::test_interactive_output_dir_default_is_quirk_output tests/test_v41_gap_closure.py::TestV41GapClosure::test_interactive_db_path_default_is_quirk_output -v` | W0 | pending |
| 16-02-01 | 02 | 2 | CLI-04 | unit | `python -m pytest tests/test_v41_gap_closure.py::TestV41GapClosure::test_package_manifest_version_is_4_1_0 tests/test_v41_gap_closure.py::TestV41GapClosure::test_pyproject_version_field_is_4_1_0 -v` | yes | pending |
| 16-02-02 | 02 | 2 | SCORE-04 | unit | `python -m pytest tests/test_v41_gap_closure.py::TestV41GapClosure::test_interactive_output_dir_default_is_quirk_output tests/test_v41_gap_closure.py::TestV41GapClosure::test_interactive_db_path_default_is_quirk_output -v` | yes | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_v41_gap_closure.py` -- RED tests: 2 for CLI-04 (metadata version + pyproject source) and 2 for SCORE-04 (output dir + db path defaults)

*Wave 0 creates the test file in Plan 16-01.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Flow C: wizard -> scan -> dashboard with correct profile | SCORE-04 | Requires interactive terminal session | Run `python -m quirk interactive`, accept all defaults, run scan, verify dashboard reads from `quirk-output/` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
