---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); found while verifying docs/installation.md (`quirk doctor`)
priority: low
area: quirk/cli/doctor_cmd.py
status: pending
resolves_phase: null
---

# `quirk doctor` tells users to run `quirk dashboard up`, a command that does not exist

When the dashboard is not running, `quirk doctor` prints
"Start the dashboard with `quirk dashboard up` and retry." (`quirk/cli/doctor_cmd.py:201` and `:207`).
`quirk dashboard up` is not a subcommand: running it fails with `quirk: error: unrecognized arguments: dashboard up`.
The real command is `quirk serve` (default `127.0.0.1:8512`).

- [ ] Change both remediation strings to `quirk serve`.
- [ ] Check `tests/test_doctor_cmd.py` / `tests/test_doctor_actionable.py` for a pinned string.

## Feasibility & Effort

**CONFIRMED** (reproduced: `quirk dashboard up` -> "unrecognized arguments: dashboard up";
`grep -n "quirk dashboard up" quirk/cli/doctor_cmd.py` -> lines 201, 207). Effort **S** (two strings plus a
possible test update). No unknowns. **No spike needed.**
