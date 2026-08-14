# Phase 149: Test Suite Triage - Research

**Researched:** 2026-08-11
**Domain:** Test suite triage / quarantine machinery (pytest, AST-based meta-gate)
**Confidence:** HIGH (all core findings verified by directly running the suite and reading source in this session)

## Summary

This phase is pure investigation-and-classification work, not implementation. The research below
does three things the planner needs: (1) establishes the **current, authoritative failure list**
(116 failures, not the ~108 CONTEXT.md snapshot — see Ground Truth Correction below), (2) clusters
those 116 failures by root cause so the planner can size tasks by cluster instead of by individual
test, and (3) confirms the exact mechanics of the reused `skip_registry.py` gate, including a
material gap CONTEXT.md flagged as unconfirmed: **the AST walker does not detect `@pytest.mark.skip`
at all** (only `pytest.skip()` calls and `@pytest.mark.skipif` decorators), which changes how D-03's
skip-vs-xfail choice interacts with the gate.

**Primary recommendation:** Structure the phase as one plan per failure-cluster (grouped by shared
root cause, not by file and not as one giant plan), each producing per-test ledger rows plus
quarantine markers for that cluster. Do the `test_no_unregistered_skips` repair (D-04, ~25-29
violations found) as its own first plan/task, since every other plan's quarantine markers depend on
that gate being green to verify against.

## Ground Truth Correction (read before using CONTEXT.md's snapshot)

CONTEXT.md's snapshot (**108 failed, 3064 passed, 8 skipped, 60 deselected**) was captured with
plain `pytest -q`, which still applies `addopts = "-m 'not slow'"` from `pyproject.toml` — the "60
deselected" in that output *is* the slow-marked tests being filtered out despite the discussion
log's framing of it as "no `-m` filter, full suite". That run did **not** satisfy Success Criterion
1's "not just the `-m 'not slow'` default."

This research re-ran the suite with `pytest -q -m ""` (explicit empty marker expression, which
overrides `addopts`'s `-m 'not slow'` on the command line — pytest takes the last `-m` value, not a
union of all `-m` values). Confirmed no deselection occurred (no "N deselected" in the summary line,
and `failed+passed+skipped` sums exactly to the total collected, 3240 — same total the CONTEXT.md
run collected, just without deselecting 60 of them into a hidden bucket).

**Current authoritative full-suite result (2026-08-11, this session):**
```
116 failed, 3107 passed, 17 skipped, 127 warnings in 887.84s (0:14:47)
```
`[VERIFIED: live pytest run, this session]` — 116 failures across **52 distinct files** (not ~30 as
estimated in CONTEXT.md's discussion — the discussion only enumerated the largest clusters, it did
not claim a total file count).

**Planner action:** Re-run `pytest -q -m ""` at plan/execute time — this count will drift further as
Phase 148 and other in-flight work lands. Use `-m ""` specifically, not bare `pytest -q`, or the run
will silently exclude slow tests again and Success Criterion 1 will not be met.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Full-suite failure enumeration | Test runner (pytest) | — | Ground truth must come from an actual run, not estimation |
| Per-test disposition record | New docs artifact (`docs/test-triage-149.md`) | — | Human/machine-readable ledger, referenced by quarantine `reason=` strings |
| Quarantine enforcement | `tests/skip_registry.py` + `tests/test_skip_registry.py` (existing Phase 41 machinery) | — | Reuse per D-02; this phase extends it, does not replace it |
| Quarantine marker placement | Individual test files | — | `pytest.mark.skip`/`xfail` decorators live where the test lives |

## Package Legitimacy Audit

Not applicable — this phase installs no new packages. It only edits test files, `tests/skip_registry.py`,
and adds one new documentation file.

## Standard Stack

No new dependencies. Existing stack in use:

| Tool | Version | Purpose |
|------|---------|---------|
| pytest | (pinned in project, not re-verified this session — unchanged by this phase) | Test runner |
| `tests/skip_registry.py` | Phase 41, in-repo | `ALLOWED_SKIPS` registry — reused per D-02 |
| `tests/test_skip_registry.py` | Phase 41, in-repo | AST-walking meta-gate — reused/repaired per D-02/D-04 |

## Confirmed Mechanics of the Reused Skip-Registry Gate

`[VERIFIED: tests/skip_registry.py, tests/test_skip_registry.py — read directly this session]`

- `ALLOWED_SKIPS` is a flat list of 4-tuples: `(file_relative_to_tests_dir, line_number, category, reason)`.
  Currently 27 entries across 2 categories (`optional_extra`, `live_infra`).
