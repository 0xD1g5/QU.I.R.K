---
phase: 31-trend-analysis
reviewed: 2026-04-26T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - docs/intelligence-schema.md
  - docs/UAT-SERIES.md
  - quirk/dashboard/api/app.py
  - quirk/dashboard/api/routes/trends.py
  - quirk/dashboard/api/schemas.py
  - quirk/intelligence/trends.py
  - README.md
  - src/dashboard/src/App.tsx
  - src/dashboard/src/components/sidebar.tsx
  - src/dashboard/src/hooks/useTrendsData.ts
  - src/dashboard/src/pages/trends.tsx
  - src/dashboard/src/types/api.ts
  - tests/test_dashboard_trends.py
  - tests/test_intelligence_trends.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 31: Code Review Report

**Reviewed:** 2026-04-26T00:00:00Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 31 implements session-over-session trend analysis: a `compute_trend_report()` intelligence function, `GET /api/trends` FastAPI route, Pydantic schema, TypeScript types, React page, and data-fetch hook. The core logic in `quirk/intelligence/trends.py` is solid — severity bucketing, scan-error exclusion, NULL-scanned_at exclusion, and sample capping all match their design requirements. The FastAPI route and Pydantic layer are structurally correct. The React UI renders and guards correctly for the 0/1-session empty state.

Four defects were found. The most significant is that `docs/intelligence-schema.md` documents a wire format that is entirely different from what the implementation emits — this will mislead anyone integrating against the API. Two frontend bugs were also found: a missing `cancelled` guard that causes a state update on an unmounted React component, and a `new Date(null)` silent coercion in `formatTs`. A display labeling issue rounds out the warnings.

---

## Warnings

### WR-01: Schema documentation wire format does not match implementation

**File:** `docs/intelligence-schema.md:43-101`

**Issue:** The documented wire format uses a nested `sessions` object (`sessions.current_ts`, `sessions.previous_ts`) and nested count objects (`new_finding_counts.high/medium/low`, `resolved_finding_counts.high/medium/low`). The actual Pydantic model (`TrendReportResponse`) and TypeScript interface (`TrendReport`) use a flat structure: `current_session_ts`, `previous_session_ts`, `new_high`, `new_medium`, `new_low`, `resolved_high`, `resolved_medium`, `resolved_low`. The documentation is completely wrong on these field names and nesting. Anyone writing an integration against the documented schema will receive deserialization failures.

**Fix:** Update the wire format examples in `docs/intelligence-schema.md` to match the actual emitted JSON:
```json
{
  "current_session_ts": "2026-04-26T10:30:00",
  "previous_session_ts": "2026-04-26T09:00:00",
  "current_score": 72,
  "previous_score": 65,
  "score_delta": 7,
  "new_high": 0,
  "new_medium": 2,
  "new_low": 1,
  "resolved_high": 1,
  "resolved_medium": 0,
  "resolved_low": 3,
  "scan_errors_new_count": 0,
  "scan_errors_resolved_count": 1,
  "new_findings_sample": [...],
  "resolved_findings_sample": [...]
}
```

---

### WR-02: `setError` called without `cancelled` guard in `useTrendsData`

**File:** `src/dashboard/src/hooks/useTrendsData.ts:23-25`

**Issue:** When `resp.ok` is false the hook calls `setError(...)` at line 24 and immediately returns. This `setError` call is not guarded by `if (!cancelled)`. If the component unmounts between the `fetch()` call completing and the `!resp.ok` branch executing, a state update is dispatched to an unmounted component, triggering a React warning ("Can't perform a React state update on an unmounted component") in React 17 and a no-op state corruption risk in React 18. Every other state mutation in this hook is correctly guarded.

**Fix:**
```typescript
if (!resp.ok) {
  if (!cancelled) {
    setError(`API error: ${resp.status} ${resp.statusText}`)
  }
  return
}
```

---

### WR-03: `formatTs(null)` silently produces the Unix epoch date

**File:** `src/dashboard/src/pages/trends.tsx:72-75`

