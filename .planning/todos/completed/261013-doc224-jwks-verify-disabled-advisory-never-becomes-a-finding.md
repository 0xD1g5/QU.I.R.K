---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS (fork C); ledger rows DCL-OPS-B-0004, DCL-OPS-A-1117, DCL-OPS-A-1118 (docs/operators-guide.md, JWT/API scanner "allow_insecure_jwks" security note)
priority: medium
area: quirk/engine/findings_evaluator.py (ADVISORY handling), quirk/dashboard/api/routes/scan.py (_derive_findings), quirk/reports/templates/report.html.j2 (Endpoint Inventory)
status: completed
completed: 2026-10-14
resolves_phase: 225.1
---

# The HIGH `JWKS/verify-disabled` advisory never becomes a finding on any surface

With `security.allow_insecure_jwks: true`, `jwt_scanner.py:310-320` (and `:262-275` on the no-keys path) stores one
`protocol="ADVISORY"`, `severity="HIGH"`, `service_detail="JWKS/verify-disabled"`, `scan_error_category="config"`
endpoint row per JWKS URL fetched. The code comment (`jwt_scanner.py:186-187`) and the operators-guide used to say a
HIGH advisory *finding* is "always emitted", "so the override is always visible in reports".

Probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc3-ops-C-jwks-advisory-surfaces-probe.py`):
the exact row through `evaluate_endpoints` -> `[]`; through the dashboard's `_derive_findings` -> `[]`; control
TLSv1/3DES row through the same harness -> 1 finding on each. The evaluator's only ADVISORY branch is
`scan_error_category == "missing_extra"` (`findings_evaluator.py:461`). The HTML Endpoint Inventory
(`report.html.j2:769`) has no service_detail or severity column, so the row shows only as `ADVISORY` for the JWKS URL.
Also, on a resumed scan `run_scan.py:3137` reloads only `protocol == "JWT"` rows, so the advisory rows drop out.

The doc now states this. A security override that disables TLS verification should be visible.

- [x] Emit a HIGH finding for `JWKS/verify-disabled` rows in `evaluate_endpoints` and `_derive_findings`.
- [x] Map its title in `COMPLIANCE_MAP` or `UNMAPPED_TITLES` (the title-join gate).
- [x] Keep ADVISORY rows on resume, or re-derive them.

## Feasibility & Effort

- **CONFIRMED** emitter shape at `quirk/scanner/jwt_scanner.py:315-318` (protocol ADVISORY, service_detail, severity HIGH).
- **CONFIRMED** the evaluator's only ADVISORY branch at `quirk/engine/findings_evaluator.py:461` (missing_extra only).
- **CONFIRMED** resume filter at `run_scan.py:3137` (`getattr(e, "protocol", "") == "JWT"`).
- **LIKELY** effort **S**: one branch in each of the two finding pipelines plus a compliance-map entry and a test;
  **UNKNOWN** whether the score should count it (today it does not). No spike needed.
