---
phase: 102
slug: dashboard-auth-ux-score-tax
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-24
---

# Phase 102 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + tsc/vite build (dashboard frontend) |
| **Config file** | tests/conftest.py (QUIRK_DB_PATH fixture); src/dashboard/tsconfig.json |
| **Quick run command** | `python -m pytest tests/test_token_cmd.py tests/test_dashboard_auth_apikey.py tests/test_route_coverage.py tests/test_score_parity.py -q` |
| **Full suite command** | `python -m pytest -q` (backend) + `cd src/dashboard && npm run build` (frontend) |
| **Estimated runtime** | ~60s backend targeted; frontend build ~30s |

---

## Sampling Rate

- **After every task commit:** Run the targeted quick command for the touched module
- **After every plan wave:** Run the phase's backend test files; frontend tsc/build after .tsx changes
- **Before `/gsd:verify-work`:** Full backend suite green + `npm run build` succeeds in src/dashboard/
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-T1 | 102-01 | 1 | AUTH-01 | T-102-01/02 | CSPRNG token + no-clobber write-back (RED scaffold) | unit | `python -m pytest tests/test_token_cmd.py -x` | ❌ W0 | ⬜ pending |
| 01-T2 | 102-01 | 1 | AUTH-01 | T-102-02/04 | generate/rotate/show; YAML round-trip preserves keys | unit | `python -m pytest tests/test_token_cmd.py -x -q` | ✅ after T1 | ⬜ pending |
| 02-T1 | 102-02 | 1 | AUTH-02 | T-102-05/08 | X-API-Key accept/precedence/reject + route-coverage gate (RED scaffold) | unit + CI gate | `python -m pytest tests/test_dashboard_auth_apikey.py tests/test_route_coverage.py` | ❌ W0 | ⬜ pending |
| 02-T2 | 102-02 | 1 | AUTH-02 | T-102-05/06/07 | require_auth accepts X-API-Key timing-safe, precedence | unit | `python -m pytest tests/test_dashboard_auth_apikey.py tests/test_route_coverage.py tests/test_api_auth.py -q` | ✅ after T1 | ⬜ pending |
| 03-T1 | 102-03 | 1 | TRANS-04 | T-102-10 | CLI score parity test exists | unit | `python -m pytest tests/test_score_parity.py -q` | ❌ W0 | ⬜ pending |
| 03-T2 | 102-03 | 1 | TRANS-04 | T-102-10/11 | score sourced from exec_content; numbers unchanged | unit | `python -m pytest tests/test_score_parity.py tests/test_cross_surface_parity.py -q` | ✅ after T1 | ⬜ pending |
| 04-T1 | 102-04 | 2 | AUTH-03 | T-102-12/15 | localStorage token + X-API-Key + probe /api/scans | typecheck | `cd src/dashboard && npx tsc --noEmit -p tsconfig.json` | N/A | ⬜ pending |
| 04-T2 | 102-04 | 2 | AUTH-03 | T-102-12/14 | LoginPage per UI-SPEC + Sign out + mount guard | typecheck | `cd src/dashboard && npx tsc --noEmit -p tsconfig.json` | N/A | ⬜ pending |
| 04-T3 | 102-04 | 2 | AUTH-03 | T-102-16 | rebuilt statics serve the login surface | build | `cd src/dashboard && npm run build` | N/A | ⬜ pending |
| 04-T4 | 102-04 | 2 | AUTH-03 | T-102-13/14 | login renders, token flow, logout, passthrough | manual UAT | human visual confirmation | N/A | ⬜ pending |
| 05-T1 | 102-05 | 3 | AUTH-01/02/03 | T-102-17 | auth surface documented (no insecure guidance) | doc check | `grep -qi "quirk token" docs/configuration.md` | N/A | ⬜ pending |
| 05-T2 | 102-05 | 3 | AUTH-01/02/03/TRANS-04 | T-102-17 | UAT-SERIES updated + Obsidian phase note | doc check | `grep -qi "quirk token" docs/UAT-SERIES.md` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_token_cmd.py` — AUTH-01 token generate/rotate/show + YAML round-trip (102-01 Task 1)
- [ ] `tests/test_dashboard_auth_apikey.py` — AUTH-02 X-API-Key + timing-safe + bearer fallback + auth-disabled passthrough (102-02 Task 1)
- [ ] `tests/test_route_coverage.py` — AUTH-02 every data-returning route depends on require_auth (102-02 Task 1)
- [ ] `tests/test_score_parity.py` — TRANS-04 score total/band/subscores identical across CLI vs exec_content (HTML/PDF/DOCX source) (102-03 Task 1)
- [ ] Frontend: tsc --noEmit + npm run build gate the AUTH-03 .tsx changes (102-04); live browser behavior is human-UAT (102-04 Task 4)

*Confirmed during planning against existing pytest + tsc/vite infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Login form renders + full dashboard loads after correct token | AUTH-03 | Requires running the built dashboard in a browser against a live API | Set QUIRK_API_TOKEN, run quirk serve, open dashboard, enter token, confirm dashboard loads; enter wrong token, confirm inline error |
| Logout returns to login form and clears stored token | AUTH-03 | Visual browser interaction | Click Sign out, confirm return to login + localStorage cleared |
| Auth-disabled passthrough skips login form | AUTH-03 | Visual browser interaction | Empty token configured → dashboard loads directly with no login form |

*Auth logic is unit-tested; live browser rendering is human-UAT (102-04 Task 4 checkpoint).*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (frontend tasks use tsc/build; live behavior is the 04-T4 human checkpoint)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (token_cmd, auth_apikey, route_coverage, score_parity)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
