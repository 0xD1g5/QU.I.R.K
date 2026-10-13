---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md Connectors Block enable_authenticated_mode)
priority: medium
area: quirk/cli/schedule_cmd.py, quirk/cli/scheduler_cmd.py
status: pending
resolves_phase: null
---

# The scheduler's authenticated-mode reject checks a file recurring runs never load

`quirk schedule add` rejects a `--config` with `enable_authenticated_mode: true`
(`quirk/cli/schedule_cmd.py:113` `_config_has_authenticated_mode(args.config)`). But that `--config`
is only used as the DB path (`schedule_cmd.py:82-93`). Recurring runs load `quirk scheduler run
--scan-config` (`quirk/cli/scheduler_cmd.py:467,480,193-194`), which is never checked. The template
comment at `quirk/config_template.yaml:178` repeats the claim. docs/configuration.md now says which file is
checked.

- [ ] Apply the check (strip or refuse) in `_materialize_scan_config`, like the OT/ICS gate at
      `scheduler_cmd.py:216-228`.
- [ ] Fix the template comment.

## Feasibility & Effort

- **Feasibility: CONFIRMED** (the fork probe ran `scheduler run --scan-config` with an authenticated-mode
  file and nothing refused it).
- **Effort: S.**
- **Unknowns:** none beyond strip-vs-refuse.
- **Spike:** no.
