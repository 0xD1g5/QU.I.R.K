---
phase: 1
slug: foundation-fixes
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-29
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing tests/test_intelligence_*.py confirm pytest is used) |
| **Config file** | none detected — pytest runs via `python -m pytest` or `pytest` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| cert-fix | scoring | 1 | CORE-02 | unit | `pytest tests/ -k cert_pubkey -x -q` | ❌ W0 | ⬜ pending |
| scoring-consolidation | scoring | 1 | CORE-01 | unit | `pytest tests/test_intelligence_scoring.py tests/test_intelligence_confidence.py -x -q` | ✅ | ⬜ pending |
| ssh-threadpool | ssh | 1 | CORE-04 | integration | `pytest tests/ -k ssh -x -q` | ❌ W0 | ⬜ pending |
| sslyze-integration | tls | 2 | SCAN-01 | integration | `pytest tests/ -k sslyze -x -q` | ❌ W0 | ⬜ pending |
| ssh-audit-integration | ssh | 2 | SCAN-02 | integration | `pytest tests/ -k ssh_audit -x -q` | ❌ W0 | ⬜ pending |
| package-rename | rename | 3 | CORE-03 | smoke | `python -c 'import quirk; print(quirk.__version__)'` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cert_pubkey_fix.py` — unit test for `_extract_cert_key_type()` returning correct value from `cert_pubkey_alg` field
- [ ] `tests/test_ssh_scanner.py` — stubs for threaded SSH scan + ssh-audit JSON parsing
- [ ] `tests/test_sslyze_integration.py` — stubs for sslyze primary path + fallback path
- [ ] `quirk/__init__.py` — must exist after rename for import smoke test

*Existing tests/test_intelligence_scoring.py and tests/test_intelligence_confidence.py already exist and cover CORE-01.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `quirk --help` prints QU.I.R.K. branding | CORE-03 | CLI invocation requires installed package or direct Python call | Run `python -m quirk --help` and verify output contains "QU.I.R.K." |
| Report headers show QU.I.R.K. not QuRisk | CORE-03 | Requires full scan run | Run against chaos lab, check markdown report header |
| sslyze fallback actually fires | SCAN-01 | Requires a host that sslyze fails on | Mock sslyze failure in test or test against non-TLS port |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
