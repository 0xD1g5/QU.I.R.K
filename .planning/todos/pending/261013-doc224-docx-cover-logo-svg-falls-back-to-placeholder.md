---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §24 branding)
priority: low
area: quirk/reports/docx_renderer.py (cover logo)
status: pending
resolves_phase: null
owner: "999.132"
---

# An SVG branding logo shows on the HTML/PDF cover but falls back to the placeholder in DOCX

`report.branding.logo_path` accepts SVG (`quirk/reports/html_renderer.py:181` maps `svg` to `svg+xml`), so the
HTML/PDF cover shows it. python-docx cannot embed SVG: `doc.add_picture` (`quirk/reports/docx_renderer.py:461`) raises,
and the fallback prints "[ Insert organization logo here ]" (`:470`). Probe `gc3-r3-f6-svg-logo-probe.py`.

When fixed, update docs/report-interpretation.md §24 DOCX row of the branding table.

## Feasibility & Effort

- **Verdict: CONFIRMED, effort S-M.** `html_renderer.py:181`; `docx_renderer.py:461,470`.
- Options: rasterise SVG for DOCX (resvg-py is only a dev pin today, so a runtime dependency decision for the operator) or warn at config load that SVG logos do not reach DOCX.
