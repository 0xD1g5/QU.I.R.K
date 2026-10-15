---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS fork B2; ledger rows DCL-OPS-B-0156..0179 (docs/operators-guide.md §8.9 Automatic Merge)
priority: medium
area: tests/test_auto_merge_trigger.py
status: pending
resolves_phase: null
owner: "999.134"
---

# Auto-merge acceptance tests are quarantined xfail; the fix is a fixture rename and all 9 pass

`tests/test_auto_merge_trigger.py` holds the only end-to-end tests of auto-merge (push -> trigger -> background
`run_auto_merge` -> `MergeRun` / `IntegrationDelivery`). Eight of its nine tests carry
`@pytest.mark.xfail(reason="TRIAGE-149: outdated-fixture ...", strict=False)` (lines 210, 248, 275, 310, 363, 408, 462,
514): their fixture sensor ids (`"sensor-a"`, `"sensor-b"`, `"sensor-ghost"`, `"test-sensor-01"`) fail the push route's
UUID-shape guard with HTTP 400 before any auto-merge logic runs. So today nothing in CI exercises the documented
auto-merge behaviour: `pytest -q tests/test_auto_merge_trigger.py` -> `1 passed, 8 xfailed`.

Probe (gc2-OPS B2): replacing those four ids with valid UUIDs and deleting the xfail markers, nothing else changed
(copy at `.planning/phases/224-doc-claim-ledger-verification/work/probes/gc2-ops-b2-automerge-uuid-probe.py`)
-> `9 passed`. The product behaviour is intact; only the fixtures are stale.

- [ ] Apply the id rename in `tests/test_auto_merge_trigger.py`, remove the eight xfail markers, and drop the eight
      entries from `tests/skip_registry.py` and `docs/test-triage-149.md` rows 103-110.
- [ ] Note `test_cadence_window_triggers` asserts the literal `"sensor-b"` in `missing_sensors` (around line 568);
      rename that literal with the fixture.

## Feasibility & Effort

- **CONFIRMED**: root cause read in `docs/test-triage-149.md:103` and the UUID guard in
  `quirk/dashboard/api/routes/sensor.py` (`_UUID_RE` check before ingest); fix proven by the 9-passed probe above.
- Effort **S** (one file of sed-style renames plus registry/triage cleanup). No unknowns, no spike.
