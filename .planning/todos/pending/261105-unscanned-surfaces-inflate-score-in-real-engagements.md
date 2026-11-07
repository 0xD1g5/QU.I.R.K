---
type: todo
created: 2026-11-05
title: Unscanned surfaces read as covered and inflate the score in real engagements
source: operator review of the 2026-11-05 full chaos-lab GUI scans (5.28.1)
priority: critical
area: quirk/reports/coverage.py, quirk/scanner/*, quirk/intelligence/scoring*, src/dashboard/src/pages/*, docs/operators-guide.md
status: pending
resolves_phase: "235.3"
owner: null
release_target: "5.28.2 (before the dashboard-first social launch leans on GUI scans)"
---

# Unscanned surfaces read as covered and inflate the score in real engagements

## Why this is critical, not a lab artefact

Tonight's triggers were lab-specific (localhost targets, no server `config.yaml`, no AWS credentials in the
dashboard's environment, a Vault token not re-typed). The **behaviour** is not. In a client environment, the
same thing happens whenever:

- an internal JWT/SAML IdP (`https://sso.corp.internal`, `10.x`) is scanned from a dashboard whose server
  policy does not allow internal targets: the connector refuses every URL and records **ran**;
- S3 is scanned from a `quirk serve` process with no usable AWS credentials (expired SSO session, missing
  role, service started as another user): `NoCredentialsError` is swallowed at verbose level and the phase
  records **ran**;
- a database target fails to connect: the row is dropped from the Data at Rest page instead of being shown failed.

Each unscanned surface contributes **zero findings**, so the readiness score comes out **higher than the
estate deserves**, and Scan Coverage says "ran". A consultant has no signal to notice before a client report
goes out. This is the CR-02 class that 5.28.1 fixed for a missing semgrep/syft binary, with more causes.

Detailed evidence and per-connector analysis: `261105-connector-phase-ran-with-zero-output-when-url-guard-refuses-all-targets.md`.

## Acceptance criteria

- [ ] A connector that produced zero rows because it could not authenticate, was refused every target, or
      could not reach any target records `skipped`/`failed` with a named reason, never `ran`. Audit **every**
      connector's outer `except`, not only JWT/SAML/S3 (enumerate from source at test time, not from this list).
- [ ] Such a skip counts as a scan error in scoring and coverage, the same way `missing-binary` does in 5.28.1,
      so the score cannot rise because a surface was not scanned.
- [ ] Scan Coverage chips, page empty states (Data at Rest, Identity, Motion, …) and the reports show the
      reason ("skipped: missing credentials (AWS)", "skipped: internal targets refused by server policy").
- [ ] Failed-to-connect targets appear as failed rows, not silently omitted.
- [ ] A run-time test fails if any connector can return `[]` from an exception path while its phase records `ran`.
- [ ] Interim, ship first: `docs/operators-guide.md` §3.0 gets a "before a client scan" checklist (server
      `config.yaml` with `allow_internal_targets` plus scoped `trusted_targets`; start `quirk serve` with the
      cloud credentials it should use; treat an enabled connector with zero results as unverified, not clean).

## Feasibility & Effort

**CONFIRMED** for JWT (direct call, `allow_internal=False` -> `[]`), S3 (direct call, no credentials -> `[]`,
`minioadmin` -> the two oracle buckets) and the Data at Rest omissions (`scan.py:680`). **Effort M** overall:
the skip-reason machinery exists (`missing-binary`, `missing-credentials`), so the work is a per-connector audit
plus the scoring tie-in, the empty-state text, tests, UAT and docs. The interim doc item is **S** and can land on its own.
