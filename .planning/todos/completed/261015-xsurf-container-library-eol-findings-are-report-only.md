---
type: todo
created: 2026-10-15
source: Phase 228 (Cross-Surface Score Parity) D-04; RESEARCH "Report-only HIGH/CRITICAL emitters"
priority: medium
area: quirk/engine/findings_evaluator.py (_evaluate_container_package), quirk/dashboard/api/routes/scan.py (derive_dashboard_finding_items)
status: pending
resolves_phase: 236
owner: "999.132"
---

# Container-image crypto-library findings exist only in the report

`evaluate_endpoints` evaluates each CONTAINER package row through `_evaluate_container_package`
(`quirk/engine/findings_evaluator.py:152-265`, called at `:820`). It emits CRITICAL/HIGH findings the dashboard never
produces: `End-of-life {label} in container image` driven by `_OPENSSL_EOL` (`:49-55`, CRITICAL for OpenSSL 0.x and 1.0.x,
HIGH for 1.1.x, 3.0.x, 3.1.x), and `Severely outdated Python cryptography package` at HIGH (`:199-202`).

The dashboard recipe (`derive_dashboard_finding_items`, `quirk/dashboard/api/routes/scan.py:405-437`) runs
`findings_for_endpoint`, identity findings and `evaluate_protocol_service_endpoints` (email, broker, code-signing). It has
no CONTAINER branch (`grep CONTAINER quirk/dashboard/api/routes/scan.py` finds nothing). So a scan with an EOL OpenSSL in
a container image trips the report's ceiling and not the dashboard's.

Phase 228 D-20 adopted the report's email, broker and code-signing evaluators on the dashboard but did not take the
container evaluator, so this is the remaining report-only HIGH/CRITICAL emitter.

- [ ] Route CONTAINER rows through the report's container evaluator in `derive_dashboard_finding_items` (same adapter
      shape as the D-20 `evaluate_protocol_service_endpoints` loop).
- [ ] Add a parity fixture row (OpenSSL 1.1.1 package) and an assertion that both surfaces carry the HIGH.

## Feasibility & Effort

- **CONFIRMED** by reading `findings_evaluator.py:49-55,152-265,820` and grepping the dashboard route at HEAD.
- Effort **S-M**. Unknown: how CONTAINER package rows are stored (service_detail format) for the dashboard path; check
  `findings_evaluator.py:805-825` before writing the adapter. No spike needed.

## Resolution (2026-11-16)

Fixed by Phase 236 (XSURF-12): `evaluate_container_endpoints` feeds the dashboard the report's own container findings. Commits main 405925d5 (PR #82 merge). Tests: tests/test_dashboard_scoring_findings.py::test_container_findings_match_report_titles_and_severities, ...test_xsurf236_container_critical_headline_parity. Score movement: dashboard drops for EOL OpenSSL/outdated cryptography in images (Pass A replay 42 -> 27).
