---
phase: 5
slug: web-dashboard
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-30
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest) / `vite.config.ts` (vitest) — Wave 0 installs both |
| **Quick run command** | `pytest tests/test_dashboard_api.py -q` |
| **Full suite command** | `pytest tests/ -q && npm --prefix dashboard test -- --run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_dashboard_api.py -q`
- **After every plan wave:** Run `pytest tests/ -q && npm --prefix dashboard test -- --run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 0 | UI-01 | unit | `pytest tests/test_dashboard_api.py::test_serve_command -q` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | UI-01 | integration | `pytest tests/test_dashboard_api.py::test_dashboard_loads -q` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 1 | UI-02 | unit | `pytest tests/test_dashboard_api.py::test_score_endpoint -q` | ❌ W0 | ⬜ pending |
| 5-02-02 | 02 | 1 | UI-02 | e2e manual | Browser: score gauge visible | n/a | ⬜ pending |
| 5-03-01 | 03 | 2 | UI-03 | unit | `pytest tests/test_dashboard_api.py::test_findings_endpoint -q` | ❌ W0 | ⬜ pending |
| 5-03-02 | 03 | 2 | UI-03 | e2e manual | Browser: findings/cert/CBOM tabs navigable | n/a | ⬜ pending |
| 5-04-01 | 04 | 3 | UI-04 | integration | `pytest tests/test_pdf_export.py -q` | ❌ W0 | ⬜ pending |
| 5-04-02 | 04 | 3 | UI-04 | manual | Click "Export PDF" → PDF file rendered correctly | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard_api.py` — stubs for UI-01, UI-02, UI-03
- [ ] `tests/test_pdf_export.py` — stubs for UI-04
- [ ] `tests/conftest.py` — shared fixtures (FastAPI TestClient)
- [ ] `fastapi`, `uvicorn`, `pytest`, `httpx` — add to `pyproject.toml` optional deps and install
- [ ] `dashboard/` directory scaffold with `package.json` (vitest configured)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Score gauge renders as arc chart | UI-02 | Visual rendering requires browser | Open dashboard, verify arc gauge displays score |
| Findings table is paginated | UI-03 | UI interaction | Open findings tab, scroll through pages |
| CBOM viewer renders graph | UI-03 | Canvas/WebGL rendering | Open CBOM tab, verify graph nodes visible |
| PDF contains full report content | UI-04 | PDF visual fidelity | Open exported PDF, verify all sections present |
| Light/dark toggle persists across reload | UI-01 | localStorage persistence | Toggle theme, reload page, verify theme preserved |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
