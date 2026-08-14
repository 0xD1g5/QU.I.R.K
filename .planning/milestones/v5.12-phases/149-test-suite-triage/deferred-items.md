# Deferred Items — Phase 149 Test Suite Triage

Out-of-scope discoveries logged during plan execution, per the executor's scope-boundary rule
(only fix issues directly caused by the current task's changes).

## 149-04

- `tests/test_cli_correctness.py::test_no_quirk_scan_references` fails (found `quirk scan`
  references in docs/CLI help text that should read `quirk --config`). Discovered incidentally
  while re-running `tests/test_cli_correctness.py` for Cluster 4 verification (Task 2). Not part
  of Cluster 3/4/7 (RESEARCH.md row 213 lists it as a separate, pre-existing failure). Not fixed
  here — out of scope for this plan.

## 149-06

- `tests/test_openapi_scanner.py` has 6 additional failing tests (`test_local_file_parse`,
  `test_local_file_security_scheme_rows`, `test_url_scope_rejected`, `test_oversize_rejected`,
  `test_external_ref_ssrf_guard`, `test_openapi_plaintext_server_evidence_counter`) discovered
  while running the file standalone for Task 3's `test_url_scope_accepts_bare_fqdn_target`
  verification. All 6 fail because `openapi-spec-validator` (a core `pyproject.toml` dependency,
  not extras-gated) is not installed in this sandbox venv — every scan_openapi_spec() call
  degrades to a single `"openapi-spec-validator not installed"` endpoint. None of the 6 appear
  in 149-RESEARCH.md's original failure catalog (a venv-completeness gap specific to this
  sandbox, not part of the ~102 tracked pre-existing failures) and none were named in
  149-06-PLAN.md's task list. Not fixed here — out of scope for this plan; if reproducible
  outside this sandbox, file as a new Phase 150 (or later) investigation.
