# Phase 100: Professional & Editable Report Delivery - Research

**Researched:** 2026-05-24
**Domain:** Python report formatting — HTML/CSS print layout + python-docx DOCX generation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**PDF Cover Page & Branding (FMT-01)**
- D-01: Logo source is `assessment.logo_path` config key; image base64-embedded at render time (offline-safe, no CDN).
- D-02: Cover page contains: logo region (top), report title, org name, data-classification banner, scan date, report owner.
- D-03: When `logo_path` is absent/unreadable — degrade gracefully, omit logo region, show org name; never a broken-image box.
- D-04: Reuse existing embedded design tokens (new-york/zinc, cssVariables); no new fonts, no CDN. All additions inside the existing inlined `<style>` block.

**PDF Pagination & Table Integrity (FMT-02)**
- D-05: `break-inside: avoid` on `tr`; `break-after: avoid` on `h1`, `h2`.
- D-06: 7-column findings table uses `table-layout: fixed` + explicit column widths + `word-wrap: break-word` to fit A4. Do NOT shrink font.
- D-07: Cover page occupies own page (`break-after: page`).
- D-08: `thead { display: table-header-group }` for header repeat across page breaks.

**DOCX Export (FMT-03)**
- D-09: `python-docx` as OPTIONAL extra `[docx]`; graceful skip when absent (mirrors Playwright fallback pattern).
- D-10: DOCX built from shared `exec_content` + findings dict (`build_exec_content`), NOT HTML→DOCX conversion.
- D-11: DOCX auto-emitted on EVERY report generation as `report-{stamp}.docx`; skip with advisory if python-docx absent.
- D-12: Structural fidelity only — cover/exec/findings/roadmap/score sections, Word Heading 1/2, native tables, editable defaults. Logo placeholder paragraph `"[ Insert organization logo here ]"` (not embedded logo).

### Claude's Discretion
- Exact `@page` margin tuning and column-width percentages for the findings table (within the "fits A4, no overflow" acceptance bar).
- Whether DOCX generation lives in a new `quirk/reports/docx_renderer.py` module (analog to html_renderer.py).
- Cover-page visual arrangement details within the locked content set (D-02).

### Deferred Ideas (OUT OF SCOPE)
None declared — discussion stayed within phase scope. DOCX styling beyond structural fidelity and logo auto-embedding into DOCX are intentionally left to the consultant per D-12.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FMT-01 | PDF report uses a professional client-ready layout: cover with configurable logo region, sectioning, consistent typography/branding | CSS cover-page block in report.html.j2; base64 logo embed via html_renderer.py; AssessmentCfg.logo_path new field |
| FMT-02 | Report tables/headings render cleanly in PDF: no overflow, truncation, or broken pagination | `@media print` @page + break rules; `table-layout: fixed` + column widths on `.findings-table` class |
| FMT-03 | Report exported as editable DOCX: opens in Word/Google Docs with sections + tables intact; consultant can insert logo and edit content | New `quirk/reports/docx_renderer.py` using python-docx optional extra; called from write_reports after PDF step |

</phase_requirements>

---

## Summary

Phase 100 is a pure formatting and new-artifact phase with no content changes. All content was shipped in Phases 98 (executive narrative, roadmap, score transparency) and 99 (per-finding quantum risk, CTX fields). The three work streams are: (1) a CSS-only cover page block inserted into `report.html.j2`; (2) print pagination CSS rules and a `findings-table` class for the 7-column findings table; and (3) a new `quirk/reports/docx_renderer.py` module that renders the same `ExecContent` / findings model into a python-docx `Document`.

The code insertion points are fully defined by reading the existing source. `write_reports` in `writer.py` is the single orchestration entry point — DOCX emit slots in after the `render_pdf_report` call at line 236, before the run-stats file. The template `report.html.j2` inserts the cover-page block as the first child of `<div class="report-body">` (before `<section id="executive-summary">`), and the `<style>` block ends at line 186 — all CSS additions go there. `AssessmentCfg` is a plain `@dataclass` and `config_from_dict` calls `AssessmentCfg(**raw["assessment"])` directly, so adding `logo_path: str | None = None` with a default is safe.

