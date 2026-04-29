---
phase: 39
slug: data-at-rest-dashboard-tab
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-29
approved: 2026-04-29
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
| 39-01-01 | 01 | 0 | GAP-04 | — | N/A | unit (stub, RED) | `pytest tests/test_dar_dashboard.py -x -q` | ❌ W0 | ⬜ pending |
| 39-02-01 | 02 | 1 | GAP-04 | T-39-01 | DarFinding model + dar_findings field on ScanLatestResponse — typed schema prevents arbitrary field exposure | unit (import + model) | `python -c "from quirk.dashboard.api.schemas import DarFinding, ScanLatestResponse; assert 'dar_findings' in ScanLatestResponse.model_fields"` | ✅ | ⬜ pending |
| 39-02-02 | 02 | 1 | GAP-04 | T-39-01, T-39-02, T-39-03 | Per-protocol projection with json.loads guard, kms_key_id label-only, scan_error skip — DoS guard via try/except per dat_scan_json parse | unit (pytest, GREEN) | `pytest tests/test_dar_dashboard.py -x -q` | ✅ | ⬜ pending |
| 39-03-01 | 03 | 2 | GAP-04 | — | data-at-rest.tsx renders ScoreGauge + 4 sections + per-section EmptyStateCard — empty-state coverage prevents blank-panel UX | type-check (tsc) | `cd src/dashboard && npx tsc --noEmit -p .` | ✅ | ⬜ pending |
| 39-03-02 | 03 | 2 | GAP-04 | T-39-04 | App.tsx route + sidebar.tsx NAV_ITEMS (HardDrive, locked order) — auth alignment via existing route layout | build | `cd src/dashboard && npm run build` | ✅ | ⬜ pending |
| 39-04-01 | 04 | 3 | GAP-04 | T-39-05 | Four locked-column tables, severity-sorted, React text-node interpolation only (no raw HTML injection) — XSS mitigation | build | `cd src/dashboard && npm run build` | ✅ | ⬜ pending |
| 39-05-01 | 05 | 4 | GAP-04 | — | Full validation gate: compileall + pytest + dashboard build | integration | `python -m compileall quirk && python -m compileall tests && pytest tests/test_dar_dashboard.py -x -q && pytest -x -q && (cd src/dashboard && npm run build)` | ✅ | ⬜ pending |
| 39-05-02 | 05 | 4 | GAP-04 | — | UAT-SERIES.md updated with ≥8 UAT-39-* cases | docs | `grep -c "UAT-39-" docs/UAT-SERIES.md \| awk '$1 >= 8 {exit 0} {exit 1}'` | ✅ | ⬜ pending |
| 39-05-03 | 05 | 4 | GAP-04 | — | Manual console-error gate (`/data-at-rest` route shows zero errors in DevTools) — Success Criterion 4 | manual checkpoint | human-verify (DevTools console clean) | n/a | ⬜ pending |
| 39-05-04 | 05 | 4 | GAP-04 | — | Obsidian phase note exists at vault filesystem path | docs sync | `test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-39-Data-At-Rest-Dashboard-Tab.md"` | ✅ | ⬜ pending |
| 39-05-05 | 05 | 4 | GAP-04 | — | UAT-SERIES.md mirrored to Obsidian vault with QU.I.R.K. frontmatter | docs sync | `test -f "/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md" && head -2 ".../UAT-Series.md" \| grep -q "project: QU.I.R.K."` | ✅ | ⬜ pending |
| 39-05-06 | 05 | 4 | GAP-04 | — | Phase-tagged commit on branch (`phase-39`) | git | `git log --oneline -1 \| grep -q "phase-39"` | ✅ | ⬜ pending |

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

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (DAR test stub + fixture)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-29
