---
type: todo
created: 2026-10-12
source: GUI-first repositioning (operator, 2026-10-12); HORIZON 999.121
priority: medium
area: run_scan.py (no-args dispatch), docs/getting-started.md
status: pending
resolves_phase: null
---

# GUI-first: bare `quirk` launches the CLI wizard, not the dashboard

**Owner phase:** unassigned (HORIZON 999.121, sub-item 1)

In a dashboard-first product, a new user who types `quirk` should land in the dashboard. Today bare
`quirk` (no `--config`) starts the interactive CLI wizard (`run_scan.py`, wizard path near `:1840`).

- [ ] Decide the default: bare `quirk` on a TTY → `quirk serve`? Keep the wizard behind an explicit
      flag/subcommand. This changes CLI behaviour, so record the compatibility call.
- [ ] Enumerate the tests/docs that pin the wizard default before changing it (grep, don't guess).
- [ ] Keep non-TTY/scripted invocations unchanged.

## Feasibility & Effort

**CONFIRMED** gap (wizard path near `run_scan.py:1840`). Effort **S-M**. Unknown: how many tests/docs pin the wizard default. No spike, it's a compatibility decision. Full analysis: `.planning/backlog/999.121-gui-first-transition/IDEA.md`.
