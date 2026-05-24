# Phase 100: Professional & Editable Report Delivery - Pattern Map

**Mapped:** 2026-05-24
**Files analyzed:** 12 (7 modified, 5 new)
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `quirk/reports/templates/report.html.j2` | template | transform | self (existing `<style>` + section blocks) | exact |
| `quirk/reports/html_renderer.py` | renderer | transform | self (`render_html_report` context dict construction) | exact |
| `quirk/config.py` | config/model | - | self (`AssessmentCfg` dataclass, `config_from_dict`) | exact |
| `quirk/config_template.yaml` | config | - | self (existing `assessment:` block lines 11–16) | exact |
| `quirk/reports/docx_renderer.py` (NEW) | renderer | transform | `quirk/reports/html_renderer.py` (module structure + optional-extra skip) | exact |
| `quirk/reports/writer.py` | orchestrator | request-response | self (existing `render_pdf_report` call site lines 235–238) | exact |
| `tests/test_fmt_cover_page.py` (NEW) | test | - | `tests/test_html_report.py` | exact |
| `tests/test_fmt_print_css.py` (NEW) | test | - | `tests/test_html_report.py` | exact |
| `tests/test_docx_renderer.py` (NEW) | test | - | `tests/test_pdf_render_hardening.py` (ImportError simulation) + `tests/test_html_report.py` | exact |
| `tests/test_html_report.py` (EXTEND) | test | - | self | exact |
| `tests/test_reports_writer.py` (EXTEND) | test | - | self | exact |
| `tests/test_cross_surface_parity.py` (EXTEND) | test | - | self | exact |

---

## Pattern Assignments

### `quirk/reports/templates/report.html.j2` (template, transform)

**Analog:** self — existing `<style>` block and section markup

**`<style>` block boundary** (lines 180–186 — last existing rules before closing `</style>`):
```css
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--accent);
      margin-right: 4px;
    }
  </style>
```
All Phase 100 CSS additions go BEFORE line 186's `</style>` close.

**`report-body` open + insertion point** (lines 195–198):
```html
<div class="report-body">

  <!-- ===== EXECUTIVE SUMMARY ===== -->
  <section id="executive-summary">
```
The cover-page `<div class="cover-page">` block is inserted immediately after line 195 (`<div class="report-body">`), before line 197 (`<!-- ===== EXECUTIVE SUMMARY ===== -->`).

**Existing `{% if %}` guard pattern for conditional template vars** (lines 212–221):
```jinja2
{% if narrative_lead %}
<div class="narrative-block">
  <h2>Readiness Assessment</h2>
  {# narrative_lead is static prose from _NARRATIVE_LEADS — mark safe (no user input) #}
  <p>{{ narrative_lead | safe }}</p>
  {% if narrative_drivers %}
  {# narrative_drivers come from score_raw["drivers"] — sanitize scanner-derived text #}
  <p>Key factors: {{ narrative_drivers | join('; ') | sanitize }}</p>
  {% endif %}
</div>
{% endif %}
```
Mirror this pattern for `{% if logo_b64 %}` guard around `.cover-logo-region`.

**`| sanitize` filter application pattern** (lines 236–238):
```jinja2
org_name=getattr(getattr(cfg, "assessment", None), "name", "Unknown"),
```
In the template: `{{ org_name | sanitize }}`, `{{ report_owner | sanitize }}`, `{{ data_classification | sanitize }}`. `generated_at` is datetime-derived — no sanitize. This is the established convention for all user-supplied config strings.

