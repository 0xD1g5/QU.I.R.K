---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §10.9 Partial re-probe banner)
priority: low
area: quirk/dashboard/api/schemas.py (HardwareFinding), src/dashboard/src/pages/hardware.tsx
status: pending
resolves_phase: null
---

# Dashboard /hardware device table cannot mark check-in-sourced rows

The reports flag check-in-sourced device rows with the Partial re-probe banner, but the dashboard device table
cannot: `HardwareFinding` (`quirk/dashboard/api/schemas.py:316`) has no `is_partial_scan` field (only
`HardwareDriftEventItem` has it, `:381`). The projection builds `HardwareFinding` at
`quirk/dashboard/api/routes/scan.py:898` from rows that do carry `is_partial_scan` (`quirk/models.py:609`), and
`hardware.tsx` never references it. A check-in device's last-known-good row looks like a full-scan row; only drift rows
get the badge.

When fixed, update docs/report-interpretation.md §10.9 banner paragraph ("the `/hardware` device table carries no check-in marker").

## Feasibility & Effort

- **Verdict: LIKELY, effort S.** `schemas.py:316` vs `:381`; `scan.py:898`; `models.py:609`; no `is_partial_scan` in `src/dashboard/src/pages/hardware.tsx`.
- Fix: add the field and a badge/banner mirroring the report (`quirk/reports/html_renderer.py:433` comment).
