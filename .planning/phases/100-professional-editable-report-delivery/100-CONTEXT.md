# Phase 100: Professional & Editable Report Delivery - Context

**Gathered:** 2026-05-24
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous)

<domain>
## Phase Boundary

Make the exported PDF a client-ready deliverable and add an editable DOCX export
— the final v5.2 milestone phase (time-boxed, must not gate the already-shipped
must-ship core per v5.2-D-04).

**In scope:**
- FMT-01: Professional PDF layout — branded cover page with a configurable logo
  region, clean section hierarchy (executive summary, findings, remediation
  roadmap, score breakdown), consistent typography/branding.
- FMT-02: Clean PDF pagination — tables/headings render with no overflow,
  truncation, or broken pagination; no table split mid-row; no orphan headers.
- FMT-03: Editable DOCX export — opens in Word/Google Docs with sections,
  headings, and tables intact, derived from the SAME content model as CLI/HTML/PDF.

**Out of scope:**
- New report content (executive narrative shipped Phase 98; per-finding context
  shipped Phase 99). This phase is presentation/formatting + a new output artifact.
- New scanner detection capabilities.
- Changing the canonical scoring engine or content model semantics.

</domain>

<decisions>
## Implementation Decisions

### PDF Cover Page & Branding (FMT-01)
- **D-01:** Logo source is a new `assessment.logo_path` config key (path to a
  local image file). The image is base64-embedded into the HTML at render time so
  the PDF/HTML stays fully self-contained and offline (honors the existing no-CDN /
  offline guarantee in render_pdf_report, which runs Chromium with JS disabled +
  offline=True).
- **D-02:** Cover page contains: logo region (top), report title, organization
  name (`assessment.name`), a data-classification banner (`assessment.data_classification`),
  scan date, and report owner (`assessment.report_owner`).
- **D-03:** When `logo_path` is absent or unreadable, degrade gracefully — omit
  the logo region and show the organization name; never render a broken-image box
  or a placeholder box.