**Locked CSS additions** (verbatim from 100-UI-SPEC.md — insert before `</style>`):
```css
/* === Phase 100 — PDF Cover Page (FMT-01) === */
.cover-page {
  background: var(--bg);
  border-top: 4px solid var(--accent);
  min-height: 100vh;
  padding: 48px 40px 32px;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}
.cover-logo-region { margin-bottom: 32px; }
.cover-logo-region img { max-width: 200px; max-height: 80px; object-fit: contain; display: block; }
.cover-title { font-size: 36px; font-weight: 900; color: var(--accent); letter-spacing: 0.04em; line-height: 1.1; margin-bottom: 16px; }
.cover-org-name { font-size: 22px; font-weight: 400; color: var(--text); line-height: 1.2; margin-bottom: 0; }
.cover-meta-block { margin-top: auto; background: var(--surface); padding: 16px 24px; border-radius: 4px; border-top: 1px solid var(--border); }
.cover-meta-label { font-size: 12px; font-weight: 400; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted); display: inline-block; width: 160px; }
.cover-meta-value { font-size: 12px; font-weight: 400; color: var(--text); }
.cover-meta-row { margin-bottom: 8px; }
.cover-meta-row:last-child { margin-bottom: 0; }
.cover-classification-banner { margin-top: 24px; padding: 8px 16px; background: var(--surface2); border: 1px solid var(--border); border-radius: 4px; text-align: center; font-size: 13px; font-weight: 900; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text); }

/* === Phase 100 — PDF Print & Pagination (FMT-02) === */
table.findings-table { table-layout: fixed; width: 100%; }
table.findings-table th, table.findings-table td { word-wrap: break-word; overflow-wrap: break-word; vertical-align: top; }
table.findings-table th:nth-child(1), table.findings-table td:nth-child(1) { width: 8%; }
table.findings-table th:nth-child(2), table.findings-table td:nth-child(2) { width: 22%; }
table.findings-table th:nth-child(3), table.findings-table td:nth-child(3) { width: 12%; }
table.findings-table th:nth-child(4), table.findings-table td:nth-child(4) { width: 5%; }
table.findings-table th:nth-child(5), table.findings-table td:nth-child(5) { width: 23%; }
table.findings-table th:nth-child(6), table.findings-table td:nth-child(6) { width: 18%; }
table.findings-table th:nth-child(7), table.findings-table td:nth-child(7) { width: 12%; }

@media print {
  @page { size: A4; margin: 15mm 12mm; }
  .cover-page { break-after: page; }
  h1 { break-after: avoid; }
  h2 { break-after: avoid; }
  tr { break-inside: avoid; }
  thead { display: table-header-group; }
  .report-header { display: none; }
  .footer { display: none; }
  .report-body { padding: 0; max-width: 100%; }
}
```

**Locked cover-page Jinja2 block** (verbatim from 100-UI-SPEC.md — insert as first child of `<div class="report-body">`):
```jinja2
{# Phase 100 / FMT-01 / D-01..D-04: PDF Cover Page #}
<div class="cover-page">

  {% if logo_b64 %}
  <div class="cover-logo-region">
    <img src="data:image/{{ logo_mime }};base64,{{ logo_b64 }}"
         alt="{{ org_name | sanitize }} logo">
  </div>
  {% endif %}

  <div class="cover-title">QU.I.R.K. Cryptographic Readiness Report</div>
  <div class="cover-org-name">{{ org_name | sanitize }}</div>

  <div class="cover-meta-block">
    <div class="cover-meta-row">
      <span class="cover-meta-label">Report Owner</span>
      <span class="cover-meta-value">{{ report_owner | sanitize }}</span>
    </div>
    <div class="cover-meta-row">
      <span class="cover-meta-label">Scan Date</span>
      <span class="cover-meta-value">{{ generated_at }}</span>
    </div>
    <div class="cover-meta-row">
      <span class="cover-meta-label">Data Classification</span>
      <span class="cover-meta-value">{{ data_classification | sanitize }}</span>
    </div>
    <div class="cover-classification-banner">{{ data_classification | upper | sanitize }}</div>
  </div>

</div><!-- /cover-page -->
```

**`findings-table` class addition** — The All Findings `<table>` element (confirmed at line ~358 of report.html.j2) must gain `class="findings-table"`. No other table in the template gets this class.

---

### `quirk/reports/html_renderer.py` (renderer, transform)

**Analog:** self — existing `render_html_report` context dict construction (lines 146–261)

**Module-level imports pattern** (lines 1–11):
```python
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from quirk.util.safe_exc import safe_str
from quirk.util.sanitize import sanitize_scanner_text
from quirk.reports.content_model import ExecContent, assert_congruent
```
Add `import base64` to this block (stdlib, no new deps).

**`getattr` pattern for optional cfg attributes** (lines 236–238):
```python
org_name=getattr(getattr(cfg, "assessment", None), "name", "Unknown"),
report_owner=getattr(getattr(cfg, "assessment", None), "report_owner", ""),
data_classification=getattr(getattr(cfg, "assessment", None), "data_classification", "CONFIDENTIAL"),
```
Use the same double-`getattr` pattern for `logo_path`:
```python
logo_path = getattr(getattr(cfg, "assessment", None), "logo_path", None)
logo_b64, logo_mime = _load_logo_b64(logo_path)
```

