---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger part 224-13, docs/configuration.md CLI Flag Reference)
priority: low
area: run_scan.py (--targets-file help), quirk/util/targets.py
status: pending
resolves_phase: null
---

# `--targets-file` help says it replaces config targets entirely; include_ips survive

The help text says "Replaces config targets entirely (does NOT merge)" (`run_scan.py:1526`), but
`apply_targets_file_override` replaces only `fqdns` and `cidrs` (`quirk/util/targets.py:314-316`);
`targets.include_ips` from the config is still scanned (fork probe). docs/configuration.md now states this.

- [ ] Decide: also clear `include_ips`, or reword the help text.

## Feasibility & Effort

- **Feasibility: CONFIRMED.**
- **Effort: S.**
- **Unknowns:** whether anyone relies on include_ips surviving.
- **Spike:** no.
