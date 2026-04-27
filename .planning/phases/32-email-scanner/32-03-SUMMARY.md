---
phase: 32-email-scanner
plan: "03"
subsystem: email-scanner
tags: [email-scanner, sslyze, starttls, smtplib, imaplib, poplib, scanner-module, struct-01, quirk]

dependency_graph:
  requires:
    - 32-01-test-scaffolding
    - 32-02-db-config-foundation
  provides:
    - quirk/scanner/email_scanner.py
    - "scan_email_targets(hosts, timeout, logger=None, session_start=None) -> List[CryptoEndpoint]"
    - "scan_one_email(host, port, protocol_label, starttls_enum, timeout, logger=None, session_start=None) -> CryptoEndpoint"
    - "EMAIL_PORTS table (7 rows: 25/465/587/143/993/110/995)"
  affects:
    - 32-04-risk-engine-findings
    - 32-05-run-scan-integration

tech-stack:
  added:
    - "sslyze.ProtocolWithOpportunisticTlsEnum (soft import — already in pyproject motion extras)"
    - "stdlib smtplib/imaplib/poplib STARTTLS handshake parsing"
  patterns:
    - "4-function scanner shape: _scan_one_sslyze + _scan_one_fallback + scan_one + scan_targets (mirrors tls_scanner.py)"
    - "Module-level stub names (SslyzeScanner=None, ProtocolWithOpportunisticTlsEnum class) when sslyze absent — keeps test patch targets resolvable"
    - "Duck-typed _peer_metadata() helper — accepts SSLSocket or MagicMock with .version()/.cipher()/.getpeercert()"
    - "Reuse, do not duplicate: _pubkey_info / _extract_sans imported from tls_scanner"

key-files:
  created:
    - quirk/scanner/email_scanner.py
  modified: []

key-decisions:
  - "Module-level sslyze stub names added in the except ImportError branch (SslyzeScanner=None plus stub enum classes) — required so tests can patch quirk.scanner.email_scanner.SslyzeScanner without AttributeError when sslyze is not installed in the test environment"
  - "Sslyze gate switched from `if not SSLYZE_AVAILABLE` to `if SslyzeScanner is None` so tests that patch SslyzeScanner can drive the sslyze code path even though the original module-level import failed"
  - "Duck-typed _peer_metadata() rather than strict isinstance(ssl.SSLSocket) — MagicMock fixtures in tests/test_email_scanner.py do not use spec=ssl.SSLSocket"
  - "_scan_one_sslyze_email constructs CryptoEndpoint with protocol='' so the orchestrator owns final protocol/service_detail/scanned_at assignment (matches Plan 03 contract)"

requirements-completed: [STRUCT-01, EMAIL-01, EMAIL-02, EMAIL-03, EMAIL-04, EMAIL-05, EMAIL-06, EMAIL-07, EMAIL-10]

metrics:
  duration: "~12 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 0
---

# Phase 32 Plan 03: Email Scanner Module Summary

**One-liner:** Canonical 4-function email TLS scanner (`scan_email_targets`, `scan_one_email`, `_scan_one_sslyze_email`, `_scan_one_fallback_email`) covering all 7 email ports via sslyze (`ProtocolWithOpportunisticTlsEnum.{SMTP,IMAP,POP3}` for STARTTLS, direct TLS for SMTPS/IMAPS/POP3S) with stdlib `smtplib`/`imaplib`/`poplib` fallback — turns the 17 RED tests from Plan 01 GREEN.

## What Was Built

### `quirk/scanner/email_scanner.py` — 556 lines

**Public symbols:**

| Symbol | Kind | Purpose |
|---|---|---|
| `EMAIL_PORTS` | list | 7-row `(port, protocol_label, service_detail_prefix, starttls_enum_or_None)` table |
| `SSLYZE_AVAILABLE` | bool | True if sslyze import succeeded |
| `scan_email_targets(hosts, timeout, logger=None, session_start=None)` | function | Top-level driver — fans out hosts × 7 ports via `ThreadPoolExecutor` |
| `scan_one_email(host, port, protocol_label, starttls_enum, timeout, logger=None, session_start=None)` | function | Per-target orchestrator: sslyze → fallback; sets protocol/service_detail/scanned_at |
| `_scan_one_sslyze_email(host, port, starttls_enum, timeout, logger=None)` | function | Primary sslyze probe; returns `Optional[CryptoEndpoint]` |
| `_scan_one_fallback_email(host, port, protocol_label, timeout, logger=None)` | function | Stdlib fallback; never raises |
| `_fallback_smtp_starttls / _fallback_imap_starttls / _fallback_pop3_starttls / _fallback_implicit_tls` | functions | Per-protocol handshake helpers — return `(tls_version, cipher_name, der_bytes)` |
| `_peer_metadata(ssock)` | function | Duck-typed extractor for `version()/cipher()/getpeercert()` (works with `ssl.SSLSocket` and `MagicMock`) |