**`template.render(...)` call site** (lines 235–259) — add two new kwargs at the end of the call:
```python
html = template.render(
    org_name=...,
    report_owner=...,
    ...
    top_risks=top_risks,
    # Phase 100 / FMT-01 / D-01: logo embed for cover page
    logo_b64=logo_b64,
    logo_mime=logo_mime,
)
```

**New helper to add** (placed before `render_html_report`, following the `_score_band` / `_score_color` / `_severity_color` helper pattern at lines 21–138):
```python
def _load_logo_b64(logo_path):
    """Return (b64_string, mime_subtype) or (None, 'png') when logo absent/unreadable.

    D-01/D-03: base64-embed for offline HTML; None means omit logo region in template.
    """
    if not logo_path:
        return None, "png"
    try:
        with open(logo_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode("ascii")
        ext = os.path.splitext(logo_path)[1].lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                "gif": "gif", "svg": "svg+xml"}.get(ext, "png")
        return b64, mime
    except (OSError, IOError):
        return None, "png"
```

**`os.makedirs` pattern** (line 260):
```python
os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
```
Mirror this in `docx_renderer.py` before `doc.save(path)`.

---

### `quirk/config.py` (config/model)

**Analog:** self — `AssessmentCfg` dataclass (lines 10–15) + `config_from_dict` at line 479

**Current `AssessmentCfg`** (lines 10–15):
```python
@dataclass
class AssessmentCfg:
    name: str
    data_classification: str
    report_owner: str
    timezone: str
```

**Extension pattern** — add one optional field with a default (safe for `AssessmentCfg(**raw["assessment"])` at config.py:479 because Python dataclass `__init__` accepts kwargs with defaults when the key is absent):
```python
@dataclass
class AssessmentCfg:
    name: str
    data_classification: str
    report_owner: str
    timezone: str
    logo_path: str | None = None   # Phase 100 / D-01 — optional path to local image file
```

**Warning:** `AssessmentCfg(**raw["assessment"])` at line 479 raises `TypeError` if a YAML includes `logo_path` BUT the field is not yet declared. The field declaration and the config_template.yaml addition must ship together.

---

### `quirk/config_template.yaml` (config)

**Analog:** self — existing `assessment:` block (lines 11–16)

**Current block** (lines 11–16):
```yaml
assessment:
  name: "My Organization"
  report_owner: "Security Team"
  data_classification: "CONFIDENTIAL"
  timezone: "UTC"
```

**Addition** — append a commented-out `logo_path` line after `timezone`:
```yaml
assessment:
  name: "My Organization"
  report_owner: "Security Team"
  data_classification: "CONFIDENTIAL"
  timezone: "UTC"
  # logo_path: /path/to/your-org-logo.png   # optional; omit to show org name only
```

---

### `quirk/reports/docx_renderer.py` (NEW renderer, transform)

**Primary analog:** `quirk/reports/html_renderer.py` — module structure, how it consumes `cfg`/`exec_content`/`findings`

**Secondary analog:** `render_pdf_report` in `html_renderer.py` (lines 290–341) — optional-extra import + graceful-skip + return bool

**Module docstring pattern** (line 1 of html_renderer.py):
```python
"""Jinja2-based standalone HTML report renderer for QU.I.R.K. (Phase 7, D-08 to D-12)."""
```
Mirror: `"""python-docx DOCX report renderer for QU.I.R.K. (Phase 100, FMT-03 / D-09..D-12)."""`

**Imports pattern** — mirrors html_renderer.py lines 1–11; stdlib only at module level (NO `from docx import Document` at module level — lazy import only):
```python
"""python-docx DOCX report renderer for QU.I.R.K. (Phase 100, FMT-03 / D-09..D-12)."""
import os
import sys
from datetime import datetime, timezone
from typing import Any, List, Optional
```

**Optional-extra import + graceful-skip pattern** (from `render_pdf_report` lines 295–299 of html_renderer.py):
```python
def render_pdf_report(html_path: str, pdf_path: str) -> bool:
    try:
        from playwright.sync_api import sync_playwright
        from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        return False
```
For `render_docx_report`, use the same structure but also print an advisory before returning:
```python
def render_docx_report(
    path: str,
    cfg: Any,
    findings: List[dict],
    exec_content: "ExecContent | None" = None,
) -> bool:
    """Write a DOCX report to path. Returns True on success, False if python-docx absent."""
    try:
        from docx import Document
    except ImportError:
        print(
            "DOCX export skipped: python-docx is not installed. "
            "Install with: pip install quirk-scanner[docx]",
            file=sys.stderr,
        )
        return False
```

