---
phase: 7
slug: polish-and-packaging
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-31
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.venv/bin/python -m pytest tests/test_brand*.py -x -q` |
| **Full suite command** | `.venv/bin/python -m pytest tests/ -q` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.venv/bin/python -m pytest tests/ -q`
- **After every plan wave:** Run `.venv/bin/python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 0 | BRAND-01 | unit | `pytest tests/test_html_report.py::test_report_contains_wordmark -x` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 0 | BRAND-01 | unit | `pytest tests/test_dashboard_theme.py::test_primary_color_token -x` | ❌ W0 | ⬜ pending |
| 7-02-01 | 02 | 0 | BRAND-02 | smoke | `pytest tests/test_cli_version.py::test_version_flag -x` | ❌ W0 | ⬜ pending |
| 7-02-02 | 02 | 0 | BRAND-02 | unit | `pytest tests/test_rich_output.py::test_scan_summary_uses_rich -x` | ❌ W0 | ⬜ pending |
| 7-03-01 | 03 | 0 | BRAND-03 | unit | `pytest tests/test_html_report.py::test_html_is_self_contained -x` | ❌ W0 | ⬜ pending |
| 7-03-02 | 03 | 0 | BRAND-03 | unit | `pytest tests/test_html_report.py::test_html_report_sections -x` | ❌ W0 | ⬜ pending |
| 7-03-03 | 03 | 0 | BRAND-03 | unit | `pytest tests/test_html_report.py::test_pdf_graceful_degradation -x` | ❌ W0 | ⬜ pending |
| 7-04-01 | 04 | 0 | BRAND-04 | unit | `pytest tests/test_cli_init.py::test_init_creates_config -x` | ❌ W0 | ⬜ pending |
| 7-04-02 | 04 | 0 | BRAND-04 | unit | `pytest tests/test_cli_init.py::test_init_no_overwrite -x` | ❌ W0 | ⬜ pending |
| 7-04-03 | 04 | 0 | BRAND-04 | smoke | `pytest tests/test_packaging.py::test_run_scan_importable -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_html_report.py` — stubs for BRAND-01 (wordmark), BRAND-03 (self-contained HTML, sections, PDF graceful degradation)
- [ ] `tests/test_cli_version.py` — stubs for BRAND-02 (`--version` flag)
- [ ] `tests/test_rich_output.py` — stubs for BRAND-02 (rich summary table in `write_reports()`)
- [ ] `tests/test_cli_init.py` — stubs for BRAND-04 (`quirk init` subcommand)
- [ ] `tests/test_packaging.py` — stubs for BRAND-04 (`run_scan` importable after install, package data present)
- [ ] `tests/test_dashboard_theme.py` — stubs for BRAND-01 (CSS token audit)
- [ ] Install Jinja2: `.venv/bin/pip install "jinja2>=3.1.0"` + add to `pyproject.toml [project] dependencies`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard navbar shows QU.I.R.K. wordmark visually | BRAND-01 | Requires visual browser inspection | Open dashboard, confirm navbar wordmark renders with correct font/color |
| CLI startup banner renders with color in terminal | BRAND-02 | Rich rendering requires TTY | Run `quirk scan --help` or `quirk scan`, verify banner displays |
| HTML report looks like a commercial security product | BRAND-03 | Aesthetic quality judgment | Open `report.html` in browser, verify layout, score gauges, color coding |
| PDF output is print-quality | BRAND-03 | PDF rendering quality | Run scan with PDF output, open `report.pdf`, verify layout/branding |
| `pip install` produces working CLI from zero | BRAND-04 | Requires clean environment test | In a fresh venv: `pip install 'git+https://github.com/.../quirk.git'`, run `quirk --version` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands pointing at pytest (not shell grep)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending execution

---

## Revision Notes (2026-03-31)

Applied checker feedback:

- **07-02:** Added `quirk/cli/init_cmd.py` stub (raises NotImplementedError) to Plan 02 Task 1, so the `from quirk.cli.init_cmd import run_init` import in run_scan.py never hits ImportError before Plan 05 runs. Added `quirk/cli/init_cmd.py` to Plan 02 `files_modified`.
- **07-03:** Wave changed 1 → 2; `depends_on` updated to include `07-02` (both plans edit writer.py — serializing prevents merge conflicts). `PackageLoader` replaced with `FileSystemLoader(os.path.dirname(__file__), 'templates')` throughout — avoids TemplateNotFound errors before pip reinstall.
- **07-04 Task 1:** `<automated>` verify changed from grep shell command to `.venv/bin/python -m pytest tests/test_dashboard_theme.py -x -q`.
- **07-04 Task 2:** `<automated>` verify changed from grep shell command to `.venv/bin/python -m pytest tests/test_dashboard_theme.py -x -q`. Added D-13 full color audit step: grep `src/dashboard/src/components/` for stray hardcoded hex/hsl() values, resolve any found, document audit result in sidebar.tsx comment.
- **07-VALIDATION.md:** `nyquist_compliant` set to `true`; sign-off checkboxes checked.
