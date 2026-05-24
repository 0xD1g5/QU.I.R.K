---
phase: 98-executive-narrative-score-transparency
plan: "01"
subsystem: reports
tags: [content-model, congruence-guard, exec-narrative, score-transparency, dataclasses]
requires: []
provides: [ExecContent, build_exec_content, _check_congruence, ReportCongruenceError, ALGO_IMPACT_MAP, EFFORT_IMPACT_MAP]
affects: [quirk/reports/executive.py, quirk/reports/html_renderer.py, quirk/reports/writer.py]
tech-stack:
  added: []
  patterns: [plain-dataclass-mutable-build-time, module-level-static-maps, custom-exception-subclass-ValueError, decision-tag-comments]
key-files:
  created:
    - quirk/reports/content_model.py
    - tests/test_exec_content_model.py
    - tests/test_congruence_guard.py
  modified: []
decisions:
  - "5->4 band collapse: EXCELLENT+GOOD share the GOOD narrative lead; MODERATE->FAIR; FAIR->POOR; POOR->CRITICAL (RESEARCH Pattern 4)"
  - "MODERATE blocked by any CRITICAL (D-06 resolution): consistent with EXCELLENT/GOOD restriction; FAIR/POOR unrestricted"
  - "Plain @dataclass (not frozen/slots): ExecContent/RiskItem/RoadmapItem are mutable build-time objects per PATTERNS.md"
  - "ALGO_IMPACT_MAP keyed on keyword strings (not tuples): single-keyword lookup with first-match wins for simplicity"
metrics:
  duration_minutes: 4
  completed: "2026-05-24"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 0
---

# Phase 98 Plan 01: ExecContent Model, Static Maps, Builder, Congruence Guard Summary

**One-liner:** Shared ExecContent dataclass + ALGO_IMPACT_MAP/EFFORT_IMPACT_MAP static maps + _check_congruence guard preventing GOOD/EXCELLENT/MODERATE band from coexisting with CRITICAL findings.

## What Was Built

### Task 1: ExecContent model, static maps, builder, congruence guard

Created `quirk/reports/content_model.py` — the single seam between scoring/findings data and both report renderers. Key components:

- **`RiskItem`/`RoadmapItem`/`ExecContent`** — plain `@dataclass` objects (mutable build-time, not frozen/slots per PATTERNS.md)
- **`ALGO_IMPACT_MAP`** — D-02 static map: crypto class keyword → `(risk_label, impact_sentence)` tuple from UI-SPEC Copywriting Contract. Covers RSA, ECC, ECDSA, DH, DSA (harvest-now-decrypt-later), WEAK_HASH/MD5/SHA-1 (integrity risk), WEAK_KEY_EXCHANGE/RC4/3DES/DES (authentication exposure)
- **`EFFORT_IMPACT_MAP`** — D-05 static map: roadmap item title keyword → `(effort_band, impact_band)`. Covers certificates (LOW/HIGH), KMS (HIGH/HIGH), TLS versions (LOW/HIGH), cipher config (LOW/MEDIUM), etc.
- **`EFFORT_RANK`/`IMPACT_RANK`** — ordering dicts for D-04 within-bucket priority scoring (`priority_score = IMPACT_RANK[impact] * (4 - EFFORT_RANK[effort])`)
- **`_NARRATIVE_LEADS`** — D-01 4-lead map using 5→4 band collapse per RESEARCH Pattern 4
- **`_BAND_CRITICAL_THRESHOLD`** — D-06 threshold dict: EXCELLENT/GOOD/MODERATE → 0 CRITICAL allowed; FAIR/POOR → None (unrestricted)
- **`ReportCongruenceError(ValueError)`** — D-06 custom exception, message matches UI-SPEC Copywriting Contract exactly
- **`_check_congruence(band, sev_counts)`** — D-06 guard raises before any I/O
- **`build_exec_content(score_raw, findings, roadmap_items)`** — builder sourcing `score_raw["score"]` (canonical key, not "total" compat wrapper — Pitfall 1 avoided); calls `_check_congruence()` before returning

Commit: `1caf89c`

### Task 2: Unit tests for content model + congruence guard

Created `tests/test_exec_content_model.py` and `tests/test_congruence_guard.py`.

All 5 VALIDATION.md node IDs green:
- `test_exec_content_model.py::test_top_risks_populated` ✅
- `test_exec_content_model.py::test_roadmap_priority_ordering` ✅
- `test_exec_content_model.py::test_subscores_all_keys_present` ✅
- `test_congruence_guard.py::test_good_band_with_critical_raises` ✅
- `test_congruence_guard.py::test_fair_band_with_critical_ok` ✅

Additional coverage: all band cases (EXCELLENT/MODERATE also raise on CRITICAL), UI-SPEC message format gate, `ReportCongruenceError` is ValueError subclass, `build_exec_content` propagates guard internally, empty subscores edge case, sev_counts computed once.

Regression gates still passing: test_score_transparency, test_executive_score_guard, test_html_report, test_score_render_parity (12 tests).

Commit: `c5e6d83`

## Decisions Made

1. **5→4 band collapse** — EXCELLENT and GOOD share the same narrative lead (strong posture). MODERATE maps to the FAIR lead (gaps requiring attention). FAIR maps to the POOR lead (significant exposure). POOR maps to the CRITICAL lead (immediate remediation). This collapses 5 scoring bands into 4 narrative tones per RESEARCH Pattern 4.

2. **MODERATE blocked by any CRITICAL** — The D-06 resolution (RESEARCH Pattern 2): EXCELLENT, GOOD, and MODERATE all require zero CRITICAL findings. Only FAIR and POOR are unrestricted. This prevents a contradictory "moderate posture" headline with multiple CRITICAL findings.

3. **Plain `@dataclass` (not frozen/slots)** — ExecContent, RiskItem, and RoadmapItem are mutable build-time objects consumed by renderers. `frozen=True, slots=True` is reserved for hash-keyed immutable registry entries (like `IntelligenceReport` in schema.py), not for build-time content containers.

4. **ALGO_IMPACT_MAP keyed on keyword strings** — Simple string keyword lookup with `_classify_finding()` searching finding text (title + description + category + check_id) for first match. Keeps Phase 98 at executive-summary tier — no per-finding "so what" logic (Phase 99).

## Deviations from Plan

None — plan executed exactly as written. The TDD flow was implicit: Task 1 created the implementation; Task 2 created the tests that all passed on first run. The test infrastructure already exists (pytest, no new packages needed).

## Known Stubs

None. The content model is fully functional as a standalone unit. No data flows are stubbed — `build_exec_content()` produces real `ExecContent` objects from real score/findings data. Renderer wiring (executive.py, html_renderer.py, writer.py) is deferred to plan 98-02 per plan scope.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. The module is pure Python computation (no I/O). The only trust boundary is finding-derived text entering `ExecContent` fields — addressed by T-98-01 (top_risks sentences come from static ALGO_IMPACT_MAP, not raw finding text) and T-98-02 (sev_counts computed once, single source for guard + both renderers).

## Self-Check

Files created:
- quirk/reports/content_model.py: `[ -f quirk/reports/content_model.py ]` → FOUND
- tests/test_exec_content_model.py: `[ -f tests/test_exec_content_model.py ]` → FOUND
- tests/test_congruence_guard.py: `[ -f tests/test_congruence_guard.py ]` → FOUND

Commits:
- `1caf89c` feat(98-01): ExecContent model, static maps, builder, congruence guard → FOUND
- `c5e6d83` test(98-01): unit tests for ExecContent model and congruence guard → FOUND

## Self-Check: PASSED
