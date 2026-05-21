---
phase: 78-html-pdf-injection-hardening
status: human_needed
score: 6/6
date: 2026-05-16
verified: 2026-05-16T00:00:00Z
overrides_applied: 0
human_verification:
  - test: "Run tests/test_report_injection_hardening.py::test_script_payload_in_cert_cn_is_escaped_in_pdf in an environment with Playwright Chromium and pypdf installed"
    expected: "PDF assertion passes — XSS_PAYLOAD ('<script>alert(1)</script>') does not appear in extracted PDF text of report-*.pdf"
    why_human: "Playwright + Chromium binary + pypdf are not installed in the current CI/dev env; the PDF half of ROADMAP success criterion #1 is gated behind pytest.importorskip and registers as 1 of 2 skips. Code path exists but live PDF rendering must be confirmed by a human / CI matrix job with the binaries provisioned."
---

# Phase 78: HTML/PDF Injection Hardening — Verification Report

**Phase Goal:** Every scanner-controlled string that reaches an HTML, PDF, or markdown report passes through a documented sanitization chokepoint — no raw scanner output can inject script tags, HTML entities, or markdown control characters into consultant deliverables.

**Verified:** 2026-05-16
**Status:** human_needed (1 human-validation item; all 6 HARDEN requirements satisfied in code; 51 tests pass, 2 skip cleanly)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criterion) | Status | Evidence |
|---|------------------------------------|--------|----------|
| 1 | `<script>alert(1)</script>` in cert CN renders as `&lt;script&gt;alert(1)&lt;/script&gt;` in HTML **AND PDF** — verified by automated unit test | ⚠ PARTIAL (HTML verified, PDF gated) | `tests/test_report_injection_hardening.py:161` (HTML — passes) and `:236` (PDF — `pytest.importorskip("playwright.sync_api")` + `pytest.importorskip("pypdf")` at lines 240–241; skips in current env) |
| 2 | Every Jinja2 template has `autoescape=True`; every `\| safe` paired with upstream `nh3.clean()` with justification | ✓ VERIFIED | `quirk/reports/html_renderer.py:65` (`autoescape=select_autoescape(["html","j2"])`); `grep "\| safe" report.html.j2` returns zero matches in main template; AST gate `tests/test_safe_filter_audit.py:137` enforces pairing |
| 3 | CI `\| safe` AST gate exits non-zero on unpaired usages — modeled on Phase 59 `safe_str` gate | ✓ VERIFIED | `tests/test_safe_filter_audit.py:137,170` — self-test `test_gate_catches_synthetic_bypass` proves non-zero exit on synthetic violation; `test_filter_lineno_populated` confirms AST line metadata captured |
| 4 | Playwright PDF runs no-JS / no-network; PDF `<title>` + Author from constants only | ✓ VERIFIED | `quirk/reports/html_renderer.py:130-134` — `browser.new_context(java_script_enabled=False, offline=True, bypass_csp=False)`; `quirk/reports/templates/report.html.j2:7` literal `<title>QU.I.R.K. Cryptographic Readiness Report</title>`; `:8` literal `<meta name="author" content="QU.I.R.K. Scanner">`; context.close() at `:152-156` precedes browser.close() at `:157-161` |
| 5 | `nh3>=0.2.17` in `[project.dependencies]` in `pyproject.toml`; clean install resolves it | ✓ VERIFIED | `pyproject.toml:31` — `"nh3>=0.2.17",` in `[project] dependencies` |
| 6 | (HARDEN-01) `md_cell()` parity across executive.py + writer.py | ✓ VERIFIED | `quirk/reports/executive.py:10` import + 8 `md_cell` call sites; `quirk/reports/writer.py:13` import + 6 `md_cell` call sites; `quirk/reports/technical.py` 5 call sites (baseline parity reference) |

**Score:** 6/6 HARDEN requirements satisfied in code. ROADMAP success criterion #1 satisfied for HTML; PDF half requires human validation in a Playwright-equipped environment.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `quirk/util/sanitize.py` | Strict allowlist chokepoint, URL pre-strip, idempotent | ✓ VERIFIED | Lines 34–37 hostile-scheme regex; 41–48 empty tag/attr/clean_content_tags sets; 51–80 `sanitize_scanner_text()` with None→"" handling, str coercion, URL strip, `nh3.clean()` with empty sets — idempotent by construction |
| `pyproject.toml` | `nh3>=0.2.17` in `[project] dependencies` | ✓ VERIFIED | Line 31 |
| `quirk/reports/html_renderer.py` | `sanitize` filter registered; Playwright context locked; context.close before browser.close | ✓ VERIFIED | Line 10 import; 67 filter register; 130–134 locked context; 152–161 ordered cleanup in finally |
| `quirk/reports/templates/report.html.j2` | Literal title constant, `<meta name="author">`, `\| sanitize` pipes on scanner vars | ✓ VERIFIED | Lines 7–8 constants; 24 scanner-controlled `\| sanitize` sites (org_name, report_owner, data_classification, drivers, findings.{title,host,description,recommendation}, ep.{host,protocol,tls_version,cipher_suite,cert_pubkey_alg}, roadmap items, source_url) |
| `quirk/reports/executive.py` | `md_cell()` wraps every scanner-controlled markdown table cell | ✓ VERIFIED | Import at line 10; 8 call sites |
| `quirk/reports/writer.py` | `md_cell()` wraps every scanner-controlled markdown cell | ✓ VERIFIED | Import at line 13; 6 call sites |
| `tests/test_safe_filter_audit.py` | AST gate with self-tests | ✓ VERIFIED | 7 test functions including forward-guard (`test_no_markdown_to_html_lib_in_deps`), `bleach` belt-and-suspenders (`test_no_bleach_in_deps`), `Markup()` walker (`test_no_markup_without_sanitize`) |
| `tests/test_report_injection_hardening.py` | script-in-CN escaped in HTML + PDF | ✓ VERIFIED (HTML); ⚠ GATED (PDF) | HTML test runs; PDF test gated behind `pytest.importorskip` on lines 240–241 |
| `docs/UAT-SERIES.md` | Last Updated 2026-05-16, HARDEN content | ✓ VERIFIED | Line 4 — `**Last Updated:** 2026-05-16 (Phase 78 wrap: HTML/PDF Injection Hardening ...)` |
| Obsidian phase note | Exists at vault path with frontmatter | ✓ VERIFIED | `/Users/digs/vaults/Digs/20_Dev-Work/QUIRK/Phases/Phase-78-HTML-PDF-Injection-Hardening.md` with `type: phase`, `status: complete`, `source: .planning/phases/78-html-pdf-injection-hardening/`, `updated: 2026-05-16` |

