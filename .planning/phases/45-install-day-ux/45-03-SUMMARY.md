---
phase: 45-install-day-ux
plan: 03
subsystem: risk-engine + reports + dashboard + intelligence
tags: [risk-engine, report-renderer, dashboard, coverage-gap, score-exclusion, install-day]
requires:
  - 45-02 (quirk/util/optional_extra.py + ADVISORY CryptoEndpoint emission)
provides:
  - "ADVISORY → coverage_gap finding mapping in risk_engine.evaluate_endpoints"
  - "Coverage Gaps HTML report section + exclusion from All Findings table, top-10 preview, and severity counts"
  - "FindingItem.category Pydantic field for dashboard parity"
  - "evidence summary excludes coverage_gap from totals + finding_severity_counts (D-07)"
affects:
  - quirk/engine/risk_engine.py
  - quirk/reports/templates/report.html.j2
  - quirk/reports/html_renderer.py
  - quirk/intelligence/evidence.py
  - quirk/dashboard/api/schemas.py
tech-stack:
  added: []
  patterns:
    - "Discriminator field on finding dict (`category='coverage_gap'`) gates rendering and scoring paths"
    - "Jinja `selectattr/rejectattr` filters keep coverage_gap out of executive surfaces"
key-files:
  created:
    - tests/test_risk_engine_coverage_gap.py
    - tests/test_html_renderer_coverage_gaps.py
    - tests/test_evidence_coverage_gap.py
    - tests/test_dashboard_schemas_finding_category.py
  modified:
    - quirk/engine/risk_engine.py
    - quirk/reports/templates/report.html.j2
    - quirk/reports/html_renderer.py
    - quirk/intelligence/evidence.py
    - quirk/dashboard/api/schemas.py
decisions:
  - "D-04 / D-05 honored: coverage_gap is a finding category — INFO severity, dedicated HTML section, host + recommendation surfaced."
  - "D-07 honored end-to-end: coverage_gap rows excluded from severity counts (renderer), excluded from totals.findings + finding_severity_counts (evidence), zero impact on readiness or confidence subscore."
  - "Q2 user decision honored: dashboard FindingItem.category added (additive, no DB migration)."
  - "Q1 user decision (motion omitted from registry) preserved — risk_engine ADVISORY branch is registry-shape-agnostic so existing Phase 41 inline motion advisories at run_scan.py:782/827 ALSO render through the same coverage_gap path."
metrics:
  duration_minutes: 5
  tasks_completed: 5
  files_modified: 5
  files_created: 4
  completed_date: 2026-05-03
---

# Phase 45 Plan 03: Coverage-Gap Visibility + Score Exclusion Summary

ADVISORY CryptoEndpoint rows from `quirk.util.optional_extra` (Plan 02) now surface as INFO `coverage_gap` findings in a dedicated HTML "Coverage Gaps" section and the dashboard DTO, while being filtered out of severity counts, the All Findings table, the top-10 executive preview, totals.findings, and finding_severity_counts — D-07's "zero score impact" requirement enforced end-to-end.

## What Was Built

**Task 1 — Risk engine ADVISORY branch** (`quirk/engine/risk_engine.py`)
New early-exit branch in `evaluate_endpoints`: rows with `protocol == "ADVISORY"` and `scan_error_category == "missing_extra"` produce a single finding dict with `severity="INFO"`, `category="coverage_gap"`, recommendation = the install hint from `scan_error`. The `continue` after append prevents double-emission via the generic scan_err handler. Defensive: ADVISORY rows with other `scan_error_category` values fall through to the existing handler.

**Task 2 — HTML report Coverage Gaps section** (`quirk/reports/templates/report.html.j2` + `quirk/reports/html_renderer.py`)
- New `<h2>Coverage Gaps</h2>` section (with explanatory caption) inserted before "All Findings", guarded by `{% if coverage_gaps %}` so it disappears when there are no gaps.
- All Findings loop now `{% for f in findings if f.get('category') != 'coverage_gap' %}` — coverage_gap rows render exactly once (in their dedicated section).
- Top-10 executive preview now `{% for f in (findings | rejectattr('category', 'equalto', 'coverage_gap') | list)[:10] %}` — coverage_gap can never dominate the executive summary.
- Severity-count loop in `render_html_report` skips `category == 'coverage_gap'` rows so the sev-badge pills (HIGH/MEDIUM/LOW/INFO) reflect actionable findings only.

