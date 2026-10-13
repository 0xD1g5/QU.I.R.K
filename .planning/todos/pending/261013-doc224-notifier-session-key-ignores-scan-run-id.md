---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger part 224-13, docs/configuration.md Notifications)
priority: high
area: quirk/notify/dispatcher.py (_find_two_sessions)
status: pending
resolves_phase: null
---

# Drift notifications compare a scan with itself

`_find_two_sessions` (`quirk/notify/dispatcher.py:108-128`) takes the two newest distinct
millisecond `scanned_at` values from `crypto_endpoints`, not the two newest scan runs. A scan whose
endpoints carry more than one timestamp is compared with itself, so the trigger does not fire.

Observed (GC3 fork probe, temp DB): run A with one LOW endpoint, run B a day later with a new HIGH
endpoint plus another endpoint a few ms apart -> `should_notify False`. The dashboard Trends grouping
(`quirk/dashboard/api/routes/trends.py:43 _list_session_timestamps`, scan_run_id-aware) on the same
data gives True. docs/configuration.md Notifications now carries a "Known limitation" note.

- [ ] Reuse `_list_session_timestamps` (or move it to quirk/intelligence/trends.py) and add a
      regression test built on the probe.

## Feasibility & Effort

- **Feasibility: CONFIRMED** (probe; the query is at `quirk/notify/dispatcher.py:116-126`).
- **Effort: S.**
- **Unknowns:** the old-data case where `scan_run_id` is NULL (the Trends helper already handles it).
- **Spike:** no.
