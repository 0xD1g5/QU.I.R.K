---
phase: 55-qramm-compliance-mapping-view
reviewed: 2026-05-08T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - quirk/cli/qramm_cmd.py
  - quirk/dashboard/api/routes/qramm.py
  - quirk/qramm/compliance_map.py
  - run_scan.py
  - src/dashboard/src/components/qramm/ComplianceMapTab.tsx
  - src/dashboard/src/pages/qramm-assessment.tsx
  - src/dashboard/src/types/api.ts
  - tests/test_qramm_compliance_map.py
  - tests/test_qramm_staleness.py
findings:
  critical: 3
  warning: 4
  info: 3
  total: 10
status: issues_found
---

# Phase 55: Code Review Report

**Reviewed:** 2026-05-08T00:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 55 adds the QRAMM compliance-map endpoint (`GET /api/qramm/sessions/{id}/compliance-map`), a CLI staleness gate (`quirk qramm status`), the `ComplianceMapTab` React component, and supporting data/type definitions. The compliance map arithmetic and data-structure consistency are sound — keys match, 96-row count is correct, and the CVI/non-CVI scoring separation is correctly implemented.

Three blockers were found: a crash-producing unguarded dictionary access in the compliance-map endpoint, an invalid-date crash in the CLI staleness command, and an orphaned-data bug caused by `delete_session` skipping `QRAMMProfile` rows. Four warnings cover fall-through CLI routing, an unbounded query parameter, a bare `open()` in a test, and a misleading helper name. Three info items cover minor quality issues.

---

## Critical Issues

### CR-01: Unguarded `PRACTICE_AREA_TO_DIMENSION` dict access produces HTTP 500

**File:** `quirk/dashboard/api/routes/qramm.py:603`
**Issue:** The compliance-map endpoint accesses `PRACTICE_AREA_TO_DIMENSION[practice_area]` with a plain bracket lookup, not `.get()`. If `QRAMM_COMPLIANCE_WEIGHTS` and `PRACTICE_AREA_TO_DIMENSION` ever diverge (e.g., a weight entry is added without a matching dimension entry during future development), the endpoint throws an unhandled `KeyError`, returning HTTP 500 to the client. The test suite validates the two dicts match at import time, but the runtime path has no safety net.

**Fix:**
```python
dimension = PRACTICE_AREA_TO_DIMENSION.get(practice_area)
if dimension is None:
    logger.error(
        "compliance_map: practice_area %r has no dimension mapping; skipping",
        practice_area,
    )
    continue
```

---

### CR-02: Invalid `QUIRK_CI_STALENESS_OVERRIDE_DATE` value crashes CLI with unhandled `ValueError`

**File:** `quirk/cli/qramm_cmd.py:31`
**Issue:** `_resolve_today()` calls `datetime.date.fromisoformat(override)` with no exception handling. If the environment variable contains a malformed value (e.g., `QUIRK_CI_STALENESS_OVERRIDE_DATE=yesterday`), the function raises `ValueError` and the entire `quirk qramm status` command terminates with a raw traceback rather than a user-readable error. This is particularly harmful in CI where the override is the primary mechanism for testing staleness.

**Fix:**
```python
if override:
    try:
        return datetime.date.fromisoformat(override)
    except ValueError:
        print(
            f"[qramm] ERROR: QUIRK_CI_STALENESS_OVERRIDE_DATE={override!r} "
            "is not a valid ISO date (YYYY-MM-DD). Using today's date.",
            file=sys.stderr,
        )
return datetime.date.today()
```

---

### CR-03: `delete_session` leaks `QRAMMProfile` rows — orphaned data on every session delete

**File:** `quirk/dashboard/api/routes/qramm.py:398-405`
**Issue:** `delete_session` explicitly cascades the `QRAMMAnswer` delete but never touches `QRAMMProfile`. The docstring comment ("Explicit cascade — SQLite FK enforcement is per-connection PRAGMA only") acknowledges the manual-cascade pattern, yet the `QRAMMProfile` table is omitted. Every `DELETE /api/qramm/sessions/{id}` call leaves a `qramm_profiles` row with its `session_id` pointing at a deleted session. On repeated new-assessment cycles (the standard user flow in `qramm-assessment.tsx`) this silently accumulates dead rows and will confuse any future query that joins profiles to sessions.

**Fix:**
```python
@router.delete("/qramm/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)) -> None:
    session = _get_session_or_404(db, session_id)
    # Explicit cascade — SQLite FK enforcement is per-connection PRAGMA only.
    db.query(QRAMMProfile).filter(QRAMMProfile.session_id == session_id).delete()
    db.query(QRAMMAnswer).filter(QRAMMAnswer.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return None
```

---

## Warnings

### WR-01: `quirk qramm <unknown-action>` silently falls through to scan argparse

**File:** `run_scan.py:252-258`
**Issue:** The `qramm` subcommand block only intercepts `argv[2] == "status"` and returns. For any other subcommand (or when `qramm` is called with no action), execution falls through to the main `argparse.ArgumentParser` for the scan command. That parser will receive `["qramm", ...]` as unknown arguments and exit with `error: unrecognized arguments: qramm ...`, printing scan-command usage instead of QRAMM help. This is a confusing UX regression: `quirk qramm` should print qramm-specific help, not scan usage.

All other subcommands (`serve`, `compliance`, `doctor`, `init`) have an unconditional `return` after their routing block. The `qramm` block is missing the fallthrough guard.

**Fix:**
```python
if len(_sys.argv) > 1 and _sys.argv[1] == "qramm":
    if len(_sys.argv) > 2 and _sys.argv[2] == "status":
        from quirk.cli.qramm_cmd import run_qramm_status
        run_qramm_status()
        return
    # No recognized action — print usage and exit cleanly.
    print("Usage: quirk qramm status", file=sys.stderr)
    sys.exit(2)
```

