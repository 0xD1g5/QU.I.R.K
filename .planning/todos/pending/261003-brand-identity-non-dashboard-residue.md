---
type: todo
created: 2026-10-11
source: 261001-adopt-pqc-brand-identity (residue at Phase 223 close)
priority: low
area: CLI, reports, GitHub, release packaging
status: pending
resolves_phase: null
---

# Brand identity: non-dashboard residue

**Owner phase:** unassigned

Left over from 261001 when the dashboard work closed in Phase 223. Each item is cited in
`223-CONTEXT.md` Deferred Ideas.

- [ ] CLI accent `#3b9dff` in `quirk/reports/writer.py` and `quirk/cli/init_cmd.py:15`, and an optional ASCII
      lens-as-Q in `quirk/cli/banner.py` (terminal UI colours; CLI rebrand deferred at the v5.27 kickoff).
- [ ] Report palette `--accent #3b9dff` in `quirk/reports/templates/report.html.j2` and the `<summary>` colour
      in `quirk/reports/html_renderer.py` (~:431). This is the report palette, not the logo.
- [ ] GitHub social preview PNG (1280x640) from `docs/brand/quirk-hero-dark.svg`. Manual repo setting;
      candidate for Phase 225/226. The raster pipeline makes it one command.
- [ ] Windows sensor installer `.ico` (`packaging/windows/`) only if an executable wrapper ships.
- [ ] apple-touch-icon / PWA manifest icons (new capability, not in BRAND-03).
