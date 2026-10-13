---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger part 224-13, docs/configuration.md CLI Flag Reference (--db-path / --resume-scan-id))
priority: medium
area: run_scan.py (checkpoint writes)
status: pending
resolves_phase: null
---

# A CLI scan without `--db-path` writes no resume checkpoints, silently

Every `write_scan_checkpoint` call is gated on `if args.db_path:` (`run_scan.py:2488`, `:2673`, `:2718`).
`args.db_path` is not defaulted from `cfg.output.db_path`, so a scan run without `--db-path` writes 0
checkpoints (fork probe: 0 vs 8 with the flag) and `--resume-scan-id` later has nothing to resume. No warning
is printed. docs/configuration.md now says resume needs `--db-path`.

- [ ] Default `args.db_path` to `cfg.output.db_path` (or warn when resume is impossible).

## Feasibility & Effort

- **Feasibility: CONFIRMED.**
- **Effort: S.**
- **Unknowns:** the `--db-path` silent no-op trap on an uninitialised file (init_db only initialises cfg.output.db_path) must be handled together.
- **Spike:** no.
