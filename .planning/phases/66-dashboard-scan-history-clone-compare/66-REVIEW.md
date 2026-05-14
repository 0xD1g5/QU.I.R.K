---
phase: 66-dashboard-scan-history-clone-compare
reviewed: 2026-05-14T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - tests/test_dashboard_scan_history.py
  - quirk/dashboard/api/schemas.py
  - quirk/dashboard/api/routes/scan.py
  - src/dashboard/src/hooks/useCompareData.ts
  - src/dashboard/src/pages/scan-history.tsx
  - src/dashboard/src/pages/compare.tsx
  - src/dashboard/src/types/api.ts
  - src/dashboard/src/pages/scan-new.tsx
  - src/dashboard/src/App.tsx
  - src/dashboard/src/components/sidebar.tsx
findings:
  critical: 0
  warning: 6
  info: 3
  total: 9
status: issues_found
---

# Phase 66: Code Review Report

**Reviewed:** 2026-05-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Phase 66 adds scan history, clone, and compare features to the QUIRK dashboard: a `GET /api/scans` enrichment (score, finding counts, clone metadata), a new `GET /api/compare` endpoint, a `ScanHistoryPage` with checkbox selection and clone navigation, and a `ComparePage` with a score-delta summary and tabbed diff view. The schemas and TypeScript types are well-aligned overall.

Six warnings and three info items were found. The most significant concerns are: a `scan_id` format mismatch between `list_scans` and `compare_scans` that will silently produce 404s when the frontend passes a history `scan_id` to `/api/compare`; a silent data loss in the endpoint-diff dictionary when a host appears on multiple ports; and an incorrect amber-notice guard in the clone handler.

---

## Warnings

### WR-01: `scan_id` format mismatch between `list_scans` and `compare_scans` causes silent 404

**File:** `quirk/dashboard/api/routes/scan.py:830` and `:1056`

**Issue:** `list_scans` stores `scan_id` as the raw `ts_str` value produced by SQLite's `strftime("%Y-%m-%d %H:%M:%S", ...)`, which uses a **space** separator — e.g. `"2026-05-14 11:51:54"`. The frontend passes this string directly to `/api/compare?a=<scan_id>`. `compare_scans` calls `datetime.fromisoformat(a)` — which accepts the space-separator form in Python 3.11+ — so parsing succeeds. However, `_fetch_session_endpoints_1s` queries with `scanned_at >= ts` and `< ts + timedelta(seconds=1)`. Because `ts` is truncated to whole seconds by `strftime`, endpoints whose `scanned_at` was stored with sub-second precision will be missed if those sub-second values happen to be at the boundary (i.e., `scanned_at` is exactly `ts` with microseconds `000000`, which is the only case the 1s window reliably captures). This is consistent with the existing `_fetch_session_endpoints_1s` design, but the deeper problem is: `compare_scans` also passes `ts_a` as `scanned_at` to `CompareScanSummary` (line 1123), which is a `datetime` field. Pydantic will serialize this as a full ISO timestamp with `T`-separator and microseconds, returning a value that differs from the `scan_id` string originally emitted by `list_scans`. Any client code that round-trips the `scan_a.scanned_at` as a `scan_id` will break.

The more immediate bug is on line 1123: `CompareScanSummary(scan_id=a, scanned_at=ts_a, ...)`. `ts_a` was produced by `datetime.fromisoformat(a)` where `a` is a space-separated string like `"2026-05-14 11:51:54"`. Pydantic serializes `scanned_at` as `"2026-05-14T11:51:54"` — a different format from `scan_id`. This inconsistency will confuse clients that use `scan_a.scanned_at` to reload a scan via `?scan_id=`.

**Fix:** Normalize `scan_id` at the source. In `list_scans`, emit `scan_id` using the same ISO format as `compare_scans` expects:
```python
# line ~830
scan_id = ts.isoformat()  # "2026-05-14T11:51:54" — T-separator, consistent with compare_scans
sessions.append(ScanSession(scan_id=scan_id, ...))
```
Then the `scan_id` passed to `/api/compare` parses cleanly and the `CompareScanSummary.scanned_at` matches it.

---

### WR-02: Endpoint diff loses multi-port hosts — last-write-wins dict clobbers earlier entries

**File:** `quirk/dashboard/api/routes/scan.py:1104–1105`

**Issue:** The `hosts_a` and `hosts_b` dicts key on `ep.host` alone:
```python
hosts_a: dict[str, CryptoEndpoint] = {ep.host: ep for ep in eps_a if ep.host}
```
When a host appears on multiple ports (e.g. `api.example.com:443` and `api.example.com:8443`) only the last endpoint row survives in the dict. All earlier ports are silently discarded. `changed_endpoints` therefore only checks one arbitrarily-chosen port pair per host, and the `only_in_a` / `only_in_b` sets cannot detect that a specific port was added or removed.

