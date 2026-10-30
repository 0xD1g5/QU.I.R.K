---
type: todo
created: 2026-10-15
source: Phase 228 code review (.planning/phases/228-cross-surface-score-parity/228-REVIEW.md), WR-05
priority: medium
area: quirk/dashboard/api/routes/scan.py:425-436 (derive_dashboard_finding_items), :446-472 (finding_by_id_and_title)
status: pending
resolves_phase: null
owner: "999.137"
---

# Email, broker and code-signing findings on `/api/scan/latest` have no id, segment, sensor or compliance

Phase 228 added these findings to the user-visible `findings` list. The adapter maps no `id`, `sensor_id`, `segment`, `category` or `compliance`, so their storyline/detail lookup (`finding_by_id_and_title` walks only `findings_for_endpoint`) can never resolve, filtered views show `segment: null`, and the report's compliance attachment is dropped. `tests/test_dashboard_finding_segment_field.py` checks provenance for TLS rows only. Fix: map each finding back to its endpoint by (host, port), or keep these scoring-only.

Deferred by the operator at Phase 228 close (2026-10-15): CR-01, WR-07 fixed in-phase (dab89ffc, 3b1d286c);
this item was triaged out of Phase 228's scope. Full evidence and the suggested fix are in the review section named
in `source`.