**Task 3 — Score / evidence exclusion** (`quirk/intelligence/evidence.py`)
`build_evidence_summary` filters `coverage_gap` entries out of `finding_list` immediately after the input copy, so every downstream consumer (`finding_severity_counts`, `totals.findings`, `_finding_targets`, scoring.py readers) sees only actionable findings. D-07's hard constraint is enforced at the source instead of relying on every consumer to remember the exclusion.

**Task 4 — Dashboard FindingItem.category** (`quirk/dashboard/api/schemas.py`)
Added `category: Optional[str] = None` to the `FindingItem` Pydantic DTO (additive only — no DB migration, no existing-call breakage). Q2 user decision encoded.

**Task 5 — Phase-gate sweep**
- `python -m compileall quirk run_scan.py` — clean.
- `pytest --deselect tests/test_cbom_schema_validation.py` — 719 passed, 36 deselected.
- `pytest -m slow tests/test_install_all_excludes_impacket.py -x` — 1 passed.

## D-07 Verification (Score Exclusion)

The hard "zero score impact" guarantee is guarded at three levels:

| Layer | Mechanism | Test guard |
|-------|-----------|------------|
| HTML renderer sev pills | `if f.get("category") == "coverage_gap": continue` in `html_renderer.render_html_report` sev_counts loop | `tests/test_html_renderer_coverage_gaps.py::test_sev_counts_exclude_coverage_gap` |
| Evidence summary | `finding_list = [f for f in finding_list if not (isinstance(f, Mapping) and f.get("category") == "coverage_gap")]` at the top of `build_evidence_summary` | `tests/test_evidence_coverage_gap.py::test_evidence_summary_excludes_coverage_gap` |
| Risk engine emission shape | `category="coverage_gap"` on the finding so all downstream filters can recognize it | `tests/test_risk_engine_coverage_gap.py::test_advisory_row_becomes_coverage_gap_finding` |

Regression guard (no behavior change for non-coverage_gap inputs): `tests/test_evidence_coverage_gap.py::test_evidence_summary_zero_coverage_gaps_unchanged` and the existing `tests/test_intelligence_evidence.py` + `tests/test_intelligence_scoring.py` suites — all GREEN.

## User Decisions Encoded

| Decision | Encoded in |
|----------|------------|
| Q1 — motion OMITTED from optional_extra registry; Phase 41 inline calls at `run_scan.py:782, 827` remain sole emitter | risk_engine ADVISORY branch is registry-agnostic — it keys on `protocol="ADVISORY" + scan_error_category="missing_extra"`, which the inline motion advisories already produce. They render through the same coverage_gap path automatically. (Locked by Plan 02 tests.) |
| Q2 — dashboard FindingItem gains `category: Optional[str] = None` (additive; no DB migration) | `quirk/dashboard/api/schemas.py` `FindingItem.category` (Task 4) |
| Q3 — redis OMITTED from optional_extra registry | Locked by Plan 02 tests; Plan 03 makes no registry changes |

## Commits

| Hash | Message |
|------|---------|
| 304ca9c | test(45-03): add coverage_gap branch tests for risk_engine |
| 8441ca6 | feat(45-03): map ADVISORY rows to coverage_gap findings in risk_engine |
| 2821b49 | test(45-03): add Coverage Gaps render and sev-count tests |
| 0012556 | feat(45-03): render Coverage Gaps section and exclude from sev counts (D-07) |
| 2491cd2 | test(45-03): add evidence-summary coverage_gap exclusion tests |
| 83fb26d | feat(45-03): exclude coverage_gap findings from evidence summary (D-07) |
| 2df3cac | test(45-03): add FindingItem.category schema tests |
| 80e47f6 | feat(45-03): add category field to dashboard FindingItem DTO (Q2) |
| 08ac456 | chore(45-03): log pre-existing CBOM schema-validation env failure to deferred-items |

## Deviations from Plan

