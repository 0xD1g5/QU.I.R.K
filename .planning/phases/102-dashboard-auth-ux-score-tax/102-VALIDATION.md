---
phase: 102
slug: dashboard-auth-ux-score-tax
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-24
---

# Phase 102 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (dashboard frontend) |
| **Config file** | tests/conftest.py (QUIRK_DB_PATH fixture); src/dashboard/src/test-setup.ts |
| **Quick run command** | `python -m pytest tests/test_token_cmd.py tests/test_dashboard_auth*.py tests/test_route_coverage.py tests/test_score_parity.py -q` |
| **Full suite command** | `python -m pytest -q` (backend) + `cd src/dashboard && npm run test` (frontend) |
| **Estimated runtime** | ~60s backend targeted; frontend vitest ~20s |

---

## Sampling Rate

- **After every task commit:** Run the targeted quick command for the touched module
- **After every plan wave:** Run the phase's backend test files; frontend vitest after .tsx changes
- **Before `/gsd:verify-work`:** Full backend suite green + `npm run build` succeeds in src/dashboard/
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

*Populated by gsd-planner during planning.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | — | — | — | — | — | — | — | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_token_cmd.py` — AUTH-01 token generate/rotate/show + YAML round-trip
- [ ] `tests/test_dashboard_auth_apikey.py` — AUTH-02 X-API-Key header + timing-safe + bearer fallback + auth-disabled passthrough
- [ ] `tests/test_route_coverage.py` — AUTH-02 every data-returning route depends on require_auth (extends existing mutating-routes test)
- [ ] `tests/test_score_parity.py` — TRANS-04 score total/band/subscores identical across CLI/HTML/PDF/DOCX
- [ ] Dashboard vitest specs for the login form (auth context, login gate, invalid-token error, logout) — under src/dashboard/src

*Confirmed during planning against existing pytest + vitest infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Login form renders + full dashboard loads after correct token | AUTH-03 | Requires running the built dashboard in a browser against a live API | Set QUIRK_API_TOKEN, run quirk serve, open dashboard, enter token, confirm dashboard loads; enter wrong token, confirm inline error |
| Logout returns to login form and clears stored token | AUTH-03 | Visual browser interaction | Click Sign out, confirm return to login + localStorage cleared |

*Auth logic is unit-tested; live browser rendering is human-UAT.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