**`getattr` pattern for cfg access** (mirrors html_renderer.py lines 236–238):
```python
org_name = getattr(getattr(cfg, "assessment", None), "name", "Unknown")
report_owner = getattr(getattr(cfg, "assessment", None), "report_owner", "")
data_classification = getattr(getattr(cfg, "assessment", None), "data_classification", "")
```

**`os.makedirs` + save pattern** (mirrors html_renderer.py line 260):
```python
os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
doc.save(path)
print(f"DOCX report written to {path}")
return True
```

**python-docx table construction pattern** (from RESEARCH.md Pattern 3 / python-docx API):
```python
tbl = doc.add_table(rows=1, cols=7)
tbl.style = 'Table Grid'
hdr_cells = tbl.rows[0].cells
for i, hdr in enumerate(["Severity", "Title", "Host", "Port",
                          "Description", "Recommendation", "Quantum Risk"]):
    hdr_cells[i].text = hdr
for finding in findings or []:
    row_cells = tbl.add_row().cells
    row_cells[0].text = str(finding.get("severity", ""))
    ...
```
When `findings` is empty: add one data row, set first cell to `"No findings recorded for this scan."`.

**exec_content consumption pattern** — mirrors html_renderer.py lines 205–233 (route through exec_content when present, fall back gracefully):
```python
if exec_content is not None:
    narrative_lead = exec_content.narrative_lead
    narrative_drivers = exec_content.narrative_drivers
    top_risks = exec_content.top_risks
    roadmap_now = [r for r in exec_content.roadmap_items if r.phase == "NOW"]
    roadmap_next = [r for r in exec_content.roadmap_items if r.phase == "NEXT"]
    roadmap_later = [r for r in exec_content.roadmap_items if r.phase == "LATER"]
    subscores = exec_content.subscores or {}
else:
    narrative_lead = None
    narrative_drivers = []
    top_risks = []
    roadmap_now = roadmap_next = roadmap_later = []
    subscores = {}
```

**DOCX document layout order** (verbatim from 100-UI-SPEC.md DOCX Structure Contract):
1. `doc.add_paragraph("[ Insert organization logo here ]", style="Normal")`
2. `doc.add_heading("QU.I.R.K. Cryptographic Readiness Report", level=1)`
3. `doc.add_heading(org_name, level=2)`
4. `doc.add_paragraph(f"Report Owner: {report_owner}  |  Date: {generated_at}  |  Classification: {data_classification}", style="Normal")`
5. Executive Summary section (Heading 1 → narrative_lead → Heading 2 sub-sections → tables)
6. Findings section (Heading 1 → 7-col table)
7. Remediation Roadmap section (Heading 1 → NOW/NEXT/LATER Heading 2 + 4-col tables each)
8. Score Breakdown section (Heading 1 → rollup sentence → 3-col table)

---

### `quirk/reports/writer.py` (orchestrator, request-response)

**Analog:** self — existing `render_pdf_report` call site (lines 235–238 + lines 294–302)

**Current PDF call site** (lines 235–238):
```python
pdf_path = os.path.join(outdir, f"report-{stamp}.pdf")
pdf_ok = render_pdf_report(html_path=html_path, pdf_path=pdf_path)
if not pdf_ok:
    pdf_path = None  # Playwright unavailable — HTML report still written
```

**DOCX call site pattern** — insert immediately after line 238, before the run-stats block at line 240:
```python
# Phase 100 / FMT-03 / D-11: DOCX auto-emit every run; skip gracefully if python-docx absent
docx_path = os.path.join(outdir, f"report-{stamp}.docx")
docx_ok = render_docx_report(
    path=docx_path,
    cfg=cfg,
    findings=findings,
    exec_content=exec_content,
)
if not docx_ok:
    docx_path = None
```

**Import extension** (line 21 of writer.py):
```python
from quirk.reports.html_renderer import render_html_report, render_pdf_report
```
Extend to:
```python
from quirk.reports.html_renderer import render_html_report, render_pdf_report
from quirk.reports.docx_renderer import render_docx_report
```

**Output files list** (lines 294–302) — add `docx_path` alongside existing paths; the existing `if p` filter handles `None`:
```python
output_files = [p for p in [
    findings_path, stats_path, exec_path, tech_path,
    scorecard_path, roadmap_path, intelligence_path,
    cbom_json_path, cbom_xml_path,
    html_path, pdf_path, docx_path,   # Phase 100: add docx_path
] if p]
```

