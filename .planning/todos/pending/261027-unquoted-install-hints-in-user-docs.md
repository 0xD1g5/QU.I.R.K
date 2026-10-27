---
type: todo
created: 2026-10-27
source: Phase 232 (261015 residue)
priority: P3
area: docs/operators-guide.md, docs/configuration.md, docs/sample-config.yaml, tests/test_install_hint_package_name.py
status: pending
owner: 999.123
---

# Unquoted `quirk-scanner[extra]` install hints in user docs

**Owner phase:** 999.123 (reference docs generated from source; the hint text in these guides is the same
"what" that backlog item wants generated rather than hand-written)

Phase 232 (POLISH-02, commit `01200b71`) quoted every install hint in the four roots the guard scans:
`quirk/`, `run_scan.py`, `scripts/` and `src/dashboard/src/`. The user docs are outside that scan set
(D-05), and they still carry the unquoted form. Pasting `pip install quirk-scanner[hw]` into zsh fails with
"no matches found", because `[...]` is a glob.

Measured on 2026-10-27 with the guard's own `scan_lines()` rule from
`tests/test_install_hint_package_name.py`: **53 unquoted right-name occurrences**.

| File | Count |
|------|-------|
| `docs/operators-guide.md` | 35 |
| `docs/configuration.md` | 17 |
| `docs/sample-config.yaml` | 1 |

None uses the wrong distribution name `quirk[`. Re-derive the list at fix time; these counts are a
snapshot, not a target.

Also record here (same class, hint text that never reaches the user as written):
`quirk/dashboard/api/connector_availability.py:96-100` says the hw connectors carry "the reason text naming
`'quirk-scanner[hw]'` directly", but the reason string is built from `"{module}.{flag} unavailable"`, so no
install hint reaches the reason. Either correct the docstring or make the reason name the quoted extra.

## Feasibility & Effort

- **Feasibility:** CONFIRMED. The fix is the same mechanical quoting 232-02 applied, and the detector
  already exists; extending `ROOTS` (or adding a docs leg) to `docs/` makes the guard police it.
- **Effort:** S for the quoting. Extending the guard to `docs/` is S-M, because doc-claim ledger anchors may
  quote hint lines verbatim (memory: doc edits break ledger anchors), so `tests/test_doc_claim_ledger_gate.py`
  must be run and any affected rows re-anchored in the same commit, and the master guide regenerated
  (both guides are master-guide sources).
- **Unknowns:** how many ledger rows anchor on these lines. No spike needed; measure at fix time.
