---
created: 2026-10-15
source: Phase 226 code review (226-REVIEW.md WR-01..03), operator chose "file as follow-up"
priority: P3
resolves_phase: 232
status: completed
completed: 2026-10-27
owner: POLISH-02
---

# Unquoted `quirk-scanner[extra]` install hints and narrow guard scope

Phase 226 renamed every `pip install quirk[<extra>]` hint to the right
distribution, `quirk-scanner`. The code review found three follow-ups that ship
in 5.27.0:

1. **WR-01: five hints are unquoted.** `install quirk-scanner[hw]` and
   `pip install quirk-scanner[docx]` fail under zsh with "no matches found"
   because `[...]` is a glob. Use the quoted form plan 226-04 standardized
   (`pip install 'quirk-scanner[<extra>]'`). Sites as of 265ea2e8:
   - `quirk/reports/docx_renderer.py:360`
   - `quirk/scanner/modbus_scanner.py:151`
   - `quirk/scanner/bacnet_scanner.py:187`
   - `quirk/scanner/snmp_scanner.py:653`
   - `run_scan.py:3025`
2. **WR-02: the guard is narrower than its docstring.**
   `tests/test_install_hint_package_name.py` scans only `quirk/` and
   `run_scan.py`, and only rejects the bare `quirk[` name. Extend it to reject
   an unquoted `quirk-scanner[` too, and to cover `scripts/` and
   `src/dashboard/src`. Prove it non-vacuous by mutation.
3. **WR-03: `tomllib` needs Python 3.11.** The new tag-derivation tests
   (`tests/test_readme_brand_logo.py`, `tests/test_readme_hero.py`) import
   `tomllib`, while `requires-python = ">=3.10"`. CI runs 3.11, so this is
   invisible there. Either fall back to `tomli` or raise the floor.

Re-derive the site list at run time. The five sites above are a hypothesis,
not a target.

## Resolution (Phase 232, 2026-10-27)

- **WR-01, the unquoted hints.** Re-derived at run time instead of trusting the five sites above. On the
  git-tracked set at `9e58bdb1`, the widened guard found **24 unquoted occurrences on 23 lines in 9 files**
  across 59 hint sites, not five. That count includes **9 wrong-name `quirk[...]` hints in the shipped
  `quirk/config_template.yaml`**, which the old guard could not see because it skipped YAML. Of 23 printed
  literals, 5 were not full pip commands: the five sites listed above, with `run_scan.py:3025` now at
  `:3102-3103`. Every site is now `pip install 'quirk-scanner[<extra>]'` when printed, and the bare quoted
  `'quirk-scanner[<extra>]'` in comments, docstrings, `help=` text and YAML comments. Fix commit `01200b71`.
- **WR-02, the guard scope.** `tests/test_install_hint_package_name.py` now enumerates the git-tracked
  files of four roots, `quirk/`, `run_scan.py`, `scripts/` and `src/dashboard/src/`, with `git ls-files`
  rather than a filesystem glob. It rejects every unquoted form, `quirk-scanner[` as well as the wrong
  name `quirk[`, and an `ast` pass requires every printed literal to be a full pip command. Floors keep it
  non-vacuous: `FILE_FLOOR=400` against 459 measured, `SITE_FLOOR=50` against 59, `PRINTED_FLOOR=20`
  against 23. Seven mutations were each proven red and reverted (232-02 SUMMARY). Commit `01200b71`.
- **WR-03, `tomllib` on 3.10.** Per D-06 the `requires-python = ">=3.10"` floor stays. The shared helper
  `tests/pyproject_helpers.py` reads the version through tomllib, then tomli, then a regex tier, and both
  README tests use it. Commits `9e58bdb1` and `d61b0f92`, which removed an unregistered `importorskip`.
- **Proof.** `tests/test_install_hint_package_name.py` 8 passed, `tests/test_docx_report.py::test_docx_skip_advisory`
  1 passed and `tests/test_pyproject_helpers.py` 7 passed, all on 2026-10-27. Plan 232-02 also observed
  40 passed, later 64 passed, in python:3.11-slim from a fresh clone. UAT-232-02, UAT-232-03 and UAT-232-04.
- **Residue, filed with owners, not fixed here:**
  1. Six non-README test files still import `tomllib` directly: `test_brand_assets_freshness.py`,
     `test_packaging.py`, `test_safe_filter_audit.py`, `test_sanitize_scanner_text.py`,
     `test_skip_registry.py` and `test_version.py`. The hypothesis was seven; the seventh,
     `test_install_all_excludes_schemathesis.py`, already falls back to tomli. `quirk/__init__.py` keeps
     its development-path `tomllib` import on purpose (D-06). Todo
     `261027-tests-import-tomllib-directly-break-on-3-10`, owner `999.119`.
  2. 53 unquoted right-name hints in user docs outside the four scanned roots: `docs/operators-guide.md`
     35, `docs/configuration.md` 17, `docs/sample-config.yaml` 1. None uses the wrong name `quirk[`. Todo
     `261027-unquoted-install-hints-in-user-docs`, owner `999.123`.
  3. Docstring drift seen in passing: `quirk/dashboard/api/connector_availability.py:96-100` says the hw
     connectors' reason text names `'quirk-scanner[hw]'`, but the reason string is built from
     `"{module}.{flag} unavailable"`. Recorded in the user-docs todo above, since it is the same "hint text
     that does not reach the user" class.
