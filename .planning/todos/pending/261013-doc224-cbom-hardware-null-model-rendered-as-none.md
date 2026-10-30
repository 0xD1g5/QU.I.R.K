---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §10.1 DEVICE component naming)
priority: low
area: quirk/cbom/builder.py (Pass 4 hardware)
status: pending
resolves_phase: null
owner: "999.130"
---

# CBOM names an unidentified device "Unknown None": str(None) for a missing model

`quirk/cbom/builder.py:1100` and `:1200` use `str(dev.get("model", "Unknown"))`. The writers always set the key,
with value `None` when no model was recorded (`quirk/reports/writer.py:717`, `quirk/merge/scan.py:265`), so the
default never applies and the output is the string `None`: the DEVICE name becomes `Unknown None` and
`quirk:hw-model` is `None`. The `"Unknown Device at {host}:{port}"` fallback (`:1202`) only fires when model is the
literal "Unknown", which real unidentified devices do not produce; the test fixture uses `model="Unknown"`.

When fixed, update docs/report-interpretation.md §10.1 DEVICE parent component paragraph.

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `builder.py:1100`, `:1200`, `:1202`; `writer.py:717`; `merge/scan.py:265`.
- Fix: `dev.get("model") or "Unknown"`; add a fixture with `model=None`.
