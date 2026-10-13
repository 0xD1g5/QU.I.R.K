---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-INTELSCHEMA-*, plan 224-10
priority: medium
area: quirk/validate.py
status: pending
resolves_phase: null
---

# `python -m quirk.validate` reports a freshly written intelligence file as invalid

`_validate_intelligence` (`quirk/validate.py:99-102`) requires `intelligence.roadmap` to be a list:

```python
roadmap = intel.get("roadmap")
if not isinstance(roadmap, list):
    errors.append("intelligence.roadmap must be a list")
```

`write_reports()` (`quirk/reports/writer.py`, the `intelligence = {... "roadmap": roadmap_raw ...}` dict) writes the
object returned by `build_phased_roadmap()`: `{"roadmap_version", "item_count", "phase_counts", "items"}`. Reproduced
2026-10-12 by calling `write_reports()` into a temp directory (the fixture used by
`tests/test_confidence_formula_version_surfaces.py`) and running `python -m quirk.validate --output-dir <dir>`:
`- intelligence.roadmap must be a list`. So the validator rejects every intelligence file QUIRK itself produces.

Nothing in the test suite runs the validator against real writer output, which is why it has stayed red-in-practice.
`docs/intelligence-schema.md` used to call `quirk/validate.py` "the authoritative schema check"; it now documents the
mismatch instead.

- [ ] Decide which side is right. The writer's object shape is the documented one and the dashboard consumes it, so the
      validator should accept a dict with `items` (and check `roadmap_version`, `item_count`, `phase_counts`).
- [ ] Add a test that writes reports via `write_reports()` and asserts `validate_run` returns ok for the
      intelligence leg (the fixture needs `run_stats` too, or the validator's `run-stats-*.json` artifact check will
      also fire).
- [ ] Then remove the sentence about the validator's `roadmap` check from `docs/intelligence-schema.md` and re-verify those rows.

## Feasibility & Effort

**CONFIRMED** (reproduction above; `quirk/validate.py:99-102` and `quirk/intelligence/roadmap.py:474-479`). Effort **S**:
a few lines in the validator and one regression test. Unknown: whether anything external relies on the validator
rejecting dict roadmaps (nothing in `quirk/` or `tests/` imports `validate_run` besides `_latest_intelligence` users).
**No spike needed.**
