---
phase: 116-windows-packaging-spike
plan: "02"
subsystem: docs/assessment
tags: [pyinstaller, windows, spike, assessment, uat-series]
dependency_graph:
  requires: [116-01]
  provides: [windows-packaging-spike assessment, UAT Series 116, v5.6 go/no-go recommendation]
  affects:
    - docs/windows-packaging-spike.md
    - docs/UAT-SERIES.md
tech_stack:
  added: []
  patterns: [spike assessment doc, evidence-only framing (D-06), Obsidian vault sync]
key_files:
  created:
    - docs/windows-packaging-spike.md
  modified:
    - docs/UAT-SERIES.md
decisions:
  - "D-04: Scheduled Task primary host model; NSSM service wrapper as always-on alternative"
  - "D-05: GO recommendation conditional on live CI build producing runnable EXE or only documented fixable hidden-import failures"
  - "D-06: evidence-only framing — CI EXE is not a production binary; no .spec/.nsi/EXE committed"
  - "--onedir recommended for v5.6 production (sensor wire contract frozen-safe; _STATIC_DIR/_TEMPLATES_DIR stable in onedir)"
metrics:
  duration_minutes: 12
  completed: 2026-05-27
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 116 Plan 02: Windows Packaging Spike Assessment + UAT Series 116 Summary

**One-liner:** Five-section PyInstaller feasibility assessment (`docs/windows-packaging-spike.md`) covering spec viability, hidden-import surface, Scheduled Task vs. Service trade-offs, CI evidence, and v5.6 effort estimate, ending with a conditional GO recommendation; UAT Series 116 (4 test cases) added and synced to Obsidian.

## What Was Built

### Task 1: docs/windows-packaging-spike.md Assessment

Created `docs/windows-packaging-spike.md` (315 non-empty lines) covering all five WINPKG-01 criterion-1 topics:

1. **PyInstaller Spec Viability** — `run_scan.py` as freeze target (not `module:function`); `multiprocessing.freeze_support()` guard added in Plan 01; `--onefile` vs `--onedir` trade-off table with production recommendation for `--onedir` (stable `__file__` paths, no AV friction, fast startup).

2. **Hidden-Import Surface** — Hook coverage matrix for all QUIRK deps against `pyinstaller-hooks-contrib 2026.5`; SQLAlchemy (no hook, HIGH risk) and FastAPI (no hook, HIGH risk) both mitigated by `--collect-all` flags; `__file__` inventory showing sensor-critical paths (CMVP cache read, `config_template.yaml`) are already frozen-safe via `importlib.resources` (STAB-02); `_STATIC_DIR`/`_TEMPLATES_DIR` safe in `--onedir`, only break in `--onefile`; sensor wire-contract compatibility table confirming enroll→scan→push path has zero blockers.

3. **Windows Host Model: Scheduled Task vs. Service** — Full trade-off table; **Scheduled Task recommended as primary** (D-04: matches sensor's periodic scan→push lifecycle); Windows Service via NSSM documented as always-on alternative with setup commands.

4. **CI Validation Results** — Exact `windows-packaging-spike` CI job invocation documented (commit 300ec19); `pyinstaller-spike-evidence` artifact (build log, warn-quirk.txt, dist/quirk.exe) cited; RESULT placeholder for live CI run after push; explicit D-06 evidence-only/not-for-production warning.

5. **v5.6 Effort Estimate** — Itemised table totalling ~4–5 days / 1 focused phase (M t-shirt size); items include spec finalisation, `_TEMPLATES_DIR`/`_STATIC_DIR` fixes, pipeline, Scheduled Task install script, E2E test, docs.

Ends with `## Recommendation: **GO (conditional on live CI build)**` — recommendation is GO based on research evidence (D-05 threshold met: sensor wire-contract compatible, HIGH-risk deps have documented mitigations, effort fits one phase); becomes unconditional GO when `pyinstaller-spike-evidence` shows `BUILD_SUCCESS`.

Includes Appendix: Illustrative .spec listing (inside markdown, not committed as a file — D-06 compliant).

**Commit:** b84cad4

### Task 2: UAT Series 116 + Obsidian Vault Sync

Appended `## UAT Series 116 — Windows Packaging Spike (Phase 116)` to `docs/UAT-SERIES.md` with four test cases:

- **UAT-116-01** (Automated): Assessment doc exists + five topic sections + `--onefile`/`--onedir` + `pyinstaller-spike-evidence` artifact + ≥80 line count.
- **UAT-116-02** (Automated): `windows-packaging-spike` CI job present and non-blocking; `freeze_support` in `run_scan.py`; pyinstaller absent from `pyproject.toml`.
- **UAT-116-03** (Human): `## Recommendation` section present with single bold GO/NO-GO/DEFER line + rationale; evidence-only warning; D-04 coverage (Scheduled Task + NSSM).
- **UAT-116-04** (Automated, Scope Guard): No `.spec`/`.nsi`/EXE committed; `pyinstaller` absent from `pyproject.toml`.

`**Last Updated:**` bumped to `2026-05-27` with Phase 116 Plan 02 summary.

Synced to Obsidian vault via `printf`+`cat`+`cp` pattern:
- Target: `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md`
- Frontmatter added: `project: QU.I.R.K.`, `type: reference`, `status: active`, `source: docs/UAT-SERIES.md`, `updated: 2026-05-27`

**Commit:** 7b83a6c

## Deviations from Plan

None — plan executed exactly as written. The CI validation results section documents the exact job invocation and expected evidence while noting the live `windows-latest` run is pending push, per the key facts guidance (D-01 CI results timing).

## Known Stubs

One intentional placeholder: the `RESULT (to be confirmed from pyinstaller-spike-evidence artifact)` line in §CI Validation Results of `docs/windows-packaging-spike.md`. This is documented as intentional — the `windows-packaging-spike` CI job has not yet run on a pushed branch. The instruction to update this line from the artifact is explicit in the doc. The spike's go/no-go is based on research evidence (D-05) and is already stated as conditional on the live build result; this is the correct design per the plan's key facts.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. This plan is documentation-only. T-116-05 mitigated: recommendation is tied to D-05 threshold and cites the CI evidence artifact; stated as conditional. T-116-06 mitigated: appendix `.spec` labelled illustrative-only; explicit evidence-only warning present.

## Self-Check: PASSED

- `docs/windows-packaging-spike.md` — exists, 315 non-empty lines, all five topic sections, Recommendation section, GO recommendation, Scheduled Task, NSSM, onedir, onefile, pyinstaller-spike-evidence, evidence-only warning
- `docs/UAT-SERIES.md` — contains "Series 116", Last Updated updated, UAT-116-01..04 present
- `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/UAT-Series.md` — exists, contains "Series 116", has QU.I.R.K. frontmatter
- No `.spec`/`.nsi`/EXE committed: confirmed
- Commit b84cad4 — exists
- Commit 7b83a6c — exists