The UI-SPEC (100-UI-SPEC.md) is the definitive locked contract for all markup, CSS, copywriting strings, Jinja2 template blocks, and DOCX structure. The planner must treat it as ground truth and ensure executor implements the exact markup/CSS/copy it specifies.

**Primary recommendation:** Three largely independent plans — (A) AssessmentCfg + logo embed in html_renderer, (B) template cover-page + print CSS, (C) docx_renderer.py new module + writer.py integration + pyproject.toml extra.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PDF cover page markup | HTML/CSS template layer | Python renderer (logo embed) | Cover is pure Jinja2/CSS; Python only handles base64 encoding of logo |
| Print pagination rules | HTML/CSS template layer | — | `@media print` + `@page` are CSS-only; Playwright inherits them automatically |
| Findings table fixed layout | HTML/CSS template layer | — | `table-layout: fixed` + class added to existing table element in template |
| Logo base64 embedding | Python (html_renderer.py) | Config layer (AssessmentCfg) | Read file, encode, pass as template context variable |
| AssessmentCfg logo_path | Config layer (config.py) | Config template (yaml) | New optional dataclass field; backward-compatible default |
| DOCX generation | New Python module (docx_renderer.py) | writer.py (orchestration) | Analog to html_renderer.py; called from write_reports |
| DOCX optional-extra gating | pyproject.toml + import guard | docx_renderer.py | `try: from docx import Document except ImportError: return False` |
| DOCX content sourcing | Content model (content_model.py) | — | Same ExecContent + findings dict already consumed by HTML; no new model |

---

## Standard Stack

### Core (existing — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Jinja2 | >=3.1.0 (core dep) | HTML template rendering | Already used by html_renderer.py [VERIFIED: pyproject.toml] |
| Python dataclasses | stdlib | AssessmentCfg extension | Pattern established by all config dataclasses [VERIFIED: codebase] |
| base64 | stdlib | Logo image embedding | Standard library encode; produces data-URI body [ASSUMED] |
| mimetypes / pathlib | stdlib | Logo MIME detection from extension | Standard library [ASSUMED] |

### New Optional Extra
| Library | Version | Purpose | Why This |
|---------|---------|---------|---------|
| python-docx | >=1.1.0 | DOCX document generation | D-09 locked; only mature Python library for .docx authoring; MIT licensed [VERIFIED: npm registry] |

**Installation (optional extra):**
```bash
pip install "quirk-scanner[docx]"
```

**pyproject.toml addition:**
```toml
docx = [
    "python-docx>=1.1.0",
]
```

The `[docx]` extra is **not** added to `[all]` — DOCX is an opt-in extra following the `[identity]` / `[api]` pattern of intentional exclusion from `[all]` only when there is a policy reason. However, because python-docx has no dependency hazard (no conflicting transitive deps), it CAN be added to `[all]`. The executor should follow the pattern from CONTEXT D-09: "optional extra [docx]" — whether it joins `[all]` is Claude's Discretion and should mirror the Playwright inclusion (playwright IS in `[all]` via `[dashboard]`). Recommendation: include `[docx]` in `[all]` since it has no dep conflict, giving all-install users automatic DOCX generation.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| python-docx | docxtpl (template-based) | docxtpl requires a .docx template file to be shipped; python-docx builds from scratch — matches existing pattern and avoids template asset management |
| python-docx | HTML-to-DOCX conversion (pypandoc, mammoth) | D-10 explicitly locks against HTML→DOCX; shared content model is required |

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| python-docx | PyPI | ~12 years | Multi-million/mo | github.com/python-openxml/python-docx | [OK] (flagged classic LLM naming pattern but confirmed established) | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

slopcheck output verbatim: `> Name starts with 'python-' -- classic LLM naming pattern. Name looks like LLM bait but package is established.` — verdict [OK]. [VERIFIED: slopcheck 0.6.1]

---

## Architecture Patterns

### System Architecture Diagram

