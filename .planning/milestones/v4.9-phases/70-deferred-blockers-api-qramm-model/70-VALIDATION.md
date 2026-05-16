---
phase: 70
slug: deferred-blockers-api-qramm-model
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-15
---

# Phase 70 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Populated from 70-RESEARCH.md "## Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_qramm_router.py tests/test_qramm_models.py tests/test_db_migrations.py tests/test_cbom_scan_route.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~30s quick / ~5min full |

---

## Sampling Rate

- **After every task commit:** Run quick command (≤30s)
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Populated by the planner from PLAN.md task IDs; this is a stub seeded from RESEARCH validation architecture.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 70-01-* | 01 | 1 | BLOCK-07 | — | FK present + safe delete | unit/integration | `pytest tests/test_qramm_delete_session_fk.py -x` | ❌ W0 | ⬜ pending |
| 70-02-* | 02 | 1 | BLOCK-08 | — | Narrow except + warning log | unit | `pytest tests/test_cbom_scan_route.py::test_qs_for_alg_narrow_except -x` | ❌ W0 | ⬜ pending |
| 70-03-* | 03 | 1 | BLOCK-08 | — | col_type allowlist | unit | `pytest tests/test_db_migrations.py::test_safe_col_type_re -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_qramm_delete_session_fk.py` — new file; FK+delete_session integration tests (BLOCK-07 success criterion 3)
- [ ] `tests/test_db_migrations.py` — new file OR extend existing; `_SAFE_COL_TYPE_RE` accept/reject matrix
- [ ] Extend `tests/test_cbom_scan_route.py` — `_qs_for_alg` narrow-except + warning-log tests
- [ ] Extend `tests/test_qramm_models.py` — `PRAGMA foreign_key_list('qramm_profiles')` schema assertion

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| AUDIT-TASKS.md row flips for CR-04/05/06/07 | BLOCK-07/08 | File-edit verification, not behavioral | `grep -E "^\| api-cli-core/CR-0[4567] \| \[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` (CLI corroboration, manual confirmation) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
