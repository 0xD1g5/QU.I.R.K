---
phase: 39
slug: data-at-rest-dashboard-tab
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-29
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend, if present) |
| **Config file** | `pyproject.toml` / `tests/conftest.py` |
| **Quick run command** | `pytest tests/test_dar_dashboard.py -x -q` |
| **Full suite command** | `pytest -x -q && python -m compileall quirk` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_dar_dashboard.py -x -q` (when DAR tests exist)
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green; dashboard build must succeed (`cd src/dashboard && npm run build`)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

> Planner fills this in during PLAN.md authorship. Each task with verifiable code output gets a row.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 39-01-01 | 01 | 0 | GAP-04 | — | N/A | unit (stub) | `pytest tests/test_dar_dashboard.py -x -q` | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_dar_dashboard.py` — stubs covering DarFinding projection across all 7 protocol variants (POSTGRESQL, MYSQL, RDS, S3, AZURE_BLOB, KUBERNETES, VAULT) plus API contract test that `dar_findings` key is present in `ScanLatestResponse`
- [ ] `tests/conftest.py` — fixture for a synthetic scan with one finding per DAR category

*Frontend: visual/console-error verification handled in Manual-Only section below — no Vitest/Jest infrastructure currently in `src/dashboard/`. Phase 44 covers automated UAT.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/data-at-rest` route renders without console errors | GAP-04 (Success Criterion 4) | No frontend test runner installed in dashboard | `cd src/dashboard && npm run dev`, navigate to `/data-at-rest`, open DevTools console, verify zero errors on load and after switching tabs |
| Empty state shows when no DAR findings | GAP-04 (Success Criterion 3) | UI rendering check | Hit a fresh scan with all DAR scanners disabled; verify each of the 4 sections renders an `EmptyStateCard` and the page does not crash |
| Sidebar nav order matches D-11 (Executive · Findings · Identity · Motion · Data at Rest · Certificates · CBOM · Roadmap · Trends) | GAP-04 (Success Criterion 1) | Visual order | Visual inspection of `src/dashboard/src/components/sidebar.tsx` rendered output |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (DAR test stub + fixture)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (planner flips on completion)

**Approval:** pending
