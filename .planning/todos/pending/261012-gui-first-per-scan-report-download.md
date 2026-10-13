---
type: todo
created: 2026-10-12
source: GUI-first repositioning (operator, 2026-10-12); HORIZON 999.121
priority: medium
area: quirk/dashboard/api/routes/reports.py, src/dashboard/src/pages/scan-history.tsx
status: pending
resolves_phase: null
---

# GUI-first: the dashboard can only download reports for the LATEST scan

**Owner phase:** unassigned (HORIZON 999.121, sub-item 3)

`GET /reports/latest/{fmt}` (`quirk/dashboard/api/routes/reports.py:155-185`) picks the newest stamp in
the output dir. The consulting-grade HTML/PDF/DOCX for an earlier scan exists on disk, but scan
history cannot download it. A consultant with several engagements has to go to the filesystem.

- [ ] Spike first: report artifacts are stamped with render time, not `scan_run_id`, so no
      scan→report association exists yet. Decide how to record one (run-stats file? DB column?).
- [ ] Then add a per-scan route plus download buttons on scan history. Keep Bearer-header auth in mind:
      a plain `<a download>` 401s when a token is set.

## Feasibility & Effort

**CONFIRMED** gap (`quirk/dashboard/api/routes/reports.py:155-185` selects the latest stamp only). Effort **M**. Main unknown: no scan↔report association exists. **Spike first.** Full analysis: `.planning/backlog/999.121-gui-first-transition/IDEA.md`.