**Reused (not redefined):**
- `_pubkey_info` and `_extract_sans` imported from `quirk.scanner.tls_scanner` (D-10 — explicitly forbids duplication).

**EMAIL_PORTS rows:**

| port | protocol_label | starttls_enum |
|------|----------------|---------------|
| 25 | SMTP-STARTTLS | `ProtocolWithOpportunisticTlsEnum.SMTP` |
| 465 | SMTPS | `None` (implicit TLS) |
| 587 | SMTP-STARTTLS | `ProtocolWithOpportunisticTlsEnum.SMTP` |
| 143 | IMAP-STARTTLS | `ProtocolWithOpportunisticTlsEnum.IMAP` |
| 993 | IMAPS | `None` (implicit TLS) |
| 110 | POP3-STARTTLS | `ProtocolWithOpportunisticTlsEnum.POP3` |
| 995 | POP3S | `None` (implicit TLS) |

## Test Status: RED → GREEN

```
$ python3 -m pytest tests/test_email_scanner.py -x -q
..................                                                       [100%]
18 passed in 0.22s
```

All 17 scanner tests + 1 DB-column test = 18 total. Tests cover:

| Requirement | Tests passing |
|---|---|
| EMAIL-00 (DB column, idempotent migration) | 2 |
| EMAIL-01 (SMTP-STARTTLS ports 25, 587) | 2 |
| EMAIL-02 (SMTPS port 465) | 1 |
| EMAIL-03 (IMAP-STARTTLS port 143) | 1 |
| EMAIL-04 (IMAPS port 993) | 1 |
| EMAIL-05 (POP3-STARTTLS port 110) | 1 |
| EMAIL-06 (POP3S port 995) | 1 |
| EMAIL-07 (stdlib fallback for SMTP/IMAP/POP3 STARTTLS) | 3 |
| D-03 (CONNECTION_REFUSED non-fatal) | 1 |
| EMAIL-10 (service_detail label format for all 7 ports) | 1 |
| EMAIL_PORTS table shape | 1 |
| STRUCT-01 (session_start propagation, no bare datetime.now()) | 2 |
| EMAIL_PORTS starttls_enum alignment | 1 |

## Regression Check

```
$ python3 -m pytest tests/ -q --ignore=tests/test_email_scanner.py
6 failed, 493 passed, 5 skipped
```

All 6 failures are the documented pre-existing baseline (packaging/version drift in `test_cli_correctness`, `test_dashboard_wiring`, `test_identity_surface`, `test_packaging`, `test_v41_gap_closure`) — unrelated to this plan. **No new regressions introduced.**

## Acceptance Criteria — All Met

| Criterion | Result |
|---|---|
| `python3 -m compileall quirk/scanner/email_scanner.py` exits 0 | PASS |
| `wc -l quirk/scanner/email_scanner.py` ≥ 350 | 556 |
| 4 main `def` matches | 4 |
| 4 fallback helper `def` matches | 4 |
| `from quirk.scanner.tls_scanner import _pubkey_info` count | 1 |
| Local `_pubkey_info` / `_extract_sans` redefinitions | 0 |
| `EMAIL_PORTS` occurrences | 7 |
| `ProtocolWithOpportunisticTlsEnum` occurrences | 8 |
| Bare `datetime.now(` outside `session_start or` | 0 |
| `enumerate_tls_capabilities` references (must be 0) | 0 |
| All 17 (18 incl. DB) tests pass | PASS |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Module-level stub names required when sslyze absent**

