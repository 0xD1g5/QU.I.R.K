---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger part 224-13, docs/configuration.md Notifications)
priority: high
area: quirk/notify/dispatcher.py (_find_two_sessions)
status: completed
completed: 2026-10-15
resolves_phase: 229
owner: FIND-12
---

# Drift notifications compare a scan with itself

`_find_two_sessions` (`quirk/notify/dispatcher.py:108-128`) takes the two newest distinct
millisecond `scanned_at` values from `crypto_endpoints`, not the two newest scan runs. A scan whose
endpoints carry more than one timestamp is compared with itself, so the trigger does not fire.

Observed (GC3 fork probe, temp DB): run A with one LOW endpoint, run B a day later with a new HIGH
endpoint plus another endpoint a few ms apart -> `should_notify False`. The dashboard Trends grouping
(`quirk/dashboard/api/routes/trends.py:43 _list_session_timestamps`, scan_run_id-aware) on the same
data gives True. docs/configuration.md Notifications now carries a "Known limitation" note.

- [x] Reuse `_list_session_timestamps` (or move it to quirk/intelligence/trends.py) and add a
      regression test built on the probe.

## Feasibility & Effort

- **Feasibility: CONFIRMED** (probe; the query is at `quirk/notify/dispatcher.py:116-126`).
- **Effort: S.**
- **Unknowns:** the old-data case where `scan_run_id` is NULL (the Trends helper already handles it).
- **Spike:** no.

## Resolution (Phase 229, 2026-10-15)

Closed by FIND-12. Fix commit `7729d6ba` (229-05, D-08/D-10): `_find_two_sessions` now keys sessions by `scan_run_id` (legacy NULL-run rows fall back to the millisecond stamp), so the two newest distinct scan runs are compared. Docs: `35aba8f9` (notifications and trends grouping, D-16/D-18/D-25), which also replaces the "Known limitation" note in `docs/configuration.md`.

Proving nodes (UAT-229-06): `tests/test_notify_session_identity.py::test_probe_two_runs_microsecond_timestamps_fires`, `::test_three_runs_compare_two_newest_distinct`, `::test_legacy_null_run_rows_in_distinct_ms_stay_distinct`, `::test_import_hygiene_no_fastapi_or_pydantic`.

The session helper is now the shared `list_session_timestamps` in `quirk/intelligence/trends.py`, used by both the dashboard Trends route and the notifier, with a regression test built on the probe. A separate sensor-session interleave limit is filed under HORIZON 999.135.
