---
type: todo
created: 2026-10-15
source: Phase 228 (Cross-Surface Score Parity) D-22; RESEARCH Open Question 3
priority: medium
area: quirk/dashboard/api/routes/scan.py (findings_for_endpoint), quirk/engine/findings_evaluator.py, quirk/dashboard/api/finding_title_bridge.py (UNBRIDGED_DASHBOARD_TITLES, SEVERITY_DIVERGENCES)
status: pending
resolves_phase: null
owner: "999.132"
---

# Dashboard "Weak cipher suites enabled" is HIGH; the report has no HIGH for that column

The dashboard emits `Weak cipher suites enabled` at HIGH whenever `ep.tls_weak_ciphers_present` is set on a TLS row
(`quirk/dashboard/api/routes/scan.py:207-213`). The report has no finding on that column. Its nearest title, `Legacy TLS
cipher suites accepted`, fires on the distinct `tls_legacy_suites_present` column and is LOW
(`quirk/engine/findings_evaluator.py:609-615`). `UNBRIDGED_DASHBOARD_TITLES` records the title as unbridged.

Re-measured in-process at HEAD (one TLS 1.2 endpoint, `tls_weak_ciphers_present=True`, no other signals):
`evaluate_endpoints` returns `[]` and `compute_readiness_score` gives **84**; the dashboard recipe
(`derive_dashboard_scoring_findings`) returns one HIGH and the score is **69**. Same estate, 15 points apart, because
the ceiling counts the raw HIGH.

The first gate leg (bridged pairs) cannot see this, since the title is unbridged. D-22 widened the gate:
`test_unbridged_high_critical_dashboard_titles_are_dispositioned` requires every unbridged HIGH/CRITICAL dashboard title
to carry a `SEVERITY_DIVERGENCES` entry, and this todo is that entry's target.

- [ ] Decide whether weak ciphers are a report finding (add a `tls_weak_ciphers_present` site to `evaluate_endpoints`) or
      whether the dashboard HIGH should drop to match the report.
- [ ] If a report site is added, bridge it and remove the `SEVERITY_DIVERGENCES` entry; add the CLI title to
      `findings_evaluator`'s vocabulary and the compliance map.
- [ ] Update `docs/report-interpretation.md` if the report starts listing it.

## Feasibility & Effort

- **CONFIRMED** by the in-process probe above (84 vs 69) and by `scan.py:207-213` / `findings_evaluator.py:609-615`.
- Effort **M**: new evaluator site, title in the compliance map, remediation theme decision, parity fixture. Unknown:
  whether `tls_weak_ciphers_present` and `tls_legacy_suites_present` should be merged (they are set from different
  capability checks, `quirk/scanner/tls_scanner.py:323-324`). No spike needed.
