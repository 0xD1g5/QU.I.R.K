---
phase: 110-cross-sensor-merge-scoring
reviewed: 2026-05-25T12:00:00Z
depth: standard
iteration: 2
files_reviewed: 4
files_reviewed_list:
  - quirk/merge/scan.py
  - quirk/cbom/builder.py
  - quirk/cli/sensor_cmd.py
  - quirk/merge/__init__.py
findings:
  critical: 0
  warning: 0
  info: 1
  total: 1
status: clean
---

# Phase 110: Code Review Report (Re-review, Iteration 2)

**Reviewed:** 2026-05-25
**Depth:** standard
**Files Reviewed:** 4
**Iteration:** 2 (post-fix re-review)
**Status:** clean

---

## Summary

Re-review of the four files modified by the iteration-1 fix pass (commits ab1795b,
1653bb6, 61bc952). All 9 original findings are correctly resolved. No new Critical or
Warning issues are introduced. One pre-existing Info item in `sensor_cmd.py` is noted for
completeness — it is not a regression introduced by this phase's fixes.

**Finding-by-finding confirmation:**

- **CR-01 (CBOM silently dropped):** Confirmed fixed. `build_cbom()` return is captured at
  `scan.py:224`. `write_cbom_files()` is called when `output_dir is not None` (lines 227-229).
  Both `cbom_json_path` and `cbom_xml_path` are present in both return paths (empty-union path
  lines 215-216; normal path lines 257-258). `_cmd_merge` derives `output_dir` from the DB
  path (sensor_cmd.py:713) and passes it through (line 715). The `output_dir=None` path builds
  the `Bom` but writes nothing and returns `None` for both paths — correct and documented.
  Tests `test_cbom_artifact_written_on_merge_run` and `test_cbom_paths_none_without_output_dir`
  cover both branches.

- **CR-02 (surrogate key collision across sensors):** Confirmed fixed. Both
  `_tls_surrogate_key()` and `_codesign_surrogate_key()` now return 4-tuples
  `(sensor_id, cert_subject, cert_pubkey_alg, cert_not_after)` with NULL sensor_id mapping
  to `""` (builder.py lines 397-414, 417-433). The `_tls_surrogate_index` type annotation is
  updated to `dict[tuple[str, str, str, str], Component]` (line 774). The `_sensor_prefix()`
  function is used consistently at all 4 bom_ref sites so the bom_ref looked up in the index
  loop (line 782) uses the same prefix as the cert component's bom_ref (line 721) —
  the key space and the lookup are coherent. `test_codesign_surrogate_attaches_to_correct_sensor_cert`
  verifies the two-sensor wildcard-cert scenario.

- **WR-01 (dead `now` param on `_assemble_union`):** Confirmed fixed. `_assemble_union` at
  line 87 now has signature `(db: Session)` only. Call site at line 181 passes only `db`.

- **WR-02 (never-pushed sensors bypass stale exclusion):** Confirmed fixed. The
  `last_push_at is None` branch (lines 55-59) now checks `enrolled_at` as the reference
  timestamp. `silent_duration = now - ref_ts` gates whether the never-pushed sensor is
  excluded (decommissioned) or flagged as overdue. `enrolled_at is None` falls through to
  `overdue.append()` — acceptable because a sensor with neither push nor enrollment timestamp
  is anomalous and should be flagged. The test uses `enrolled_at=datetime(2026, 5, 25, 12, 0, 0)`
  with `now=12:30` so `silent_duration` = 30 minutes which is well under `stale_days=30` —
  the recently-enrolled sensor is correctly flagged rather than silently excluded.

- **WR-03 (None cadence crashes `timedelta`):** Confirmed fixed. Lines 68-70 guard
  `expected_cadence_minutes` with a `None` check and default to 1440 minutes.

- **WR-04 (double-commit coupling):** Confirmed fixed. Both `db.commit()` calls replaced
  with `db.flush()` (lines 205 and 246). `get_session()` in `db.py:459` issues the sole
  `session.commit()` at context exit — single commit owner. The `MergeRun` row is visible
  within the session immediately after `flush()`. `test_merge_run_persisted` queries a
  separate session after `get_session` exits, confirming the row is durable on disk.

- **WR-05 (CBOM paths absent from result dict):** Resolved together with CR-01 (confirmed above).

- **IN-01 (`datetime.utcnow()` deprecated):** Confirmed fixed in `scan.py`. Line 178 now
  uses `datetime.now(timezone.utc).replace(tzinfo=None)` and `timezone` is imported at line 13.

- **IN-02 (`quirk/merge/__init__.py` exports nothing):** Confirmed fixed. `__init__.py`
  now re-exports `merge_scan` with `__all__` following the `quirk/cbom/__init__.py` pattern.

No regressions observed. Option A (single `build_evidence_summary` + `compute_readiness_score`
call over the full union) and MERGE-05 (`scanned_at` never rewritten) remain intact.

---

## Info

### IN-03: `datetime.utcnow()` in `_build_envelope()` — pre-existing, not introduced by this phase

**File:** `quirk/cli/sensor_cmd.py:296`
**Issue:** `_build_envelope()` uses `datetime.utcnow().strftime(...)` for the `pushed_at`
field of the wire envelope. This is a pre-existing issue in the sensor push path that predates
Phase 110. The FIX-pass for IN-01 correctly fixed the call in `scan.py` but did not (and was
not asked to) touch this separate call in `sensor_cmd.py`. The REVIEW-FIX.md notes that the
deprecation warnings in `test_sensor_ingest.py` are "pre-existing `utcnow()` usage — not
introduced by these fixes", which corroborates this.
**This is not a regression from the iteration-1 fixes.** It is recorded here for backlog
visibility — the fix is a one-line substitution identical to IN-01.
**Fix:** `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")` (add `timezone` to
the existing `from datetime import datetime` import on line 39).

---

_Reviewed: 2026-05-25_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2_
