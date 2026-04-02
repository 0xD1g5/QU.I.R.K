# Folder Restructure Audit — 2026-03-31

## Summary

Full audit of the project following the `qcscan/ → quirk/` package rename and associated
cleanup. All dependency issues have been identified and resolved. Application is fully functional.

---

## Restructuring Overview

| Change | Before | After | Status |
|--------|--------|-------|--------|
| Python package directory | `qcscan/` | `quirk/` | Complete |
| Package name (pyproject.toml) | `qcscan` | `quirk` | Complete |
| CLI entry point | `qcscan = run_scan:main` | `quirk = run_scan:main` | Complete |
| Database filename | `data/qcscan.sqlite` | `data/quirk.db` | Complete |
| Ghost_Weight attack module | Tracked in repo | Removed from repo | Complete |
| Output artefacts (output/) | Tracked in repo | Removed from repo | Complete |
| Temp files (tmp/) | Tracked in repo | Removed from repo | Complete |
| Dashboard Vite output path | (unchanged) | `quirk/dashboard/static/` | Correct |

---

## Issues Found and Fixed

### 1. Test file imports — `qcscan.*` → `quirk.*`

**Files affected:** 10 test files
**Type:** Broken imports — tests would fail on `ModuleNotFoundError` if not fixed

| File | Fix Applied |
|------|-------------|
| `tests/test_ssh_scanner.py` | `from qcscan.models` → `from quirk.models`; `from qcscan.scanner.ssh_scanner` → `from quirk.scanner.ssh_scanner`; all `@patch("qcscan.scanner.ssh_scanner.*")` → `@patch("quirk.scanner.ssh_scanner.*")` |
| `tests/test_sslyze_integration.py` | `from qcscan.scanner.tls_scanner` → `from quirk.scanner.tls_scanner`; `from qcscan.scanner.tls_capabilities` → `from quirk.scanner.tls_capabilities` |
| `tests/test_cert_pubkey_fix.py` | Module docstring updated; `from qcscan.reports.writer` → `from quirk.reports.writer` |
| `tests/test_intelligence_confidence.py` | `from qcscan.intelligence.*` → `from quirk.intelligence.*` |
| `tests/test_intelligence_evidence.py` | `from qcscan.intelligence.evidence` → `from quirk.intelligence.evidence` |
| `tests/test_intelligence_roadmap.py` | `from qcscan.intelligence.roadmap` → `from quirk.intelligence.roadmap` |
| `tests/test_intelligence_schema.py` | `from qcscan.intelligence.schema` → `from quirk.intelligence.schema` |
| `tests/test_intelligence_scoring.py` | `from qcscan.intelligence.scoring` → `from quirk.intelligence.scoring` |
| `tests/test_reports_scorecard.py` | `from qcscan.reports.scorecard` → `from quirk.reports.scorecard` |
| `tests/test_scoring_consolidation.py` | All `qcscan.*` path checks updated to `quirk.*`; `pathlib.Path … "qcscan" / "reports"` → `"quirk" / "reports"` |

### 2. Dashboard backend route — schema/import alignment

**File:** `quirk/dashboard/api/routes/scan.py`
**Type:** Already correct — uses `from quirk.*` throughout. No fix needed.

### 3. Frontend TypeScript — new features added

**Files affected:** `src/dashboard/src/pages/cbom.tsx`, `src/dashboard/src/pages/roadmap.tsx`,
`src/dashboard/src/types/api.ts`
**Type:** Feature additions, not dependency breakage

- `cbom.tsx`: Added interactive node detail panel with `NodeDetail` discriminated union type;
  imported `X` icon from lucide-react; changed system node color.
- `roadmap.tsx`: No import changes; logic refinements only.
- `api.ts`: No changes from restructure — types already aligned with backend schemas.

---

## Issues NOT Found (Verified Clean)

| Check | Result |
|-------|--------|
| `qcscan` imports in `quirk/` package Python files | None found |
| `qcscan` imports in `tests/` Python files | None found (all fixed) |
| `qcscan` references in `run_scan.py` | None — uses `quirk.*` throughout |
| `qcscan` references in `config.yaml` | None — `db_path: output/quirk.db` |
| `qcscan` references in `quirk/config_template.yaml` | None |
| `qcscan` references in `src/dashboard/` TypeScript | None |
| `qcscan` references in `docs/` | None |
| `qcscan` references in `README.md` | None |
| Vite build output path | `quirk/dashboard/static/` — correct |
| `pyproject.toml` package discovery | `include = ["quirk*"]` — correct |
| `pyproject.toml` entry point | `quirk = "run_scan:main"` — correct |
| `quirk.egg-info/top_level.txt` | `quirk\nrun_scan` — correct |
| Dashboard `deps.py` default DB path | `data/quirk.db` — correct |
| `conftest.py` imports | All use `quirk.*` — correct |

**Residual `qcscan` references (not application code):**
- `.vs/VSWorkspaceState.json` — Visual Studio IDE state file, not part of the application.
  Contains stale tree-view state from before the rename. Harmless.
- `.planning/` documentation — historical notes referencing the old name. Informational only.
- `data/_archive/qcscan-legacy.sqlite` — archived legacy database. Harmless.

---

## Verification

```
.venv/bin/python -m pytest tests/ -q
165 passed, 13 warnings in 4.37s
```

TypeScript type check: `tsc --noEmit` — 0 errors.

---

## Deprecation Warnings (Non-blocking)

Two files use `datetime.utcnow()` which is deprecated in Python 3.12+:

| File | Line | Warning |
|------|------|---------|
| `quirk/reports/executive.py` | 17 | `datetime.datetime.utcnow()` deprecated |
| `quirk/reports/technical.py` | 25 | `datetime.datetime.utcnow()` deprecated |

These do not break anything but should be updated to `datetime.now(datetime.UTC)` in a
future cleanup pass.
