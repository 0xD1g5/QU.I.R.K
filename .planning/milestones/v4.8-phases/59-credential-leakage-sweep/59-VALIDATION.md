---
phase: 59
slug: credential-leakage-sweep
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 59 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_safe_exc.py tests/test_credential_leakage.py -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_safe_exc.py tests/test_credential_leakage.py -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -q --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 59-01-01 | 01 | 1 | LEAK-01 | — | `safe_str(exc)` returns class name only when exc contains credential-shaped text | unit | `python -m pytest tests/test_safe_exc.py -q` | ❌ W0 | ⬜ pending |
| 59-01-02 | 01 | 1 | LEAK-01 | — | scrubbing regex patterns match base64 tokens, passwords, GCP ADC paths, Vault tokens | unit | `python -m pytest tests/test_safe_exc.py -q` | ❌ W0 | ⬜ pending |
| 59-02-01 | 02 | 1 | LEAK-02 | — | vault connector `scan_error` writes contain only exception class name | unit | `python -m pytest tests/test_credential_leakage.py::test_vault -q` | ❌ W0 | ⬜ pending |
| 59-02-02 | 02 | 1 | LEAK-02 | — | GCP connector variable assignment uses `safe_str` | unit | `python -m pytest tests/test_credential_leakage.py::test_gcp -q` | ❌ W0 | ⬜ pending |
| 59-02-03 | 02 | 1 | LEAK-02 | — | broker/email/tls/ssh connectors route through `safe_str` | unit | `python -m pytest tests/test_credential_leakage.py -q` | ❌ W0 | ⬜ pending |
| 59-03-01 | 03 | 2 | LEAK-03 | — | AST gate pytest test enumerates scan_error writes and fails if bypass detected | unit | `python -m pytest tests/test_scan_error_gate.py -q` | ❌ W0 | ⬜ pending |
| 59-03-02 | 03 | 2 | LEAK-03 | — | corpus replay finds zero credential-shaped substrings in scan_error values | unit | `python -m pytest tests/test_scan_error_gate.py::test_corpus_replay -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_safe_exc.py` — stubs for LEAK-01 (safe_str unit tests)
- [ ] `tests/test_credential_leakage.py` — stubs for LEAK-02 (per-connector end-to-end leak tests)
- [ ] `tests/test_scan_error_gate.py` — stubs for LEAK-03 (AST gate + corpus replay tests)

*Existing pytest infrastructure covers the framework — only new test files needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| v4.7 scan database corpus replay shows zero leaks | LEAK-03 | Requires real scan databases from v4.7 run history | Run `python -m pytest tests/test_scan_error_gate.py::test_corpus_replay` with a test fixture DB seeded with known-bad scan_error values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