---

### Key Link Verification

| From | To | Via | Status |
|------|----|----|--------|
| `html_renderer.py` | `quirk/util/sanitize.py::sanitize_scanner_text` | `env.filters["sanitize"] = sanitize_scanner_text` | ✓ WIRED (line 67) |
| `report.html.j2` scanner vars | sanitize filter | `\| sanitize` pipe (24 sites) | ✓ WIRED |
| `executive.py` / `writer.py` md cells | `_md_escape.md_cell` | direct import + call (14 sites total) | ✓ WIRED |
| Playwright PDF render | locked context | `browser.new_context(java_script_enabled=False, offline=True, bypass_csp=False)` | ✓ WIRED (lines 130–134) |
| CI `\| safe` gate | AST scan | `tests/test_safe_filter_audit.py` (self-tested) | ✓ WIRED |
| `pyproject.toml` dep | runtime import | `import nh3` at `quirk/util/sanitize.py:28` (top-level, non-optional) | ✓ WIRED |

---

### Test Gate Result

```
pytest tests/test_sanitize_scanner_text.py tests/test_md_cell_escape.py \
  tests/test_safe_filter_audit.py tests/test_report_injection_hardening.py \
  tests/test_reports_writer.py tests/test_report_sanitization.py \
  tests/test_html_renderer_roadmap_section.py tests/test_pdf_render_hardening.py \
  tests/test_pdf_metadata_constants.py -q --tb=no

51 passed, 2 skipped in 0.30s   ✓ matches expected (Playwright/pypdf importorskip)
```

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| HARDEN-01 | `md_cell()` parity in executive.py + writer.py | ✓ SATISFIED | 14/14 cluster A call sites (8 exec + 6 writer); imports at exec:10 / writer:13 |
| HARDEN-02 | autoescape=True + `\| safe` paired with `nh3.clean()` + single allowlist | ✓ SATISFIED | html_renderer.py:65; zero `\| safe` in report.html.j2; allowlist sealed in sanitize.py:41–48 |
| HARDEN-03 | Scanner free-text sanitized to HTML/PDF/MD | ✓ SATISFIED | `sanitize_scanner_text` (HTML via filter; MD via md_cell) — 24 HTML pipe sites + 14 MD call sites |
| HARDEN-04 | Playwright no-JS / no-network; metadata constants | ✓ SATISFIED | html_renderer.py:130-134; report.html.j2:7-8 |
| HARDEN-05 | AST CI gate non-zero on unpaired `\| safe` | ✓ SATISFIED | tests/test_safe_filter_audit.py:170 `test_gate_catches_synthetic_bypass` |
| HARDEN-06 | `nh3>=0.2.17` core dep | ✓ SATISFIED | pyproject.toml:31 |

---

### Anti-Patterns Found

None. No `TODO`/`FIXME`/`XXX`/`TBD` in phase-modified files. No empty stubs. No unpaired `| safe`. No `bleach` dep (forward-guard test enforces).

---

### Human Verification Required

**1. PDF assertion for ROADMAP success criterion #1**

- **Test:** Run `pytest tests/test_report_injection_hardening.py::test_script_payload_in_cert_cn_is_escaped_in_pdf -v` in an environment with Playwright (`pip install playwright && playwright install chromium`) and `pypdf` installed.
- **Expected:** Test passes — extracted text from `report-*.pdf` does NOT contain the literal `<script>alert(1)</script>` payload.
- **Why human:** The test is correctly structured but is currently gated behind `pytest.importorskip("playwright.sync_api")` (line 240) and `pytest.importorskip("pypdf")` (line 241). It registers as 1 of the 2 skips in the test gate. The ROADMAP success criterion #1 explicitly requires the PDF half of the regression to "pass against both HTML output AND PDF rendering" — code path exists and is exercised in HTML; PDF needs a Playwright-equipped runner to flip the skip to a pass.

---

### Gaps Summary

No code gaps. All six HARDEN requirements have substantive, wired, exercised implementations. The single open item is environment-dependent CI/manual validation of the PDF regression test, per ROADMAP success criterion #1's explicit "both HTML and PDF" wording. Once the test runs (rather than skips) in a Playwright-equipped CI matrix job, the phase becomes unambiguously `passed`.

---

_Verified: 2026-05-16_
_Verifier: Claude (gsd-verifier)_
