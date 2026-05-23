---
phase: 88-scoring-residuals
plan: "01"
subsystem: scoring-transparency
tags: [scoring, transparency, testing, reports]
dependency_graph:
  requires: []
  provides: [EVIDENCE-TALLY-01, RENDER-CLI-01, RENDER-PDF-01, SCORE-XPARENCY-01]
  affects: [quirk/reports/writer.py, quirk/reports/executive.py, quirk/reports/html_renderer.py, quirk/reports/templates/report.html.j2]
tech_stack:
  added: []
  patterns: [forward-locking invariant tests, parametrized pytest gates, Jinja2 template context extension]
key_files:
  created:
    - tests/test_scoring_orthogonal_contract.py
    - tests/test_score_render_parity.py
    - tests/test_score_transparency.py
  modified:
    - quirk/reports/writer.py
    - quirk/reports/executive.py
    - quirk/reports/html_renderer.py
    - quirk/reports/templates/report.html.j2
decisions:
  - "D-01: EVIDENCE-TALLY-01 resolved as won't-fix correct-by-design; orthogonal subscore model is intentional and locked via parametrized test"
  - "D-04: RENDER-CLI-01/RENDER-PDF-01 verified no-bug at data layer; single scoring engine confirmed (readiness_score.py deleted; writer.py imports from quirk.intelligence.scoring)"
  - "D-07: Subscore decomposition added to all three non-dashboard report surfaces with canonical label mapping mirroring executive.tsx"
  - "modern_tls trigger key: used finding_severity_counts={LOW:5} not {HIGH:5} because HIGH flows into agility_signals via high_impact ratio — PATTERNS.md had a cross-category leakage error"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-22"
  tasks_completed: 2
  files_changed: 7
---

# Phase 88 Plan 01: Scoring Transparency Gates and Report Decomposition Summary

**One-liner:** Forward-locking orthogonality + render parity tests plus six-subscore N/25 decomposition block on CLI markdown, executive markdown, and HTML/PDF report surfaces.

## What Was Built

### Task 1: Forward-locking orthogonality + render-parity test gates

Two new forward-locking test modules:

**`tests/test_scoring_orthogonal_contract.py`** — Parametrized over all six scoring categories. For each category, asserts that triggering that category's evidence key reduces only that subscore, leaving the other five at 25/25. Module docstring contains the EVIDENCE-TALLY-01 won't-fix rationale citing `quirk/intelligence/scoring.py`'s `_apply_weighted_impacts` architecture and D-01's explicit rejection of cross-category penalties.

Deviation: PATTERNS.md specified `finding_severity_counts={"HIGH": 5}` as the `modern_tls` trigger, but HIGH severity feeds `agility_high_impact_ratio` in the agility category too. The test was corrected to `{"LOW": 5}` (LOW = legacy TLS count) which isolates to `modern_tls` only. This was caught during the RED phase run.

**`tests/test_score_render_parity.py`** — Data-layer parity gate asserting the writer.py-style wrapped dict `{"total": canonical["score"], "subscores": canonical["subscores"]}` equals the canonical engine output, and a second independent `compute_readiness_score` call returns identical values. Also anchors the Phase 86 0-100 integer contract: overall must be `int` in `[0, 100]`, subscores must each be `int` in `[0, 25]`.

Commit: `3a13c8d`

### Task 2: Subscore decomposition on CLI markdown, executive markdown, and HTML/PDF

**`quirk/reports/writer.py`** — Added `## Score Decomposition` markdown table after the `## Score` section in `_scorecard_markdown`. Six rows with hardcoded labels (not scanner-derived, no `md_cell` needed) and `subscores.get(key, '—')` values, followed by `**Rollup:** {raw_sum} ÷ 1.5 = **{total} / 100**`. Uses `score.get("subscores")` (WRAPPED dict with key `"subscores"`).

**`quirk/reports/executive.py`** — Added `### Score Decomposition` section after the Score Drivers block and before `## Confidence & Coverage` in `build_exec_markdown`. Uses `score_raw.get("subscores")` (RAW dict, not the writer.py wrapper).

**`quirk/reports/html_renderer.py`** — Added `subscores=score.get("subscores", {})` to the `template.render(...)` kwargs. `score` is the WRAPPED dict (Pitfall 6 from PATTERNS.md).

**`quirk/reports/templates/report.html.j2`** — Added `{% if subscores %}` guarded decomposition table after the score-card `<div>` block. Six hardcoded label rows, integer values (no `| sanitize` needed per T-88-01), and `{{ subscores.values() | sum }} &divide; 1.5 = <strong>{{ total_score }} / 100</strong>` rollup.

**`tests/test_score_transparency.py`** — Gate asserting `_scorecard_markdown` output contains `"/25"`, `"÷ 1.5"`, and `"Score Decomposition"`; and `build_exec_markdown` output contains the same strings. Uses a mock cfg and the actual scoring engine with empty fixtures.

Commit: `7c23c55`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected modern_tls orthogonality trigger key**
- **Found during:** Task 1 RED phase — `test_subscore_orthogonality[modern_tls...]` failed because `finding_severity_counts={"HIGH": 5}` also affects `agility_signals` via `agility_high_impact_ratio`.
- **Issue:** PATTERNS.md "Evidence key catalogue" listed `{"HIGH": 5}` for modern_tls trigger, but HIGH severity is consumed by both `modern_tls_legacy_versions_ratio` (actually LOW is legacy) and `agility_high_impact_ratio`. HIGH doesn't even affect modern_tls — it's LOW (legacy TLS) that does.
- **Fix:** Changed trigger to `{"LOW": 5}` which triggers `modern_tls_legacy_versions_ratio` only, leaving all other subscores at 25.
- **Files modified:** `tests/test_scoring_orthogonal_contract.py`
- **Commit:** `3a13c8d`

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Subscore values are Python `int` from scoring engine (T-88-01: accepted). Labels are hardcoded Python/Jinja2 literals (T-88-02: mitigated by design — no scanner input reaches decomposition cells).

## Known Stubs

None. All decomposition blocks wire to live `subscores` data from `compute_readiness_score`.

## Self-Check

See below.
