---
phase: 21
slug: identity-surface
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-24
updated: 2026-04-24
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project venv) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_identity_surface.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_identity_surface.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | IDENT-01/02/03/04 | unit (RED scaffold) | `python -m pytest tests/test_identity_surface.py -x -q` | ✅ | ✅ green |
| 21-01-02 | 01 | 1 | IDENT-02 | unit (model) | `python -m pytest tests/test_identity_surface.py::IdentityFindingModelTests -x -q` | ✅ | ✅ green |
| 21-02-01 | 02 | 2 | IDENT-01 | unit (evidence counters) | `python -m pytest tests/test_identity_surface.py::IdentityEvidenceCounterTests -x -q` | ✅ | ✅ green |
| 21-02-02 | 02 | 2 | IDENT-01 | unit (scoring weights) | `python -m pytest tests/test_identity_surface.py::IdentityScoringTests -x -q` | ✅ | ✅ green |
| 21-02-03 | 02 | 2 | IDENT-02/04 | unit (derivation) | `python -m pytest tests/test_identity_surface.py::IdentityDerivationTests -x -q` | ✅ | ✅ green |
| 21-02-04 | 02 | 2 | IDENT-03/04 | manual (React UI) | Dashboard Identity tab and protocol filter | N/A | ✅ manual |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_identity_surface.py` — 17-test RED scaffold for IDENT-01 through IDENT-04 (Plan 01 creates this)
- [x] `quirk/dashboard/api/schemas.py` — IdentityFinding Pydantic model + identity_findings on ScanLatestResponse (Plan 01 creates this)
- [x] `src/dashboard/src/types/api.ts` — IdentityFinding TypeScript interface + identity_findings field (Plan 01 creates this)

*Plan 01 establishes the RED scaffold and data contracts; Plan 02 turns all tests GREEN.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Identity tab at `/identity` shows per-protocol summary cards | IDENT-03 | Requires running React dashboard | Start API + dashboard, navigate to `/identity`, confirm Kerberos/SAML/DNSSEC cards present with finding counts |
| Protocol filter dropdown on findings page filters by KERBEROS/SAML/DNSSEC | IDENT-04 | Requires live browser interaction | On `/findings`, select each protocol from dropdown, confirm table filters correctly |
| Identity findings appear in findings table with correct protocol label | IDENT-04 | Requires scan data with identity endpoints | Run scan against chaos lab with Kerberos/SAML/DNSSEC targets, check findings table |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-24

---

## Validation Audit 2026-04-24
| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 17/17 tests green (reconstructed from SUMMARY — Phase 21 executed 2026-04-10) |
| Escalated | 0 |
| Manual-only | 3 (React Identity tab, protocol filter UI, findings table with scan data) |