- `_allowed(filename, lineno)` matches on **exact filename** (no path prefix — `tests/scanner/test_jwt_hardening.py`
  would need to be registered as `"test_jwt_hardening.py"` inside `tests/scanner/`, since the gate
  walks `TESTS_DIR.glob("*.py")` — **note:** the current glob is `TESTS_DIR.glob("*.py")`, non-recursive,
  so files under `tests/scanner/` (e.g. `test_jwt_hardening.py`) are **not walked at all** by the
  existing gate. Confirm at planning/execution time whether this is intentional (scanner subpackage
  tests exempt) or a second gate defect needing repair alongside D-04's registered-skip drift — the
  research task did not find explicit prior documentation of this scoping choice.
- Line matching uses `abs(entry_line - lineno) <= 2` (the documented `±2` tolerance) — confirmed in
  `LINE_TOLERANCE = 2` at `tests/test_skip_registry.py:32`.
- **Detection scope — this is the unconfirmed item CONTEXT.md flagged, now confirmed:**
  - Detected: `pytest.skip(...)` calls, `pytest.importorskip(...)` calls, `@pytest.mark.skipif(...)` decorators.
  - **NOT detected: `@pytest.mark.skip(...)` decorator (bare skip, no "if").** The walker's
    `_is_pytest_skipif_decorator` only matches `target.attr == "skipif"` — a bare `@pytest.mark.skip`
    decorator has `attr == "skip"` and never matches, so it is invisible to the gate and requires no
    registry entry to pass.
  - **NOT detected: `@pytest.mark.xfail(...)`** in any form — confirmed no code path in
    `test_no_unregistered_skips` looks for `xfail`. This matches CONTEXT.md's flagged uncertainty.
  - Two exempt files: `skip_registry.py` and `test_skip_registry.py` themselves.
- No existing `@pytest.mark.skip` or `@pytest.mark.xfail` usage currently exists anywhere in `tests/`
  `[VERIFIED: grep -rn "pytest.mark.skip(\|@pytest.mark.skip\b" tests/*.py — zero results]` — so this
  phase will be the first user of both mechanisms in this codebase.

**Implication for D-03 (skip vs. xfail choice):** Because the gate only enforces registration for
`pytest.skip()`/`importorskip()`/`skipif`, an executor who quarantines a test with bare
`@pytest.mark.skip(reason=...)` will get a passing meta-gate **without adding a registry entry** —
which silently violates D-02/D-03's stated intent ("a matching entry added to ALLOWED_SKIPS so the
meta-gate stays green" implies the gate is the enforcement mechanism). Two options for the planner:
1. **(Recommended)** Extend the AST walker in this phase to also detect `@pytest.mark.skip` and
   `@pytest.mark.xfail` decorators, so the gate genuinely enforces registration for every marker
   type D-03 permits. This is a small, contained change to `_is_pytest_skipif_decorator`-equivalent
   logic and belongs in the same plan that repairs D-04's drift.
2. Accept the gap and rely on code review / the ledger's exact-count cross-check (Success Criterion 2)
   as the enforcement mechanism instead of the AST gate for skip/xfail markers.
Given Success Criterion 3 explicitly requires "machine-checkable," option 1 is the safer choice and
should be flagged to the planner as a likely additional task, not left as a silent gap.

## D-04 Groundwork: Current Unregistered-Skip Violations

`[VERIFIED: pytest tests/test_skip_registry.py -q -m "" — this session]` — approximately **25-29
unregistered violations** (CONTEXT.md estimated "~15+"; actual count is higher, another drift data
point — see note below on why the exact count needs a fresh capture):

```
test_cbom_vault_consistency.py:50      [@pytest.mark.skipif]
test_chaos_lab_idempotency.py:111      [pytest.skip]
test_chaos_storage.py:44               [@pytest.mark.skipif]
test_chaos_storage.py:71               [@pytest.mark.skipif]
test_cmvp_refresh.py:22                [pytest.importorskip]
test_cmvp_refresh.py:23                [pytest.importorskip]
test_credential_leakage.py:306         [pytest.skip]
test_db_migrate_cli.py:166             [pytest.skip]
test_distributed_topology.py:48        [pytest.skip]
test_dnssec_scanner.py:480             [@pytest.mark.skipif]
test_identity_scanner_hardening.py:80  [pytest.importorskip]
test_jobs_api.py:489                   [@pytest.mark.skipif]
test_jwt_scanner.py:209                [pytest.importorskip]
test_kerberos_scanner.py:384           [@pytest.mark.skipif]
test_pdf_metadata_constants.py:19      [pytest.importorskip]
test_pdf_metadata_constants.py:20      [pytest.importorskip]
test_pdf_metadata_constants.py:56      [pytest.skip]
test_pqc_discriminator.py:126          [@pytest.mark.skipif]
test_pqc_discriminator.py:141          [@pytest.mark.skipif]
test_report_injection_hardening.py:240 [pytest.importorskip]
test_report_injection_hardening.py:241 [pytest.importorskip]
test_report_injection_hardening.py:254 [pytest.skip]
test_report_render_undetermined_hosts.py:162 [pytest.skip]
test_report_render_undetermined_hosts.py:215 [pytest.skip]
test_report_render_undetermined_hosts.py:150 [pytest.skip]
test_scheduler_cmd.py:314              [@pytest.mark.skipif]
test_snmp_scanner_contract.py:598      [pytest.skip]
test_snmp_scanner_contract.py:631      [pytest.skip]
test_snmp_scanner_contract.py:673      [pytest.skip]
```

This session's captured output was truncated by terminal scrollback on the first capture attempt
(only the tail of the violation list was visible). **Re-run
`pytest tests/test_skip_registry.py -q -m ""` at execution time and use its live output as the
authoritative violation list and count** — do not rely on the list above as final; treat it as
strong directional evidence that the true count exceeds CONTEXT.md's "~15+" estimate, not as a
locked number. Some of these are likely legitimate `importorskip` guards for genuinely optional
imports that just need a registry entry, not a deletion — each needs the same read-the-code judgment
as the 116 failures, not a blanket registration.

**Minor unrelated finding:** `@pytest.mark.skip_registry_gate` (used to tag the meta-test itself) is
not declared in `pyproject.toml`'s `markers = [...]` list, producing a `PytestUnknownMarkWarning`.
Not a failure, but cheap to fix in the same plan while touching this file (`markers` list already
lives at `pyproject.toml:152-155`).

## Failure Clusters (116 total, by root cause — verified via targeted re-runs this session)

This is the single most important table for the planner: **do not plan 116 individual tasks.** Most
failures collapse into a small number of systemic root causes. Cluster-level investigation was done
by running representative tests in isolation and reading the failing assertion/traceback; each
cluster below states its recommended disposition **category** — the planner still needs one ledger
row per test, but the reasoning is shared within a cluster.

| # | Cluster | Files (test count) | Root cause (verified) | Recommended disposition |
|---|---------|---------------------|------------------------|--------------------------|
| 1 | SSRF/DNS-blocked sandbox | `test_notify_email.py`(3), `test_notify_webhook.py`(5), `test_ticketing_servicenow.py`(6), `test_sensor_cmd.py`(9) = **23 tests** | `ValueError: SSRF blocked (dns_failure)` / `console URL blocked by SSRF allowlist — dns_failure` — this sandbox has no outbound DNS resolution. Confirmed by reading `test_sensor_cmd.py::test_push_posts_to_correct_url` stderr directly. | **quarantine, sub-reason `environment-dependent`** — pending confirmation these pass on a normal dev machine/CI runner with DNS. Do NOT delete; do NOT attempt to fix in this phase (D-01). |
| 2 | Playwright cross-test pollution | `test_reports_writer.py`(5), `test_report_injection_hardening.py`(4), `test_pdf_metadata_constants.py`(3), `test_writer.py`(1), `test_pdf_export.py`(1) = **14 tests** | `AttributeError: 'PlaywrightContextManager' object has no attribute '_playwr...'`. **Verified: every test in this cluster passes when run in isolation or as a small group** (`pytest tests/test_reports_writer.py tests/test_writer.py` → 7 passed). This is order-dependent global-state pollution (something earlier in the full run tears down a shared Playwright singleton), not a per-file defect. | **quarantine, sub-reason `flaky` (test-isolation / shared global state)** — investigate the shared Playwright fixture/singleton lifecycle as a single fix in Phase 150, not per-file. |
| 3 | Version staleness — environment (dist-info stale) | `test_version.py`(5) | `assert '5.10.0' == '5.11.0'`. Confirmed: `pyproject.toml` declares `version = "5.11.0"`, but `pip show quirk-scanner` reports `5.10.0` — the editable install's dist-info metadata was never refreshed after the version bump (`quirk/__init__.py` reads `importlib.metadata` first). Fixed by `pip install -e .` (no code/test change). | **quarantine, sub-reason `environment-dependent`** (stale local install), OR run `pip install -e .` as a one-time environment fix before this phase's own run — but this is *not* the narrow D-01 "test asserted stale value" exception (the test is correct; the environment is stale). Flag as an Open Question for planner confirmation — see below. |
| 4 | Version staleness — genuinely stale test assertions | `test_packaging.py::test_version_is_4_2_0`(1) expects `5.5.0`, `test_v41_gap_closure.py`(1) expects `4.4.0`/`4.1.0`, `test_cli_correctness.py::test_version_consistency`(1) expects `5.5.0` = **3 tests** | These tests hardcode version strings from 5+ milestones ago and were never updated or retired. | **fixed, per D-01's narrow exception** (correct the hardcoded assertion to current version) — OR **deleted-as-obsolete** if the test's entire premise (pinning a specific historical version number forever) is itself the defect; recommend deletion since a test that must be hand-edited every release is an anti-pattern, but this is Claude's-discretion-territory for the executor, not locked here. |
| 5 | `sensor_id` shape / AUDIT-08 regression | `test_auto_merge_trigger.py`(8), `test_sensor_push_id_revalidation.py`(2) = **10 tests** | `quirk/dashboard/api/routes/sensor.py:494` raises `400 Invalid sensor_id shape` from a new UUID-shape re-validation guard (`AUDIT-08`, added in a prior phase per the code comment "defense-in-depth"). Test fixtures use human-readable IDs like `"sensor-a"` / `"sensor-b"`, not UUIDs, so they now fail the new strict `_UUID_RE.match()` check. `test_sensor_push_id_revalidation.py` is the AUDIT-08 feature's own test file and fails on a *different* assertion (row-count mismatch: "9 SensorPush row(s) found" when fewer expected) — this one needs separate, closer investigation; it is not obviously the same defect as the fixture-ID mismatch. | **quarantine, sub-reason `outdated-fixture`** for `test_auto_merge_trigger.py` (8 tests — fixture predates the AUDIT-08 UUID guard). `test_sensor_push_id_revalidation.py`(2) needs individual investigation during execution — do not batch-classify with cluster 5's fixture explanation without confirming the row-count logic separately. |
| 6 | pip `--dry-run` extras-install tests | `test_install_all_excludes_impacket.py`, `test_install_all_excludes_pysnmp.py`, `test_snmp_scanner_contract.py::test_install_all_excludes_pysnmp`, `test_install_all_excludes_schemathesis.py`, `test_install_all_includes_notify.py`, `test_install_all_includes_tickets.py` = **6 tests** | All fail with generic `pip install --dry-run -e <repo>[all] FAILED`. **Verified: `test_install_all_excludes_impacket.py` passes in isolation** (9.39s). Same order/resource-contention shape as cluster 2 — likely full-suite-only flakiness (pip subprocess timeout or shared temp/cache contention under full-suite load), not a per-package regression. | **quarantine, sub-reason `flaky`** — re-verify each individually in isolation during execution before finalizing; do not assume all 6 share the exact same cause without a per-test isolation check (cheap: ~10s each). |
| 7 | Optional GCP extras missing | `test_gcs_reuse.py`(2) | `ModuleNotFoundError: No module named 'googleapiclient'` / `'google'`. Google Cloud Storage client libs are an optional extra not installed in this environment. | **quarantine, sub-reason `optional_extra`** — reuse the existing `optional_extra` category exactly as `broker_scanner`/`sslyze` entries do, this is not a new pattern. |
| 8 | Meta-gate self-failure | `test_skip_registry.py::test_no_unregistered_skips`(1) | The gate itself, per D-04 — see dedicated section above. | **fixed** (repair the 25-29 violations — register legitimate ones, delete/convert stale ones) — this is the one cluster where "fixed" applies to the gate's own currently-broken state, which is explicit groundwork D-04 calls for, not a D-01 violation. |
| 9 | Remaining individually-distinct failures | ~44 tests across ~30 files not covered by clusters 1-8 (e.g. `test_dashboard_scan_history.py`(5) `/api/compare` 400s, `test_jwt_scanner.py`(6) key-count assertions, `test_qramm_staleness.py`(2) `exit=-11` SIGSEGV crashes, `test_route_coverage.py`(1) missing `require_auth`, `test_qramm_evidence_bridge.py::test_no_risk_engine_import`(1), etc.) | Not clustered — each has a distinct failure signature (see raw list below) requiring its own read/grep pass. Several look like genuine drift from later phases changing an API shape the test never caught up to (e.g. `/api/compare` 400 — dashboard scan-history endpoint likely changed contract); `exit=-11` (SIGSEGV) in `test_qramm_staleness.py` warrants specific attention — a segfault in a CLI subprocess is unusual and worth a few extra minutes to rule out a native-library crash (cryptography/openssl binding) vs. a subprocess/pytest-capture artifact. | **No blanket disposition — plan one task-cluster per file or small file-group, each doing real grep/read investigation.** This is where most of the phase's actual effort budget goes. |

**Cluster arithmetic:** 23 + 14 + 5 + 3 + 10 + 6 + 2 + 1 = 64 tests accounted for by clusters 1-8;
the remaining ~52 tests (across the ~44 "individually distinct" cluster estimate plus files not
enumerated above — full raw list below has the complete 116) need per-test/per-file investigation
during execution. **Use the raw list below as the authoritative enumeration, not this table's counts**
— the table is a planning aid for clustering effort, not a substitute for the full list.

## Raw Full Failure List (116, ground truth 2026-08-11, `pytest -q -m ""`)

`[VERIFIED: live pytest run, this session]` — one entry per line, `test_id - failure_summary`:

```
tests/scanner/test_jwt_hardening.py::test_allow_insecure_jwks_uses_verify_false_and_emits_advisory - AssertionError: Expected at least one verify=False call when allow_insecure...
tests/scanner/test_jwt_hardening.py::test_scan_jwt_targets_propagates_flag - assert False
tests/test_auto_merge_trigger.py::test_all_sensors_in_triggers_merge - AssertionError: push failed 400: {"detail":"Invalid sensor_id shape"}
tests/test_auto_merge_trigger.py::test_auto_merge_disabled - AssertionError: push failed 400: {"detail":"Invalid sensor_id shape"}
tests/test_auto_merge_trigger.py::test_revoked_sensor_excluded - AssertionError: push failed 400: {"detail":"Invalid sensor_id shape"}
tests/test_auto_merge_trigger.py::test_mixed_token_sensor_is_required_for_all_in - AssertionError: push failed 400: {"detail":"Invalid sensor_id shape"}
tests/test_auto_merge_trigger.py::test_zero_token_sensor_not_counted_as_active - AssertionError: push failed 400: {"detail":"Invalid sensor_id shape"}
tests/test_auto_merge_trigger.py::test_merge_failure_isolated - AssertionError: push failed 400: {"detail":"Invalid sensor_id shape"}
tests/test_auto_merge_trigger.py::test_double_fire_harmless - AssertionError: push failed 400: {"detail":"Invalid sensor_id shape"}
tests/test_auto_merge_trigger.py::test_cadence_window_triggers - AssertionError: push failed 400: {"detail":"Invalid sensor_id shape"}
tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_success - KeyError: 'rabbitmq_version'
tests/test_broker_scanner_rabbitmq.py::test_enrich_rabbitmq_mgmt_401 - AssertionError: Expected {'mgmt_auth': 'rejected_401'}, got {}
tests/test_cbom_schema_validation.py::test_parametrize_set_matches_docker_compose_profiles - AssertionError: Drift between docker-compose.yml profiles and PROFILE_ENDPOINTS
tests/test_cli_correctness.py::test_version_consistency - AssertionError: quirk.__version__ is '5.10.0', expected '5.5.0'
tests/test_cli_correctness.py::test_no_quirk_scan_references - AssertionError: Found 'quirk scan' references (should be 'quirk --config') in repo
tests/test_cli_init.py::test_init_creates_config - AssertionError: config.yaml not created at temp dir
tests/test_cli_init.py::test_init_no_overwrite - FileNotFoundError: No such file or directory (temp dir)
tests/test_compliance_title_join.py::test_every_emitted_title_is_mapped_or_allowlisted - AssertionError: Emitted finding titles missing from COMPLIANCE_MAP and UNMAPPED allowlist
tests/test_dashboard_scan_history.py::test_compare_schema - AssertionError: Expected 200 from /api/compare; got 400
tests/test_dashboard_scan_history.py::test_compare_self - AssertionError: Expected detail='Cannot compare a scan to itself.'; got different detail
tests/test_dashboard_scan_history.py::test_compare_score_delta - AssertionError: Expected 200 from /api/compare; got 400
tests/test_dashboard_scan_history.py::test_compare_finding_diff - AssertionError: Expected 200 from /api/compare; got 400
tests/test_dashboard_scan_history.py::test_compare_endpoint_diff - AssertionError: Expected 200 from /api/compare; got 400
tests/test_dashboard_theme.py::test_primary_color_token - AssertionError: Expected '--primary: 210 100% 56%' token not found
tests/test_dashboard_theme.py::test_accent_color_token - AssertionError: Expected '--accent: 210 100% 56%' token not found
tests/test_db_migrate_cli.py::test_fresh_db_reports_every_column_added - sqlalchemy.exc.NoSuchTableError: sensor_tokens
tests/test_db_migrate_cli.py::test_dry_run_does_not_write - sqlalchemy.exc.NoSuchTableError: sensor_tokens
tests/test_db_migrate_cli.py::test_result_shape - sqlalchemy.exc.NoSuchTableError: sensor_tokens
tests/test_email_run_scan_wiring.py::test_email_branch_logger_calls_use_real_logger_signatures - AssertionError: quirk.logging_util.Logger.info must take exactly one non-self positional arg
tests/test_errors_cmd.py::test_lookup_single_known_returns_zero - AssertionError: 'QRK-INSTALL-001' not found in ANSI-colored output
tests/test_gap_closure.py::test_findings_quantum_label_dsa - AssertionError: Expected at least one Vulnerable finding for DSA, got: []
tests/test_gap_closure.py::test_findings_quantum_label_ecdsa - AssertionError: Expected at least one Vulnerable finding for ECDSA, got: []
tests/test_gcs_reuse.py::test_gcs_reuse_reads_sentinel_no_api_call - ModuleNotFoundError: No module named 'googleapiclient'
tests/test_gcs_reuse.py::test_gcs_reuse_zero_storage_buckets_list_call - ModuleNotFoundError: No module named 'google'
tests/test_identity_scanner_hardening.py::test_kdc_udp_decode_failure_logs - AttributeError: module 'quirk.scanner.kerberos_scanner' has no attribute 'decode...'
tests/test_identity_scanner_hardening.py::test_build_as_req_nonce_uses_secrets - NameError: name 'constants' is not defined
tests/test_init_db_idempotent.py::test_all_ensure_functions_idempotent - TypeError: _ensure_columns() missing 2 required positional arguments: 'table...'
tests/test_install_all_excludes_impacket.py::test_install_all_excludes_impacket - AssertionError: pip install --dry-run -e <repo>[all] FAILED (passes in isolation — see Cluster 6)
tests/test_install_all_excludes_pysnmp.py::test_install_all_excludes_pysnmp - AssertionError: pip install --dry-run -e <repo>[all] FAILED
tests/test_install_all_excludes_schemathesis.py::test_install_all_excludes_schemathesis - AssertionError: pip install --dry-run -e <repo>[all] FAILED
tests/test_install_all_includes_notify.py::test_install_all_includes_notify - AssertionError: pip install --dry-run -e <repo>[all] FAILED
tests/test_install_all_includes_tickets.py::test_install_all_includes_tickets - AssertionError: pip install --dry-run -e <repo>[all] FAILED
tests/test_install_errors.py::test_port_conflict_format - AssertionError: Expected QRK-INSTALL-004 in output; got empty
tests/test_install_errors.py::test_dashboard_missing_uvicorn_format - AssertionError: Expected QRK-INSTALL-002; got empty
tests/test_jwt_scanner.py::test_multi_key_jwks - assert 0 == 3
tests/test_jwt_scanner.py::test_jwt_rsa_key_size - assert 0 == 1
tests/test_jwt_scanner.py::test_jwt_ec_key_size - assert 0 == 1
tests/test_jwt_scanner.py::test_jwt_query_param_cred_ctx_appends_key_to_url - AssertionError: httpx.Client.get was never called
tests/test_jwt_scanner.py::test_jwt_no_cred_ctx_unchanged_behavior - assert 0 == 3
tests/test_jwt_scanner.py::test_append_query_param_continue_iteration_skips_conflicting_target - AssertionError: Expected >=3 endpoints from clean target; got 0
tests/test_notify_email.py::test_starttls_path_timeout_and_recipients - ValueError: SSRF blocked (dns_failure) for SMTP host 'smtp.example.com'
tests/test_notify_email.py::test_ssl_path_timeout_passed - ValueError: SSRF blocked (dns_failure) for SMTP host 'smtp.example.com'
tests/test_notify_email.py::test_no_login_when_smtp_user_none - ValueError: SSRF blocked (dns_failure) for SMTP host 'smtp.example.com'
tests/test_notify_webhook.py::test_no_hmac_when_key_env_not_set - ValueError: SSRF blocked (dns_failure) for webhook URL
tests/test_notify_webhook.py::test_hmac_header_present_when_key_set - ValueError: SSRF blocked (dns_failure) for webhook URL
tests/test_notify_webhook.py::test_hmac_absent_when_key_env_empty - ValueError: SSRF blocked (dns_failure) for webhook URL
tests/test_notify_webhook.py::test_body_omits_topology_keys - ValueError: SSRF blocked (dns_failure) for webhook URL
tests/test_notify_webhook.py::test_non_2xx_raises_runtime_error - ValueError: SSRF blocked (dns_failure) for webhook URL
tests/test_openapi_scanner.py::test_url_scope_accepts_bare_fqdn_target - AssertionError: Expected 'get' to have been called once. Called 0 times.
tests/test_packaging.py::test_version_is_4_2_0 - AssertionError: Expected 5.5.0, got '5.10.0'
tests/test_pdf_export.py::test_pdf_export_endpoint - AssertionError: Unexpected status: 500
tests/test_pdf_metadata_constants.py::test_pdf_title_is_constant - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_pdf_metadata_constants.py::test_pdf_author_is_constant - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_pdf_metadata_constants.py::test_pdf_renders_with_locked_context - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_phase135_docs_presence.py::test_required_sections_present - AssertionError: Phase 135 docs missing required sections: [('README.md', 'v...')]
tests/test_phase136_docs_presence.py::test_section9_deferred_topics_absent - AssertionError: §9 leaks deferred Phase 137 content: ['snmpv3']
tests/test_posture_scorefix125.py::test_gcp_kms_403_emits_scan_error - AssertionError: GCP Cloud KMS 403 (IAM permission denied) must produce a scan_error
tests/test_posture_scorefix125.py::test_gcp_sql_403_emits_scan_error - AssertionError: GCP Cloud SQL 403 (IAM permission denied) must produce a scan_error
tests/test_qramm_evidence_bridge.py::test_no_risk_engine_import - AssertionError: 'quirk.engine.risk_engine' found in import graph, expected absent
tests/test_qramm_evidence_bridge.py::test_unconfirmed_excluded_from_score - assert 422 == 200
tests/test_qramm_model_stale.py::test_is_qramm_model_stale_boundary[today1-True] - assert False is True
tests/test_qramm_models.py::TestInitDbQRAMMTables::test_ensure_qramm_tables_called_after_phase46 - AssertionError: _PHASE46_COLUMNS migration call not found in init_db
tests/test_qramm_staleness.py::test_qramm_status_cli_smoke_fresh - AssertionError: exit=-11 (SIGSEGV) stdout='' stderr=''
tests/test_qramm_staleness.py::test_qramm_status_cli_smoke_stale_via_override - AssertionError: expected exit=1 (STALE), got exit=-11 (SIGSEGV)
tests/test_report_injection_hardening.py::test_script_payload_in_cert_cn_is_escaped_in_html - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_report_injection_hardening.py::test_javascript_url_in_finding_recommendation_stripped - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_report_injection_hardening.py::test_db_stored_raw_payload_preserved - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_report_injection_hardening.py::test_script_payload_in_cert_cn_is_escaped_in_pdf - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_reports_writer.py::test_json_export_preserves_description - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_reports_writer.py::test_json_export_preserves_deprecation_phrase - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_reports_writer.py::test_html_report_has_description_column - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_reports_writer.py::test_docx_emitted_by_write_reports - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_reports_writer.py::test_docx_none_on_fail_not_in_output_files - AttributeError: PlaywrightContextManager (see Cluster 2)
tests/test_route_coverage.py::test_all_data_routes_have_auth_dependency - AssertionError: routes missing require_auth (AUTH-02 violation)
tests/test_safe_filter_audit.py::test_safe_filter_paired_with_sanitize - Failed: Jinja `| safe` filter usages without an upstream `| sanitize`
tests/test_scan_error_gate.py::test_scan_error_writes_use_safe_str - Failed: scan_error writes bypassing safe_str
tests/test_sensor_cmd.py::test_push_posts_to_correct_url - assert 1 == 0 (SSRF blocked, see Cluster 1)
tests/test_sensor_cmd.py::test_push_retry_on_5xx - AssertionError: 5xx should trigger retries (SSRF blocked, see Cluster 1)
tests/test_sensor_cmd.py::test_push_no_retry_on_4xx - AssertionError: 4xx must not trigger retry (SSRF blocked, see Cluster 1)
tests/test_sensor_cmd.py::test_push_connect_error_retries - AssertionError: Expected 5 retry attempts, got 0 (SSRF blocked, see Cluster 1)
tests/test_sensor_cmd.py::test_push_409_treated_as_success - assert 1 == 0 (SSRF blocked, see Cluster 1)
tests/test_sensor_cmd.py::test_spool_on_connect_failure - AssertionError: Expected 1 spooled file, found 0 (SSRF blocked, see Cluster 1)
tests/test_sensor_cmd.py::test_spool_flush_delivers_and_unlinks - assert 1 == 0 (SSRF blocked, see Cluster 1)
tests/test_sensor_cmd.py::test_spool_409_unlinks_file - assert 1 == 0 (SSRF blocked, see Cluster 1)
tests/test_sensor_cmd.py::test_spool_filename_is_uuid_pattern - assert 0 == 1 (SSRF blocked, see Cluster 1)
tests/test_sensor_push_id_revalidation.py::test_malformed_sensor_id_path_traversal_rejected - AssertionError: AUDIT-08 RED: 9 SensorPush row(s) found; malformed sensor_id
tests/test_sensor_push_id_revalidation.py::test_malformed_sensor_id_short_string_rejected - AssertionError: AUDIT-08 RED: 9 SensorPush row(s) found after malformed id
tests/test_sensor_windows_smoke.py::TestCleanShutdownOnKeyboardInterrupt::test_keyboard_interrupt_in_run_sensor_exits_130 - AssertionError: Expected exit code 0, 1, or 130 on KeyboardInterrupt, got -11 (SIGSEGV)
tests/test_skip_registry.py::test_no_unregistered_skips - Failed: unregistered skip markers found (see D-04 section above)
tests/test_snmp_scanner_contract.py::test_install_all_excludes_pysnmp - AssertionError: pip install --dry-run -e <repo>[all] FAILED
tests/test_ticketing_servicenow.py::test_create_incident - ValueError: SSRF blocked (dns_failure) for ServiceNow URL
tests/test_ticketing_servicenow.py::test_dedup_then_work_notes - ValueError: SSRF blocked (dns_failure) for ServiceNow URL
tests/test_ticketing_servicenow.py::test_correlation_id_is_fingerprint - ValueError: SSRF blocked (dns_failure) for ServiceNow URL
tests/test_ticketing_servicenow.py::test_credentials_not_in_logs - ValueError: SSRF blocked (dns_failure) for ServiceNow URL
tests/test_ticketing_servicenow.py::test_create_issue_missing_sys_id_raises_runtime_error - ValueError: SSRF blocked (dns_failure) for ServiceNow URL
tests/test_ticketing_servicenow.py::test_create_issue_non_json_response_raises_runtime_error - ValueError: SSRF blocked (dns_failure) for ServiceNow URL
tests/test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_true - assert None is not None
tests/test_tls_scanner_chain_verified.py::test_sslyze_success_chain_verified_false - assert None is not None
tests/test_v41_gap_closure.py::TestV41GapClosure::test_pyproject_version_field_is_4_1_0 - AssertionError: pyproject.toml does not contain 'version = "4.4.0"'
tests/test_vault_connector.py::test_pki_sha1_signed_ca_high_severity - RuntimeError: openssl SHA1 cert failed
tests/test_version.py::test_package_version_matches_pyproject - AssertionError: assert '5.10.0' == '5.11.0' (stale dist-info, see Cluster 3)
tests/test_version.py::test_cbom_platform_version_matches_pyproject - AssertionError: assert '5.10.0' == '5.11.0' (stale dist-info, see Cluster 3)
tests/test_version.py::test_reports_platform_version_matches_pyproject - AssertionError: assert '5.10.0' == '5.11.0' (stale dist-info, see Cluster 3)
tests/test_version.py::test_intelligence_config_default_matches_pyproject - AssertionError: assert '5.10.0' == '5.11.0' (stale dist-info, see Cluster 3)
tests/test_version.py::test_cli_version_subprocess - Failed: CLI --version returned non-zero (stale dist-info, see Cluster 3)
tests/test_writer.py::test_run_stats_ports_and_hosts_scanned - AttributeError: PlaywrightContextManager (see Cluster 2)
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Skip/quarantine tracking | A new registry file or CSV ledger format | Extend `tests/skip_registry.py`'s existing `ALLOWED_SKIPS` tuple shape with a new `category` value | D-02 explicitly reuses this; a parallel system would fragment enforcement across two mechanisms |
| Detecting unregistered skips | A new linter/grep script | Extend the existing `tests/test_skip_registry.py` AST walker to also catch `@pytest.mark.skip`/`xfail` | One AST walker, one source of truth, consistent with the `skipif` detection already there |

**Key insight:** Every piece of quarantine machinery this phase needs already exists from Phase 41.
The only genuinely new work is (a) the ledger document itself, (b) extending the AST walker's
detection scope if the planner takes the recommended option in the D-03 implication above, and (c)
adding a new `category` string.

## Common Pitfalls

### Pitfall 1: Re-deriving the failure count from CONTEXT.md instead of a fresh run
**What goes wrong:** Planning against the 108-count snapshot produces a ledger that's already wrong
before Wave 0 starts, and the count won't match Success Criterion 2's exact-match requirement.
**Why it happens:** CONTEXT.md's snapshot is authoritative-looking (dated, detailed) but was
captured with a command that still applied the default `-m 'not slow'` filter despite being
described as unfiltered.
**How to avoid:** Always re-run `pytest -q -m ""` (not bare `pytest -q`) immediately before writing
the ledger, and use that run's count as ground truth.
**Warning signs:** A "N deselected" line in the pytest summary means slow tests were excluded —
that run does not satisfy Success Criterion 1.

### Pitfall 2: Treating full-suite-only failures as per-file defects
**What goes wrong:** Clusters 2 and 6 (Playwright pollution, pip dry-run flakiness — 20 tests
combined) look like 20 separate defects if you only read the full-suite log, but both are
order/isolation artifacts that vanish when the same tests run standalone. Writing 20 separate
"quarantined: wrong-assumption" ledger rows with 20 different investigations wastes the phase's
effort budget and produces a worse (harder to fix in Phase 150) ledger than one row per cluster
citing the shared root cause.
**How to avoid:** For every failure, run it once via `pytest tests/test_X.py::test_Y -q -m ""` in
isolation before writing its disposition. If it passes in isolation, the disposition reason should
say so explicitly ("passes standalone, full-suite-only — likely shared global state/test-order
pollution") rather than inventing a per-test explanation.
**Warning signs:** `AttributeError` on framework/library internals (not application code), or
generic subprocess/dry-run failures with no test-specific detail in the message.

### Pitfall 3: Confusing "environment stale" with "test asserts a stale value" (D-01's exception)
**What goes wrong:** `test_version.py`'s 5 failures look identical in symptom (version mismatch) to
`test_packaging.py`'s 1 failure, but the root cause is inverted: `test_version.py` is *correct* and
the local editable install is stale (`pip install -e .` fixes it with zero code/test changes);
`test_packaging.py` hardcodes a version from 3+ major versions ago and *is* the stale artifact.
Applying D-01's "fixed" exception to `test_version.py` would mean editing a correct test to match a
wrong environment — backwards.
**How to avoid:** Before writing "fixed" for any version-mismatch test, check which side is actually
stale: `python -c "import quirk; print(quirk.__version__)"` vs. `grep '^version' pyproject.toml` vs.
`pip show quirk-scanner`. If the installed package metadata disagrees with `pyproject.toml`, the fix
is `pip install -e .`, not a test edit.
**Warning signs:** Multiple tests in the same file expecting the *same* version string that matches
`pyproject.toml` exactly — that's the environment-stale pattern, not the hardcoded-stale-test pattern.

### Pitfall 4: Assuming `@pytest.mark.skip` needs no registry entry because the gate doesn't flag it
**What goes wrong:** Since the AST walker doesn't detect bare `@pytest.mark.skip`, an executor could
quarantine all 116 tests with `@pytest.mark.skip(reason=...)` and never touch `ALLOWED_SKIPS` — the
gate would stay green, but Success Criterion 3 ("machine-checkable... not silently passing or
invisibly excluded") would be violated in spirit, since nothing actually verifies the reason string
references the ledger.
**How to avoid:** Either extend the walker (recommended, see D-03 implication section) or manually
enforce a project convention/review step that every `skip`/`xfail` addition also gets a registry
entry regardless of gate coverage.
**Warning signs:** A grep for `pytest.mark.skip(` or `pytest.mark.xfail(` in `tests/` finding entries
with no corresponding `ALLOWED_SKIPS` row.

## Code Examples

### Existing `ALLOWED_SKIPS` entry shape (follow exactly for the 116 new entries)
```python
# Source: tests/skip_registry.py (read directly this session)
ALLOWED_SKIPS = [
    ("test_broker_scanner_kafka.py", 12, "optional_extra", "broker_scanner is [motion]; D-05"),
    # ... new pattern for this phase:
    ("test_notify_webhook.py", 45, "pre_existing_triage_149",
     "TRIAGE-149: environment-dependent (SSRF DNS-blocked sandbox); see docs/test-triage-149.md#test-notify-webhook-test-no-hmac-when-key-env-not-set"),
]
```

### AST walker detection gap (what currently passes silently)
```python
# tests/test_skip_registry.py:57-68 — _is_pytest_skipif_decorator only matches "skipif"
def _is_pytest_skipif_decorator(node: ast.AST) -> bool:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute) and target.attr == "skipif":   # <- "skip" or "xfail" never matches
        ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| No general pytest CI job | (Phase 150, SUITE-03, out of scope here) | Not yet — deferred to next phase | 116 failures have been invisible to CI since ~Phase 97 per REQUIREMENTS.md SUITE-01 framing |
| `ALLOWED_SKIPS` covers 2 categories (`optional_extra`, `live_infra`) | This phase adds a 3rd category (`pre_existing_triage_149`) | This phase | Keeps the ~108-116 triage entries filterable/countable separately, per D-02 |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Clusters 1 (SSRF/DNS) and 3 (dist-info stale version) will resolve cleanly outside this sandbox (normal dev machine / GitHub Actions runner with DNS and a fresh `pip install`) | Failure Clusters table, Pitfall 3 | If DNS-blocking or install staleness is actually present in the target CI environment too, "environment-dependent" quarantine reasoning would be wrong and these should instead be treated as real failures needing a different fix in Phase 150 |
| A2 | The AUDIT-08 `sensor_id` UUID-shape guard (cluster 5) is intentional, correct, currently-shipped behavior and the *test fixtures* are what's outdated (not the reverse — that AUDIT-08 itself has a bug) | Failure Clusters table, cluster 5 | If AUDIT-08's UUID guard is itself over-strict or buggy, quarantining the fixture-mismatch tests would hide a real product defect rather than a test staleness issue — Phase 150 should verify AUDIT-08's correctness independently, not just accept this phase's fixture-outdated framing |
| A3 | The `TESTS_DIR.glob("*.py")` non-recursive scope in `test_skip_registry.py` (which skips `tests/scanner/*.py`, including `test_jwt_hardening.py`) is either intentional or a second defect this phase should decide on, not something to leave ambiguous | Confirmed Mechanics section | If left unaddressed, any `tests/scanner/*.py` skip/xfail markers added during triage silently bypass the gate entirely, which could hide non-compliant quarantines from future audits |

**All three assumptions above should be raised as explicit planner/executor decisions before Wave 0
tasks are written — they are not free-standing research conclusions the planner can silently adopt.**

## Open Questions

1. **Does `pip install -e .` (refreshing the stale dist-info) count as an in-scope environment fix
   for this phase, or does it require its own "fixed" ledger row citing D-01's exception even though
   it's not a code/test edit?**
   - What we know: it resolves cluster 3 (5 `test_version.py` failures + likely `test_cli_correctness.py::test_version_consistency`) with zero source changes.
   - What's unclear: D-01 is written narrowly around "the test itself was asserting something already-stale" — this is the inverse case (environment is stale). CONTEXT.md does not address this scenario.
   - Recommendation: Treat as in-scope hygiene (not a "fix" under D-01's meaning) — run `pip install -e .` once, record it as a ledger note, and move on; do NOT count it as one of the "fixed" dispositions since it required no judgment call about the test's correctness.

2. **Should the AST walker be extended to detect `@pytest.mark.skip`/`xfail` in this phase (per the
   D-03 implication above), or is that scope creep beyond "disposition-only"?**
   - What we know: without the extension, the gate's "machine-checkable" guarantee (Success Criterion 3) is partial — it only enforces registration for `skip()`/`skipif`, not `skip`/`xfail` decorators.
   - What's unclear: whether extending the walker counts as "fixing" per D-01, or as legitimate quarantine-mechanism scope per D-02 (which explicitly says "both built in Phase 41" are reused, implying the gate's correctness is fair game).
   - Recommendation: In scope — it's infrastructure for the quarantine mechanism itself (D-02's domain), not a fix to a failing test's implementation (D-01's domain). Flag for explicit planner confirmation.

