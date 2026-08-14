---
phase: 149-test-suite-triage
reviewed: 2026-08-12T02:10:00Z
depth: standard
files_reviewed: 55
files_reviewed_list:
  - docs/test-triage-149.md
  - pyproject.toml
  - quirk/scanner/kerberos_scanner.py
  - quirk/scanner/tls_scanner.py
  - tests/scanner/test_jwt_hardening.py
  - tests/skip_registry.py
  - tests/test_auto_merge_trigger.py
  - tests/test_broker_scanner_rabbitmq.py
  - tests/test_cbom_schema_validation.py
  - tests/test_cli_correctness.py
  - tests/test_cli_init.py
  - tests/test_compliance_title_join.py
  - tests/test_dashboard_scan_history.py
  - tests/test_dashboard_theme.py
  - tests/test_db_migrate_cli.py
  - tests/test_email_run_scan_wiring.py
  - tests/test_gap_closure.py
  - tests/test_gcs_reuse.py
  - tests/test_identity_scanner_hardening.py
  - tests/test_init_db_idempotent.py
  - tests/test_install_all_excludes_impacket.py
  - tests/test_install_all_excludes_pysnmp.py
  - tests/test_install_all_excludes_schemathesis.py
  - tests/test_install_all_includes_notify.py
  - tests/test_install_all_includes_tickets.py
  - tests/test_install_errors.py
  - tests/test_jwt_scanner.py
  - tests/test_notify_email.py
  - tests/test_notify_webhook.py
  - tests/test_openapi_scanner.py
  - tests/test_packaging.py
  - tests/test_pdf_export.py
  - tests/test_pdf_metadata_constants.py
  - tests/test_phase135_docs_presence.py
  - tests/test_phase136_docs_presence.py
  - tests/test_posture_scorefix125.py
  - tests/test_qramm_evidence_bridge.py
  - tests/test_qramm_model_stale.py
  - tests/test_qramm_models.py
  - tests/test_qramm_staleness.py
  - tests/test_report_injection_hardening.py
  - tests/test_reports_writer.py
  - tests/test_route_coverage.py
  - tests/test_safe_filter_audit.py
  - tests/test_scan_error_gate.py
  - tests/test_sensor_cmd.py
  - tests/test_sensor_push_id_revalidation.py
  - tests/test_sensor_windows_smoke.py
  - tests/test_skip_registry.py
  - tests/test_snmp_scanner_contract.py
  - tests/test_ticketing_servicenow.py
  - tests/test_v41_gap_closure.py
  - tests/test_vault_connector.py
  - tests/test_version.py
  - tests/test_writer.py
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 149: Code Review Report

**Reviewed:** 2026-08-12T02:10:00Z
**Depth:** standard
**Files Reviewed:** 55
**Status:** issues_found

## Summary

Phase 149's ledger (`docs/test-triage-149.md`) and `tests/skip_registry.py` were cross-checked
line-by-line: every `@pytest.mark.xfail`/`@pytest.mark.skip` decorator cited in the ledger's 116
rows was located at its documented file:line, its `reason=` text matches the ledger's stated
root cause, and the corresponding `ALLOWED_SKIPS` registry tuple's line number is within the
gate's `+/-2` tolerance. `pytest tests/test_skip_registry.py -q -m ""` passes (meta-gate green).
The two production bug fixes were read in full: the sslyze `__version__` submodule-shape
normalization in `quirk/scanner/tls_scanner.py` and the impacket `MethodData`→`METHOD_DATA`
import-rename fallback in `quirk/scanner/kerberos_scanner.py` are both correct, narrowly scoped,
and do not regress the impacket<0.13 / sslyze<6.3 code paths.