**Fix:** Key on `(host, port)` tuple to preserve all endpoints per host:
```python
hosts_a = {(ep.host, ep.port): ep for ep in eps_a if ep.host}
hosts_b = {(ep.host, ep.port): ep for ep in eps_b if ep.host}
only_in_a = sorted(f"{h}:{p}" for h, p in set(hosts_a) - set(hosts_b))
only_in_b = sorted(f"{h}:{p}" for h, p in set(hosts_b) - set(hosts_a))
```
Update `CompareEndpoint` accordingly or keep host-only display while keying internally on `(host, port)`.

---

### WR-03: Clone amber-notice guard is inverted — fires for dashboard scans, not CLI scans

**File:** `src/dashboard/src/pages/scan-history.tsx:39`

**Issue:**
```typescript
if (s.profile === null) params.set("reconstructed", "1")  // amber notice trigger
```
The comment says "amber notice trigger," meaning this is supposed to fire when the scan was launched from the CLI (no `ScanJob` row, so `profile` is `null`). However, a scan where `profile` is `null` AND `target` contains a reconstructed host list (from the fallback path in `list_scans`) is already being navigated to the new-scan form with those targets pre-filled. The amber notice correctly appears in that case.

The actual logic error is on the line before it: `if (s.target) params.set("target", s.target)`. A CLI-reconstructed scan (no `ScanJob`) will have `target` set to a comma-joined host list from the fallback path. A dashboard-launched scan (with `ScanJob`) will also have `target` set from `job.target`. Both will set `target` in the URL params. The distinction is whether the user should be warned — which is supposed to be CLI scans only (`profile === null`).

But `profile` can also be `null` for dashboard-launched scans if the `ScanJob` row has no `profile` column populated (though the schema requires it). More critically: the logic `if (s.profile === null)` fires for every CLI scan but also any future null-profile case, and the `reconstructed=1` param is set **after** the target param is conditionally set — so a scan with `s.target !== null` and `s.profile === null` will set both `target` and `reconstructed=1`, which is correct. A scan with `s.target !== null` and `s.profile !== null` will set only `target`, which is also correct. The guard is logically consistent.

Re-examining: the real bug is that the comment says the `reconstructed` notice should indicate "targets reconstructed from scan results" (i.e., CLI scan), but `ScanNewPage` displays the amber notice when `searchParams.get("reconstructed") === "1"`. Since CLI scans have `profile === null`, the guard correctly marks them. However, the guard expression reads `s.profile === null` while the outer `if` just above already passed `s.profile` as falsy to `params.set`. The `params.set("reconstructed", "1")` is inside `handleClone` at line 39, which fires regardless of `s.target`. This means a CLI scan that produced **zero** endpoints (empty `target`) still gets `reconstructed=1` in the URL, but has no target to pre-fill — the amber notice fires with an empty target field, which is confusing.

More critically, line 39 runs unconditionally only when `s.profile === null`, but line 36 `if (s.target)` won't set the target. The amber notice will appear with no pre-filled target for null-target CLI scans, giving the user a warning about "reconstructed targets" when there are none. This is incorrect behavior.

**Fix:**
```typescript
function handleClone(s: ScanSession) {
  const params = new URLSearchParams()
  if (s.target) params.set("target", s.target)
  if (s.profile) params.set("profile", s.profile)
  if (s.calibration) params.set("calibration", s.calibration)
  // Only show amber notice if targets were reconstructed AND there are targets to show
  if (s.profile === null && s.target) params.set("reconstructed", "1")
  navigate(`/scan/new?${params.toString()}`)
}
```

---

### WR-04: `useCompareData` — `loading` not reset to `false` when `scanA` or `scanB` is cleared

**File:** `src/dashboard/src/hooks/useCompareData.ts:19–20`

**Issue:** When `scanA` or `scanB` becomes null/empty mid-render (e.g., the user navigates away or query params are cleared), the `useEffect` fires and immediately returns on line 20 (`if (!scanA || !scanB) return`). At that point `loading` retains whatever value it had from a previous run — potentially `true` if a prior fetch was in-flight and `cancelled` was set. The `finally` block in `fetchCompare` sets `if (!cancelled) setLoading(false)`, but once cancelled is set to `true` during cleanup, that branch never executes. Result: `loading` stays `true` indefinitely after the component unmounts or params clear while a fetch is in flight.

**Fix:** Reset loading state in the early-return branch:
```typescript
useEffect(() => {
  if (!scanA || !scanB) {
    setLoading(false)
    setData(null)
    setError(null)
    return
  }
  // ... rest unchanged
}, [scanA, scanB])
```

---