3. **`test_sensor_push_id_revalidation.py`'s 2 failures ("9 SensorPush row(s) found" — a count
   mismatch, not the `sensor-a`-shape mismatch of cluster 5) — what's actually wrong?**
   - What we know: this file's stated purpose (per its name and the AUDIT-08 code comment) is to be the test suite *for* the sensor_id shape guard itself.
   - What's unclear: this research pass did not have budget to trace the row-count assertion logic; it may be a genuine implementation bug in AUDIT-08's cleanup/rollback path (worth flagging to Phase 150 as a real regression, not quarantine-and-defer) or a fixture issue like cluster 5.
   - Recommendation: Dedicate a specific, non-batched investigation task to this pair during execution — do not fold it into cluster 5's "outdated-fixture" reasoning without verifying.

## Recommended Ledger Format

**Location:** `docs/test-triage-149.md` — matches the exact path CONTEXT.md's own D-03 example
reason string already cites (`"TRIAGE-149: see docs/test-triage-149.md#<test-id>"`), so this is
effectively pre-selected by the discussion, not a fresh discretionary choice.

**Structure:** One markdown table (or one row per test in a flat list — table is more scannable at
116 rows) with columns: `Test ID | Disposition | Sub-reason | Evidence/Notes | Registry entry?`.
Group rows under `##` headings by the cluster numbers above (1-9) so the document is both
per-test (satisfies Success Criterion 2's exact-count requirement — 116 rows, countable) and
navigable (satisfies human readability — nobody wants a flat 116-row unsorted table).

Recommended per-row anchor convention for `reason=` string linkage: use the test's fully-qualified
node ID with `::` and `.` replaced by `-` for the markdown anchor (e.g.
`test_notify_webhook.py::test_no_hmac_when_key_env_not_set` → anchor
`#test_notify_webhookpy-test_no_hmac_when_key_env_not_set`, standard GitHub-flavored-markdown
slugification — verify actual anchor generation in whatever renders `docs/*.md` for this project,
likely just GFM on GitHub, before finalizing the reason-string format across 116 entries).

**Exact-count reconciliation:** The ledger's own header should state the exact `pytest -q -m ""`
summary line it was built against (e.g. "Built against: 116 failed, 3107 passed, 17 skipped —
2026-08-11") so Success Criterion 2 is checkable by re-running the suite and diffing counts, not by
eyeballing.

## Recommended Plan/Wave Structure

Given 116 failures / 52 files / a 25-29-item D-04 backlog, recommend:

- **Plan 1 (must run first, blocks everything else):** Repair `test_no_unregistered_skips` (D-04) —
  triage each of the current violations to registered/deleted, add the new
  `pre_existing_triage_149` category constant, and (per Open Question 2) decide + implement the
  `skip`/`xfail` AST-detection extension if the planner confirms it's in scope. This must land first
  because every subsequent plan's quarantine markers need a *working* gate to verify against.
- **Plans 2-N (one per cluster or small cluster-group, parallelizable):** One plan per row of the
  Failure Clusters table (clusters 1, 2, 3+4 combined, 5, 6, 7 can each be a single plan since they
  share root-cause reasoning; cluster 9's ~52 remaining tests should be split into 3-5 plans grouped
  by file-affinity or subsystem, not attempted as one plan — each of those still needs real per-test
  grep/read work, not blanket dispositions). Each plan: investigate → write ledger rows → add
  quarantine markers + registry entries → verify gate stays green.
- **Final plan:** Reconcile the ledger's total row count against a final `pytest -q -m ""` run
  (Success Criterion 2), and do a final pass confirming no test was left with an implicit disposition
  (every row must be non-empty for disposition + sub-reason).

This structure keeps each plan's task list scoped to a coherent investigation (not "triage 15
unrelated tests"), matches the effort-budget insight that ~64 of 116 failures are pre-clustered by
root cause already, and isolates the one groundwork dependency (D-04 gate repair) as a hard
prerequisite rather than something that could get skipped or done last.

## Project Constraints (from CLAUDE.md)

- PEP 8 for all Python changes; keep diffs minimal.
- After changes, run `python -m compileall` and relevant tests — applies to any AST-walker
  extension code touched in the D-04 repair plan.
- No new chaos-lab, CLI, config, or report-surface changes are introduced by this phase, so most of
  CLAUDE.md's "Per-Phase Documentation Checklist" doc-sync rows do not apply. The one new artifact
  (`docs/test-triage-149.md`) is not itself one of the tracked doc types in that checklist (it isn't
  a getting-started/operators-guide/report-interpretation category) — no Obsidian sync obligation
  identified for this specific file, but confirm this reading with the user if uncertain, since the
  checklist is stated as mandatory for every phase.
- Version-bump doc-sync row does NOT apply — this phase does not change `quirk.__version__` (Cluster
  3's `pip install -e .` refresh is an environment-metadata sync only, not a version bump).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| SUITE-01 | Every pre-existing full-suite failure has an explicit written disposition — fixed, quarantined with a reason, or deleted as obsolete | Ground Truth Correction section establishes the authoritative 116-failure list to disposition; Failure Clusters table + raw list give the planner the material to build per-test tasks; D-04 section + skip-registry mechanics confirm the exact machine-checkable mechanism (Success Criterion 3) and its current gap (bare `skip`/`xfail` undetected) |

</phase_requirements>

## Sources

### Primary (HIGH confidence — all read/run directly in this session)
- `tests/skip_registry.py` — full contents read via `cat -n`
- `tests/test_skip_registry.py` — full contents read via `cat -n`
- `pyproject.toml` lines ~140-160 — `markers`, `addopts`, `testpaths` config
- `quirk/dashboard/api/routes/sensor.py:460-500` — AUDIT-08 sensor_id shape guard source
- `quirk/__init__.py` — `__version__` resolution logic (importlib.metadata first, pyproject fallback)
- Live `pytest -q -m ""` full-suite run (887.84s, 3240 tests collected, 116 failed)
- Live `pytest tests/test_skip_registry.py -q -m ""` run (unregistered-skip violations)
- Targeted isolation re-runs: `test_reports_writer.py`+`test_writer.py`, `test_auto_merge_trigger.py::test_auto_merge_disabled`, `test_sensor_cmd.py::test_push_posts_to_correct_url`, `test_install_all_excludes_impacket.py`
- `pip show quirk-scanner` vs. `grep '^version' pyproject.toml` vs. `python -c "import quirk; print(quirk.__version__)"`

### Secondary (MEDIUM confidence)
- None — no external/web sources were needed for this phase; it is entirely codebase-internal investigation.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A — no new dependencies
- Skip-registry mechanics: HIGH — read directly, cross-verified against a live gate run
- Failure enumeration: HIGH — live run this session, but will drift (explicitly time-boxed, re-run required)
- Cluster root-cause attribution: HIGH for clusters 1, 2, 3, 5, 6, 7 (isolation-verified or source-read); MEDIUM for cluster 4 (inferred from version-string content, not independently re-run); LOW/unverified for the ~52 tests in cluster 9 (raw list only, no individual investigation done — flagged as the phase's main remaining work)

**Research date:** 2026-08-11
**Valid until:** Effectively immediate — the failure count and cluster composition are point-in-time
and will drift as other in-flight phases (148, 150 prep, etc.) land commits. Re-run `pytest -q -m ""`
at the start of execution, not just at planning time, and treat any count/list divergence from this
document as expected, not a research error.