---

### `tests/test_fmt_cover_page.py` (NEW test)

**Analog:** `tests/test_html_report.py` (lines 1–76)

**Minimal cfg fixture pattern** (test_html_report.py lines 6–17):
```python
def _make_minimal_cfg():
    from types import SimpleNamespace
    return SimpleNamespace(
        assessment=SimpleNamespace(
            name="Test Org",
            report_owner="Test Owner",
            data_classification="CONFIDENTIAL",
            timezone="UTC",
        ),
        output=SimpleNamespace(directory="/tmp/quirk_test_html"),
    )
```
Phase 100 tests extend this with `logo_path=None` (or a real tmp image path for logo embed tests).

**render + read pattern** (test_html_report.py lines 23–37):
```python
from quirk.reports.html_renderer import render_html_report
cfg = _make_minimal_cfg()
os.makedirs(cfg.output.directory, exist_ok=True)
out = os.path.join(cfg.output.directory, "report-test.html")
render_html_report(
    path=out, cfg=cfg, endpoints=[], findings=[],
    score={"total": 75, "subscores": {}, "drivers": []},
    conf={"confidence": 80, "confidence_factors": {}},
    roadmap_items=[],
)
content = open(out).read()
assert "QU.I.R.K." in content
```

**Tests to implement** (from 100-RESEARCH.md Validation Architecture):
- `test_cover_page_in_html` — `"cover-page"` in rendered HTML content
- `test_logo_absent_graceful` — `logo_b64` is `None` when `logo_path=None`
- `test_logo_embedded` — `"data:image/png;base64,"` in rendered HTML when `logo_path` set to a real PNG tmp file
- `test_assessment_cfg_logo_path` — `AssessmentCfg(name="X", data_classification="C", report_owner="R", timezone="UTC", logo_path="/tmp/x.png")` does not raise
- `test_backward_compat_config` — `AssessmentCfg(name="X", data_classification="C", report_owner="R", timezone="UTC")` (no logo_path) does not raise and `.logo_path` is `None`

---

### `tests/test_fmt_print_css.py` (NEW test)

**Analog:** `tests/test_html_report.py` (same render + read pattern)

**Tests to implement:**
- `test_print_media_block` — `"@media print"` in rendered HTML
- `test_findings_table_class` — `'class="findings-table"'` in rendered HTML (confirms the table element got the class)
- `test_fixed_table_layout_css` — `"table-layout: fixed"` in rendered HTML stylesheet

---

### `tests/test_docx_renderer.py` (NEW test)

**Analog:** `tests/test_pdf_render_hardening.py` (lines 1–60) for ImportError simulation; `tests/test_html_report.py` for cfg fixture

**ImportError simulation pattern** (test_pdf_render_hardening.py lines 44–75):
```python
# Simulate missing optional extra by patching sys.modules
import sys
from unittest import mock

def test_docx_graceful_skip(monkeypatch, tmp_path, capsys):
    monkeypatch.setitem(sys.modules, "docx", None)
    from quirk.reports.docx_renderer import render_docx_report
    result = render_docx_report(path=str(tmp_path / "report.docx"), cfg=_make_minimal_cfg(), findings=[])
    assert result is False
    captured = capsys.readouterr()
    assert "python-docx is not installed" in captured.err
```
Note: `monkeypatch.setitem(sys.modules, "docx", None)` makes the lazy `from docx import Document` raise `ImportError`.

**DOCX structure inspection pattern** (open rendered DOCX to assert structure):
```python
def test_docx_written(tmp_path):
    from docx import Document
    from quirk.reports.docx_renderer import render_docx_report
    path = str(tmp_path / "report.docx")
    result = render_docx_report(path=path, cfg=_make_minimal_cfg(), findings=[])
    assert result is True
    assert os.path.exists(path)
    doc = Document(path)
    # Assert structure via doc.paragraphs / doc.tables
```

**Tests to implement** (from 100-RESEARCH.md):
- `test_docx_written` — file exists + returns True
- `test_logo_placeholder` — first paragraph text == `"[ Insert organization logo here ]"`
- `test_docx_section_headings` — heading paragraphs contain `"Executive Summary"`, `"Findings"`, `"Remediation Roadmap"`, `"Score Breakdown"`
- `test_docx_findings_table_cols` — first table has 7 columns, header row matches `["Severity", "Title", "Host", "Port", "Description", "Recommendation", "Quantum Risk"]`
- `test_docx_graceful_skip` — returns False when `docx` absent in sys.modules
- `test_docx_skip_advisory` — stderr contains `"python-docx is not installed"`
- `test_writer_docx_none_on_fail` — when `render_docx_report` returns False, `docx_path` not in output files list

