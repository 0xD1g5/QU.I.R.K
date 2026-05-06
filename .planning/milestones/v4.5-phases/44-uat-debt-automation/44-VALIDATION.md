---
phase: 44
slug: uat-debt-automation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-03
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, no new install) |
| **Config file** | none — uses `tests/conftest.py` + `tests/skip_registry.py` |
| **Quick run command** | `python -m pytest tests/ -m "not slow" -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~30 seconds (not slow), ~90 seconds (with slow/live_infra) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -m "not slow" -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green (live_infra tests skip unless chaos lab running)
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 1 | UAT-01 | N/A — test infra | integration | `python -m pytest tests/test_uat_db_integration.py -m "not slow" -q` | ❌ W0 | ⬜ pending |
| 44-02-01 | 02 | 1 | UAT-03 | N/A — test infra | integration | `python -m pytest tests/test_kerberos_scanner.py tests/test_saml_scanner.py -m "not slow" -q` | ✅ | ⬜ pending |
| 44-03-01 | 03 | 1 | UAT-03 | N/A — test infra | integration | `python -m pytest tests/test_vault_connector.py -m "not slow" -q` | ✅ | ⬜ pending |
| 44-04-01 | 04 | 1 | UAT-04 | N/A — dashboard | unit | `python -m pytest tests/test_dashboard_trends.py -q` | ✅ | ⬜ pending |
| 44-05-01 | 05 | 2 | UAT-01,02,03,04 | N/A — bug fixes | unit | `python -m pytest tests/ -m "not slow" -q` | ✅ | ⬜ pending |
| 44-06-01 | 06 | 3 | UAT-04 | N/A — bookkeeping | manual | Review STATE.md Deferred Items table | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_uat_db_integration.py` — new file created in Plan 44-01 Task 1
- [x] `tests/skip_registry.py` — ALLOWED_SKIPS entries added in Plans 44-01 Task 2 and 44-03 Task 2

*All other infrastructure (pytest, fixtures, chaos lab profiles) already exists.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| STATE.md Deferred Items reflects 7 closures | UAT-04 | Text review required | Open `.planning/STATE.md`, verify 7 rows updated to `automated (chaos lab)` or `cloud-only` |
| live_infra integration tests pass against running chaos lab | UAT-01, 03 | Requires Docker | `./quantum-chaos-enterprise-lab/lab.sh up database vault kerberos saml && QUIRK_DB_INTEGRATION=1 QUIRK_VAULT_INTEGRATION=1 QUIRK_KERBEROS_INTEGRATION=1 QUIRK_INTEGRATION_TESTS=1 python -m pytest tests/test_uat_db_integration.py tests/test_kerberos_scanner.py tests/test_saml_scanner.py tests/test_vault_connector.py -m slow -v` |

---

## Validation Architecture

### Dimension 1–3: Unit + Integration
- DB integration tests (`test_uat_db_integration.py`) validate Phase 27 UAT scenarios against live `database` chaos lab
- Identity tests (`test_kerberos_scanner.py`, `test_saml_scanner.py`) validate Phase 25 UAT with live `kerberos`/`saml` profiles
- Vault tests validate Phase 30 UAT with live `vault` profile

### Dimension 4: Bug Fix Regression
- `python -m pytest tests/ -m "not slow" -q` catches regressions from pdf.py, print.tsx, data-at-rest.tsx, motion.tsx fixes

### Dimension 5: Coverage Gate
- `test_skip_registry.py` meta-test enforces that every new live_infra skip is registered

### Dimension 8: Sampling Continuity
- Every task has an automated verify command; no 3 consecutive unverified tasks

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (test_uat_db_integration.py + skip_registry entries)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-03
