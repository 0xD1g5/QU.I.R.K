---
phase: 74-qramm-compliance-warnings
plan: 03
subsystem: qramm-compliance
tags: [warning-class, migration-advisor, evidence-bridge, compliance-map, staleness, audit]
requires:
  - quirk/assessment/migration_advisor.py (existing — Phase 70 title-driven advisor)
  - quirk/qramm/evidence_bridge.py::_walk_json_for_alg_strings (existing — Phase 53)
  - quirk/qramm/compliance_map.py SCANNER_COVERAGE (existing — Phase 55)
  - quirk/qramm/model_meta.py QRAMM_MODEL (existing — Phase 51)
  - docs/operators-guide.md §7 Compliance Map Maintenance (line 321, existing)
provides:
  - CANONICAL_ALG_SYNONYMS + _matches word-boundary regex in migration_advisor
  - non-keyed string scan via _matches in _walk_json_for_alg_strings (D-09)
  - SCANNER_COVERAGE_STATUS parallel dict + dashboard rollup consumer (D-10)
  - is_qramm_model_stale public helper (D-11)
  - stale # TODO Phase 50 removed from quirk/compliance/__init__.py (D-12)
affects:
  - quirk/dashboard/api/routes/qramm.py ComplianceMapRow (NEW coverage_status field)
  - tests/test_qramm_compliance_map.py (contract update for pending exclusion)
tech-stack:
  added: []
  patterns:
    - "Word-boundary regex (`r'\\b(...)\\b'`) over substring matching for canonical-token detection"
    - "Parallel status dict alongside numeric weight dict to disambiguate zero-weight semantics"
    - "Nested catalog dict access (`QRAMM_MODEL[\"last_verified\"]`) instead of module-level constants"
key-files:
  created:
    - tests/test_migration_advisor_precision.py
    - tests/test_compliance_coverage_status.py
    - tests/test_qramm_model_stale.py
  modified:
    - quirk/assessment/migration_advisor.py
    - quirk/qramm/evidence_bridge.py
    - quirk/qramm/compliance_map.py
    - quirk/dashboard/api/routes/qramm.py
    - quirk/qramm/model_meta.py
    - quirk/compliance/__init__.py
    - tests/test_qramm_compliance_map.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "D-08 path (a): CANONICAL_ALG_SYNONYMS + _matches helper introduced; title-driven advisor stays per RESEARCH C-4 + C-8 deferral. Synonyms map is also the D-09 consumer's shared source of truth."
  - "D-09 third dict-arm pattern: non-_ALG_KEYS string values scanned via _matches; preserves existing keyed + list behavior (RESEARCH Pitfall 6)."
  - "D-10 targets SCANNER_COVERAGE (not QRAMM_COMPLIANCE_WEIGHTS): SGRM/DPE/ITR → 'pending'; CVI → 'covered'. Pending/n/a EXCLUDED from rollup; partial at half-weight (D-10a)."
  - "D-11 uses nested QRAMM_MODEL['last_verified'] access (no top-level LAST_VERIFIED constant) per RESEARCH C-6 + user input override. Boundary is strict `>` STALENESS_THRESHOLD_DAYS."
  - "D-12: no deferred-items.md note required — target doc docs/operators-guide.md:321 §7 Compliance Map Maintenance verified to exist (RESEARCH C-9)."
metrics:
  duration: ~40 minutes
  completed: 2026-05-15
---

# Phase 74 Plan 03: QWARN-03 Migration Advisor + Compliance Map + Meta Summary

Five surgical fixes (D-08..D-12) close the final 5 of 13 qramm-compliance WARNING-severity audit rows: word-boundary algorithm matching, non-keyed evidence scanning, explicit coverage-status semantics, centralized staleness math, and stale TODO removal. All 13 qramm-compliance WR rows are now closed under Phase 74.

## What Changed

### D-08 (WR-09) — Migration advisor word-boundary regex
- Added module-level `CANONICAL_ALG_SYNONYMS: Final[dict[str, frozenset[str]]]` (DES, 3DES, RC4, MD5, SHA1) and `_matches(canonical, text) -> bool` helper using `r"\b(...)\b"` regex with `re.IGNORECASE`.
- Replaced four title substring checks (`legacy tls`, `plaintext http`, `quantum`, `ssh`) with `re.search(r"\b...\b", title)`. The `\bssh\b` form closes the `sshfp` false-positive cited in audit.
- Per RESEARCH C-4 path (a) + user override: advisor stays title-driven; synonyms map is the D-09 consumer's shared source of truth.

### D-09 (WR-10) — Evidence bridge non-keyed scan
- Imported `CANONICAL_ALG_SYNONYMS` + `_matches` into `quirk/qramm/evidence_bridge.py`.
- Added third dict-iteration arm in `_walk_json_for_alg_strings` after the existing `_ALG_KEYS` and recursive-container branches: `elif isinstance(value, str) and value: if any(_matches(canon, value) for canon in CANONICAL_ALG_SYNONYMS): out.append(value)`.
- Preserves existing keyed + list-of-bare-strings behavior verbatim.

### D-10 (WR-11) — SCANNER_COVERAGE_STATUS + rollup consumer
- NEW `SCANNER_COVERAGE_STATUS: Final[Dict[str, CoverageStatus]]` parallel dict in `quirk/qramm/compliance_map.py` with `CoverageStatus = Literal['covered','partial','pending','n/a']`. Defaults: `CVI='covered'`, `SGRM/DPE/ITR='pending'`.
- Existing `SCANNER_COVERAGE` numeric dict and `QRAMM_COMPLIANCE_WEIGHTS` are UNCHANGED per D-14.
- Dashboard consumer `quirk/dashboard/api/routes/qramm.py::get_compliance_map` imports `SCANNER_COVERAGE_STATUS`, surfaces a new optional `coverage_status` field on `ComplianceMapRow`, and excludes `pending`/`n/a` from the rollup (`relevance_score=None`). `partial` contributes at half-weight (D-10a default).

