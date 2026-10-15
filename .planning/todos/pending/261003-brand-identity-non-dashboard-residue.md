---
type: todo
created: 2026-10-11
source: 261001-adopt-pqc-brand-identity (residue at Phase 223 close)
priority: low
area: CLI, reports, GitHub, release packaging
status: pending
resolves_phase: 232
---

# Brand identity: non-dashboard residue

**Owner phase:** unassigned

Left over from 261001 when the dashboard work closed in Phase 223. Each item is cited in
`223-CONTEXT.md` Deferred Ideas.

- [ ] CLI accent `#3b9dff` in `quirk/reports/writer.py` and `quirk/cli/init_cmd.py:15`, and an optional ASCII
      lens-as-Q in `quirk/cli/banner.py` (terminal UI colours; CLI rebrand deferred at the v5.27 kickoff).
- [ ] Report palette `--accent #3b9dff` in `quirk/reports/templates/report.html.j2` and the `<summary>` colour
      in `quirk/reports/html_renderer.py` (~:431).
- [ ] **HTML report header wordmark** — `quirk/reports/templates/report.html.j2:325` still renders a typed
      `<span class="wordmark">QU.I.R.K.</span>` styled (lines ~46-51) in `var(--accent)` (`#3b9dff`) monospace,
      i.e. the old electric-blue wordmark, not the brand logo. Found by the Phase 223 verifier (2026-10-12);
      the dashboard does not serve this report, so Phase 223 criterion 5 ("no served surface") holds, but a
      repo-wide grep finds it. Operator accepted it as out of Phase 223 scope and re-homed it here. An earlier
      wording of this todo called the report item "the report palette, not the logo" — that was wrong.
- [x] GitHub social preview PNG (1280x640) from `docs/brand/quirk-hero-dark.svg`. Manual repo setting;
      candidate for Phase 225/226. The raster pipeline makes it one command.
      DONE: generated in Phase 226 plan 03 as docs/brand/quirk-social-preview.png; uploaded in plan 11.
- [ ] Windows sensor installer `.ico` (`packaging/windows/`) only if an executable wrapper ships.
- [ ] apple-touch-icon / PWA manifest icons (new capability, not in BRAND-03).
