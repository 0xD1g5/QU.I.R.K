---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §10 (PDF note) and §26 format table)
priority: medium
area: quirk/reports/html_renderer.py (render_hardware_section, render_pdf_report)
status: pending
resolves_phase: null
owner: "999.130"
---

# PDF report prints the Hardware PQC Advisory section collapsed: heading only, no device table or caveats

The HTML hardware section is a `<details>` block with no `open` attribute (`quirk/reports/html_renderer.py:443`).
`render_pdf_report` prints the HTML with JavaScript disabled (`:1382-1383` `java_script_enabled=False`, `:1389`
`page.pdf(`), and no print CSS expands `<details>`. The PDF therefore carries only the summary line: no device
table, SNMP/Modbus/BACnet/Bridge/CVE columns, or bridge/abort/staleness caveats. Probe
`gc3-r3-f2-hw-render-surfaces-probe.py` (full write_reports report, three devices): PDF contains 'Hardware PQC
Advisory' True, 'Catalyst 9300' False, '10.0.1.2' False, 'CVE-2017-16744' False. The doc now documents this as
current behaviour.

When fixed, update docs/report-interpretation.md §10 "The PDF shows the hardware section collapsed" note, the §10 surface lists that dropped PDF, and the §26 PDF format row.

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S.** `html_renderer.py:443` (details, no open); `:1383` (JS off); `:1389` (page.pdf). Only one `<details` in the renderer.
- Fix: emit `<details open>` (or a print stylesheet `details{display:block}` plus summary handling); rerun the PDF probe.
- Unknown: whether the collapsed default is wanted in the interactive HTML; `open` changes that too.
