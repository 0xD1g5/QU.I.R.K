---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-ARCH-* (architecture.md sections 8 and 10), plan 224-10
priority: low
area: quirk/reports/writer.py
status: pending
resolves_phase: null
---

# `SCHEMA_VERSION = 2` in `quirk/reports/writer.py` is defined and never used

`quirk/reports/writer.py:298` defines `SCHEMA_VERSION = 2`. A grep for `SCHEMA_VERSION` across `quirk/`, `tests/` and
`run_scan.py` finds no reader of this constant (the other `SCHEMA_VERSION` names are separate constants in
`quirk/intelligence/schema.py` (`"1.0.0"`) and `EVIDENCE_SCHEMA_VERSION` in `evidence.py`). No report file embeds it.
`git log -S"SCHEMA_VERSION" -- quirk/reports/writer.py` shows two commits: the package rename and an unrelated
print-block replacement; it has never been bumped.

`docs/architecture.md` sections 8 and 10 claimed "SCHEMA_VERSION = 2 ... bumped only on incompatible structural changes.
Reports embed these so consumers can detect schema-incompatible changes without parsing the body" -- false on both
counts. The doc now says the constant is defined and not emitted.

- [ ] Decide: emit it (a `report_schema_version` key in `intelligence-<stamp>.json` and `findings-<stamp>.json`, with a
      documented bump rule), or delete the constant.
- [ ] Update `docs/architecture.md` sections 8 and 10 to match the decision.

## Feasibility & Effort

**CONFIRMED** (grep above, run 2026-10-12). Effort **S**. A consumer-visible key is a contract, so emitting it needs the
bump rule written down and a test pinning it. No spike needed.
