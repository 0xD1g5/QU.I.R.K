---
type: todo
created: 2026-11-09
title: Executive Skipped badge drops later entries after a null-category error row
source: v5.28.2 milestone audit, integration check F1 (.planning/milestones/v5.28.2-MILESTONE-AUDIT.md)
priority: high
area: run_scan.py:1223 (_collect_stage_partial_failures), quirk/dashboard/api/routes/scan.py:1713 (_load_partial_failures)
status: pending
resolves_phase: null
owner: null
---

# Executive Skipped badge drops later entries after a null-category error row

Kind: product (regression introduced in 5.28.2 / Phase 235.3)

Ledger note: .planning/LEDGER.md is not on `main` yet. This item belongs in LEDGER.md (id
`261109-executive-skipped-badge-drops-null-category-entries`) when PR #74 lands.

## Observed

1. When a connector skips, 235.3's P-08 forwarding (`run_scan.py:546-548`) copies its in-band scan_error rows
   into `error_endpoints`. Several connectors build those rows without `scan_error_category`, including
   `db_connector.py:189-195` (`connection-error`), `k8s_connector.py:360/405`, and the gcp/aws/vault
   connectors.
2. `_collect_stage_partial_failures` (`run_scan.py:1223`) calls
   `getattr(ep, "scan_error_category", "exception")`. The column exists and is nullable (`models.py:37`), so the
   default never applies and the entry is serialised with `error_category: null`.
3. `_load_partial_failures` builds `PartialFailureEntry(error_category=None)`, but that field is a required
   `str` (`schemas.py:629`). This raises a pydantic `ValidationError`, which is a `ValueError`. One
   `try`/`except (ValueError, KeyError): pass` wraps the whole per-checkpoint loop, so **every later entry in
   that stage is silently dropped**.

Reproduced in the v5.28.2 audit with the real `_classify_connector_outcomes`, using an unreachable DB with its
connection-error row followed by an unreachable Vault. The categories came out
`['targets_unreachable', None, 'targets_unreachable']`, and the loader returned only the db entry, so Vault's
Skipped badge vanished. The auditor independently confirmed that
`PartialFailureEntry(error_category=None)` raises.

The bug triggers with real stage orderings:
- Identity: aws → azure → gcp → db
- Data at rest: s3 → blob → k8s → dnssec → saml → kerberos → smime → adcs → codesign → vault

## Impact

- Not affected: the score (the advisory rows are still counted) and the Scan Coverage chips.
- Affected: only the Executive Scanner Status card, for dashboard-job scans.
- The 235.4 Pass A walkthrough missed it because missing-credentials and refused skips emit no in-band rows.
- The announcement claims the reason shows on Scan Coverage, which is unaffected.

## Fix sketch

- Writer: `getattr(ep, "scan_error_category", None) or "exception"` (or a more specific default).
- Reader: move the `try` inside the per-entry loop, so one bad entry skips only itself. Coalesce
  `entry.get("error_category") or "exception"`.
- Optionally give the in-band connector rows a real category at source.
- Red-first test: a checkpoint `error_summary` of `[valid, null-category, valid]` must load 3 entries. Add an
  in-process db→vault ordering test.

## Feasibility & Effort

Small (1-2 hours). The change is two lines plus two tests. Check `findings_evaluator` and trends for the same
`getattr` default pattern on `scan_error_category`.