```
config.yaml (assessment.logo_path) ──→ AssessmentCfg.logo_path
                                              │
                              ┌───────────────┘
                              ↓
write_reports()               html_renderer.render_html_report()
  │                             ├── read logo file → base64 encode
  │                             ├── logo_b64 / logo_mime → template context
  │                             └── report.html.j2 renders cover + pagination CSS
  │
  │── render_pdf_report(html_path, pdf_path)   [Playwright, A4, 15/12mm margins]
  │                                             prints HTML (inherits all CSS)
  │
  └── docx_renderer.render_docx_report(path, cfg, findings, exec_content)
         │
         ├── try: from docx import Document   [optional-extra guard]
         ├── except ImportError → print advisory to stderr, return False
         │
         └── Document()
               ├── add_paragraph("[ Insert organization logo here ]")  ← logo placeholder
               ├── add_heading("QU.I.R.K. Cryptographic Readiness Report", level=1)
               ├── add_heading(org_name, level=2)
               ├── add_paragraph(metadata_line)                        ← Normal style
               ├── add_heading("Executive Summary", level=1)
               │    ├── narrative_lead paragraph
               │    ├── Heading 2: Score Decomposition  → Word table (3 cols)
               │    ├── Heading 2: Priority Business Risks → Word table (2 cols)
               │    └── Heading 2: Top Findings → Word table (4 cols)
               ├── add_heading("Findings", level=1)
               │    └── Word table (7 cols — all findings)
               ├── add_heading("Remediation Roadmap", level=1)
               │    ├── Heading 2: NOW → Word table (4 cols)
               │    ├── Heading 2: NEXT → Word table (4 cols)
               │    └── Heading 2: LATER → Word table (4 cols)
               └── add_heading("Score Breakdown", level=1)
                    └── rollup formula paragraph + Score Decomposition table
```

### Recommended Project Structure

```
quirk/
├── config.py                       # +logo_path: str | None = None on AssessmentCfg
├── config_template.yaml            # +commented-out logo_path entry in assessment: block
├── reports/
│   ├── writer.py                   # +render_docx_report call after render_pdf_report
│   ├── html_renderer.py            # +logo loading + base64 encode; pass logo_b64/logo_mime to template
│   ├── docx_renderer.py            # NEW — analog to html_renderer.py; render_docx_report()
│   └── templates/
│       └── report.html.j2          # +cover-page block; +CSS in <style>; +findings-table class
pyproject.toml                      # +docx = ["python-docx>=1.1.0"]
tests/
├── test_fmt_cover_page.py          # NEW — cover page render assertions
├── test_fmt_print_css.py           # NEW — @media print + findings-table CSS presence
├── test_docx_renderer.py           # NEW — DOCX generation, graceful-skip, structure
└── test_cross_surface_parity.py    # EXTEND — add DOCX surface to parity checks
```

### Pattern 1: Optional-Extra + Graceful Skip (mirrors render_pdf_report)

The established pattern in `html_renderer.py`:

```python
# Source: quirk/reports/html_renderer.py:295-299 [VERIFIED: codebase]
def render_pdf_report(html_path: str, pdf_path: str) -> bool:
    try:
        from playwright.sync_api import sync_playwright
        from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError
    except ImportError:
        return False
```

For docx_renderer.py, follow this exact pattern:

```python
# Source: pattern from html_renderer.py; applied to docx [CITED: CONTEXT.md D-09/D-11]
def render_docx_report(path: str, cfg: Any, findings: list, exec_content=None) -> bool:
    try:
        from docx import Document
    except ImportError:
        import sys
        print(
            "DOCX export skipped: python-docx is not installed. "
            "Install with: pip install quirk-scanner[docx]",
            file=sys.stderr,
        )
        return False
    # ... build document ...
    return True
```

Called from writer.py after line 236 (pdf render), analogous to pdf_ok:

```python
# Source: write_reports pattern from quirk/reports/writer.py [VERIFIED: codebase]
docx_path = os.path.join(outdir, f"report-{stamp}.docx")
docx_ok = render_docx_report(
    path=docx_path,
    cfg=cfg,
    findings=findings,
    exec_content=exec_content,
)
if not docx_ok:
    docx_path = None  # python-docx unavailable or generation failed
```

`docx_path` is then added to the `output_files` list (currently at writer.py:294-299), gated by `if p` (None is already filtered there).

### Pattern 2: Logo Base64 Embedding in html_renderer.py

