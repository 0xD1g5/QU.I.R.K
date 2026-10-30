---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-02, D-10); generated-doc source review in plan 224-11
priority: medium
area: quirk/errors.py, quirk/cli/doctor_cmd.py, docs/error-codes.md (generated)
status: pending
resolves_phase: null
owner: "999.128"
---

# Four error hints name a header, config blocks, a Python floor or a file that is not what the product uses

Found by checking every command, flag, header and config reference in the `fix=` strings of `quirk/errors.py` (the
source of the generated `docs/error-codes.md`) against the code. Wrong-PyPI-package pip hints are a separate, already
filed defect (`261012-doc224-install-hints-name-wrong-pypi-package.md`); the CMVP refresh hints are another
(`261012-doc224-error-hints-recommend-cmvp-refresh.md`). The rest:

1. **`DASHBOARD-001`** (`quirk/errors.py:85`, `docs/error-codes.md:42`): "Send the dashboard auth token in the
   `X-Quirk-Auth` header." Nothing else in the repo uses that header. The auth dependency accepts
   `Authorization: Bearer <token>` and an `X-API-Key` header (`quirk/dashboard/api/middleware/auth.py:43-57`), so a
   client following the hint is rejected with the same error.
2. **`INSTALL-005`** (`quirk/errors.py:53`, `docs/error-codes.md:77`): "Install Python 3.11 or newer". The project
   declares `requires-python = ">=3.10"` (`pyproject.toml:10`), but `quirk doctor` enforces 3.11
   (`quirk/cli/doctor_cmd.py:37`, `_PYTHON_MIN = (3, 11)`) and fails on a supported 3.10 interpreter with this hint.
   Either the floor or the check is wrong; the docs now say 3.10 (D-21).
3. **`JWT-001` and `SSH-001`** (`quirk/errors.py:301,306`, `docs/error-codes.md:88,105`): "Check `jwt_scanner` /
   `ssh_scanner` block in your config.yaml". `quirk/config.py` has no such blocks (`grep -c "jwt_scanner\|ssh_scanner"
   quirk/config.py` -> 0) and neither code is raised anywhere else in `quirk/` or `run_scan.py`. They are "reserved"
   entries whose hint describes configuration that does not exist.
4. **`INSTALL-009`** (`quirk/errors.py:73`): "see CLAUDE.md Staleness Review Cadence". `CLAUDE.md` is not tracked
   (`git ls-files CLAUDE.md` -> 0 lines) and is not shipped, so an operator cannot open it.

- [ ] Change the `DASHBOARD-001` hint to the header the server reads (`Authorization: Bearer <token>`).
- [ ] Align `_PYTHON_MIN` in `quirk/cli/doctor_cmd.py` and `INSTALL-005` with `requires-python` (3.10), or raise
      `requires-python` deliberately.
- [ ] Reword or delete the reserved `JWT-001` / `SSH-001` entries; point `INSTALL-009` at `docs/` or at the catalog
      module's own `source_url` instead of `CLAUDE.md`.
- [ ] Regenerate `docs/error-codes.md` (`tests/test_error_codes_freshness.py`) and update any test that pins the text.

## Feasibility & Effort

**CONFIRMED** for all four (file:line above, plus `grep -rn "X-Quirk-Auth" . --include=*.py --include=*.md` finding it
only in `errors.py` and the generated doc). Effort **S**: string edits and one constant, plus regeneration; the
`_PYTHON_MIN` decision touches `tests/` that exercise `doctor` on an older interpreter. **No spike needed.**
