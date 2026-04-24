---
phase: 17
slug: identity-infrastructure
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-08
updated: 2026-04-24
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `python -m pytest tests/test_identity_infra.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_identity_infra.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 0 | INFRA-01 | unit (RED) | `python -m pytest tests/test_identity_infra.py::test_migration_idempotent -x -q` | ✅ | ✅ green |
| 17-01-02 | 01 | 0 | INFRA-02 | unit (RED) | `python -m pytest tests/test_identity_infra.py::test_connectors_cfg_identity_fields -x -q` | ✅ | ✅ green |
| 17-01-03 | 01 | 0 | INFRA-03 | integration (RED) | `python -m pytest tests/test_identity_infra.py::test_identity_extras_declared -x -q` | ✅ | ✅ green |
| 17-02-01 | 02 | 1 | INFRA-01 | unit (GREEN) | `python -m pytest tests/test_identity_infra.py::test_migration_idempotent -x -q` | ✅ | ✅ green |
| 17-02-02 | 02 | 1 | INFRA-02 | unit (GREEN) | `python -m pytest tests/test_identity_infra.py::test_connectors_cfg_identity_fields -x -q` | ✅ | ✅ green |
| 17-02-03 | 02 | 1 | INFRA-03 | integration (GREEN) | `python -m pytest tests/test_identity_infra.py::test_identity_extras_declared -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_identity_infra.py` — RED test stubs for INFRA-01, INFRA-02, INFRA-03

*Existing infrastructure covers pytest; only the new test file is needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `quirk init` output contains commented identity section | INFRA-02 | Config template rendering requires CLI invocation | Run `quirk init --stdout` and confirm commented `enable_kerberos`, `enable_saml`, `enable_dnssec` lines appear inside `connectors:` block |
| `pip install quirk[identity]` resolves without conflicts | INFRA-03 | Requires network + pip resolver | In a fresh venv: `pip install --no-cache-dir ".[identity]"` then `pip check` exits 0 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-24

---

## Validation Audit 2026-04-24
| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 6 (all tasks green) |
| Escalated | 0 |
| Manual-only | 2 (quirk init stdout check, pip install check) |