```python
# Source: pattern derived from D-01/D-03; base64 stdlib [CITED: CONTEXT.md D-01]
import base64
import os

def _load_logo_b64(logo_path):
    """Return (b64_string, mime_subtype) or (None, 'png') when logo absent/unreadable."""
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

Then in `render_html_report`, before calling `template.render(...)`:

```python
logo_b64, logo_mime = _load_logo_b64(
    getattr(getattr(cfg, "assessment", None), "logo_path", None)
)
```

Pass `logo_b64=logo_b64, logo_mime=logo_mime` to `template.render(...)`.

### Pattern 3: python-docx Table Construction

```python
# Source: python-docx 1.2.0 API docs [CITED: python-docx.readthedocs.io/en/latest/api/table.html]
doc = Document()
tbl = doc.add_table(rows=1, cols=7)
tbl.style = 'Table Grid'
hdr_cells = tbl.rows[0].cells
for i, header_text in enumerate(["Severity", "Title", "Host", "Port",
                                   "Description", "Recommendation", "Quantum Risk"]):
    hdr_cells[i].text = header_text
for finding in findings:
    row_cells = tbl.add_row().cells
    row_cells[0].text = str(finding.get("severity", ""))
    # ... etc
```

### Pattern 4: AssessmentCfg Backward-Compatible Extension

`config_from_dict` calls `AssessmentCfg(**raw["assessment"])` at line 479. Adding a keyword argument with a default to `AssessmentCfg` is safe — existing configs that do not include `logo_path` in their YAML will use `None` by default. [VERIFIED: codebase — AssessmentCfg is a plain `@dataclass`, no `__init__` override, no extra-key stripping]

```python
# Source: quirk/config.py:11-16 [VERIFIED: codebase] + D-01 extension
@dataclass
class AssessmentCfg:
    name: str
    data_classification: str
    report_owner: str
    timezone: str
    logo_path: str | None = None   # Phase 100 / D-01 — optional path to local image file
