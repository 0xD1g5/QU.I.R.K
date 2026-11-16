---
type: todo
created: 2026-11-16
source: Phase 236-09 code review WR-01 (236-09-REVIEW.md)
priority: low
area: quirk/dashboard/api/finding_derivation.py, quirk/dashboard/api/routes/scan.py
status: pending
resolves_phase:
owner: "999.132"
---

# Errored TLS/HTTP rows show nothing on the dashboard Findings page; the report lists them

Since 236-09 (`e13b62f8`), `findings_for_endpoint` returns early for any row with a truthy `scan_error`. The report's
`evaluate_endpoints` scan-error branch still emits a MEDIUM "TLS handshake blocked assessment", an INFO "mTLS required" or an
INFO "Informational protocol observation" for those rows. The dashboard has no equivalent row: the scan_error INFO rows in
`routes/scan.py::_derive_dar_findings` cover POSTGRESQL/MYSQL only. Headline score is unaffected (both surfaces skip the
TLS/HTTP derivation); the gap is finding-list parity. Plan 236-09 Task 2 required this row; its SUMMARY skipped it on the
mistaken reading that `_derive_dar_findings` already covered these protocols.

## Feasibility & Effort

**Feasibility: HIGH.** Emit the same scan-error finding from the dashboard deriver (or share the report's scan-error branch).
**Effort: S.** Add a behaviour-gate family asserting finding-list parity for errored TLS/HTTP rows.
