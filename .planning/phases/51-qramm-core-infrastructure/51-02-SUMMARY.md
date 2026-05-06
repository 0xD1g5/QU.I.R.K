---
phase: 51-qramm-core-infrastructure
plan: "02"
subsystem: qramm
tags: [qramm, scoring, catalog, csnp, python]
completed: "2026-05-06"
duration_minutes: 3

dependency_graph:
  requires: []
  provides:
    - quirk.qramm package (4 modules)
    - QRAMM_QUESTIONS 120-entry CSNP catalog
    - weakest-link scoring engine (compute_practice_score, compute_dimension_score, compute_overall_score)
    - QRAMM_MODEL staleness metadata
  affects:
    - Plan 51-03 (router will consume these modules)
    - Plan 51-04 (unit tests target these modules)

tech_stack:
  added: []
  patterns:
    - Pure stdlib Python module with zero external dependencies
    - D-09 isolation: scoring.py imports only __future__ and typing
    - Weakest-link min() scoring (D-06) — not average
    - Staleness metadata constant pattern (mirrors quirk/compliance/__init__.py)
    - _entry() factory function for catalog entry construction

key_files:
  created:
    - quirk/qramm/__init__.py
    - quirk/qramm/scoring.py
    - quirk/qramm/model_meta.py
    - quirk/qramm/questions.py
  modified: []

decisions:
  - "D-09 isolation enforced by grep acceptance criterion: scoring.py imports only __future__ and typing"
  - "Weakest-link rule uses min() not average — defining QRAMM scoring decision per CSNP scoring-methodology.md"
  - "STALENESS_THRESHOLD_DAYS=90 (quarterly cadence) vs compliance module's 365 (annual)"
  - "Q1 uses specific CSNP verbatim maturity labels; Q2-Q120 use generic 4-point labels per RESEARCH.md A1"
  - "get_question() helper added for O(1) lookup by question_number"

metrics:
  completed_date: "2026-05-06"
  task_count: 2
  file_count: 4
---

# Phase 51 Plan 02: QRAMM Package — Questions, Scoring, Model Meta

**One-liner:** Pure-Python quirk/qramm/ package with 120-question CSNP catalog, weakest-link scoring engine (min() rule, D-09 isolated), and 90-day staleness metadata constant.

## What Was Built

### Task 1: quirk/qramm/ package — __init__.py, scoring.py, model_meta.py

Created three foundational modules for the QRAMM data layer:

**`quirk/qramm/__init__.py`** — Package init with module docstring identifying all three sub-modules and crediting the MIT-licensed CSNP source.

**`quirk/qramm/scoring.py`** — Pure-math weakest-link scoring engine implementing:
- `compute_practice_score(answers: List[int]) -> float` — average of question answers, rounded to 4 decimal places
- `compute_dimension_score(practice_scores: List[float]) -> float` — min() of practice scores (weakest-link D-06, NOT average)
- `compute_overall_score(dimension_scores: Dict[str, float], multiplier: float) -> Dict` — applies profile multiplier, averages 4 dimensions, returns maturity label
- `_maturity_label(score: float) -> str` — maps score to Basic/Developing/Established/Advanced/Optimizing
- D-09 isolation enforced: zero imports from quirk.risk_engine, quirk.scanner, quirk.db, or quirk.models

**`quirk/qramm/model_meta.py`** — Staleness metadata constant:
- `STALENESS_THRESHOLD_DAYS = 90` (quarterly cadence for active open-source CSNP toolkit)
- `QRAMM_MODEL` dict with all 5 required keys: qramm_version, last_verified, source_url, github_url, license

Commit: `bafb31e`

### Task 2: quirk/qramm/questions.py — 120 verbatim CSNP catalog entries

Created the full 120-question CSNP QRAMM catalog:

- **Exact 120 entries** in `QRAMM_QUESTIONS` list with sequential question_number 1-120
- **Dimension distribution:** CVI (Q1-30), SGRM (Q31-60), DPE (Q61-90), ITR (Q91-120) — 30 each
- **Practice area distribution:** 12 practice areas (1.1-4.3), 10 questions each
- **Maturity labels:** Q1 uses verbatim CSNP-specific 4 labels; Q2-Q120 use generic 4-level labels (per RESEARCH.md A1 assumptions)
- **`get_question(n)`** helper with bounds validation (raises IndexError for n outside 1..120)
- All question texts verbatim from CSNP MIT-licensed source

Spot-checks verified:
- Q1: "How does your organization identify cryptographic assets?" ✓
- Q120: "How does your organization contribute to industry standards or best practices for validating cryptographic implementations?" ✓
- Q11: dimension=CVI, practice_area=1.2 ✓

Commit: `d200a74`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All four modules are complete implementations with no placeholder values. The CLI surface (`quirk qramm status`) is intentionally deferred to Phase 55 per plan design.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries introduced. All four files are pure-Python with no I/O, no external calls, and no database access. T-51-04 (question text drift) and T-51-07 (scoring.py forbidden imports) mitigations verified by grep acceptance criteria.

## Self-Check

Files created:
- `quirk/qramm/__init__.py` — EXISTS
- `quirk/qramm/scoring.py` — EXISTS
- `quirk/qramm/model_meta.py` — EXISTS
- `quirk/qramm/questions.py` — EXISTS

Commits:
- `bafb31e` — Task 1 (3 files)
- `d200a74` — Task 2 (1 file)