---

### `tests/test_reports_writer.py` (EXTEND)

**Analog:** self — existing `@patch` + stub pattern (lines 118–135)

**Extension approach** — within the existing `test_json_export_preserves_description` or a new test, assert that `docx_path` appears in the output files returned or that a `report-*.docx` file exists in `tmp_path`. Follow the existing `@patch` decorator stack on the writer stubs.

---

### `tests/test_cross_surface_parity.py` (EXTEND)

**Analog:** self — existing `test_narrative_content_parity` (lines 91–134)

**Extension approach** — after asserting HTML and CLI surfaces contain `narrative_lead`, add a DOCX surface assertion:
```python
from quirk.reports.docx_renderer import render_docx_report
docx_path = str(tmp_path / "parity_test.docx")
render_docx_report(path=docx_path, cfg=cfg, findings=_FINDINGS, exec_content=exec_content)
# Inspect DOCX paragraphs for narrative_lead text
from docx import Document
doc = Document(docx_path)
full_text = "\n".join(p.text for p in doc.paragraphs)
assert exec_content.narrative_lead in full_text
```

---

## Shared Patterns

### Optional-Extra Lazy Import + Graceful Skip
**Source:** `quirk/reports/html_renderer.py` lines 295–299 (`render_pdf_report`)
**Apply to:** `quirk/reports/docx_renderer.py::render_docx_report`
```python
try:
    from playwright.sync_api import sync_playwright
    from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
except ImportError:
    return False
```
Mirror exactly: `try: from docx import Document except ImportError: print(advisory, file=sys.stderr); return False`.

CRITICAL: The `from docx import Document` import MUST be inside the function body. Never at module level. See project feedback memory: "optional-extra import trap".

### Double-`getattr` Pattern for cfg Access
**Source:** `quirk/reports/html_renderer.py` lines 236–238
**Apply to:** `quirk/reports/docx_renderer.py`, `quirk/reports/html_renderer.py` (logo_path extraction)
```python
getattr(getattr(cfg, "assessment", None), "name", "Unknown")
```

### `os.makedirs` Before File Write
**Source:** `quirk/reports/html_renderer.py` line 260
**Apply to:** `quirk/reports/docx_renderer.py` before `doc.save(path)`
```python
os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
```

### exec_content Routing (Single Content Pipeline)
**Source:** `quirk/reports/html_renderer.py` lines 175–233
**Apply to:** `quirk/reports/docx_renderer.py`
Route through `exec_content` when present; fall back gracefully when `None`. This is D-10 — the DOCX must consume the same content model as HTML/CLI, not build its own.

### `SimpleNamespace` Minimal Cfg in Tests
**Source:** `tests/test_html_report.py` lines 6–17
**Apply to:** all new test files (`test_fmt_cover_page.py`, `test_fmt_print_css.py`, `test_docx_renderer.py`)
```python
from types import SimpleNamespace
SimpleNamespace(
    assessment=SimpleNamespace(
        name="Test Org",
        report_owner="Test Owner",
        data_classification="CONFIDENTIAL",
        timezone="UTC",
    ),
    ...
)
```
For Phase 100 tests, add `logo_path=None` to the `assessment` namespace.

### `monkeypatch.setitem(sys.modules, ...)` for Missing Optional Extra
**Source:** `tests/test_pdf_render_hardening.py` lines 44–75 (via fake module approach)
**Apply to:** `tests/test_docx_renderer.py` — simulating absent python-docx
```python
monkeypatch.setitem(sys.modules, "docx", None)
```

---

## No Analog Found

None — all files have close analogs in the existing codebase.

---

## Metadata

**Analog search scope:** `quirk/reports/`, `quirk/config.py`, `quirk/config_template.yaml`, `tests/`
**Files read:** html_renderer.py (342 lines), writer.py (lines 200–302), config.py (lines 1–60 + 470–488), config_template.yaml (lines 8–25), report.html.j2 (lines 180–229), test_html_report.py (lines 1–80), test_pdf_render_hardening.py (lines 1–60), test_reports_writer.py (lines 1–135), test_cross_surface_parity.py (lines 1–134)
**Pattern extraction date:** 2026-05-24
