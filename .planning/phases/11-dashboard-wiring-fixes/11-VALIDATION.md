---
phase: 11
slug: dashboard-wiring-fixes
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | none (runs from project root) |
| **Quick run command** | `python3 -m pytest tests/test_dashboard_wiring.py tests/test_dashboard_api.py tests/test_gap_closure.py -x -q` |
| **Full suite command** | `python3 -m pytest tests/ -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_dashboard_wiring.py tests/test_dashboard_api.py tests/test_gap_closure.py -x -q`
- **After every plan wave:** Run `python3 -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | UI-01, UI-04 | unit | `python3 -m pytest tests/test_dashboard_wiring.py -x -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | UI-01 | unit | `python3 -m pytest tests/test_dashboard_wiring.py::test_deps_default_db_path -x` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | UI-04 | unit | `python3 -m pytest tests/test_dashboard_wiring.py::test_server_sets_quirk_serve_port -x` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | UI-03 | unit | `python3 -m pytest tests/test_dashboard_wiring.py::test_derive_cbom_ssh_algorithms -x` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | UI-03 | unit | `python3 -m pytest tests/test_dashboard_wiring.py::test_derive_cbom_ssh_only_scan -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard_wiring.py` — stubs for UI-01 (db_path default), UI-04 (QUIRK_SERVE_PORT set), UI-03 (SSH CBOM non-empty)

*Existing `conftest.py` and `dashboard_client` fixture cover all tests — no new framework or conftest needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| E2E: `quirk init` → scan → `quirk serve` → `/api/scan/latest` returns scan data | UI-01 | Requires full install + config edit + scan run | Run `quirk init`, edit config.yaml, run `quirk --config config.yaml`, run `quirk serve`, GET `/api/scan/latest` — expect 200 with data |
| PDF export at non-default port | UI-04 | Requires browser + running server | Run `quirk serve --port 9000`, click PDF export — inspect PDF URL targets port 9000, not 8512 |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
