---
phase: 110-cross-sensor-merge-scoring
fixed_at: 2026-05-25T00:00:00Z
review_path: .planning/phases/110-cross-sensor-merge-scoring/110-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 110: Code Review Fix Report

**Fixed at:** 2026-05-25
**Source review:** .planning/phases/110-cross-sensor-merge-scoring/110-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9
- Fixed: 9
- Skipped: 0

## Fixed Issues

### CR-01: `build_cbom()` return value discarded — merged CBOM silently dropped

**Files modified:** `quirk/merge/scan.py`, `quirk/cli/sensor_cmd.py`
**Commit:** ab1795b
**Applied fix:** Captured the `Bom` object from `build_cbom(union)`. Added `output_dir: Optional[str] = None` parameter to `merge_scan()`. When `output_dir` is supplied, calls `write_cbom_files(bom, output_dir, stamp)` and stores the returned paths. Added `cbom_json_path` and `cbom_xml_path` to the result dict (None when no output_dir). Updated `_cmd_merge` in `sensor_cmd.py` to derive `output_dir` from the DB path and print the CBOM artifact paths. Added two new tests: `test_cbom_artifact_written_on_merge_run` and `test_cbom_paths_none_without_output_dir`.

---

### CR-02: `_tls_surrogate_index` key omits `sensor_id` — cross-sensor CODE_SIGNING dedup collision

**Files modified:** `quirk/cbom/builder.py`
**Commit:** 1653bb6
**Applied fix:** Added `sensor_id` as the first element of both `_tls_surrogate_key()` and `_codesign_surrogate_key()`, changing return type from `tuple[str, str, str]` to `tuple[str, str, str, str]`. Updated the `_tls_surrogate_index` type annotation accordingly. NULL/missing sensor_id maps to `""` preserving backward compatibility with single-sensor runs. Added `test_codesign_surrogate_attaches_to_correct_sensor_cert` test verifying two-sensor wildcard-cert scenario.

---

### WR-01: `_assemble_union` accepts `now` parameter but never uses it

**Files modified:** `quirk/merge/scan.py`
**Commit:** ab1795b
**Applied fix:** Removed the `now: datetime` parameter from `_assemble_union()` and updated the call site in `merge_scan()` from `_assemble_union(db, now)` to `_assemble_union(db)`.

---

### WR-02: Never-pushed sensors bypass the stale-decommissioned exclusion

**Files modified:** `quirk/merge/scan.py`
**Commit:** ab1795b
**Applied fix:** In `_build_coverage_warning`, the `last_push_at is None` branch now checks `enrolled_at` as the reference timestamp for the stale cutoff. If enrolled long ago (silence > stale_days) with no push ever, the sensor is excluded (decommissioned). If enrolled recently (within stale_days), it is still flagged as overdue. Updated `test_coverage_warning_overdue_sensor` to use `enrolled_at=today` so the recently-enrolled never-pushed sensor is correctly flagged.

---

### WR-03: `timedelta(minutes=None)` will raise `TypeError` if `expected_cadence_minutes` is NULL

**Files modified:** `quirk/merge/scan.py`
**Commit:** ab1795b
**Applied fix:** Added a None guard before constructing `timedelta`: if `s.expected_cadence_minutes` is None, defaults to 1440 minutes (24h, per architecture §6).

---

### WR-04: `merge_scan()` commits on a caller-managed session — double-commit coupling

**Files modified:** `quirk/merge/scan.py`
**Commit:** ab1795b
**Applied fix:** Replaced both `db.commit()` calls in `merge_scan()` with `db.flush()`. The caller (`get_session` context manager) owns the commit at context exit. This removes double-commit coupling and makes `merge_scan()` composable in larger units of work. The `_cmd_merge` CLI path is unaffected — `get_session` commits on exit.

---

### WR-05: `merge_scan()` result dict does not include CBOM paths

**Files modified:** `quirk/merge/scan.py`
**Commit:** ab1795b
**Applied fix:** Resolved together with CR-01. The result dict now always contains `cbom_json_path` and `cbom_xml_path` keys (None when `output_dir` is not supplied).

---

### IN-01: `datetime.utcnow()` is deprecated in Python 3.12+

**Files modified:** `quirk/merge/scan.py`
**Commit:** ab1795b
**Applied fix:** Replaced `datetime.utcnow()` with `datetime.now(timezone.utc).replace(tzinfo=None)` and added `timezone` to the `from datetime import` statement, consistent with the rest of the codebase.

---

### IN-02: `quirk/merge/__init__.py` exports nothing

**Files modified:** `quirk/merge/__init__.py`
**Commit:** 61bc952
**Applied fix:** Added `from quirk.merge.scan import merge_scan` and `__all__ = ["merge_scan"]`, following the pattern established by `quirk/cbom/__init__.py`.

---

## Verification

**compileall:** `python -m compileall quirk run_scan.py -q` — exit 0, no errors.

**pytest:** `pytest tests/test_merge_scan.py tests/test_merge_cli.py tests/test_cbom_builder.py tests/test_sensor_ingest.py -q`
- **59 passed, 0 failed, 9 warnings** (deprecation warnings in test_sensor_ingest.py for pre-existing `utcnow()` usage — not introduced by these fixes)
- New tests added: `test_cbom_artifact_written_on_merge_run`, `test_cbom_paths_none_without_output_dir`, `test_codesign_surrogate_attaches_to_correct_sensor_cert` — all pass.

---

_Fixed: 2026-05-25_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