### WR-05: `handleCompare` crashes with `TypeError` if either `scan_id` is not found in `sessions`

**File:** `src/dashboard/src/pages/scan-history.tsx:45–46`

**Issue:**
```typescript
const sess1 = sessions.find(s => s.scan_id === s1)!
const sess2 = sessions.find(s => s.scan_id === s2)!
```
The non-null assertions (`!`) suppress TypeScript's undefined warning. However `sessions.find(...)` can return `undefined` at runtime if the session list was refreshed between the user checking the checkbox and pressing "Compare scans" (e.g., a new scan completed and the list re-fetched, altering `scan_id` values). Calling `sess1.scanned_at` on `undefined` throws a `TypeError` that propagates uncaught, producing a blank crash rather than a user-visible error.

**Fix:**
```typescript
function handleCompare() {
  const [s1, s2] = selected
  const sess1 = sessions.find(s => s.scan_id === s1)
  const sess2 = sessions.find(s => s.scan_id === s2)
  if (!sess1 || !sess2) return  // stale selection; silently no-op
  const newer = sess1.scanned_at >= sess2.scanned_at ? s1 : s2
  const older = newer === s1 ? s2 : s1
  navigate(`/compare?a=${encodeURIComponent(newer)}&b=${encodeURIComponent(older)}`)
}
```

---

### WR-06: `/api/compare` 400 error body is not consumed before `return` in the `resp.status >= 400` general branch

**File:** `src/dashboard/src/hooks/useCompareData.ts:45`

**Issue:** The generic `!resp.ok` error handler on line 45 only uses `resp.status` and `resp.statusText`, never reading the body:
```typescript
if (!cancelled) setError(`API error: ${resp.status} ${resp.statusText}`)
```
For non-400/401/403/429 HTTP error codes (e.g., 500 or 404), the response body (which may contain a useful `detail` from FastAPI's `HTTPException`) is discarded. The user sees "API error: 404" instead of "No scan found: '2026-05-14 11:51:54'". This is especially impactful here because a 404 from `/api/compare` means a session was not found, and the error detail contains the offending `scan_id`.

**Fix:**
```typescript
const body = await resp.json().catch(() => ({}))
const detail = (body as { detail?: string })?.detail
if (!cancelled) setError(detail ?? `API error: ${resp.status} ${resp.statusText}`)
```

---

## Info

### IN-01: Subscores tab shows `—` for Scan A and Scan B columns — no individual subscore data in API response

**File:** `src/dashboard/src/pages/compare.tsx:210–211`

**Issue:** The subscores table renders `—` for both "Scan A" and "Scan B" columns (hardcoded):
```tsx
<TableCell className="font-data">—</TableCell>
<TableCell className="font-data">—</TableCell>
```
The `CompareResponse` schema only returns `subscore_deltas`, not the individual subscore values for each scan. Users cannot determine whether, for example, `hygiene` delta of `-5` means A=80/B=85 or A=0/B=5. The delta alone is ambiguous. This is a UX gap — the data for per-scan subscores is computed in `compare_scans` (`sub_a`, `sub_b`) but not returned.

**Fix (API):** Add `subscore_a: SubscoreDelta` and `subscore_b: SubscoreDelta` to `CompareResponse` and populate them in `compare_scans`. Then the frontend can display actual values.

---

### IN-02: `_count_by_bucket` import is from `quirk.intelligence.trends` — private function used across module boundary

**File:** `quirk/dashboard/api/routes/scan.py:40`

**Issue:**
```python
from quirk.intelligence.trends import _count_by_bucket
```
`_count_by_bucket` has a leading underscore indicating it is module-private. Importing it into an unrelated module creates a fragile coupling: any internal refactor of `trends.py` will silently break `list_scans` without a failing import. This is also inconsistent with the project's pattern of using public APIs across module boundaries.

**Fix:** Expose `_count_by_bucket` as a public function (`count_by_bucket`) in `quirk/intelligence/trends.py`, or move it to a shared `quirk/intelligence/utils.py` module.

---

### IN-03: `FindingItem` missing `compliance` and `category` fields in TypeScript `api.ts`

**File:** `src/dashboard/src/types/api.ts:23–34`

**Issue:** The Python `FindingItem` schema (schemas.py lines 49–65) includes `compliance: List[Dict[str, Any]] = []` (Phase 49 D-02) and `category: Optional[str] = None` (Phase 45). Neither field appears in the TypeScript `FindingItem` interface. If any frontend code uses `FindingItem` for compliance display, it will receive `compliance` data from the API but TypeScript won't know it exists, suppressing the field silently at type-check time.

**Fix:**
```typescript
export interface FindingItem {
  // ... existing fields
  category?: string
  compliance?: Record<string, unknown>[]
}
```

---

_Reviewed: 2026-05-14T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
