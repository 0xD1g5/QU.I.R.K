---
phase: 112-distributed-chaos-lab-stabilization
plan: "03"
subsystem: stabilization
tags: [datetime, dep-hygiene, uat-series, obsidian, milestone-final, stab-03]
dependency_graph:
  requires:
    - 112-01 (distributed topology, sensor tests)
    - 112-02 (operators-guide §8, oracle)
  provides:
    - quirk/cli/sensor_cmd.py (timezone-aware pushed_at)
    - docs/UAT-SERIES.md Series 112 (five UAT items)
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-112-Distributed-Chaos-Lab-Stabilization.md
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md (synced)
    - /Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Operators-Guide.md (synced)
  affects:
    - quirk/cli/sensor_cmd.py (wire format pushed_at)
    - docs/UAT-SERIES.md (Series 112 added)
tech_stack:
  added: []
  patterns:
    - datetime.now(timezone.utc) idiom (from dispatcher.py / merge/scan.py)
    - AST gate for datetime.utcnow() call-site verification
    - UAT-SERIES Series pattern (H2 + metadata + prose callout + UAT items)
key_files:
  created: []
  modified:
    - quirk/cli/sensor_cmd.py (L39 import, L296 pushed_at)
    - docs/UAT-SERIES.md (Series 112 + Last Updated)
decisions:
  - "datetime fix: wire-format pushed_at uses .strftime() (not .replace(tzinfo=None)) to stay consistent with dispatcher.py idiom and preserve ISO-8601 output"
  - "pyproject.toml dep audit: verify-only, no edits — platformdirs/tenacity/zstandard already pinned in core group at L32-34"
  - "qramm_cmd.py L9 utcnow() mention is a module docstring (documentation text), not a call site — AST gate confirms zero call sites"
  - "UAT-112-03 typed Human (deferred live E2E run) per CONTEXT.md verification approach; four other Series 112 items are Automated"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-26"
  tasks_completed: 3
  files_created: 0
  files_modified: 2
---

# Phase 112 Plan 03: Stabilization, UAT Series 112, Obsidian Close-Out Summary

datetime.utcnow() eliminated from quirk/ (wire-format pushed_at now uses datetime.now(timezone.utc)); deps confirmed pinned; UAT-SERIES Series 112 added (5 items, all v5.4 phases covered); Obsidian vault synced (UAT-Series.md, Operators-Guide.md) and final Phase 112 capstone note written.

## What Was Built

### Task 1: Fix datetime.utcnow() in sensor_cmd.py + confirm dep pinning

**Files:** `quirk/cli/sensor_cmd.py`
**Commit:** `cc56b95`

Fixed the single `datetime.utcnow()` call site at sensor_cmd.py L296 in `_build_envelope`:

- **L39 import:** `from datetime import datetime` → `from datetime import datetime, timezone`
- **L296:** `datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")` → `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")`

Wire-format `pushed_at` string is now unambiguous UTC — no naive-local drift (T-112-06 mitigated). The `.strftime()` form is used (not `.replace(tzinfo=None)`) because this is a wire-format ISO string going into the push envelope, not a SQLite-storage datetime; this matches the pattern in `quirk/notify/dispatcher.py:208` and `quirk/merge/scan.py:178`.

**AST verification:** `python -c "import ast, pathlib; ..."` gate confirms zero `datetime.utcnow()` call-site AST nodes in any `quirk/` source file. The `grep` hit in `qramm_cmd.py:9` is a module docstring line, not a call.

**Dep audit (verify-only, no edits):** `pyproject.toml` L32–34 confirmed:
```
"platformdirs>=4.3.0",   # Phase 108 SENSOR-05
"tenacity>=8.2.0",       # Phase 108 SENSOR-02
"zstandard>=0.22.0",     # Phase 108 SENSOR-02/03/04
```
All three are in `[project.dependencies]` (core group) — no misplacement into an optional extra. No changes made.

**Tests:** 107 sensor tests pass; `python -m compileall quirk run_scan.py -q` clean.

### Task 2: Add UAT-SERIES Series 112

**Files:** `docs/UAT-SERIES.md`
**Commit:** `708c287`

Appended `## Series 112: Distributed Chaos-Lab + Stabilization (Phase 112 — v5.4)` after Series 111, following the Series 106 structure. Five items with IDs UAT-112-01..05:

