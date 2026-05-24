---
phase: 100
slug: professional-editable-report-delivery
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-24
---

# Phase 100 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | conftest.py at tests/ |
| **Quick run command** | `python -m pytest tests/test_html_report.py tests/test_docx_report.py tests/test_reports_writer.py -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~30-60 seconds (targeted) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (targeted to touched report modules)
- **After every plan wave:** Run the full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

> Task IDs provisional — refined once the planner emits PLAN.md files.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 100-01-* | 01 | 1 | FMT-01 | — | cover page renders with logo region (base64-embedded), title, org, classification banner, date, owner; graceful omit when logo_path absent/unreadable | unit | `python -m pytest tests/test_html_report.py -q` | ❌ W0 | ⬜ pending |
| 100-01-* | 01 | 1 | FMT-01 | T-100-LOGO | logo_path config key optional + backward-compatible (existing configs without it still parse); logo image read+base64 safely (no crash on missing/oversized/invalid file) | unit | `python -m pytest tests/test_config.py tests/test_html_report.py -q` | ❌ W0 | ⬜ pending |
| 100-01-* | 01 | 1 | FMT-02 | — | print @page + page-break CSS present: break-inside:avoid rows, break-after:avoid headings, cover break-after:page, thead table-header-group; findings table fixed table-layout | unit | `python -m pytest tests/test_html_report.py -q` | ❌ W0 | ⬜ pending |
| 100-02-* | 02 | 2 | FMT-03 | — | DOCX built from shared exec_content+findings; sections (cover/exec/findings/roadmap/score) + Heading 1/2 + native tables + logo placeholder paragraph; opens as valid .docx | unit | `python -m pytest tests/test_docx_report.py -q` | ❌ W0 | ⬜ pending |
| 100-02-* | 02 | 2 | FMT-03 | T-100-DEP | DOCX auto-emits in write_reports every run; graceful skip + stderr advisory when python-docx absent (no crash) | unit | `python -m pytest tests/test_docx_report.py tests/test_reports_writer.py -q` | ❌ W0 | ⬜ pending |
| 100-02-* | 02 | 2 | FMT-03 | — | cross-surface parity: DOCX section/finding content matches HTML/PDF content model (no parallel/divergent content) | unit | `python -m pytest tests/test_cross_surface_parity.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Extend `tests/test_html_report.py` — cover-page render + logo embed/absent + print/page-break CSS presence (FMT-01, FMT-02) — created/extended by Plan 01
- [x] Add `tests/test_docx_report.py` — DOCX structure, sections/headings/tables, logo placeholder, graceful-skip when lib absent (FMT-03) — created by Plan 02
- [x] Extend `tests/test_reports_writer.py` — DOCX auto-emit in write_reports artifact set (FMT-03) — extended by Plan 02
- [x] Extend `tests/test_cross_surface_parity.py` — DOCX vs HTML/PDF content parity (FMT-03) — extended by Plan 02
- [x] `tests/test_config.py` — optional logo_path field backward-compat (FMT-01)

*Existing infrastructure (pytest + conftest) covers framework needs. python-docx installed via `[docx]` extra for the DOCX test path; tests guard graceful-skip when absent.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PDF cover page + section layout visual quality ("hand to a CISO without apology") | FMT-01 | Visual judgment requires rendering the PDF and eyeballing layout/branding | Run a scan, open the PDF, confirm branded cover + clean sections |
| PDF pagination integrity (no overflow/truncation/mid-row table split) | FMT-02 | Pagination defects only manifest in the rendered multi-page PDF | Render PDF with enough findings to span pages; confirm no table splits, no overflow |
| DOCX opens in Word AND Google Docs with structure intact | FMT-03 | Requires Microsoft Word + Google Docs (external apps) | Open the .docx in both; confirm sections/headings/tables intact, logo placeholder present, narrative editable |

*Automated tests cover structure/data-flow/graceful-degradation; visual fidelity in real renderers/word processors is the manual layer (consistent with prior report-phase deferrals).*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-24