```

**Warning:** The `conn_raw` stripping at config.py:416 (`{k: v for k, v in ... if k in _KNOWN_CONNECTOR_KEYS}`) applies only to the `connectors` block. The `assessment` block has no such filter — `AssessmentCfg(**raw["assessment"])` is called directly with no key filtering. An unknown key in the YAML `assessment:` block would crash with a TypeError. The `logo_path` key must be declared as a field on `AssessmentCfg` before any YAML includes it. The template adds it commented-out, so existing configs are safe.

### Anti-Patterns to Avoid

- **Font shrinking to fit the table:** D-06 explicitly rejects this. Use `table-layout: fixed` + column widths + `word-wrap: break-word`.
- **HTML→DOCX conversion:** D-10 locks against this. Build from ExecContent + findings dict directly.
- **Logo embedded in DOCX:** D-12 explicitly specifies a text placeholder, not an embedded image. The consultant inserts the logo manually.
- **CDN references in HTML/CSS:** D-04 bans this. All additions must go inside the existing `<style>` block.
- **New `@page` margin CSS that conflicts with Playwright call:** Playwright already passes `margin={top:15mm,bottom:15mm,left:12mm,right:12mm}`. The CSS `@page { margin: 15mm 12mm }` is belt-and-braces for direct browser printing — it must not override to different values. UI-SPEC confirms same values.
- **Eager top-level `import docx` in docx_renderer.py:** This would break the `[minimal install]` path. The import MUST be inside the `render_docx_report` function body, same as Playwright's lazy import in `render_pdf_report`. See feedback memory: `optional-extra import trap`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DOCX file format | Custom XML/ZIP writer | python-docx | .docx is a complex OOXML package; edge cases in headers, styles, table XML are handled by the library |
| Logo MIME detection | Complex magic-byte inspection | Extension lookup dict + fallback | For a logo image path the extension is reliable and matches what browsers accept in data-URIs |
| Word table styling | Raw python-docx XML manipulation | `tbl.style = 'Table Grid'` | Built-in style handles borders; raw XML is fragile across Word versions |

**Key insight:** python-docx abstracts all the Word XML complexity. The DOCX renderer is a thin adapter from the content model to python-docx calls — no custom XML, no style overrides beyond standard heading/table styles.

---

## Common Pitfalls

### Pitfall 1: AssessmentCfg Strict Keyword Construction

**What goes wrong:** `AssessmentCfg(**raw["assessment"])` raises `TypeError: __init__() got an unexpected keyword argument 'logo_path'` if a user YAML includes `logo_path` but the dataclass doesn't yet have that field.

**Why it happens:** Python dataclass `__init__` rejects unknown kwargs (unlike dict construction).

**How to avoid:** Add the `logo_path: str | None = None` field to `AssessmentCfg` in the same commit as the config_template.yaml addition.

**Warning signs:** `TypeError` at `config_from_dict` startup.

### Pitfall 2: Optional-Extra Eager Import

**What goes wrong:** `from docx import Document` at module level in `docx_renderer.py` causes an `ImportError` for any user who does `pip install quirk-scanner` without `[docx]`, making ALL reports fail to load the writer module.

**Why it happens:** Python resolves top-level imports at module load time. `docx_renderer.py` is imported by `writer.py`, which is always imported.

**How to avoid:** Keep `from docx import Document` inside `render_docx_report()` body — same pattern as `from playwright.sync_api import sync_playwright` inside `render_pdf_report()`.

**Warning signs:** `ModuleNotFoundError` on minimal install when importing `quirk.reports.writer`.

### Pitfall 3: logo_b64 None Check in Template

**What goes wrong:** Jinja2 renders `<img src="data:image/None;base64,...">` if `logo_b64` is falsy but the `{% if logo_b64 %}` guard is missing or uses wrong variable.

**Why it happens:** None is falsy in Python/Jinja2 but a data-URI with "None" as type would not display as a broken image — but `{% if logo_b64 %}` is the correct guard per UI-SPEC D-03.

**How to avoid:** Use `{% if logo_b64 %}` exactly as specified in the UI-SPEC template block. Entire `.cover-logo-region` div is inside the `{% if %}` guard.

**Warning signs:** `<img src="data:image/png;base64,">` (empty base64) or `<img src="data:image/None;base64,...">` in rendered HTML.

### Pitfall 4: write_reports Output Files List Missing docx_path

**What goes wrong:** `report-{stamp}.docx` is written to disk but not shown in the "Output files" rich table displayed to the user.

**Why it happens:** The `output_files` list at writer.py:294-299 is assembled manually; a new artifact must be added explicitly.

**How to avoid:** Add `docx_path` to the `output_files` list. The existing `if p` filter already handles the `None` case (python-docx absent).

**Warning signs:** DOCX file exists on disk but is not listed in the scan summary output.

### Pitfall 5: `<table class="findings-table">` Class Addition

**What goes wrong:** The `table-layout: fixed` CSS rule in `.findings-table` applies to all `<table>` elements if the rule targets the base `table` selector instead of the class.

**Why it happens:** Confusing the global `table` CSS rule (line 89 of report.html.j2) with the class-specific `.findings-table` rule.

**How to avoid:** CSS must use `table.findings-table { table-layout: fixed }` (class selector), and the "All Findings" `<table>` element in the template must gain `class="findings-table"`. The "Top Findings" table (4-col) is NOT a `.findings-table` — only the 7-column all-findings table needs fixed layout.

**Warning signs:** Other tables (metadata, score decomposition) render with fixed layout and unexpectedly narrow columns.

### Pitfall 6: DOCX `add_row()` on an Empty Table

**What goes wrong:** A findings table with zero findings would have no data rows. If the code calls `tbl.add_row()` inside a loop over an empty list, the table has only the header row — which is correct behavior. But if the header is also conditional, the table may be empty.

**How to avoid:** Always write the header row unconditionally. Per UI-SPEC: when no findings, add a single cell in the first data row with "No findings recorded for this scan."

---

## Code Examples

Verified patterns from official sources and codebase:

### Cover Page Jinja2 Block (verbatim from UI-SPEC)
```html
{# Source: 100-UI-SPEC.md §Cover Page Template Block — locked markup [CITED: 100-UI-SPEC.md] #}
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

**Insertion point:** first child inside `<div class="report-body">` (before line 198 in report.html.j2, which is `<!-- ===== EXECUTIVE SUMMARY ===== -->`).

### Print CSS Block (verbatim from UI-SPEC)
```css
/* Source: 100-UI-SPEC.md §HTML/CSS Additions Contract [CITED: 100-UI-SPEC.md] */
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

### DOCX render_docx_report Skeleton

```python
# Source: pattern from html_renderer.py:290-330 + python-docx API [CITED: html_renderer.py + python-docx docs]
def render_docx_report(
    path: str,
    cfg: Any,
    findings: list,
    exec_content: "ExecContent | None" = None,
) -> bool:
    """Write a DOCX report to path. Returns True on success, False if python-docx absent."""
    try:
        from docx import Document
    except ImportError:
        import sys
        print(
            "DOCX export skipped: python-docx is not installed. "
            "Install with: pip install quirk-scanner[docx]",
            file=sys.stderr,
        )
        return False

    org_name = getattr(getattr(cfg, "assessment", None), "name", "Unknown")
    report_owner = getattr(getattr(cfg, "assessment", None), "report_owner", "")
    data_classification = getattr(getattr(cfg, "assessment", None), "data_classification", "")
    from datetime import datetime, timezone
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    doc = Document()

    # Logo placeholder (D-12 — exactly this string, Normal style)
    doc.add_paragraph("[ Insert organization logo here ]", style="Normal")

    # Document title block
    doc.add_heading("QU.I.R.K. Cryptographic Readiness Report", level=1)
    doc.add_heading(org_name, level=2)
    meta_line = (
        f"Report Owner: {report_owner}  |  "
        f"Date: {generated_at}  |  "
        f"Classification: {data_classification}"
    )
    doc.add_paragraph(meta_line, style="Normal")

    # ... sections built from exec_content and findings ...

    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    doc.save(path)
    print(f"DOCX report written to {path}")
    return True
```

### writer.py Integration Point

```python
# Source: quirk/reports/writer.py:235-238 [VERIFIED: codebase] — insertion after pdf step
pdf_path = os.path.join(outdir, f"report-{stamp}.pdf")
pdf_ok = render_pdf_report(html_path=html_path, pdf_path=pdf_path)
if not pdf_ok:
    pdf_path = None

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

`render_docx_report` must be imported at the top of `writer.py` alongside `render_html_report`, `render_pdf_report`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No PDF cover page | Cover page with logo/title/org/classification/owner/date | Phase 100 | Client-ready first impression |
| 7-column findings table with no fixed layout | `table-layout: fixed` + column widths on `.findings-table` | Phase 100 | No horizontal overflow on A4 |
| No DOCX output | `report-{stamp}.docx` auto-emitted via python-docx [docx] extra | Phase 100 | Editable client deliverable |

**Deprecated/outdated:**
- None — this phase adds new capabilities, not replacements.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `base64` and `mimetypes`/`os.path.splitext` stdlib are the right tools for logo MIME detection | Standard Stack / Code Examples | Low risk — these are stdlib; fallback to "png" if ext unknown |
| A2 | `[docx]` extra should/can be added to `[all]` (no dep conflict) | Standard Stack | If python-docx conflicts with any transitive dep in [all], must remain excluded — executor should verify no conflict before adding to [all] |
| A3 | `'Table Grid'` is a valid built-in python-docx table style name | Code Examples | python-docx docs confirm built-in styles exist but exact string not verified in live venv; fallback: omit `tbl.style` line (inherits default) |

---

## Open Questions

1. **Should `[docx]` join `[all]`?**
   - What we know: `[dashboard]` (which includes playwright + pypdf) IS in `[all]`. python-docx has no known dep conflicts with the existing stack. The `[api]` and `[identity]` extras are excluded for policy/security reasons, not dep reasons.
   - What's unclear: Whether there is any preference to keep DOCX out of `[all]` (e.g., keeping binary size down).
   - Recommendation: Add to `[all]`. It matches the "all report features bundled" intent of `[all]`. If executor has concerns, can leave out and document.

2. **`pypdf` extra declaration:** `pypdf` is currently listed under `[dashboard]` (pyproject.toml line 41) but is used by `_inject_pdf_metadata` in html_renderer.py — a function that runs on every PDF. Is this correct grouping? Not a Phase 100 concern, but noting it as a pre-existing quirk.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python-docx | FMT-03 DOCX generation | Not in project venv | N/A | Graceful skip with advisory (D-11) |
| playwright | PDF generation | Part of [dashboard] extra | Not probed | Pre-existing graceful skip |
| Jinja2 | HTML template | Core dep | >=3.1.0 | None needed |
| Python base64/os stdlib | Logo embed | Always available | stdlib | None needed |

**Missing dependencies with no fallback:** None — python-docx absence is handled by graceful skip per D-09/D-11.

**Missing dependencies with fallback:** python-docx (not in project venv; must be installed via `pip install "quirk-scanner[docx]"` or added to `[all]` in pyproject.toml and reinstalled).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_fmt_cover_page.py tests/test_fmt_print_css.py tests/test_docx_renderer.py -x` |
| Full suite command | `pytest tests/ -m 'not slow and not live_infra'` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FMT-01 | Cover page block present in rendered HTML | unit | `pytest tests/test_fmt_cover_page.py::test_cover_page_in_html -x` | ❌ Wave 0 |
| FMT-01 | `logo_b64` is None when logo_path absent | unit | `pytest tests/test_fmt_cover_page.py::test_logo_absent_graceful -x` | ❌ Wave 0 |
| FMT-01 | Logo base64-embedded when logo_path set | unit | `pytest tests/test_fmt_cover_page.py::test_logo_embedded -x` | ❌ Wave 0 |
| FMT-01 | AssessmentCfg accepts logo_path field | unit | `pytest tests/test_fmt_cover_page.py::test_assessment_cfg_logo_path -x` | ❌ Wave 0 |
| FMT-01 | Existing configs (no logo_path) parse without error | unit | `pytest tests/test_fmt_cover_page.py::test_backward_compat_config -x` | ❌ Wave 0 |
| FMT-02 | `@media print` block present in rendered HTML | unit | `pytest tests/test_fmt_print_css.py::test_print_media_block -x` | ❌ Wave 0 |
| FMT-02 | `findings-table` class on All Findings table | unit | `pytest tests/test_fmt_print_css.py::test_findings_table_class -x` | ❌ Wave 0 |
| FMT-02 | `table-layout: fixed` rule in HTML stylesheet | unit | `pytest tests/test_fmt_print_css.py::test_fixed_table_layout_css -x` | ❌ Wave 0 |
| FMT-03 | DOCX written to outdir on report generation | unit | `pytest tests/test_docx_renderer.py::test_docx_written -x` | ❌ Wave 0 |
| FMT-03 | DOCX has logo placeholder paragraph | unit | `pytest tests/test_docx_renderer.py::test_logo_placeholder -x` | ❌ Wave 0 |
| FMT-03 | DOCX has correct section headings | unit | `pytest tests/test_docx_renderer.py::test_docx_section_headings -x` | ❌ Wave 0 |
| FMT-03 | DOCX has 7-column findings table | unit | `pytest tests/test_docx_renderer.py::test_docx_findings_table_cols -x` | ❌ Wave 0 |
| FMT-03 | Graceful skip when python-docx absent | unit | `pytest tests/test_docx_renderer.py::test_docx_graceful_skip -x` | ❌ Wave 0 |
| FMT-03 | DOCX skip advisory written to stderr | unit | `pytest tests/test_docx_renderer.py::test_docx_skip_advisory -x` | ❌ Wave 0 |
| FMT-03 | docx_path = None in writer when docx_ok=False | unit | `pytest tests/test_docx_renderer.py::test_writer_docx_none_on_fail -x` | ❌ Wave 0 |
| EXEC-04 | DOCX cross-surface parity (narrative_lead in DOCX) | unit | `pytest tests/test_cross_surface_parity.py -x` | ✅ existing (extend) |

### Sampling Rate
- **Per task commit:** `pytest tests/test_fmt_cover_page.py tests/test_fmt_print_css.py tests/test_docx_renderer.py -x`
- **Per wave merge:** `pytest tests/ -m 'not slow and not live_infra'`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps (all new test files)
- [ ] `tests/test_fmt_cover_page.py` — FMT-01 cover page + logo embed + config backward-compat
- [ ] `tests/test_fmt_print_css.py` — FMT-02 @media print block + findings-table class + CSS rules
- [ ] `tests/test_docx_renderer.py` — FMT-03 DOCX generation, structure, graceful skip, advisory
- [ ] `tests/test_cross_surface_parity.py` — EXTEND existing: add DOCX surface assertions alongside CLI/HTML

### Test Harness Patterns (follow existing conventions)

From `test_html_report.py` and `test_reports_writer.py`:
- Minimal cfg via `SimpleNamespace` with `assessment`, `output`, `intelligence` namespaces
- `tmp_path` pytest fixture for isolation
- `monkeypatch` + `sys.modules` patching to simulate missing optional deps (see `test_pdf_render_hardening.py` pattern for ImportError simulation)
- Read rendered HTML from file after `render_html_report()` call
- For DOCX, open rendered `.docx` with `from docx import Document; doc = Document(path)` inside the test to inspect structure

---

## Security Domain

`security_enforcement` is not explicitly `false` in config.json, so this section is required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surfaces touched |
| V3 Session Management | no | No session surfaces touched |
| V4 Access Control | no | No access control surfaces touched |
| V5 Input Validation | yes | `sanitize_scanner_text` filter already applied to all user-supplied strings in Jinja2 template; extend to cover-page new vars (org_name, report_owner, data_classification already sanitized at existing meta-table; cover page uses same vars, same `\| sanitize` filter) |
| V6 Cryptography | no | No crypto operations added |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via logo_path filename or image contents | Tampering | logo_b64 is the base64-encoded image bytes — no HTML rendered from the path. The `alt` attribute uses `org_name \| sanitize` which is already sanitized. Logo data in data-URI is binary-safe. |
| Path traversal via logo_path | Information Disclosure | `open(logo_path, "rb")` with try/except OSError; no directory traversal artifact produced — file is read once and encoded. The path comes from operator-controlled config, not user input. |
| Cover-page injection via config strings | Tampering | All cover-page Jinja2 variables (org_name, report_owner, data_classification) already pass through `\| sanitize` filter in the template. The `generated_at` value is produced by `datetime.now().strftime(...)` — not user input. |
| DOCX macro injection | Tampering | python-docx builds DOCX from structured API calls (paragraphs + tables), not from raw XML or user-supplied template files. No macro execution surface introduced. |

---

## Sources

### Primary (HIGH confidence)
- `quirk/reports/writer.py` — confirmed `write_reports` structure, exec_content scope, output files list, insertion point for DOCX
- `quirk/reports/html_renderer.py` — confirmed `render_html_report` signature + all template context keys, `render_pdf_report` pattern for graceful skip
- `quirk/reports/templates/report.html.j2` — confirmed `<style>` block ends at line 186, `report-body` div at line 195, executive-summary section at line 198, all-findings table at line 358 (no `findings-table` class yet), generated_at format
- `quirk/reports/content_model.py` — confirmed ExecContent fields, RoadmapItem fields, RiskItem fields, build_exec_content signature
- `quirk/config.py` — confirmed AssessmentCfg fields (name, data_classification, report_owner, timezone), config_from_dict calls `AssessmentCfg(**raw["assessment"])` directly (no key filter)
- `pyproject.toml` — confirmed extras structure, playwright in [dashboard] in [all], no docx extra yet
- `100-CONTEXT.md` — locked decisions D-01..D-12
- `100-UI-SPEC.md` — locked markup, CSS, copywriting strings, template blocks, DOCX structure

### Secondary (MEDIUM confidence)
- python-docx 1.2.0 official docs (readthedocs.io) — Document(), add_heading(), add_paragraph(), add_table(), add_row(), cells, save() API [CITED: python-docx.readthedocs.io/en/latest/api/document.html]
- slopcheck 0.6.1 — python-docx passes legitimacy check [VERIFIED: slopcheck]
- pip index versions python-docx — 1.2.0 is current [VERIFIED: PyPI via pip]

### Tertiary (LOW confidence)
- `'Table Grid'` style name for python-docx — from training knowledge + pattern from community examples [ASSUMED: A3]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified in codebase and registry
- Architecture: HIGH — exact insertion points and signatures verified from live source
- Pitfalls: HIGH — derived from direct code reading and established patterns
- python-docx API: MEDIUM — verified via official readthedocs docs; live execution not possible in project venv (python-docx not yet installed there)

**Research date:** 2026-05-24
**Valid until:** 2026-06-24 (30 days; stable stack — python-docx, Jinja2, html/css are stable)
