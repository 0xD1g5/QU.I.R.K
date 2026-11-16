---
type: todo
created: 2026-10-15
source: Phase 228 (Cross-Surface Score Parity) D-04; operator decision 2026-10-15 to file rather than fix
priority: medium
area: quirk/dashboard/api/routes/scan.py (findings_for_endpoint), quirk/engine/findings_evaluator.py (_normalize_finding), quirk/dashboard/api/finding_title_bridge.py (SEVERITY_DIVERGENCES)
status: pending
resolves_phase: 236
owner: "999.132"
---

# Legacy TLS is HIGH on the dashboard and LOW in the report, on different conditions

The dashboard emits `Legacy TLS version: {ep.tls_version}` at HIGH when the *negotiated* version is TLSv1 / TLSv1.1 /
"TLS 1.0" / "TLS 1.1" (`quirk/dashboard/api/routes/scan.py:190-196`, severity literal at `:195`). The report emits
`Legacy TLS versions allowed (TLS 1.0/1.1)` at LOW (`quirk/engine/findings_evaluator.py:594-599`), keyed on
`_has_legacy_tls_versions(e)`, which also looks at the *offered* versions in `tls_supported_versions`. Even if the
emission site said otherwise, `_normalize_finding` forces that title to LOW (`findings_evaluator.py:343-344`).

The two titles are bridged (`DASHBOARD_TITLE_BRIDGE["Legacy TLS version: "]`), but the ceiling counts raw severities,
so one legacy-TLS endpoint adds a HIGH to the dashboard's count and a LOW to the report's. That moves the headline
between surfaces. Phase 228 does not change it: the conditions differ (negotiated vs offered) and the operator decided
on 2026-10-15 to file it. `tests/test_finding_title_bridge.py::test_bridged_pair_severities_match_or_are_dispositioned`
now reads both severities from source at run time and carries this pair in `SEVERITY_DIVERGENCES`.

- [ ] Decide the intended severity for legacy TLS (the report's LOW is a deliberate `_normalize_finding` rule).
- [ ] Align the dashboard literal at `scan.py:195` (or the report rule) and widen/narrow the dashboard condition to
      match `_has_legacy_tls_versions`.
- [ ] Remove the `"Legacy TLS version: "` entry from `SEVERITY_DIVERGENCES` in the same change; the gate fails if it stays.

## Feasibility & Effort

- **CONFIRMED** by reading `scan.py:190-196` and `findings_evaluator.py:343-344,594-599` at HEAD, and by the run-time gate
  finding exactly this pair.
- Effort **S** for the severity literal, **M** if the dashboard condition also moves to offered-versions (needs
  `tls_supported_versions` parity and a fixture). Unknown: which severity the product wants. No spike needed.

## Resolution (2026-11-16)

Fixed by Phase 236 (XSURF-09): shared `is_max_legacy_tls`; HIGH "Only legacy TLS versions offered (no TLS 1.2+)" and LOW "Legacy TLS versions allowed (TLS 1.0/1.1)" on both surfaces. Commits main 405925d5 (PR #82 merge). Tests: tests/test_weak_crypto_helper.py::test_is_max_legacy_tls, tests/test_ticketing_fingerprint_stability.py::test_max_legacy_title_keeps_legacy_tls_fingerprint, tests/test_severity_divergence_behaviour.py, tests/test_cross_surface_parity.py::test_xsurf236_scan_error_tls_row_headline_parity, tests/test_severity_divergence_behaviour.py::test_injected_mutations_turn_new_gate_red[M3_drop_scan_error_guard]. Score movement: report scores drop for endpoints with no TLS 1.2+ (incl. SSLv2/SSLv3-only); dashboard gains a LOW for legacy alongside TLS 1.2+. Also (236-09): dashboard scores rise for TLS or HTTP rows whose scan errored after populating columns (they no longer raise dashboard HIGH/CRITICAL findings, matching the report).
