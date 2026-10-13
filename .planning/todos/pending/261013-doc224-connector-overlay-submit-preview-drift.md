---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md Connector detail fields settable from the dashboard)
priority: low
area: quirk/dashboard/api/schemas.py, quirk/dashboard/api/routes/config.py
status: pending
resolves_phase: null
---

# Connector overlay: submit and preview disagree on whole-number floats, and the submit 422 echoes input

The submit field type `Dict[str, Union[bool, str, int, List[str], List[dict]]]`
(`quirk/dashboard/api/schemas.py:1158-1159`) coerces `10.0` to `10` before `validate_connectors_overlay`
runs, so `smime_timeout: 10.0` is accepted on submit (201) but rejected by the preview (422,
`quirk/dashboard/api/routes/config.py:182`). The submit 422 body is FastAPI's error list and includes
`input`, which echoes the submitted overlay. The preview's 422 `detail` is one string. The lockstep test
(`tests/test_connector_detail_overlay_lockstep.py`) has no float case. docs/configuration.md now states
both differences.

- [ ] Make both paths parse the overlay the same way (validate the raw JSON in both).
- [ ] Decide whether the submit 422 should drop `input` (T-197-03 intent: never echo the value).

## Feasibility & Effort

- **Feasibility: CONFIRMED** (fork probe: submit 201, preview 422 for the same payload).
- **Effort: S.**
- **Unknowns:** whether any client relies on the FastAPI error-list shape.
- **Spike:** no.
