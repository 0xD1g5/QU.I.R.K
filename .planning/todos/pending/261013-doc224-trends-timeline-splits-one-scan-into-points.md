---
type: todo
created: 2026-10-13
source: Phase 224 GC2 re-audit (ledger rows DCL-INTELSCHEMA-0037, -0075, -0144; docs/intelligence-schema.md Trends Timeline)
priority: medium
area: quirk/dashboard/api/routes/trends.py (_list_session_timestamps_n, get_trends_timeline)
status: pending
resolves_phase: null
owner: "999.134"
---

# `/api/trends/timeline` shows one scan as several points

RVW-003 fixed `GET /api/trends` so that a session is one `scan_run_id` (`_list_session_timestamps`,
`quirk/dashboard/api/routes/trends.py:43`, docstring "a session is one `scan_run_id`, represented by its *earliest*
endpoint timestamp"). The timeline lister was not changed: `_list_session_timestamps_n`
(`quirk/dashboard/api/routes/trends.py:163`) still groups by `func.strftime("%Y-%m-%d %H:%M:%f", scanned_at)` and
`group_by("ts_usec")`. Each point is then resolved by `_fetch_session_endpoints` (`quirk/intelligence/trends.py:101`),
which maps the timestamp to its `scan_run_id` and returns the whole scan. So a scan whose stages stamp rows at
different milliseconds becomes several timeline points that all carry the same whole-scan score and counts.

Observed (TestClient, in-memory DB, isolated HOME): scan R1 with rows at 09:00:00 and 09:00:03, scan R2 with rows
at 10:30:00.000 and 10:30:00.200. `GET /api/trends` reports 2 sessions (correct); `GET /api/trends/timeline` returns
**4** points (10:30:00.200, 10:30:00, 09:00:03, 09:00:00). The Trends page fetches `/api/trends/timeline?n=30`
(`src/dashboard/src/hooks/useTimelineData.ts:23`), so the sparkline repeats each scan and `n=30` covers fewer scans
than it says.

`docs/intelligence-schema.md` now documents the real behaviour (millisecond points, not scans); revert that caveat
if this is fixed.

- [ ] Make `_list_session_timestamps_n` key by `scan_run_id` with the legacy millisecond fallback, exactly as
      `_list_session_timestamps` does (or share one helper with a limit parameter).
- [ ] Test: one scan with rows at two different milliseconds yields one timeline point; two scans yield two.
- [ ] Update the Trends Timeline section of `docs/intelligence-schema.md`.

## Feasibility & Effort

**CONFIRMED** defect: both listers read at the cited lines; the 4-point observation was produced by a seeded
TestClient run (re-run before starting). Effort **S**: the correct grouping already exists in
`_list_session_timestamps` (`trends.py:58-80`, Python-side `key = row_run_id or stamp_utc_iso(...)`); the change is
reusing it with a limit of `n` instead of 10. Unknowns: whether any test or the frontend relies on per-stage points
(`tests/test_dashboard_trends.py::test_trends_timeline_n_param` seeds rows without `scan_run_id`, so it should keep
passing on the legacy path) and the cost of loading all `(scanned_at, scan_run_id)` pairs for large databases, which
`_list_session_timestamps` already pays. No spike needed.

## Second symptom (found 2026-10-15, Phase 228 plan 07)

A scan whose `scanned_at` carries **sub-millisecond** precision gets **no** timeline point at all. The
lister truncates to milliseconds (`func.strftime("%Y-%m-%d %H:%M:%f", ...)` in
`_list_session_timestamps_n`), and `_fetch_session_endpoints` resolves the point by equality
(`quirk/intelligence/trends.py:124` `CryptoEndpoint.scanned_at == target_ts`), so the truncated stamp
matches no row. Phase 228's XSURF-07 fixture (`tests/test_cross_surface_parity.py`,
`test_xsurf07_trend_merge_segment_scores_match_headline`) uses a whole-second stamp to avoid it. The fix
above (key by `scan_run_id`, millisecond fallback only for legacy rows) closes both symptoms.

- [ ] Test: a scan whose rows carry microsecond `scanned_at` yields exactly one timeline point.
