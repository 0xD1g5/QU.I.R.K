---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger row DCL-INSTALL-0148
priority: high
area: quirk/util/optional_extra.py, quirk/errors.py, quirk/notify/channels/slack.py, quirk/cli/ticket_cmd.py, quirk/ticketing/jira.py, quirk/scanner/k8s_connector.py, quirk/dashboard/api/routes/reports.py
status: pending
resolves_phase: null
---

# Runtime install hints tell users to `pip install quirk[<extra>]`, which is a different PyPI project

QU.I.R.K.'s PyPI distribution is `quirk-scanner`. A different, unrelated project named `quirk` exists on PyPI
(`curl -s https://pypi.org/pypi/quirk/json` -> name `quirk`, version 0.1.3, "Build powerful predictive models
with a few lines of code"). Yet the product's own messages say `pip install quirk[identity]`, `quirk[db]`,
`quirk[cloud]`, `quirk[dashboard]`, `quirk[cbom]`, `quirk[tickets]`, `quirk[notify]`, `quirk[docx]`:

- `quirk/util/optional_extra.py:85,95,105,115,144,156` (the missing-extra advisories every scan can emit)
- `quirk/errors.py:33,38` (`INSTALL-*` fix text)
- `quirk/notify/channels/slack.py:40`, `quirk/cli/ticket_cmd.py:97`, `quirk/ticketing/jira.py:58`
- `quirk/scanner/k8s_connector.py:436,451,472`
- `quirk/dashboard/api/routes/reports.py:109` (`REASON_DOCX_EXTRA_MISSING`, shown as a tooltip in the dashboard)

A user following the hint installs a stranger's package (a supply-chain footgun, not just a typo). Found while
verifying `docs/installation.md` "Coverage advisories": the doc originally promised the exact
`pip install quirk-scanner[<extra>]` command, which is not what the code prints. The doc now states the correct
form and names the discrepancy (D-10: docs change, code does not).

- [ ] Replace every `pip install quirk[<extra>]` in the files above with `pip install 'quirk-scanner[<extra>]'`.
- [ ] Update the tests that pin the old literal (`tests/test_optional_extra.py::test_all_hints_contain_pip_install_literal`,
      `tests/test_errors.py`, `tests/test_reports_download_route.py`, `tests/test_evidence_coverage_gap.py`,
      `tests/test_coverage_gap_severity_invariant.py`, and the `tests/test_install_all_*` files).
- [ ] Regenerate `docs/error-codes.md` (`python run_scan.py errors --dump-md > docs/error-codes.md`) and any
      golden fixtures that embed the hint text.
- [ ] Then delete the discrepancy sentence from `docs/installation.md` "Coverage advisories" and regenerate
      `docs/quirk-master-guide.md`.

## Feasibility & Effort

**CONFIRMED** (18 occurrences of `pip install quirk[` in `quirk/` and `run_scan.py`, counted with
`grep -rn "pip install quirk\[" quirk run_scan.py --include="*.py" | wc -l`). Effort **S**: a mechanical string
replacement, but it fans out to roughly eight pinned tests, the error-code doc generator
(`docs/error-codes.md` is gated by `tests/test_error_codes_freshness.py`) and possibly report fixtures. No
unknowns beyond finding every golden file that embeds the text. **No spike needed.**

## Resolution

Resolved in Phase 226 plans 04 and 06 (2026-10-14): runtime sites and quirk/config_template.yaml now name quirk-scanner; `git grep -nE "pip install ['"]?quirk\[" -- quirk run_scan.py` returns 0 lines; standing guard tests/test_install_hint_package_name.py.