- **Found during:** Task 2 (initial test run after Task 1 implementation)
- **Issue:** Tests use `@patch("quirk.scanner.email_scanner.SslyzeScanner")` but the original `try/except ImportError` left `SslyzeScanner` undefined when sslyze is not installed in the test env, raising `AttributeError: module ... does not have the attribute 'SslyzeScanner'` at patch entry.
- **Fix:** Added stub assignments in the `except ImportError` branch:
  - `SslyzeScanner = None` (and `ServerScanRequest`, `ServerNetworkLocation`, `ScanCommand`, `ServerNetworkConfiguration`)
  - Stub `class` definitions for `ScanCommandAttemptStatusEnum`, `ServerScanStatusEnum`, `ProtocolWithOpportunisticTlsEnum` mirroring the test file's own fallback stubs.
  - Switched the `_scan_one_sslyze_email` gate from `if not SSLYZE_AVAILABLE` to `if SslyzeScanner is None` so a test that patches `SslyzeScanner` to a `MagicMock` actually drives the sslyze code path.
- **Files modified:** quirk/scanner/email_scanner.py (single file)
- **Verification:** All 18 tests pass.
- **Committed in:** d5eb3b9

**2. [Rule 3 - Blocking] Duck-typed peer metadata extraction**

- **Found during:** Task 2 (preemptively, while reading test fixtures)
- **Issue:** Tests build mock SSLSockets via plain `MagicMock` (no `spec=ssl.SSLSocket`), so a strict `isinstance(ssock, ssl.SSLSocket)` guard in fallback helpers would have rejected every test fixture and forced fallback into the error path.
- **Fix:** Introduced `_peer_metadata(ssock)` helper that calls `.version()` / `.cipher()` / `.getpeercert()` defensively without isinstance gates. The four `_fallback_*` helpers raise `RuntimeError` only when the underlying library returns `None` for the socket attribute (genuine STARTTLS failure, not a test mock).
- **Files modified:** quirk/scanner/email_scanner.py (same file)
- **Committed in:** d5eb3b9

**3. [Rule 2 - Critical] Tasks 1 and 2 committed together**

- **Issue:** Task 2 in the plan is a verification-and-fix pass on the file produced by Task 1. With sslyze absent in this environment, Task 1's first implementation immediately surfaced the deviations above; splitting Task 1 and Task 2 into separate commits would have committed broken code at Task 1.
- **Action:** Combined both tasks into a single GREEN commit (`d5eb3b9`). Plan acceptance criteria for both tasks verified post-commit.

---

**Total deviations:** 3 (all auto-fixed; no scope change). No architectural decisions; no checkpoints reached.

## Issues Encountered

None beyond the deviations above.

## TDD Gate Compliance

This plan executes against tests created in Plan 01 (RED commit `a0fffea`).
- **RED gate:** Plan 01 commit `a0fffea` (test-only, RED state — 17 tests skipped)
- **GREEN gate:** Plan 03 commit `d5eb3b9` (implementation — 17/17 GREEN)
- **REFACTOR:** None needed — implementation passes acceptance criteria on first GREEN.

## Threat Flags

None — implementation stays inside the threat surface defined by the plan's `<threat_model>` (T-32-06 through T-32-10). `ssl.CERT_NONE + check_hostname=False` in the fallback path matches T-32-07 (accepted: scanner must observe weak certs, not reject them).

## Known Stubs

None. Module is fully wired; no placeholder/empty values. The `SslyzeScanner = None` stub in the `except ImportError` branch is intentional sslyze-absent fallback infrastructure, not a feature stub.

## Next Phase Readiness

- `scan_email_targets()` is the public entry point Plan 32-05 (run_scan integration) will import.
- `cfg.connectors.enable_email` (Plan 02) is the gate flag.
- `email_scan_json` column on `crypto_endpoints` (Plan 02) is available for storing per-host summaries.
- Plan 32-04 (`evaluate_email_endpoints` in risk_engine) consumes the `CryptoEndpoint` objects this scanner produces — fields `protocol`, `port`, `cipher_suite`, `tls_version`, `tls_pfs_supported` are all populated.

## Self-Check: PASSED

- quirk/scanner/email_scanner.py exists: FOUND (556 lines)
- Commit d5eb3b9 exists: FOUND (`git log --oneline -1` confirmed)
- 17 scanner tests + 1 DB test = 18 passing: CONFIRMED
- 4 main functions + 4 fallback helpers: CONFIRMED
- _pubkey_info / _extract_sans NOT redefined: CONFIRMED
- No bare datetime.now() outside session_start fallback: CONFIRMED
- No enumerate_tls_capabilities calls: CONFIRMED
- python3 -m compileall exits 0: CONFIRMED

---
*Phase: 32-email-scanner*
*Completed: 2026-04-27*
