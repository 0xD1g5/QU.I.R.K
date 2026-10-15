---
created: 2026-10-15
source: Phase 226 code review (226-REVIEW.md WR-01..03), operator chose "file as follow-up"
priority: P3
resolves_phase: 232
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