### D-11 (WR-12) — is_qramm_model_stale public helper
- Added `import datetime` and public `def is_qramm_model_stale(today: datetime.date | None = None) -> bool` in `quirk/qramm/model_meta.py` using nested `QRAMM_MODEL["last_verified"]` access (no top-level `LAST_VERIFIED` constant per RESEARCH C-6 + user override).
- Boundary: `age > STALENESS_THRESHOLD_DAYS` (strict greater-than) — exactly 90 days is NOT stale, 91 days IS stale.
- Phase 75 (QWARN-04) will wire this into `quirk doctor`.

### D-12 (WR-13) — stale TODO Phase 50 removed
- Stripped trailing ` # TODO Phase 50` from line 3 of `quirk/compliance/__init__.py` docstring. Rest of line preserved verbatim.
- Target doc `docs/operators-guide.md:321 §7 Compliance Map Maintenance` verified to exist (RESEARCH C-9). No `deferred-items.md` note created.

### Audit Ledger
- Flipped WR-09, WR-10, WR-11, WR-12, WR-13 in `.planning/audit-2026-05-08/AUDIT-TASKS.md` from `[ ] open` to `Phase 74 | [x] closed` with per-row evidence summary.
- **Combined total: 13/13 qramm-compliance WR rows closed under Phase 74.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Contract update] Updated tests/test_qramm_compliance_map.py for D-10 contract**
- **Found during:** Task 2 (D-10 wiring)
- **Issue:** `test_endpoint_scored_sgrm_dpe_itr_zero` asserted pending dimensions cap at `relevance_score == 0.0` and `test_endpoint_row_shape` enforced an exact key set without `coverage_status`. Both were pre-D-10 contracts that the plan's `'pending' EXCLUDED from rollup` semantics directly invalidate.
- **Fix:** Renamed to `test_endpoint_scored_sgrm_dpe_itr_pending` asserting `relevance_score is None` and `coverage_status == "pending"`; added `coverage_status` to `test_endpoint_row_shape` expected key set.
- **Files modified:** `tests/test_qramm_compliance_map.py`
- **Commit:** `450ddec`
- **Justification:** This is a direct consequence of the locked D-10 contract change, not collateral damage. The plan's success criterion explicitly requires `pending` excluded from rollup; the existing test encoded the pre-D-10 weight=0.0 semantics that the audit row WR-11 flagged as ambiguous.

**2. [Test parametrize clarification] TripleDES_v2 case for `_matches('3DES', ...)`**
- **Found during:** Task 1 (RED test authoring)
- **Issue:** Plan flagged this case as "researcher confirms expected semantics" — `\b` between `S` and `_` in Python regex.
- **Fix:** Documented choice in test source: Python regex `\b` treats `_` as a word character, so `\b3DES\b`/`\bTripleDES\b` does NOT match `TripleDES_v2`. Expectation overridden to `False` in the parametrize body with inline justification.
- **Files modified:** `tests/test_migration_advisor_precision.py`
- **Commit:** `c336535`
- **Justification:** Plan delegated semantic choice to researcher.

## Self-Check: PASSED

**Files verified:**
- FOUND: `quirk/assessment/migration_advisor.py` (CANONICAL_ALG_SYNONYMS + _matches present)
- FOUND: `quirk/qramm/evidence_bridge.py` (third dict-arm with _matches present)
- FOUND: `quirk/qramm/compliance_map.py` (SCANNER_COVERAGE_STATUS present)
- FOUND: `quirk/dashboard/api/routes/qramm.py` (coverage_status surfaced)
- FOUND: `quirk/qramm/model_meta.py` (is_qramm_model_stale present)
- FOUND: `quirk/compliance/__init__.py` (TODO Phase 50 removed; 0 matches)
- FOUND: `tests/test_migration_advisor_precision.py` (15 tests passing)
- FOUND: `tests/test_compliance_coverage_status.py` (4 tests passing)
- FOUND: `tests/test_qramm_model_stale.py` (5 tests passing)

**Commits verified (git log):**
- FOUND: `c336535` test(74-03): add failing tests for QWARN-03 (D-08..D-11)
- FOUND: `4a783ff` feat(74-03): word-boundary advisor + non-keyed alg scan (D-08, D-09, WR-09, WR-10)
- FOUND: `450ddec` feat(74-03): add SCANNER_COVERAGE_STATUS + dashboard rollup consumer (D-10, WR-11)
- FOUND: `2a5552d` feat(74-03): add is_qramm_model_stale public helper (D-11, WR-12)
- FOUND: `e0ccc4f` chore(74-03): remove stale TODO Phase 50 comment (D-12, WR-13)
- FOUND: `8cf11bc` docs(74-03): close qramm-compliance WR-09..WR-13 in audit ledger

**Verification matrix:**
- `python -m compileall` clean on all 6 modified source files
- `pytest tests/test_migration_advisor_precision.py tests/test_compliance_coverage_status.py tests/test_qramm_model_stale.py tests/test_qramm_compliance_map.py tests/test_qramm_staleness.py tests/test_compliance_freshness.py -x` → 45 passed
- `grep -cE "qramm-compliance/WR-(09|10|11|12|13).*Phase 74.*\[x\] closed"` → 5
- `grep -cE "qramm-compliance/WR-.*\[ \] open"` → 0
- `grep -cE "qramm-compliance/WR-.*Phase 74.*\[x\] closed"` → 13 (full phase closure)
- `grep -cE "TODO Phase 50" quirk/compliance/__init__.py` → 0