| Item | Requirement | Type | What it validates |
|------|-------------|------|-------------------|
| UAT-112-01 | LAB-01, LAB-03 | Automated | `docker compose config -q` exits 0; `expected_results_distributed.md` exists; lab.sh distributed arm present; ALL_PROFILES unaffected |
| UAT-112-02 | LAB-01, LAB-02, LAB-03 | Automated | `pytest tests/test_distributed_topology.py -q` — 10 topology assertions pass |
| UAT-112-03 | LAB-01, LAB-02 | Human | Live `./lab.sh distributed e2e` → two `crypto.internal:443` components in merged CBOM + one score + coverage_warning null |
| UAT-112-04 | STAB-03 | Automated | `python -W error::DeprecationWarning -c "import quirk.cli.sensor_cmd"` exits 0; grep gate zero non-comment utcnow() |
| UAT-112-05 | STAB-01 | Automated | `grep -q "## 8. Distributed Sensor Deployment" docs/operators-guide.md` + key command strings |

Updated `**Last Updated:**` to `2026-05-26` with Phase 112 completion summary. UAT-SERIES now spans Series 100–112, covering all seven v5.4 phases (106–112).

### Task 3: Obsidian sync + final Phase 112 note (mandatory CLAUDE.md steps)

**Files:** vault filesystem (not committed to repo)

Per CLAUDE.md mandatory phase completion steps:

1. **UAT-Series.md synced** to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` — frontmatter prepended (project/type: reference/status: active/source: docs/UAT-SERIES.md/updated: 2026-05-26), full file copied via `printf + cat + cp` (not obsidian CLI content= — file too large).

2. **Operators-Guide.md synced** to `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Operators-Guide.md` — frontmatter prepended (type: guide/status: active/source: docs/operators-guide.md), full file copied.

3. **Phase 112 capstone note written** at `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-112-Distributed-Chaos-Lab-Stabilization.md` — frontmatter (status: complete/updated: 2026-05-26) + Goal + Requirements Covered (LAB-01/02/03, STAB-01/03) + Success Criteria (all 5 marked ✅) + What Was Built (one section per plan, sourced from 112-01/02/03 SUMMARYs) + v5.4 milestone completion table + [[Roadmap]] link. Written directly to vault filesystem, not via obsidian CLI content=.

## Deviations from Plan

None — plan executed exactly as written.

- pyproject.toml was verify-only as planned (no edits needed; deps already pinned)
- qramm_cmd.py:9 utcnow() mention is a docstring (documented exception in the plan)
- docs/UAT-SERIES.md Last Updated already showed 2026-05-26 (Phase 111 same-day completion); updated with Phase 112 completion summary as specified

## Verification Results

- `grep -rn "datetime.utcnow()" quirk/ | grep -v '^[[:space:]]*#'` — only hit is `qramm_cmd.py:9` (docstring); AST gate confirms zero call sites
- `python -W error::DeprecationWarning -c "import quirk.cli.sensor_cmd"` — exits 0, no warnings
- `python -m compileall quirk run_scan.py -q` — CLEAN
- `pytest tests/ -k "sensor" -q` — 107 passed, 20 warnings (pre-existing test-fixture utcnow in test files, out of scope)
- `grep -q "## Series 112" docs/UAT-SERIES.md` — PASS
- `grep -q "UAT-112-05" docs/UAT-SERIES.md` — PASS
- Phase 112 vault note with `status: complete` — FOUND
- UAT-Series.md in vault — FOUND (includes Series 112)
- Operators-Guide.md in vault Guides/ — FOUND (includes §8)

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. The datetime fix is a pure correctness change (T-112-06 mitigated). Dep audit is verify-only.

## Known Stubs

None. All deliverables are fully wired. UAT-112-03 (live distributed E2E) is a deferred human-UAT by design (documented in UAT-SERIES and CONTEXT.md).

## Self-Check: PASSED

- `quirk/cli/sensor_cmd.py` (datetime.now(timezone.utc)): FOUND at L296
- `docs/UAT-SERIES.md` (Series 112): FOUND
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-112-Distributed-Chaos-Lab-Stabilization.md`: FOUND
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`: FOUND
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Guides/Operators-Guide.md`: FOUND
- Commit `cc56b95`: FOUND
- Commit `708c287`: FOUND
