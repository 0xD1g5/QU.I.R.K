---
phase: 99
slug: per-finding-context-code-signing-expiry
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-24
---

# Phase 99 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest configured via repo (conftest.py at tests/) |
| **Quick run command** | `python -m pytest tests/test_content_model.py tests/test_findings_evaluator.py tests/test_codesign_scanner.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~30-60 seconds (targeted); full suite longer |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (targeted to touched modules)
- **After every plan wave:** Run the full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Task IDs are provisional — refined once the planner emits PLAN.md files. Maps phase requirements to verification approach.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 99-01-* | 01 | 1 | CTX-01 | — | quantum_risk field populated for every crypto-class finding from ALGO_IMPACT_MAP (3-tuple); both unpack break-sites fixed | unit | `python -m pytest tests/test_content_model_phase99.py -q` | ❌ W0 | ⬜ pending |
| 99-01-* | 01 | 1 | CTX-02 | — | REMEDIATION_CATALOG returns weakness-specific copy, no generic-only fallback | unit | `python -m pytest tests/test_content_model_phase99.py -q` | ❌ W0 | ⬜ pending |
| 99-02-* | 02 | 1 | CTX-03 | — | expired codesign cert (even SAFE-crypto) emits a finding; ≤90d → MEDIUM, expired → HIGH; both LDAP + TLS paths populate expiry | unit | `python -m pytest tests/test_codesign_expiry_classification.py -q` | ❌ W0 | ⬜ pending |
| 99-02-* | 02 | 1 | CTX-01/02/03 | — | evaluate_codesign_endpoints emits findings into report list; catalog-sourced recommendation (== REMEDIATION_CATALOG['CODESIGN_EXPIRY']); email + broker paths route through _build_finding and carry quantum_risk | unit | `python -m pytest tests/test_codesign_findings_evaluator.py -q` | ❌ W0 | ⬜ pending |
| 99-03-* | 03 | 2 | CTX-01 | — | quantum_risk + remediation render across CLI markdown, HTML, PDF surfaces (parity), with sanitize on new fields | unit | `python -m pytest tests/test_quantum_risk_render_parity.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_content_model_phase99.py` — ALGO_IMPACT_MAP 3-tuple unpack + quantum_risk lookup + REMEDIATION_CATALOG (CTX-01, CTX-02) — created by Plan 01
- [x] `tests/test_codesign_expiry_classification.py` — expiry classification stacking with weak-crypto, both LDAP + TLS paths (CTX-03) — created by Plan 02
- [x] `tests/test_codesign_findings_evaluator.py` — evaluate_codesign_endpoints wiring + catalog-sourced recommendation + email/broker path quantum_risk coverage (CTX-01/02/03, D-06) — created by Plan 02
- [x] `tests/test_quantum_risk_render_parity.py` — quantum_risk present in all three surfaces (CTX-01/D-03) — created by Plan 03
- [x] Existing tests updated for behavior changes: `tests/test_exec_content_model.py` (3-tuple unpack), `tests/test_risk_engine.py` (conditional NIST boilerplate)

*Existing infrastructure (pytest + conftest) covers framework needs — no new framework install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF visual render of quantum_risk + remediation block | CTX-01/D-03 | PDF rendering needs a running server + Playwright (environment-gated, consistent with v5.1/Phase 98 deferrals) | Run scan, export PDF, visually confirm each finding shows the "so what" + remediation |
| HTML browser render of new finding fields | CTX-01/D-03 | Visual confirmation in a browser | Open HTML report, confirm quantum_risk renders per finding |

*Automated tests cover content-model and data-flow correctness; visual render parity is the manual layer.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-24
