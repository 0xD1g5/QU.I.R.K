---
type: todo
created: 2026-10-13
source: Phase 224 GC3-R3 (part 05, docs/report-interpretation.md §7.1 lift equality)
priority: high
area: quirk/dashboard/api/routes/scan.py (findings_for_endpoint/_derive_findings)
status: completed
completed: 2026-10-15
resolves_phase: 228
owner: XSURF-06
---

# Dashboard-only findings move the dashboard headline score, ceiling and lift badges away from the report

`findings_for_endpoint` (`quirk/dashboard/api/routes/scan.py:120-337`, called by `_derive_findings`) runs its
certificate/TLS checks on every non-identity row, including S/MIME, AD CS, Vault and database rows, which the CLI
evaluator does not turn into the same findings. Those extra findings feed the dashboard's evidence, so its §3.6
ceiling and lift badges differ from the report for the same scan. Probe `gc3-r3-f1-*` (S/MIME RSA-1024 row): report
score 83 with no lift badges; dashboard 68 with a `+15` badge.

Note: the existing todo `261013-doc224-smime-adcs-severities-never-surface-as-findings` states that these severities
never become findings anywhere. This probe (and Evidence Audit 2 on DCL-CHAOSLAB-0803) contradicts it on the
dashboard side; its owner should correct that todo rather than treat this one as a duplicate.

When fixed, update docs/report-interpretation.md §7.1 "Where you'll see both numbers" (the two divergence cases).

## Feasibility & Effort

- **Verdict: CONFIRMED, effort M.** `scan.py:120-337` (checks gated on cert/TLS fields, not protocol); `_derive_findings` used by the headline path (`scan.py:1811`).
- Fix options: align the CLI evaluator to emit the same cert findings for these protocols, or exclude them on the dashboard; product decision.
- Unknown: impact on `tests/test_score_lift_cross_surface_numbers.py` and the dashboard/report parity gate.

## Resolution (Phase 228, 2026-10-15)

- Fix: the shared predicate `runs_tls_certificate_checks` and report-findings composer (`bfea8dc9`), the dashboard TLS-only certificate checks `2cd1b90d`, and one dashboard scoring-findings helper adopting the report email/broker/code-signing evaluators `6df84979` (D-05, D-20).
- Proof: `tests/test_finding_engine_parity.py::test_non_tls_rows_get_no_tls_certificate_findings`, `::test_both_pipelines_call_the_shared_tls_predicate`, `tests/test_cross_surface_parity.py::test_xsurf0508_no_critical_cross_surface_parity` (`ff1f638e`). UAT-228-02, -03, -08.
- Docs: `ce1506b8`, changelog `19fe440a`.
- Remaining class-level divergences (weak cipher suites, legacy TLS, ECDSA, container EOL) are filed as `261015-xsurf-*` todos, not part of this requirement.