- **D-04:** Reuse the existing embedded design tokens (new-york / zinc, the
  cssVariables already in report.html.j2's `<style>` block) plus add print-specific
  `@page` / section CSS. Introduce NO new fonts and NO external stylesheets
  (offline constraint). Branding stays within the existing inlined `<style>` block.

### PDF Pagination & Table Integrity (FMT-02)
- **D-05:** Apply `break-inside: avoid` to table rows and `break-after: avoid` to
  section headings so no table splits mid-row and no heading is orphaned at a page
  bottom.
- **D-06:** The wide findings table (7 columns incl. Quantum Risk from Phase 99)
  uses a fixed `table-layout` with explicit column widths and cell word-wrap so it
  always fits A4 width — no horizontal overflow or truncation. Do NOT shrink the
  font to fit (rejected alternative).
- **D-07:** The cover page occupies its own page (`break-after: page`); major
  sections (executive summary, findings, remediation roadmap, score breakdown)
  start cleanly.
- **D-08:** Table headers repeat across page breaks via
  `thead { display: table-header-group }`.

### DOCX Export (FMT-03)
- **D-09:** Use `python-docx` as an OPTIONAL extra (e.g. `[docx]`), with graceful
  degradation when the library is absent — mirrors the existing optional-extra
  pattern for pypdf/playwright (PDF already degrades gracefully if Playwright is
  missing). Zero-new-core-dep preference is relaxed for this genuinely new output
  format, but kept out of the minimal install.
- **D-10:** The DOCX is built directly from the shared `exec_content`
  (`build_exec_content`) + findings dict / `IntelligenceReport` content model that
  already drives CLI/HTML/PDF — a single content pipeline, NOT an HTML→DOCX
  conversion and NOT a hand-assembled parallel document (locks v5.2-D-07; inherits
  EXEC-04 / TRANS-03 cross-surface consistency by construction).
- **D-11:** The DOCX is auto-emitted on EVERY report generation, alongside the
  HTML/PDF artifacts inside `write_reports` (`report-{stamp}.docx`) — user
  decision: DOCX generation happens every time a report is generated, not behind an
  opt-in flag. If `python-docx` is unavailable, skip gracefully with an advisory
  (same pattern as the PDF Playwright fallback) and continue.
- **D-12:** DOCX fidelity is STRUCTURAL, not pixel-matched: cover / executive
  summary / findings / remediation roadmap / score breakdown sections, with Word
  headings (Heading 1/2 styles) and native Word tables, using editable default
  styles. Include a clearly-marked logo placeholder (e.g. a labelled paragraph the
  consultant replaces) rather than embedding the configured logo — the consultant
  inserts the logo and edits narrative text before final client handoff.

### Claude's Discretion
- The exact `@page` margin tuning and column-width percentages for the findings
  table (within the "fits A4, no overflow" acceptance bar).
- The `[docx]` extra's exact name and whether DOCX generation lives in a new
  `quirk/reports/docx_renderer.py` module (analog to html_renderer.py) — follow
  PATTERNS.md / the html_renderer.py structure.
- Cover-page visual arrangement details within the locked content set (D-02).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/reports/writer.py::write_reports(cfg, endpoints, findings, ...)` — the
  single report orchestrator. Builds `exec_content` via `build_exec_content`, then
  renders tech markdown, exec markdown, HTML, and PDF to a timestamped outdir. The
  DOCX emit (D-11) slots in here after the PDF step.
- `quirk/reports/html_renderer.py::render_html_report(...)` and
  `render_pdf_report(html_path, pdf_path)` — PDF is HTML printed via headless
  Chromium (JS disabled, offline, A4, 15/12mm margins). All FMT-01/02 layout is
  CSS/template work in report.html.j2; PDF inherits automatically.
- `quirk/reports/templates/report.html.j2` — the single HTML template + embedded
  `<style>` block. Cover-page markup + print CSS land here.
- `quirk/reports/content_model.py::build_exec_content` / `ExecContent` — the shared
  content model the DOCX exporter consumes (D-10).
- `quirk/config.py::AssessmentCfg` (name, report_owner, data_classification,
  timezone) — extend with `logo_path` (D-01); also `quirk/config_template.yaml`
  `assessment:` block.

### Established Patterns
- Optional-extra + graceful degradation: `render_pdf_report` returns False when
  Playwright is absent rather than crashing — the DOCX renderer follows this exact
  pattern (D-09/D-11).
- All report formats are written on every scan run (no per-format flag today) — so
  auto-emitting DOCX (D-11) matches existing behavior.
- Self-contained/offline artifacts: HTML inlines all CSS, no CDN; PDF runs offline.
  Logo must be embedded, not linked (D-01).

### Integration Points
- `write_reports` outdir + `report-{stamp}.*` naming — DOCX joins as
  `report-{stamp}.docx`.
- `AssessmentCfg` construction in `config.py` (`assessment=AssessmentCfg(**raw["assessment"])`)
  + `config_template.yaml` — the new `logo_path` key threads through here (make it
  optional with a safe default so existing configs don't break).

</code_context>

<specifics>
## Specific Ideas

- DOCX every time: the user explicitly wants DOCX produced on every report
  generation (D-11), not opt-in.
- "Hand the file to a CISO without visual apology" is the FMT-01 acceptance bar;
  "every row fully readable, no table split mid-row" is the FMT-02 bar; "opens in
  Word and Google Docs with structure intact, consultant can insert a logo and edit
  narrative" is the FMT-03 bar.
- This phase is time-boxed and is the deferral candidate if scope pressure arises
  (v5.2-D-04) — but no pressure currently; all prior phases shipped.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (DOCX styling beyond structural
fidelity, and any logo auto-embedding into DOCX, are intentionally left to the
consultant per D-12.)

</deferred>

---

*Phase: 100-professional-editable-report-delivery*
*Context gathered: 2026-05-24 via smart discuss (autonomous)*