**1. [Rule 1 — test refinement] Adjusted `test_sev_counts_exclude_coverage_gap` post-RED-commit**
- **Found during:** Task 2 GREEN check.
- **Issue:** Initial regex-based assertion (`re.search(r"INFO[^0-9<]{0,80}([0-9]+)", html)`) matched score-band UI text containing "INFO" prose far from the sev_counts pills, producing a false positive (`INFO=100`).
- **Fix:** Replaced fragile regex with a stronger, template-shape-aware substring check: assert `"HIGH: 1" in html` and `"INFO: 2" not in html` and `"INFO: 1" not in html`. The renderer's sev-badge template (`{% if sev_counts.get(sev, 0) > 0 %}<div class="sev-badge sev-{{ sev }}">{{ sev }}: {{ sev_counts.get(sev, 0) }}</div>{% endif %}`) only emits a badge when count > 0, so the absence of any "INFO: N" badge is the strongest assertion possible.
- **Files modified:** `tests/test_html_renderer_coverage_gaps.py`
- **Commit:** Folded into 0012556 (combined with the production change so the GREEN gate is committed atomically with the corrected assertion).

**2. [Scope-boundary] Deferred pre-existing CBOM schema-validation environment failure**
- **Found during:** Task 5 phase-gate sweep.
- **Issue:** `tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[*]` fails with `MissingOptionalDependencyException: ... cyclonedx-python-lib with the extra "json-validation"`.
- **Fix:** None — verified pre-existing via `git stash` on parent commit; test was already failing before any Plan 45-03 work. Logged to `.planning/phases/45-install-day-ux/deferred-items.md` per scope-boundary rule.
- **Resolution path:** Add `cyclonedx-python-lib[json-validation]` to dev/test requirements (out of scope for Plan 45-03).
- **Commit:** 08ac456

No other deviations — the plan executed exactly as written.

## Out-of-Scope (Per Plan)

- TypeScript mirror in `src/dashboard/src/types/api.ts` (deferred to future dashboard polish — confirmed in plan).
- CLAUDE.md mandatory phase-completion steps (UAT update, vault sync, phase note, manual checkpoint) — owned by Plan 04 (Wave 3).
- Compact / aggregated rendering, confidence-subscore penalty, `quirk doctor` CLI, per-scanner `*_AVAILABLE` migration (D-11).

## Threat Model Verification

| Threat ID | Disposition | Verified by |
|-----------|-------------|-------------|
| T-45-08 (Tampering — sev count inflation) | mitigate | `test_sev_counts_exclude_coverage_gap` |
| T-45-09 (Tampering — score skew) | mitigate | `test_evidence_summary_excludes_coverage_gap` + existing intelligence_scoring tests still GREEN |
| T-45-10 (Information Disclosure — install_hint XSS) | mitigate | Jinja `select_autoescape(["html", "j2"])` already configured at `html_renderer.py:61`; install hint is rendered via `{{ f.get('recommendation','') }}` (escaped) |
| T-45-11 (Tampering — double-emission of motion advisories) | mitigate | risk_engine `continue` after coverage_gap append; `test_advisory_row_becomes_coverage_gap_finding` asserts no "Informational protocol observation" duplicate |

## Hand-Off to Plan 04 (Wave 3)

GREEN gate state at completion:
- `python -m compileall quirk run_scan.py`: clean.
- Default suite (excluding pre-existing CBOM schema-validation env failure): 719 passed, 36 deselected.
- Slow regression `tests/test_install_all_excludes_impacket.py`: 1 passed.

Plan 04 inherits this state and is unblocked. Plan 04 is responsible for the CLAUDE.md phase-completion steps: UAT-SERIES.md update, vault sync, Obsidian phase note, ROADMAP.md update, manual checkpoint.

## Self-Check: PASSED

- Files created (all confirmed via `[ -f ... ]`):
  - tests/test_risk_engine_coverage_gap.py
  - tests/test_html_renderer_coverage_gaps.py
  - tests/test_evidence_coverage_gap.py
  - tests/test_dashboard_schemas_finding_category.py
- Commits confirmed via `git log --oneline`: 304ca9c, 8441ca6, 2821b49, 0012556, 2491cd2, 83fb26d, 2df3cac, 80e47f6, 08ac456 — all present.
