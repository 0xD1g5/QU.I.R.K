---
phase: 64
slug: trend-analysis-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-10
---

# Phase 64 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python backend) |
| **Config file** | pytest.ini / pyproject.toml (existing) |
| **Quick run command** | `python -m pytest tests/test_dashboard_trends.py tests/test_intelligence_trends.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_dashboard_trends.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 64-01-01 | 01 | 1 | TREND-01 | T-64-01 (n param DoS) | Pydantic `Query(ge=2, le=200)` rejects n=1 and n=201 with 422 | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_n_validation -x` | ❌ W0 | ⬜ pending |
| 64-01-02 | 01 | 1 | TREND-01 | — | GET /api/trends/timeline returns 200 with sessions array | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_endpoint -x` | ❌ W0 | ⬜ pending |
| 64-01-03 | 01 | 1 | TREND-01 | — | Response schema has session_ts, score, subscores (6 keys), finding_counts | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_schema -x` | ❌ W0 | ⬜ pending |
| 64-01-04 | 01 | 1 | TREND-01 | — | ?n=5 returns at most 5 sessions | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_n_param -x` | ❌ W0 | ⬜ pending |
| 64-01-05 | 01 | 1 | TREND-01 | — | Empty DB returns {"sessions": []} | integration | `python -m pytest tests/test_dashboard_trends.py::test_trends_timeline_empty -x` | ❌ W0 | ⬜ pending |
| 64-01-06 | 01 | 1 | TREND-02 | — | Existing GET /api/trends still returns 200 (non-regression) | integration | `python -m pytest tests/test_dashboard_trends.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard_trends.py` — add 5 new test functions for the timeline endpoint:
  - `test_trends_timeline_endpoint` — GET /api/trends/timeline returns 200
  - `test_trends_timeline_schema` — response has correct shape (session_ts, score, subscores, finding_counts)
  - `test_trends_timeline_n_param` — ?n=5 returns at most 5 sessions
  - `test_trends_timeline_n_validation` — ?n=1 returns 422 (ge=2 Pydantic constraint)
  - `test_trends_timeline_empty` — empty DB returns {"sessions": []}
- [ ] No new conftest needed — existing `dashboard_client` fixture and UUID-cache pattern from existing tests cover all needed patterns.

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LineChart renders with 7 colored lines and correct left-to-right time ordering | TREND-01 | Requires browser; Recharts render is visual-only | Start `quirk serve`, navigate to /trends, confirm chart has multiple lines, oldest scan on left |
| Hover tooltip shows full timestamp + all 7 score values | TREND-01 | Requires interactive browser session | Hover each data point, confirm tooltip lists all 7 series with score values |
| RegressionAlertChip appears on ExecutivePage when score drops ≥ 5 pts | TREND-02 | Requires two scans with controlled scores; visual verification | Run two scans with intentional score drop, navigate to /, confirm chip appears |
| Dismissing chip writes localStorage and hides chip without reload | TREND-02 | Requires browser devtools inspection | Click ×, confirm chip hidden, check localStorage for `quirk.dismissed_regression.*` key |
| New scan with regression shows fresh chip even after prior dismissal | TREND-02 | Requires per-session localStorage key verification | Dismiss chip, run third scan with new regression, confirm new chip appears |
| `npm run build` in src/dashboard/ required before serving | TREND-01, TREND-02 | FastAPI serves pre-built static assets | After .tsx edits: `cd src/dashboard && npm run build` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
