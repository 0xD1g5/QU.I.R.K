---
phase: 52-compliance-uplift-health-check
plan: "04"
subsystem: cli
tags: [doctor, health-check, cli, rich, DOCS-05]
dependency_graph:
  requires: [52-01]
  provides: [quirk-doctor-subcommand]
  affects: [run_scan.py, quirk/cli/doctor_cmd.py]
tech_stack:
  added: []
  patterns: [rich-table, subcommand-intercept, tdd-green]
key_files:
  created:
    - quirk/cli/doctor_cmd.py
  modified:
    - run_scan.py
decisions:
  - "Informational categories (QRAMM, network, dashboard) return True from check functions so failed flag is never set — matches D-14 contract"
  - "Config absent treated as informational [!], config malformed treated as fatal [✗] — allows operator flexibility on first run"
  - "Doctor intercept inserted after compliance block and before main argparse — mirrors existing subcommand pattern"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-05"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 52 Plan 04: quirk doctor CLI Health Check Summary

**One-liner:** Rich 8-row pre-engagement health table via `quirk doctor` with exit-code machine signal (0=ready, 1=blocked).

## What Was Built

### Task 1: quirk/cli/doctor_cmd.py — 8-category run_doctor()

Created `quirk/cli/doctor_cmd.py` (168 lines) implementing Phase 52 DOCS-05. The `run_doctor()` function:

- Category 1 (non-info): Python version >= 3.11 gate
- Category 2 (non-info): shutil.which checks for nmap, syft, semgrep — 3 table rows
- Category 3 (non-info): COMPLIANCE_MAP freshness against STALENESS_THRESHOLD_DAYS
- Category 4 (info only): importlib probe for `quirk.qramm` — never sets failed
- Category 5 (non-info): sqlite3.connect with 2s timeout + SELECT 1
- Category 6 (non-info/info): config.yaml absent = informational [!]; malformed = fatal [✗]
- Category 7 (info only): TCP probe to 8.8.8.8:53 — never sets failed
- Category 8 (info only): TCP probe to 127.0.0.1:8512 — never sets failed

All 3 Plan 01 stub tests turned GREEN:
- `test_doctor_exits_0_all_pass` — exit 0 when all non-info checks pass
- `test_doctor_exits_1_missing_binary` — exit 1 when binary missing
- `test_informational_checks_never_exit_1` — network/dashboard OSError never triggers exit 1

Commit: `908e950`

### Task 2: run_scan.py — doctor subcommand intercept block

Inserted 4-line intercept block in `run_scan.py:main()` after the compliance block (lines 246-250):

```python
# --- doctor subcommand: intercept before scan argparse (Phase 52 DOCS-05 / D-10) ---
if len(_sys.argv) > 1 and _sys.argv[1] == "doctor":
    from quirk.cli.doctor_cmd import run_doctor
    run_doctor()
    return
```

End-to-end smoke test: `python run_scan.py doctor` renders Rich health table, exits 0 or 1 (semgrep not in PATH on dev machine = exit 1, correct). All other subcommands (init, serve, compliance) unaffected.

Commit: `a0e8668`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all 8 health categories are wired to real system probes.

## Threat Flags

No new threat surface beyond what the plan's threat model documents (T-52-04-01 through T-52-04-05). The `quirk doctor` command is strictly operator-local with no remote input attack surface.

## Self-Check

## Self-Check: PASSED

| Item | Status |
|------|--------|
| quirk/cli/doctor_cmd.py | FOUND |
| 52-04-SUMMARY.md | FOUND |
| commit 908e950 (feat: doctor_cmd.py) | FOUND |
| commit a0e8668 (feat: run_scan.py intercept) | FOUND |
| 3 doctor tests GREEN | PASSED |