---

### WR-02: `list_sessions` `limit` query parameter has no upper bound — full table scan possible

**File:** `quirk/dashboard/api/routes/qramm.py:427`
**Issue:** The `limit: int = 50` parameter is a plain `int` with no `ge`/`le` constraint. A caller can pass `limit=0` (returns zero rows while still running the full subquery), `limit=-1` (SQLite/SQLAlchemy interprets as no limit, returning all rows), or any arbitrarily large value. For a local desktop tool this is low risk today, but it is inconsistent with how `AnswerItem` and `SaveAnswersRequest` validate their fields with explicit `Field(ge=..., le=...)` bounds.

**Fix:**
```python
def list_sessions(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
) -> List[SessionSummary]:
```
Add `from fastapi import Query` to the imports.

---

### WR-03: `test_no_engine_imports_in_compliance_map` uses bare `open()` without `with` — file handle leak

**File:** `tests/test_qramm_compliance_map.py:69`
**Issue:** The test reads the source file with `src = open(cm.__file__).read()`. The file handle is never explicitly closed. CLAUDE.md requires PEP 8 compliance; PEP 8 and the project's own conventions (search for "with" file patterns elsewhere) expect file handles to be managed with a `with` statement. On CPython the GC closes it, but on PyPy or in resource-constrained CI environments this is a real file-handle leak.

**Fix:**
```python
with open(cm.__file__) as fh:
    src = fh.read()
```

---

### WR-04: `_now_iso` is misleadingly named — returns `datetime`, not an ISO string

**File:** `quirk/dashboard/api/routes/qramm.py:177-178`
**Issue:** The helper is named `_now_iso` but its return type annotation is `-> datetime` and it returns a `datetime` object, not an ISO-formatted string. The actual ISO string conversion is done by the separate `_iso_str` helper. The misleading name creates a false expectation for anyone reading call sites — particularly at lines 312, 314, 393, 500, 547 where the return value is assigned to ORM datetime columns — and could cause a future developer to accidentally pass the result directly to a context expecting a string.

**Fix:** Rename to `_now_utc` or `_utcnow`:
```python
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)
```
Update all 6 call sites accordingly.

---

## Info

### IN-01: `PRACTICE_AREA_NAMES` duplicated between Python and TypeScript with no shared source

**Files:** `quirk/qramm/compliance_map.py:49-62`, `src/dashboard/src/components/qramm/ComplianceMapTab.tsx:29-42`
**Issue:** The 12 practice-area name strings are defined identically in both the Python module and the React component. The Phase 55 design decision (D-04) requires "server-side single source of truth — no duplicate weight data in the React app" for weights; the same concern applies to names. A future rename in Python will silently leave the UI showing the old name unless both files are updated. The compliance-map API response already includes `dimension` and `practice_area` keys; adding `practice_name` to the `ComplianceMapRow` response would allow the UI to consume server-side names directly.

**Fix:** Add `practice_name: str` to `ComplianceMapRow` (server) and `QRAMMComplianceMapRow` (TypeScript type), populate it from `PRACTICE_AREA_NAMES[practice_area]` in the endpoint, and remove `PRACTICE_AREA_NAMES` from `ComplianceMapTab.tsx`.

---

### IN-02: Error message in `ComplianceMapTab` swallows HTTP status code

**File:** `src/dashboard/src/components/qramm/ComplianceMapTab.tsx:100-104`
**Issue:** The `fetch` catch handler ignores the rejected status value and always displays "Check your connection and try again." A 404 (session not found), 422 (validation error), or 500 (server error) all produce the same message, making it hard to diagnose failures without opening DevTools.

**Fix:**
```typescript
.then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
.then((data: QRAMMComplianceMapRow[]) => { ... })
.catch((status) => {
  if (cancelled) return
  const msg = typeof status === "number"
    ? `Could not load compliance map (HTTP ${status}). Check your connection and try again.`
    : "Could not load compliance map. Check your connection and try again."
  setError(msg)
  setLoading(false)
})
```

---

### IN-03: `test_qramm_staleness_override_fresh` and `test_qramm_staleness_override_stale` do not exercise `_resolve_today`

**File:** `tests/test_qramm_staleness.py:62-81`
**Issue:** The two override tests compute staleness arithmetic manually in the test body without actually setting `QUIRK_CI_STALENESS_OVERRIDE_DATE` or calling `_resolve_today`. They validate the math is correct (30 days < 90; 100 days > 90) but do not test the override mechanism itself — specifically that `_resolve_today` reads the environment variable and passes it through correctly. The subprocess test (`test_qramm_status_cli_smoke_stale_via_override`) does exercise the full path, but the unit-level override tests are vacuous.

**Fix:** Refactor using `monkeypatch.setenv` so the override tests actually call `_resolve_today`:
```python
def test_qramm_staleness_override_fresh(monkeypatch) -> None:
    from quirk.qramm.model_meta import QRAMM_MODEL, STALENESS_THRESHOLD_DAYS
    last_verified = datetime.date.fromisoformat(QRAMM_MODEL["last_verified"])
    fake_today = (last_verified + datetime.timedelta(days=30)).isoformat()
    monkeypatch.setenv("QUIRK_CI_STALENESS_OVERRIDE_DATE", fake_today)
    from quirk.cli.qramm_cmd import _resolve_today
    result = _resolve_today()
    assert (result - last_verified).days <= STALENESS_THRESHOLD_DAYS
```

---

_Reviewed: 2026-05-08T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
