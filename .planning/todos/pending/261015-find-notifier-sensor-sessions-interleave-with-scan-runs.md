---
type: todo
created: 2026-10-15
source: Phase 229 (Finding & State Correctness) D-16 / Pitfall 7
priority: low
area: quirk/intelligence/trends.py (list_session_timestamps), quirk/cli/sensor_cmd.py
status: pending
resolves_phase: null
owner: "999.135"
---

# Notifier treats a sensor push between two scans as the previous session

**Owner:** 999.135 (Notifications and ticketing)

Rows with a NULL `scan_run_id` (sensor pushes) remain millisecond legacy sessions in `list_session_timestamps`, and sensor `scanned_at` is whole-second per stage (`quirk/cli/sensor_cmd.py` around lines 364-370). A sensor push that lands between two scheduled scans therefore becomes the "previous" session for drift notifications. The `/api/trends` grouping behaves the same way.

- [ ] Decide whether sensor pushes should form their own session stream.

## Feasibility & Effort

- **LIKELY**. Effort **S-M**. Unknown: whether the Trends page should change in step. Spike: no.