However, the phase's headline deliverable claim — a fresh `pytest -q -m ""` full-suite run is
"0 failed... a genuinely green, reconciled baseline" (Plan 11 Reconciliation section) — does
**not hold up under independent verification**. Two separate fresh full-suite runs performed
during this review both failed with the *same* single failure:
`tests/test_dashboard_trends.py::test_trends_timeline_empty`, a test file Phase 149 never
touched and that has no row in the 116-test ledger. This is a real, reproducible orphaned
failure of the exact defect class (shared `sqlite:///file::memory:?cache=shared&uri=true`
in-memory DB leaking rows across test files within one pytest worker process) that Phase 149
itself identified and quarantined elsewhere (Cluster 5's `test_sensor_push_id_revalidation.py`)
— but this instance was missed by Plan 11's reconciliation sweep. See CR-01 below.

## Critical Issues

### CR-01: "0 failed" reconciled-baseline claim is not reproducible — an orphaned, undocumented flaky failure exists

**File:** `docs/test-triage-149.md:381-391, 484-490` (claim); root cause in `tests/conftest.py:108-131` and `tests/test_dashboard_trends.py:352`
**Issue:** The Reconciliation section states: "After the fixes and quarantines documented below,
a fresh run is **0 failed** — a true green baseline, not merely a re-labeled one" and the Net
Result section claims "0 orphaned failures, 0 false-`fixed` rows, ... ready to hand off as
Phase 150's sizing input." Two independent `pytest -q -m ""` runs performed during this review
(current HEAD, no code changes) both reproduce a **1-failed** result:

```
FAILED tests/test_dashboard_trends.py::test_trends_timeline_empty - AssertionError: assert [{'finding_co...e': 19, ...}}] == []
1 failed, 3087 passed, 42 skipped, 81 xfailed, ... in ~305s
```

`test_trends_timeline_empty` asserts an empty-DB `/api/trends/timeline` response returns
`sessions == []`, but in full-suite order it observes a leftover session row written by an
earlier test. The test passes standalone (`pytest tests/test_dashboard_trends.py -q -m ""` →
8 passed). `test_dashboard_trends.py` was **not modified by Phase 149** (confirmed via
`git log`/`git diff 014fc75~1..HEAD`) and has **no row in the 116-test ledger** — it is a new,
previously-undocumented orphaned failure of the identical root-cause class Phase 149 already
diagnosed for Cluster 5: the `dashboard_client` fixture (`tests/conftest.py:108-131`) creates
`sqlite:///file::memory:?cache=shared&uri=true`, a single process-wide shared-cache in-memory
DB that is not test-isolated — rows written by one test file's `dashboard_client` calls persist
for the rest of the pytest worker's session. Plan 11's own text acknowledges this exact
mechanism drove `test_sensor_push_id_revalidation.py`'s two rows, but the reconciliation sweep's
"11 orphaned failures, 0 new" accounting did not catch this file.

This matters because Phase 149's stated purpose is to hand off a verified, accurate baseline
to Phase 150 ("ready to hand off as Phase 150's sizing input"). Shipping a false "0 failed"
claim risks Phase 150 either being blindsided by a "new" regression that isn't new, or
mis-scoping its starting baseline. It also means the reconciliation's own acceptance criteria
("(a) Orphaned failures: zero found") is not actually satisfied for this test.

**Fix:** Add `test_dashboard_trends.py::test_trends_timeline_empty` as a new Cluster 5 (or a
new Cluster 10) row in `docs/test-triage-149.md`, and add a matching `pre_existing_triage_149`
entry to `tests/skip_registry.py` with an `@pytest.mark.xfail(strict=False)` (or fix the
underlying shared-cache DB isolation — e.g. give `dashboard_client` a per-test unique cache
name instead of the literal `file::memory:?cache=shared&uri=true`, which is the more durable
fix and would also retroactively resolve the two already-quarantined
`test_sensor_push_id_revalidation.py` rows). At minimum, correct the Reconciliation section's
"0 failed" / "0 orphaned failures" language to reflect the actual, currently-reproducible
result before handing the ledger to Phase 150.

## Warnings

### WR-01: `test_identity_scanner_hardening.py`'s pre-existing `optional_extra` registry row is now stale in this sandbox

**File:** `tests/skip_registry.py:55` (`("test_identity_scanner_hardening.py", 80, "optional_extra", "impacket not installed")`)
**Issue:** This entry (pre-dating Phase 149, category `optional_extra`) documents
`pytest.importorskip("impacket")` at `tests/test_identity_scanner_hardening.py:80` as skipping
because impacket isn't installed. Plan 11's own reconciliation finding establishes that this
sandbox **does** have impacket 0.13.0 installed (that's precisely how it discovered the
`MethodData`/`KDCOptions` bugs) — so this fixture no longer skips here; it now executes and any
test depending on it exercises the real (partially-broken) kerberos_scanner code path. The
registry entry is harmless (an unused allow-list row doesn't fail the meta-gate) but is
misleading documentation: a reader would assume `_kerb_mod`-dependent tests are cleanly skipped
in the current environment when they are not.
**Fix:** Add a comment near this entry noting it is sandbox-dependent (impacket presence varies
by environment) and cross-reference the new Plan 11 entries at lines 202-203 that supersede it
when impacket is actually installed.

### WR-02: Chaos-lab `otics` profile CBOM drift is a live CLAUDE.md Chaos Lab Maintenance gap, deferred without a tracked follow-up ticket

**File:** `tests/test_cbom_schema_validation.py:77-88`; `tests/skip_registry.py:180`
**Issue:** `test_parametrize_set_matches_docker_compose_profiles` is correctly diagnosed as a
genuine `tests/_cbom_profiles.py::PROFILE_ENDPOINTS` gap (the `otics` compose profile from
Phase 141-07 never got a CBOM synthesizer). Per this repo's own `CLAUDE.md` "Chaos Lab
Maintenance" section, any phase that changes a chaos-lab profile (which Phase 141 did) is
"incomplete until `lab.sh`, the README, and the expected-results oracle are all updated" — this
gap predates Phase 149 and isn't this phase's fault to have introduced, but quarantining it via
`xfail` without opening a tracked Phase-150 backlog item (only a docs cross-reference) risks it
silently living as permanent tech debt rather than getting fixed, since `xfail(strict=False)`
never turns red again to force attention.
**Fix:** File an explicit Phase 150 backlog/ROADMAP entry for the `otics` CBOM synthesizer gap
(not just a doc cross-reference) so it doesn't get lost among the other ~15 Phase-150-flagged
follow-ups in this ledger.

### WR-03: `test_route_coverage.py`'s exemption-set staleness sets a precedent for exemption drift without automated enforcement

**File:** `tests/test_route_coverage.py:18-30`
**Issue:** The investigation correctly concludes `GET /api/config` is intentionally
unauthenticated and not a real security finding. However, the fix quarantines the test via
`xfail` rather than updating the test's own `{"/api/health", "/api/health/"}` exemption set to
add `/api/config`. Since this is a security-relevant coverage gate (every dashboard route must
have `require_auth` unless explicitly exempted), leaving it `xfail`'d means any *future*
genuinely-unprotected route added alongside `/api/config` in the same PR would also silently
pass this gate (xfail suppresses the assertion entirely, it doesn't distinguish "already known
exempt route" from "a new route that's also missing auth"). A one-line fix (add
`/api/config` to the test's own exemption set) would have both closed this ticket and kept the
gate live for future drift, and was clearly in scope for a "fixed" disposition rather than
"quarantined-xfail" per the plan's own Rule 1 (fix in place when trivial).
**Fix:** Replace the `xfail` marker with a one-line update to the test's exemption allowlist
(`{"/api/health", "/api/health/", "/api/config", "/api/config/"}`) and remove the quarantine —
this restores the gate's ability to catch new unauthenticated routes.

## Info

### IN-01: `docs/test-triage-149.md` Reconciliation section slightly under-reports intermittent-failure risk

**File:** `docs/test-triage-149.md:387-391`
**Issue:** The doc notes "three repeated fresh runs... consistently showed 9-12 failures
depending on whether the intermittent SIGSEGV cluster below fired that run" before fixes, then
states a post-fix run is 0 failed. Given the now-confirmed existence of at least one additional
order-dependent flake outside the SIGSEGV cluster (CR-01), the "0 failed" single-data-point
claim understates the suite's true flake surface. A more defensible closing statement would
note the baseline is "green modulo N known intermittent classes" rather than a flat "0 failed."
**Fix:** Cosmetic — reword once CR-01 is addressed to avoid re-introducing the same
overconfident framing.

### IN-02: `KDCOptions` production bug is real but not fully characterized for blast radius

**File:** `quirk/scanner/kerberos_scanner.py:96-98`
**Issue:** The Plan 11 fix correctly restores `IMPACKET_AVAILABLE=True`, but leaves the deeper
`constants.KDCOptions(constants.KDCOptions.forwardable)` incompatibility (impacket 0.13.0
changed `KDCOptions` from a bit-flag helper to a plain `enum.Enum`) unfixed and quarantined. This
review traced the call path and confirmed the resulting `pyasn1`/`KeyError` in `_build_as_req`
is caught by `scan_kerberos_targets`'s broad `except Exception` (both the TCP path at
`_probe_kdc`'s call site and the UDP fallback in `_probe_kdc_udp`), so it degrades to a "both
paths failed" unreachable-endpoint result rather than crashing — consistent with the ledger's
description. However, this means Kerberos scanning is now silently non-functional (0 real
etypes ever discovered) for every operator on the currently-pinned `impacket>=0.13.0,<0.14`,
which is arguably a more severe operator-facing regression than the ledger's "quarantined
pending a dedicated Phase 150 fix" framing suggests (it was completely broken before this
phase too via the `MethodData` bug, so no regression was introduced, but the fix did not
restore actual functionality — only correctly identified the residual break).
**Fix:** None required from this phase (correctly scoped out per the plan's own Rule 1
boundary), but recommend Phase 150 treat this as a P1 (Kerberos scanning is completely
non-functional on the current impacket pin), not routine test debt.

---

_Reviewed: 2026-08-12T02:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
