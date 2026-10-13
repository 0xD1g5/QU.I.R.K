---
type: todo
created: 2026-10-12
source: GUI-first repositioning (operator, 2026-10-12); HORIZON 999.121
priority: medium
area: quirk/dashboard/api/routes/, src/dashboard/src/pages/, run_scan.py subcommands
status: pending
resolves_phase: null
---

# GUI-first: triage the 11 CLI-only subcommands for dashboard parity

**Owner phase:** unassigned (HORIZON 999.121, sub-item 2)

On 2026-10-12, these `run_scan.py` subcommands had no matching dashboard API route: **token,
compliance, cve, ticket, doctor, init, db, export, errors, analyze-token, console**. (serve, sensor,
schedule/scheduler and qramm do have GUI surfaces.) Re-enumerate at run time. Don't trust this list.

- [ ] Classify each one: belongs-in-GUI / CLI-only by design (operator plumbing such as db, errors,
      console, init) / partially covered elsewhere. Write a reason for each.
- [ ] Include the remote/team bind: a non-loopback `quirk serve` refuses to start until the operator
      runs `export QUIRK_API_TOKEN=...` in a shell (`quirk/dashboard/server.py:116-134`). Decide
      whether token issue/rotation gets a GUI (the `token` subcommand already mints tokens).
- [ ] Likely first candidates: compliance status, CVE correlation, doctor (health check), ticket export.
- [ ] Each port becomes its own phase-sized item. This todo produces the triage, not the code.

## Feasibility & Effort

**CONFIRMED** gap (11 argv-dispatched subcommands, no matching dashboard route on 2026-10-12). Effort **M-L**, mostly triage. Several are CLI-only by design. No spike. Full analysis: `.planning/backlog/999.121-gui-first-transition/IDEA.md`.
