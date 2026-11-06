---
type: todo
created: 2026-11-05
title: Report sections per enabled connector (S3, JWT, SAML, Vault, ...)
source: operator feature request, 2026-11-05 full chaos-lab GUI scan (5.28.1)
priority: medium
area: quirk/reports/content_model.py, quirk/reports/html_renderer.py, quirk/reports/docx_renderer.py, quirk/reports/coverage.py, src/dashboard/src/pages/print*.tsx
status: pending
resolves_phase: null
owner: null
---

# Report sections per enabled connector

## Request (operator, verbatim intent)

"In the reporting it would be nice if we could also add sections that correspond to each enabled config.
For example a S3 section and all hosts or findings are in that section. Same for JWT, SAML, etc. It is
duplicative but clearly shows the details."

So: for every connector the scan had **enabled**, the report gets its own section listing that connector's
hosts/endpoints and the findings on them. Duplication with the severity-ordered findings list is accepted and
intended. The point is a per-surface audit view ("what did the S3 check see?").

## Why it matters (observed the same night)

The 2026-11-05 GUI scan had JWT, SAML and S3 enabled. All three phases recorded `status: ran` and wrote **zero
endpoint rows** (JWT in 2 ms, SAML in 1 ms), because the dashboard job ran with
`security.allow_internal_targets: false` and the URL guard refused every localhost target without an error
(see `261105-connector-phase-ran-with-zero-output-when-url-guard-refuses-all-targets.md`). A per-connector
section that says "enabled, ran, 0 endpoints, 0 findings" would have made that visible in the report at a
glance. Today only the Scan Coverage chips mention the phase, and they read "ran".

## What exists to build on

- **Grouping key on endpoints:** every scanner stamps `crypto_endpoints.protocol` (S3, JWT, SAML, VAULT,
  ADCS, SMIME, DNSSEC, POSTGRESQL, MYSQL, KAFKA-TLS, KAFKA-PLAIN, AMQPS, REDIS-TLS, CONTAINER, SOURCE, ...).
  This needs a protocol -> connector map (e.g. KAFKA-*/AMQP*/REDIS-* -> Broker; POSTGRESQL/MYSQL -> Database).
- **Enabled/ran/skipped per connector:** `scan_phase_records` (phase_name, status, reason, detail,
  duration_sec) already has one row per connector phase, and `quirk/reports/coverage.py:38` maps phase names
  to labels ("jwt_scanning" -> "JWT"). Each section can open with that status line.
- **Findings do NOT carry provenance:** in `findings-*.json` `check_id` is `""` on all 116 rows and there is
  no `protocol` field. Attributing a finding to a connector needs either a join on `(host, port)` to the
  endpoint rows (fragile: e.g. container findings use `port: 0` and a `host` that is an image ref), or plumbing
  a `source_connector`/`protocol` field from the rule that emits the finding (cleaner).
- **Two report pipelines** (memory: TWO report pipelines): the HTML/PDF/DOCX writer and the dashboard's
  Export PDF (`/print` page). Both need the section, or the request is only half met. Render-parity tests
  check presence, not appearance (memory: report render tests assert presence).

## Open design questions

- Which connectors count: only `enable_*` true, or also always-on phases (TLS, SSH, PQC probe)? The request
  says "each enabled config", which suggests the connector toggles; TLS/SSH would be very long sections.
- Placement: an appendix ("Connector detail") after the findings, so the executive flow is not diluted.
- Endpoint rows that are not findings (S/MIME, S3 per 999.132) belong in the section; that is part of the value.
- Empty connector: still render the section with "enabled, ran, 0 endpoints". Never omit it; omitting
  is exactly the invisibility problem above.

## Feasibility & Effort

**FEASIBLE.** The endpoint grouping key and the per-phase status already exist. The hard part is finding
attribution. **Effort M-L**:
- S: protocol -> connector map + per-connector endpoint tables + phase status line in the HTML writer.
- M: plumb provenance onto findings (touches the finding emitters and `findings-*.json`), plus the DOCX renderer.
- M: the `/print` dashboard pipeline, parity tests, `docs/report-interpretation.md` (new report section
  row in the CLAUDE.md doc checklist), UAT cases.
Fits as one phase in a post-5.28 milestone. Not a 5.28.x patch item.
