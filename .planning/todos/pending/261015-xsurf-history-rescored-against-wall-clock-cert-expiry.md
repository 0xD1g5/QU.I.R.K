---
type: todo
created: 2026-10-15
source: Phase 228 code review (.planning/phases/228-cross-surface-score-parity/228-REVIEW.md), WR-04
priority: medium
area: quirk/dashboard/api/routes/scan.py (findings_for_endpoint now=), quirk/engine/findings_evaluator.py:631, quirk/intelligence/evidence.py:107-120
status: pending
resolves_phase: null
owner: "999.134"
---

# Timeline and trend history re-score past sessions when a certificate expires after the scan

Phase 228 made timeline points and trend `previous_score` derive findings. Both finding generators measure cert expiry against `datetime.now()`, while `build_evidence_summary` uses the session's `scanned_at`. A session that was healthy when scanned gets a retroactive CRITICAL ceiling (score <= 34) on every historical point once its cert expires, and within one summary `certificate_observations.expired_count` and the CRITICAL finding count can contradict each other. Test fixtures work around this ("Pitfall 7"). Fix: pass a reference time into finding derivation and use `scanned_at` for historical points; add a test that a cert expiring after `scanned_at` leaves the timeline score unchanged. Overlaps the existing 999.134 timeline todo's area.

Deferred by the operator at Phase 228 close (2026-10-15): CR-01, WR-07 fixed in-phase (dab89ffc, 3b1d286c);
this item was triaged out of Phase 228's scope. Full evidence and the suggested fix are in the review section named
in `source`.
