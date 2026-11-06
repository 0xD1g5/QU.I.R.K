---
type: todo
created: 2026-11-05
title: Dashboard parity for every config setting the docs tell an operator to set
source: operator requirement, 2026-11-05 ("any configs we suggest for .yaml need to be in the dashboard for parity")
priority: high
area: quirk/dashboard/api/routes/jobs.py, quirk/util/server_config.py, quirk/dashboard/api/schemas.py, src/dashboard/src/components/ConnectorsPanel.tsx, src/dashboard/src/pages/*
status: pending
resolves_phase: null
owner: "999.121"
---

# Dashboard parity for every config setting the docs tell an operator to set

## Requirement (operator)

QUIRK is dashboard-first and CLI-complete. Any `config.yaml` setting that the docs, a runbook or support
guidance tell an operator to set must be settable from the dashboard too, or carry a written reason why it is
server-policy only. PARITY-01..09 (v5.21/v5.22) covered connector toggles, target lists, credentials and
Advanced scan fields. Tonight's guidance found what they did not cover.

## Gaps found 2026-11-05 (read from source)

1. **`security.allow_internal_targets` / `security.trusted_targets`** are server policy only
   (`jobs.py:862-867` takes them from `QUIRK_CONFIG_PATH` / `./config.yaml`; client values are dropped). That is
   the right security boundary: a scan submitter must not be able to point the server at internal hosts (SSRF).
   But there is **no dashboard surface at all**. The operator must hand-edit a YAML file next to wherever
   `quirk serve` was started, and nothing tells them so. The Effective config panel shows the value; nobody opens it.
2. **`security.allow_cleartext_broker_probe` and `security.allow_insecure_jwks` cannot be enabled for a
   dashboard scan by any route.** The job YAML's `security` block carries only `allow_internal_targets`
   (`jobs.py:307-309`, plus `trusted_targets`), and `ServerSecurity` has only those two fields
   (`server_config.py:139-142`). The CLI flags `--allow-cleartext-broker-probe` / `--allow-insecure-jwks` have
   no dashboard equivalent, not even server-side.
3. **Cloud credentials for S3-compatible endpoints** (MinIO, moto, on-prem object stores): the form has
   `aws_profile`, `aws_region`, `aws_endpoint_url`, but no access key/secret. The only path is the
   environment of the `quirk serve` process. Without it S3 "runs" and finds nothing (see the critical todo).
4. **Re-using saved settings:** Clone drops ports and connectors (`261105-dashboard-scan-history-clone-drops-ports-and-connectors.md`).
5. **Credentials re-typed on every scan** (by design, never persisted). Consider server-side secret
   *references* (env var name, Vault path) that the form can select without the value ever reaching the browser.

## Fix shape

- An **admin-only Server settings page** (behind `QUIRK_API_TOKEN`, audited) that reads and writes the server
  policy block: `allow_internal_targets`, `trusted_targets`, `allow_cleartext_broker_probe`,
  `allow_insecure_jwks`, with the SSRF trade-off stated beside each switch. Never in the per-scan form.
- Thread `allow_cleartext_broker_probe` / `allow_insecure_jwks` through `ServerSecurity` into the job YAML.
- New Scan warns when targets or connector URLs are loopback/RFC1918 and the server policy refuses them.
- S3-compatible access key/secret as request-scoped masked credentials (same model as PARITY-03), or a
  documented "set these in the serve environment" note in the panel.
- **A standing gate (the real fix for drift):** a run-time test that walks every `dataclasses.fields()` of
  `ScanCfg`, `ConnectorsCfg`, `SecurityCfg`, `TargetsCfg`, `OutputCfg`, `AssessmentCfg` and requires one
  disposition each: `form`, `server-admin`, or `cli-only: <reason>`, like `CONNECTOR_HOST_FIELD_DISPOSITION` in
  `quirk/util/target_trust.py`. A new config key then cannot ship without a parity decision. (A naive grep of
  the dashboard source is not this gate: the form builds connector keys at run time from
  `/api/connectors/availability`, so string-absence is a false negative.)

## Feasibility & Effort

**CONFIRMED** gaps 1-3 from source on 2026-11-05 (lines cited). **Effort M-L**: the disposition gate is S,
threading the two security flags is S, the admin Server settings page is M (auth, persistence of
`config.yaml`, audit, tests, UAT, docs), and credential references are M. Coordinate with
`261105-unscanned-surfaces-inflate-score-in-real-engagements.md`, whose interim doc item depends on item 1.
