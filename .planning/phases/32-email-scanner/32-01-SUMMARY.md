---
phase: 32-email-scanner
plan: "01"
subsystem: email-scanner
tags: [email-scanner, testing, scaffolding, tdd, quirk, sslyze]
dependency_graph:
  requires: []
  provides:
    - tests/test_email_scanner.py
    - tests/fixtures/email/__init__.py
  affects: []
tech_stack:
  added: []
  patterns:
    - pytest.importorskip soft-skip for Wave 0 RED state
    - MagicMock sslyze ServerScanResult mock helper
    - smtplib/imaplib/poplib fallback mock helpers
key_files:
  created:
    - tests/test_email_scanner.py
    - tests/fixtures/email/__init__.py
  modified: []
decisions:
  - "Used pytest.importorskip (not hard import) so Wave 0 reports SKIP not ERROR — plan specifies both outcomes as acceptable at this stage"
  - "Separate _make_mock_sslyze_result() and _make_mock_sslyze_scanner() helpers keep test bodies concise and mirror test_dnssec_scanner.py pattern"
  - "sslyze enums (ServerScanStatusEnum, ScanCommandAttemptStatusEnum) imported with a soft guard so test file is parseable even when sslyze absent"
  - "smtplib/imaplib/poplib mocked at module attribute level (@patch qualifier) matching the plan requirement — no live network in any test"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 32 Plan 01: Email Scanner Test Scaffolding Summary

**One-liner:** RED test scaffolding for email scanner — 17 pytest stubs covering EMAIL-00 through EMAIL-10 and STRUCT-01 using sslyze/smtplib/imaplib/poplib mocks; module skipped via importorskip until Plan 03.

## What Was Built

### Task 1 — tests/test_email_scanner.py + tests/fixtures/email/__init__.py

Created `tests/test_email_scanner.py` (524 lines, 17 test functions) with:

- Module-level `pytest.importorskip("quirk.scanner.email_scanner")` guard — the entire module is reported as SKIP when `email_scanner.py` does not exist (Wave 0 / Plan 01). After Plan 03 creates the module, importorskip becomes a no-op and all 17 tests run.
- Two mock helper functions:
  - `_make_mock_sslyze_result(tls_version, cipher, completed)` — builds a full MagicMock sslyze `ServerScanResult` with cipher suites, cert deployments, and status enum populated.
  - `_make_mock_sslyze_scanner(result)` — wraps result into a scanner mock with `queue_scans()` / `get_results()` interface.
  - `_make_mock_smtp_sock(tls_version, cipher_name, der_bytes)` — builds a mock `ssl.SSLSocket` for smtplib/imaplib/poplib fallback paths.

Test coverage per requirement:

| Test | Requirement | Status |
|------|-------------|--------|
| test_email_scan_json_column_exists | EMAIL-00 | RED (skipped) |
| test_scan_one_smtp_starttls_sslyze_port25 | EMAIL-01 | RED |
| test_scan_one_smtp_starttls_sslyze_port587 | EMAIL-01 | RED |
| test_scan_one_smtps_sslyze_port465 | EMAIL-02 | RED |
| test_scan_one_imap_starttls_sslyze_port143 | EMAIL-03 | RED |
| test_scan_one_imaps_sslyze_port993 | EMAIL-04 | RED |
| test_scan_one_pop3_starttls_sslyze_port110 | EMAIL-05 | RED |
| test_scan_one_pop3s_sslyze_port995 | EMAIL-06 | RED |
| test_fallback_smtp_starttls_returns_tls_metadata | EMAIL-07 | RED |
| test_fallback_imap_starttls_returns_tls_metadata | EMAIL-07 | RED |
| test_fallback_pop3_starttls_returns_tls_metadata | EMAIL-07 | RED |
| test_connection_refused_non_fatal_port25 | D-03/EMAIL-01 | RED |
| test_service_detail_labels_match_spec | EMAIL-10 | RED |
| test_email_ports_table_has_seven_entries | EMAIL_PORTS shape | RED |

### Task 2 — STRUCT-01 tests appended to test_email_scanner.py

Three additional tests appended:

| Test | Requirement | Status |
|------|-------------|--------|
| test_session_start_propagation | STRUCT-01 | RED |
| test_no_datetime_now_inside_scanner | STRUCT-01/ISSUE-3 | RED |
| test_email_ports_starttls_enum_alignment | EMAIL-01..06 | RED |

Created `tests/fixtures/email/__init__.py` as package marker for future recorded DER handshake fixtures.

## Deviations from Plan

None — plan executed exactly as written.

- Tasks 1 and 2 committed together (single file set, no intermediate state needed).
- sslyze enum guard added at module level (Rule 2 pre-emption: ensures test collection works when sslyze absent, matching the soft-import contract the scanner module will use).

## RED State Verification

```
$ python3 -m pytest tests/test_email_scanner.py -x -q
1 skipped in 0.01s

$ python3 -m py_compile tests/test_email_scanner.py
(exits 0 — no syntax errors)

$ grep -v '^#' tests/test_email_scanner.py | grep -c "^def test_"
17

$ grep -c "MagicMock\|patch" tests/test_email_scanner.py
45
```

The skip is intentional: `pytest.importorskip` silently skips the module when `quirk/scanner/email_scanner.py` does not exist. Plan 03 creates the module and makes all 17 tests GREEN.

## Known Stubs

None — test file contains no placeholder stubs that would prevent its goal. The importorskip mechanism IS the intentional stub mechanism for Wave 0.

## Self-Check: PASSED

- tests/test_email_scanner.py exists: FOUND
- tests/fixtures/email/__init__.py exists: FOUND
- Commit a0fffea exists: FOUND
- 17 test functions: CONFIRMED
- 45 MagicMock/patch occurrences: CONFIRMED
- py_compile exits 0: CONFIRMED
