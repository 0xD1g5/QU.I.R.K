---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS (fork C1); docs/operators-guide.md §8 sensor enroll paragraph
priority: low
area: quirk/cli/sensor_cmd.py (_cmd_enroll)
status: pending
resolves_phase: null
owner: "999.134"
---

# `quirk sensor enroll` prints an "Enrollment token (shown once — save it now)" that nothing uses

`_cmd_enroll` generates `raw_token = secrets.token_urlsafe(32)` (`quirk/cli/sensor_cmd.py:266`), hashes it into an
unused local (`:268`, `# noqa: F841`, comment "console-side storage is Phase 109"), never writes it anywhere
(`sensor_cfg` at `:277-286` omits it) and prints it with a warning that it will not be shown again (`:292-293`).
The push credential is the per-sensor token from `quirk console enroll`, stored as `console_api_token`. An operator
following the on-screen instruction can easily save the wrong value. The operators-guide now tells readers to ignore
it, which is a documentation workaround for leftover Phase 108 scaffolding.

- [ ] Remove the token print (and the dead hash), or replace it with a pointer to `quirk console enroll`.
- [ ] Update the operators-guide paragraph that says to ignore it.

## Feasibility & Effort

- **CONFIRMED** by reading `quirk/cli/sensor_cmd.py:265-295`. **LIKELY** effort **S** (delete a few lines, adjust any
  test that asserts the print; grep `Enrollment token` under `tests/`). No unknowns beyond that grep. No spike.
