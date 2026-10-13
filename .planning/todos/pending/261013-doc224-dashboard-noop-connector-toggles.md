---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger part 224-12, docs/configuration.md Per-surface connector coverage)
priority: medium
area: src/dashboard/src/components/ConnectorsPanel.tsx, quirk/dashboard/api/routes/jobs.py, run_scan.py
status: pending
resolves_phase: null
---

# Connectors panel offers toggles that do nothing on a dashboard scan

- `enable_nmap`: every dashboard job runs `run_scan --config ...` (`quirk/dashboard/api/routes/jobs.py:924-941`),
  and with `--config` `run_scan.py:2004-2005` overwrites `connectors.enable_nmap` from `--discovery`. Only the
  nmap checkbox matters.
- `enable_codesign`: nothing reads it; code signing runs only with `--inventory-code-signing`
  (`run_scan.py:1729`, `:3761`), which the job argv never adds.
- `enable_recurring_otics` matters only to the scheduler.

`validate_connectors_overlay` accepts all of them. docs/configuration.md now says the first two have no
effect on a dashboard scan.

- [ ] Hide or disable these toggles, or map `enable_nmap` to the nmap checkbox and `enable_codesign` to the flag.

## Feasibility & Effort

- **Feasibility: CONFIRMED** (source; fork probe of the overlay validator).
- **Effort: S.**
- **Unknowns:** whether CLI YAML users also expect `enable_nmap: true` to work (it is ignored there too).
- **Spike:** no.
