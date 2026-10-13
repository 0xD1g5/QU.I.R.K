---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); found while verifying docs/installation.md "Verify properly"
priority: low
area: scripts/validate-fresh-install.sh
status: pending
resolves_phase: null
---

# `scripts/validate-fresh-install.sh` rejects Python 3.10 although the project floor is 3.10

`pyproject.toml:10` declares `requires-python = ">=3.10"`, and `docs/installation.md` tells users the floor is
3.10 (CI tests 3.11). `scripts/validate-fresh-install.sh:181-186` fails check 1 for any `python3` below 3.11
("python3 3.x is below the required 3.11"), so the script that exists to validate the documented install
reports a failure on a supported interpreter. Observed with `scripts/validate-fresh-install.sh --self-check`
on a Python 3.9 host (that case is correctly below both floors); a 3.10 host was not available here.

- [ ] Decide whether the script's floor should be 3.10 (matching `pyproject.toml`) or the docs should say 3.11.
- [ ] Align the script comment at `scripts/validate-fresh-install.sh:167` ("glibc >= 2.17 is docs/installation.md's
      own stated Playwright floor"), which cites a figure the installation guide no longer states.

## Feasibility & Effort

**LIKELY** (the thresholds are visible at `scripts/validate-fresh-install.sh:183-186` against
`pyproject.toml:10`; behaviour on a real 3.10 host was not run). Effort **S**. Unknown: whether 3.10 passes
every later check of the script (the Playwright and PDF checks). **Spike**: run the script with `--yes` on a
throwaway Ubuntu 22.04 VM (Python 3.10) before changing the threshold.

## Addendum (Phase 224, plan 14)

`quirk doctor` has the same disagreement: `quirk/cli/doctor_cmd.py` sets `_PYTHON_MIN = (3, 11)` and fails check 1 with
`QRK-INSTALL-005` on a 3.10 interpreter, while `pyproject.toml` declares `requires-python = ">=3.10"`. Align the doctor
floor and the install script together with whichever floor is chosen.
