---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); found while verifying docs/installation.md "Verify properly"
priority: low
area: scripts/validate-fresh-install.sh
status: completed
resolves_phase: null
owner: "999.129"
---

# `scripts/validate-fresh-install.sh` rejects Python 3.10 although the project floor is 3.10

`pyproject.toml:10` declares `requires-python = ">=3.10"`, and `docs/installation.md` tells users the floor is
3.10 (CI tests 3.11). `scripts/validate-fresh-install.sh:181-186` fails check 1 for any `python3` below 3.11
("python3 3.x is below the required 3.11"), so the script that exists to validate the documented install
reports a failure on a supported interpreter. Observed with `scripts/validate-fresh-install.sh --self-check`
on a Python 3.9 host (that case is correctly below both floors); a 3.10 host was not available here.

- [x] Decide whether the script's floor should be 3.10 (matching `pyproject.toml`) or the docs should say 3.11.
- [x] Align the script comment at `scripts/validate-fresh-install.sh:167` ("glibc >= 2.17 is docs/installation.md's
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

## Resolution (2026-10-30, Phase 235 plan 16)

Closed by Phase 235 and shipped in v5.28.0. The floor decision was **3.10** (`requires-python = ">=3.10,<3.15"`).

- `9a882f31` (build(235-02)) declared the supported range 3.10-3.14 and moved the validator's floor to match:
  `scripts/validate-fresh-install.sh` now passes any `python3` in 3.10-3.14 (`:183-188`) and its glibc comment no longer
  cites a figure the installation guide does not state.
- `f0d2c465` (feat(235-02)) moved `quirk/cli/doctor_cmd.py` `_PYTHON_MIN` to `(3, 10)`, the Addendum item; `QRK-INSTALL-005` now reads
  "Install Python 3.10 to 3.14".
- 3.10 leg evidence on the published artifact: `.planning/phases/235-release-launch-gate/235-evidence/smoke-pypi/linux-3.10.txt`
  (python:3.10-slim, quirk-scanner[all]==5.28.0 from PyPI, doctor exit 0, scan, HTML, PDF, serve, `RESULT: PASS`, 2026-10-30).
  D-08b (raise the floor to 3.11) was therefore not triggered.
- Honest limit: the 3.10 leg ran the installed package, not `validate-fresh-install.sh` itself on a 3.10 host, so the
  Unknown in the Feasibility section (whether 3.10 passes every later check of that script) stays unmeasured. It is a
  script-only check and is not what this todo's defect was.
