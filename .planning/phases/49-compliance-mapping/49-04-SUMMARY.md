---
phase: 49-compliance-mapping
plan: 04
subsystem: cli
tags: [cli, compliance, argparse]
requires: [49-02]
provides: [quirk-compliance-status-cli]
affects: [run_scan.py]
tech_stack:
  added: []
  patterns: [argparse-pre-intercept-subcommand]
key_files:
  created: []
  modified:
    - run_scan.py
decisions: []
metrics:
  duration: ~3 min
  completed: 2026-05-05
requirements: [COMPLY-08, COMPLY-09]
---

# Phase 49 Plan 04: CLI `compliance status` Subcommand Summary

CLI intercept block in `run_scan.py:main()` exposes `quirk compliance status [--format json]` via the existing pre-argparse argv inspection pattern (mirrors `init` / `serve`).

## What Was Built

- Added a third pre-intercept block at `run_scan.py:223–245` (between the `serve` block's `return` and the main scan parser's `parser = argparse.ArgumentParser(...)`).
- Local argparse parser with required `action` subparser and `status` action; `--format` constrained to `["text", "json"]` (default `text`).
- Lazy import `from quirk.compliance import status_report` inside the dispatch branch — keeps cold-start cost off the scan path (matches `quirk.cli.init_cmd` lazy-import convention).
- Single `return` at block end. Zero edits to line 223 or below in pre-edit numbering (now line 246+).
- Total diff: +23 lines, 0 deletions.

## Verification

- `python -m compileall -q run_scan.py` — exit 0
- `pytest tests/test_compliance_cli.py -x -q` — 3 passed (path-exists, text smoke, json smoke)
- `pytest tests/test_compliance_schema.py tests/test_compliance_freshness.py tests/test_compliance_title_join.py tests/test_compliance_cli.py tests/test_pqc_terminology_gate.py -x -q` — 12 passed
- `python run_scan.py compliance status` — prints fixed-width table with FIPS 140-3, HIPAA 45 CFR, PCI-DSS 4.0.1 rows
- `python run_scan.py compliance status --format json` — emits valid JSON dict keyed by framework
- `python run_scan.py --version` — `QU.I.R.K. v4.4.0` (regression check on bare-flag fall-through)

## Success Criteria — Met

- COMPLY-08 GREEN — CLI smoke test passes (text + json variants)
- COMPLY-09 structurally satisfied — operator can run `quirk compliance status` to verify map freshness pre-engagement
- All Wave 0 RED tests now GREEN: schema, freshness, title-join, CLI smoke
- Existing scan, init, serve invocations show zero regression (verified via `--version` fall-through)

## Deviations from Plan

None — plan executed exactly as written. Anchor verification (Step 0) returned exactly one match each as expected; insertion bracket matched the planned lines (after serve `return` at line 221, before scan parser at line 223).

## Self-Check: PASSED

- run_scan.py modification verified (`git diff --stat`: 23 insertions)
- Compile check passed
- All 4 verification commands returned expected output
- 12/12 Phase 49 + adjacent gate tests passed
