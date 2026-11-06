---
type: todo
created: 2026-11-05
source: operator request on 2026-11-05 ("how can we save these scans and settings so I can rerun them later"), 5.28.1 full chaos-lab GUI scan
priority: medium
area: src/dashboard/src/pages/scan-history.tsx, src/dashboard/src/pages/scan-new*.tsx, quirk/dashboard/api/routes/jobs.py
status: pending
resolves_phase: null
owner: "999.121"
---

# GUI-first: Scan History "Clone" re-creates only target, profile and calibration

## Problem

The operator wanted to save a full dashboard scan and re-run it later (and record it for conference talks).
The dashboard has no way to do that:

- **Clone** in Scan History (`scan-history.tsx:42-49`, `handleClone`) navigates to `/scan/new` with only
  `target`, `profile` and `calibration` in the query string. The Custom port list (38 ports on 2026-11-05) and
  every Connectors-panel toggle and target list (JWT, container, SAML, DNSSEC, S/MIME, AD CS, Postgres, MySQL,
  broker, S3, Vault, SNMP, Modbus, BACnet) are lost, so the operator must retype them.
- The settings are already saved, though: each dashboard job writes its full effective config to
  `output/jobs/<job-id>/config.yaml` (117 lines for that scan, credentials stripped). Nothing in the UI reads it back.
- There is no saved-scan or preset concept for user-defined scans. Vertical presets (§2.3) are fixed per edition.
  `quirk scheduler` has only `run`; schedules are not created from a past job.

The workaround used on 2026-11-05 was an external demo kit: a copy of the job `config.yaml`, a paste-ready
cheat sheet for the New Scan form, and CLI `quirk --config` re-runs.

## Fix shape

- **Clone from the job's stored config:** have Clone (or a new "Re-run with same settings") load
  `output/jobs/<id>/config.yaml` through an API route and pre-fill the whole form: ports, connectors and
  their targets, and the Advanced fields. Credentials stay excluded by design; the form already re-prompts
  with masked fields, so state that in the UI.
- Optional: "Save as preset" on the New Scan page, and "Download config" on the job page (a redacted YAML that
  `quirk --config` accepts, with credential placeholders).
- Reconstructed sessions (`profile === null`, the amber notice) have no job config; keep today's behaviour there.

## Feasibility & Effort

**CONFIRMED** gap (read from `scan-history.tsx` on 2026-11-05; the job `config.yaml` exists and is complete).
**Effort S-M**: a read-only API route for the stored job config, plus mapping its YAML into the form state
(the Effective config panel already maps the form into config, so the reverse mapping has a reference), plus
vitest coverage and a UAT case. "Save as preset" would be M, because it needs persistence.