**Issue:** `formatTs` is declared to accept `string | null`. When passed `null`, `new Date(null)` constructs `new Date(0)` — the Unix epoch (January 1, 1970). The function returns that epoch date formatted as a locale string rather than `"—"`. The guard `if (!iso) return "—"` at line 73 only fires for falsy values: `null`, `undefined`, and the empty string `""` are all falsy, so `null` IS handled correctly. However `new Date(null)` coercion is a subtle JavaScript trap and `null` is explicitly typed as a valid input — if the guard were removed or rearranged the silent coercion would surface. Additionally, if the API ever returns a malformed timestamp string, `new Date(iso).toLocaleString()` returns `"Invalid Date"` with no error boundary or fallback.

**Fix:** Be explicit about the null check and add a validity guard:
```typescript
function formatTs(iso: string | null): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (isNaN(d.getTime())) return "—"
  return d.toLocaleString()
}
```

---

### WR-04: `new_high` badge label misleads for CRITICAL findings

**File:** `src/dashboard/src/pages/trends.tsx:129-130, 140-141`

**Issue:** CRITICAL and HIGH severity findings are both bucketed into `new_high` / `resolved_high` by the backend (`_SEVERITY_BUCKET` in `trends.py:34-35`). The dashboard renders this count with a badge labeled literally "HIGH":
```tsx
<Badge className={SEVERITY_STYLES.HIGH}>HIGH {data.new_high}</Badge>
```
A user who has 3 CRITICAL new findings will see "HIGH 3" — the word CRITICAL never appears. The label does not communicate that this bucket includes CRITICAL severity items, which is the most urgent finding class.

**Fix:** Relabel the badge to reflect the actual bucket contents:
```tsx
<Badge className={SEVERITY_STYLES.CRITICAL}>CRITICAL/HIGH {data.new_high}</Badge>
```
Or use a different badge style that maps to the "high" bucket concept rather than the "HIGH" severity label.

---

## Info

### IN-01: Redundant `isnot(None)` filter in `_fetch_session_endpoints`

**File:** `quirk/intelligence/trends.py:93-95`

**Issue:** The filter at line 95 (`CryptoEndpoint.scanned_at.isnot(None)`) is logically redundant: any row where `scanned_at IS NULL` already cannot satisfy `scanned_at >= target_ts` (a non-null datetime). SQLite evaluates `NULL >= value` as NULL (falsy), so NULL rows are excluded by the range filter regardless. The explicit filter adds no correctness value. It is not harmful, but it is dead predicate logic.

**Fix:** Remove the redundant filter to simplify the query. If intentional as documentation of the D-13 invariant, add a comment explaining that it is present for documentation purposes only.

---

### IN-02: Test fixture shares in-memory SQLite across concurrent test runs

**File:** `tests/conftest.py:93-95`

**Issue:** The `dashboard_client` fixture uses `sqlite:///file::memory:?cache=shared&uri=true`. The `cache=shared` URI parameter means all connections using the same in-process connection string share one in-memory database. If pytest runs tests in parallel (via `pytest-xdist` or similar), multiple test instances will share state and produce non-deterministic results. `test_trends_single_session` expects an empty database — shared cache breaks this invariant under parallel execution.

**Fix:** Use a unique per-invocation URI (e.g., a `uuid4`-tagged name) to ensure isolation:
```python
import uuid
db_name = f"file:testdb_{uuid.uuid4().hex}?mode=memory&cache=shared&uri=true"
engine = create_engine(db_name, connect_args={"check_same_thread": False})
```

---

### IN-03: `README.md` version string inconsistency

**File:** `README.md:1`

**Issue:** The README title and the "What's New" section reference `v4.0.0` in the header (`# QU.I.R.K. — v4.0.0`) but UAT-SERIES.md and CLAUDE.md confirm this is a v4.3 milestone (Phase 31 is in the v4.3 series). The README version string is stale.

**Fix:** Update the README title to `# QU.I.R.K. — v4.3.0` to match the milestone in progress.

---

_Reviewed: 2026-04-26T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
