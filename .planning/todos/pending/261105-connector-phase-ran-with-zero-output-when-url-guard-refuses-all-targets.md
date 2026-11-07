---
type: todo
created: 2026-11-05
title: Connector phase reads "ran" with zero output when the URL guard refuses every target
source: 2026-11-05 full chaos-lab GUI scan (5.28.1), reproduced by direct call
priority: high
area: quirk/scanner/jwt_scanner.py, quirk/scanner/saml_scanner.py, quirk/util/url_allowlist.py, quirk/reports/coverage.py, quirk/dashboard/api/routes/jobs.py
status: pending
resolves_phase: "235.3"
owner: null
---

# Connector phase reads "ran" with zero output when the URL guard refuses every target

## Observed

A dashboard New Scan of `127.0.0.1` with JWT (`http://localhost:20001..20004`), SAML
(`http://localhost:8080/simplesaml/saml2/idp/metadata.php`) and S3 (`http://localhost:29000`) enabled. The lab
endpoints answered (`/.well-known/jwks.json` 200, SAML metadata 200). `scan_phase_records`:

| phase | status | duration | endpoint rows |
|---|---|---|---|
| jwt_scanning | ran | 0.002 s | 0 |
| saml_scanning | ran | 0.001 s | 0 |
| s3_scanning | ran | 2.113 s | 0 |

## Cause (confirmed for JWT)

The job config had `security.allow_internal_targets: false`. That is by design: `jobs.py:862-867` takes it only
from the server's `QUIRK_CONFIG_PATH` / `./config.yaml`, and `quirk serve` had been started in a directory with
none. `scan_jwt_targets(["http://localhost:20001","http://localhost:20004"])` returns `[]`, and with
`allow_internal=True` returns 2 JWT endpoints. `validate_external_url(..., allow_internal=...)`
(`jwt_scanner.py:313`, `:339`) refuses the URL and the scanner moves on with no row, no error and no skip.
SAML uses the same guard (`saml_scanner.py`). S3 not yet traced.

Meanwhile TLS against `127.0.0.1` in the same job worked, so the operator sees a plausible, partly populated
scan with three connectors quietly reading clean.

## Why it matters

This is the CR-02 class again (5.28.1 fixed it for a missing semgrep/syft binary): a configured surface that
did not run reads as if it ran clean. Scan Coverage shows "ran". The score has no way to know.

## Fix shape

- When the guard refuses **every** target of a connector, record the phase as `skipped` with a reason such as
  `internal-target-refused` (detail: which targets, and that `security.allow_internal_targets` is server
  policy), and count it like the other skip reasons. Partial refusal: `ran` plus a disclosed per-target note.
- Dashboard: the New Scan form could warn when targets/connector URLs are loopback/RFC1918 and the server
  policy is false (the Effective config panel already shows the Security block, but nobody opens it).
- Audit every `validate_external_url` caller in scanners (jwt, saml, openapi, rest_fuzzer) and the S3 path
  for the same silent drop.
- Docs: `docs/operators-guide.md` §3.0 should say that scanning internal targets from the dashboard needs
  `security.allow_internal_targets: true` in the server's config.yaml.

## Feasibility & Effort

**CONFIRMED** defect (direct-call repro above). **Effort S-M**: the skip-recording pattern exists
(`missing-binary`, `missing-credentials` in `quirk/reports/coverage.py`), so the change is a refusal counter
per scanner plus a new skip reason, tests per connector, the coverage-gap/UAT entries and the doc line.
Candidate for a 5.28.x fix before the dashboard-first launch messaging leans on GUI scans.

## Second instance: S3 with no AWS credentials (confirmed 2026-11-05)

The URL guard is not the only cause. In both host GUI scans that night, `s3_scanning` recorded `ran` (about 2.1 s)
with **0 rows**, including the scan made after `allow_internal_targets: true` was in place. Direct call:
`_scan_s3_encryption(boto3.Session(), logger, endpoint_url="http://localhost:29000")` with no credentials in
the chain -> `list_buckets()` raises `NoCredentialsError` ("Unable to locate credentials"), the outer
`except Exception` in `quirk/scanner/aws_connector.py` logs it only through `logger.v()` (verbose) and returns
`[]`. With `AWS_ACCESS_KEY_ID/SECRET=minioadmin` the same call returns the two oracle buckets
(`encrypted-bucket` S3/sse-s3, `unencrypted-bucket` S3/unencrypted HIGH). The dashboard has no S3 credential
field (cloud connectors use the server process's ambient chain, by design), so a dashboard started without
AWS credentials can never scan S3, and says nothing.

So the fix belongs in the phase-status layer, not in one scanner: **a connector that produced zero rows
because it could not authenticate or was refused every target must record `skipped` (or `failed`) with a
reason** (`missing-credentials`, `internal-target-refused`, `auth-failed`), never `ran`. The Vault connector
already does this (`missing-credentials: connectors.vault_token / VAULT_TOKEN not set`); S3, JWT and SAML do
not. Audit every connector's outer `except` for this.

## Third symptom: page empty states ignore the recorded skip reason

The Data at Rest page (`src/dashboard/src/pages/data-at-rest.tsx:320`, `:342`) shows static empty-state
text whenever its list is empty. In the second scan Vault was **enabled with an address** and was recorded as
`skipped / missing-credentials`, yet the page said "No Vault mounts scanned in this session — enable the Vault
connector or configure a Vault address", which points the operator at the wrong cause. Empty states should read
the connector's `scan_phase_records` row and say "skipped: missing credentials (vault_token)" or "ran, 0
results", the same rule as the per-connector report sections in `261105-report-sections-per-enabled-connector.md`.
Also: database rows with `scan_error` are dropped from the Database Encryption table (`scan.py:680`), so a
target that failed to connect (2 of 3 Postgres targets that night) simply disappears from the page.
