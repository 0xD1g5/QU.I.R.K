---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger row DCL-GETSTARTED-0069
priority: medium
area: quirk/dashboard/api/routes/reports.py, quirk/dashboard/api/routes/jobs.py, src/dashboard/src/pages/executive.tsx
status: pending
resolves_phase: null
owner: "999.121"
---

# GUI-first: report downloads on the home page cannot see reports from dashboard-started scans

**Owner phase:** unassigned (related to HORIZON 999.121, sibling of `261012-gui-first-per-scan-report-download.md`)

Found while verifying `docs/getting-started.md` for the dashboard-first quickstart (D-16). In an empty
directory, `quirk serve`, then POST `/api/jobs` for `127.0.0.1` (or the New Scan form): the job completes and
writes `report-*.html/pdf/docx` and `cbom-*.cdx.{json,xml}` to `output/jobs/<job-id>/`, but
`GET /api/reports/latest/manifest` answers every format `available:false, reason: "No scan has run yet."`, so
the report download buttons on the home page stay greyed out for the very scans the dashboard just ran.

Cause: the manifest and download routes resolve the directory from `QUIRK_CONFIG_PATH` or `./config.yaml`
(`quirk/dashboard/api/routes/reports.py:129-131`), while each dashboard job writes to its own
`output/jobs/<job-id>/` directory (`quirk/dashboard/api/routes/jobs.py:637-639`, config at `jobs.py:298-300`).
A CLI scan in a directory with a `config.yaml` works: the same routes serve its reports (HTTP 200
`application/pdf`).

Documentation was narrowed to match (section 4 of `getting-started.md`); nothing in code was changed (D-10).

- [ ] Decide the fix: make `_output_directory()` / the manifest consider `output/jobs/*/` (newest job), or have
      the job write its reports under the configured output directory.
- [ ] Dependency: the per-scan report association spike in `261012-gui-first-per-scan-report-download.md`
      (artifacts are stamped with render time, not `scan_run_id`).
- [ ] When fixed, revert the "These buttons do not list reports from scans started with New Scan" sentence in
      `docs/getting-started.md` section 4 and regenerate `docs/quirk-master-guide.md`.

## Feasibility & Effort

**CONFIRMED** defect (reproduced live 2026-10-12; `reports.py:129-131` reads `./config.yaml`, `jobs.py:639`
returns `output/jobs/<id>`). Effort **M**: the directory change itself is small, but choosing between "newest
job dir" and "write to configured output dir" interacts with scan history and the missing scan-to-report
association. Unknowns: whether scheduled scans (not checked) share this output layout and should land in the
same place, and the interaction with `QUIRK_CONFIG_PATH` in deployed consoles. **Spike first** (half a day) on
the shared association question before implementing.
