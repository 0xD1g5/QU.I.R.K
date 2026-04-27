---
phase: 32-email-scanner
plan: "08"
subsystem: email-scanner
tags: [email-scanner, db-persistence, gap-closure, regression-test, tdd, quirk]

dependency_graph:
  requires:
    - 32-02-db-schema-and-config (email_scan_json column on CryptoEndpoint)
    - 32-03-email-scanner-module (scan_email_targets driver function)
    - 32-06-lab-expected-results (logger regression context)
  provides:
    - "Populated CryptoEndpoint.email_scan_json (one row per scanned host)"
    - "Real-Logger smoke test guarding run_scan.py email branch"
  affects:
    - 35-cbom-integration (CBOM Pass-1 can read email_scan_json)
    - 36-dashboard (Dashboard Data-in-Motion tab can render email_scan_json)

tech-stack:
  added: []
  patterns:
    - "Per-host JSON aggregation attached to lowest-port endpoint, mirroring kerberos_scan_json pattern at quirk/scanner/kerberos_scanner.py:329"
    - "AST-based logger-signature guard: parse run_scan.py with `ast`, locate the email_scanning phase-timer block, and assert every logger.info() call inside has exactly one positional string arg"

key-files:
  created:
    - .planning/phases/32-email-scanner/32-08-SUMMARY.md
  modified:
    - quirk/scanner/email_scanner.py
    - tests/test_email_scanner.py
    - tests/test_email_run_scan_wiring.py

key-decisions:
  - "Mirrored kerberos_scanner's attachment pattern verbatim — group by host post-as_completed, sort endpoints by port for determinism, attach the JSON blob to the first (lowest-port) endpoint via the existing email_scan_json column. No changes needed in run_scan.py since session.add(ep) already persists the attribute."
  - "Made the aggregation tolerant of MagicMock-backed endpoints in unit tests (skip if ep.host is not a real string and use an int-coercing port key) so the existing test_session_start_propagation test continues to pass without modification."
  - "Implemented the 32-06-flagged Logger regression smoke test as an AST-based static check rather than driving run_scan.main() end-to-end. Driving main() would require a live network or extensive scaffolding; the AST check parses the email_scanning block and asserts every logger.info() inside has exactly one positional str arg, which is the precise contract violated by the original bug. Augmented with a real Logger.info() smoke call to prove signature compatibility end-to-end."
  - "Performed dual-direction TDD confirmation inline: temporarily reverted run_scan.py:703 to the buggy stdlib-style positional form, ran the new test (FAIL with clear error pointing at line 703 + 3 args), restored the f-string fix, re-ran (PASS). Committed as a single test(...) commit since Task 2 has no production code change."

requirements-completed: []

metrics:
  duration: "~3.5 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 3
---

# Phase 32 Plan 08: Email Scan JSON Persistence (Gap Closure) Summary

**One-liner:** Closed Phase 32 SC-1 by populating `CryptoEndpoint.email_scan_json` via a per-host JSON aggregation attached to the lowest-port endpoint (mirroring the `kerberos_scan_json` pattern), and added an AST-based real-Logger smoke test that catches the class of stdlib-positional-args drift fixed in 32-06.

## What Was Built

### Task 1 — `email_scan_json` aggregation (RED → GREEN)

**`tests/test_email_scanner.py`** — added `test_email_scan_json_attached_per_host` (RED commit `4d444f9`):
- Stubs `scan_one_email` to return deterministic per-port `CryptoEndpoint`s (port 25 simulates a failure to prove failed scans round-trip into the JSON)
- Drives `scan_email_targets(["mail.example.com"], ...)` across all 7 EMAIL_PORTS
- Asserts: 7 endpoints returned, exactly one endpoint per host has `email_scan_json` set, the attached endpoint is the lowest-port one (determinism), the JSON deserializes to a `dict` with `host`, `session_start`, `ports`, the `ports` set equals the scanned-port set, and the simulated failure preserves `scan_error` in the JSON.

**`quirk/scanner/email_scanner.py`** — extended `scan_email_targets` (GREEN commit `b87e56b`):
- After the `as_completed` loop, group endpoints by host
- For each host: sort by port (numeric `_port_key` tolerant of MagicMock test stubs), build a payload dict with `host`, `session_start_iso`, and a list of per-port summaries (port, service_detail, tls_version, cipher_suite, cert_pubkey_alg/subject/issuer/not_after, scan_error, tls_blocker_reason)
- Serialize via `json.dumps(payload, default=str)` and attach to the first endpoint
- Skips aggregation cleanly when `ep.host` is not a real string (unit-test fixture safety)

### Task 2 — Real-Logger signature smoke test

**`tests/test_email_run_scan_wiring.py`** — added `test_email_branch_logger_calls_use_real_logger_signatures` (commit `065b1d1`):
- Confirms `quirk.logging_util.Logger.info` signature has exactly one non-self parameter (catches regressions in Logger itself)
- Parses `run_scan.py` with `ast`, walks `with _phase_timer(..., "email_scanning"):` block, collects every `logger.info(...)` call inside it
- Asserts each call has 0 kwargs, exactly 1 positional arg, and that arg is a string-producing expression (`Constant str` or `JoinedStr` f-string)
- Drives a real `quirk.logging_util.Logger` instance with the canonical email-branch message (`"Email scan: 0 endpoints from 0 hosts"`) and asserts the line appears on stdout — would have raised `TypeError` before commit `0c6a8c3`

**Dual-direction confirmation** (per plan): temporarily reverted `run_scan.py:703` to the original buggy form `logger.info("Email scan: %d endpoints from %d hosts", len(...), len(...))` and re-ran the test. It failed with the clear error: *"logger.info() at run_scan.py:703 has 3 positional args; quirk.logging_util.Logger.info accepts exactly ONE str arg."* Restored the f-string fix and re-ran — GREEN.

## Task Commits

1. `4d444f9` — `test(32-08): add failing test for per-host email_scan_json aggregation`
2. `b87e56b` — `feat(32-08): aggregate per-host email_scan_json on first endpoint`
3. `065b1d1` — `test(32-08): add real-Logger signature smoke test for email branch`

## Acceptance Criteria — All Met

| Criterion                                                                       | Result |
| ------------------------------------------------------------------------------- | ------ |
| `tests/test_email_scanner.py::test_email_scan_json_attached_per_host` is GREEN  | PASS   |
| All existing email tests still pass (no regressions)                            | PASS — 36 tests across test_email_scanner.py + test_email_findings.py + test_email_run_scan_wiring.py |
| One new logger-signature smoke test added and GREEN                             | PASS   |
| `python -m compileall quirk run_scan.py` succeeds                               | PASS   |
| SUMMARY.md created at `.planning/phases/32-email-scanner/32-08-SUMMARY.md`      | PASS   |
| REQUIREMENTS.md: EMAIL-11 marked complete                                       | N/A — see note below |
| `git log` shows 1 RED + 1 GREEN commit per task (TDD discipline)                | Task 1: RED `4d444f9` + GREEN `b87e56b`. Task 2: single `test(...)` commit since no production code change (the regression target was already fixed in 32-06); dual-direction confirmation performed inline as documented above. |

**Note on EMAIL-11:** The plan's `## Requirements covered` lists `EMAIL-11 (DB persistence of email_scan_json)`, but `REQUIREMENTS.md` defines `EMAIL-11` as the Postfix+Dovecot lab Docker Compose profile (already marked complete via 32-05). There is no separate `REQUIREMENTS.md` entry for `email_scan_json` DB persistence — it is captured under Phase 32 SC-1 (Roadmap success criterion #1) rather than a discrete `EMAIL-NN` row. SC-1 is now satisfied; no `REQUIREMENTS.md` checkbox change required.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] MagicMock-backed endpoints broke the aggregation sort**

- **Found during:** Task 1, after the GREEN implementation, when running the full email regression suite.
- **Issue:** `test_session_start_propagation` (a pre-existing test) drives `scan_email_targets` with a MagicMock-backed `scan_one_email`. The MagicMock endpoints have `.port` and `.host` attributes that are themselves MagicMocks, so `sorted(host_endpoints, key=lambda e: e.port)` raised `TypeError: '<' not supported between instances of 'MagicMock' and 'MagicMock'`.
- **Fix:** Two guards in `scan_email_targets`:
  1. Skip aggregation for any endpoint whose `host` is not a real `str` (i.e., MagicMock test stubs).
  2. Use a `_port_key` helper that coerces `ep.port` via `int(...)` and falls back to `0` on `TypeError`/`ValueError`.
- **Why this is correct, not a workaround:** the production scanner always constructs `CryptoEndpoint(host=<str>, port=<int>)` via `_scan_one_sslyze_email` and `_scan_one_fallback_email`, so the guards never trigger in real scans. They only protect unit tests that use MagicMock to bypass the scanner internals — exactly the case the existing `test_session_start_propagation` relies on.
- **Files modified:** `quirk/scanner/email_scanner.py`
- **Committed in:** `b87e56b` (rolled into the GREEN commit, since this fix is part of making the GREEN implementation play nice with the existing test fixture).

No Rule 2/3/4 deviations. No checkpoints reached. No architectural decisions.

## Issues Encountered

- **REQUIREMENTS.md/Plan mismatch:** the plan references `EMAIL-11 (DB persistence)` but `REQUIREMENTS.md` defines `EMAIL-11` as the lab profile. Documented as N/A in the acceptance table above; no functional impact.

## Verification Output

```
$ .venv/bin/python -m pytest tests/test_email_scanner.py tests/test_email_findings.py tests/test_email_run_scan_wiring.py -q
....................................                                     [100%]
36 passed in 0.25s

$ .venv/bin/python -m compileall quirk run_scan.py -q
(no errors)
```

## TDD Gate Compliance

This plan is structured around two TDD-style tasks:

- **Task 1:** RED commit `4d444f9` (test added, fails) → GREEN commit `b87e56b` (implementation added, test passes). Strict RED→GREEN cycle observed.
- **Task 2:** Single `test(...)` commit `065b1d1`. The regression target (the stdlib-positional-args bug) was already fixed in 32-06 commit `0c6a8c3`, so there is no new production code to implement. Dual-direction confirmation was performed inline (revert → FAIL → restore → PASS) and is documented in the commit body and the deviations section. The plan explicitly permits this trade-off: *"the executor can verify by temporarily reverting that one line and re-running, then restoring — or skip the dual-direction confirmation if it makes the test brittle."*

Gate sequence in `git log`: `test(32-08) RED` → `feat(32-08) GREEN` → `test(32-08) regression smoke`. All three commits visible.

## Threat Surface

No new threat surface. The aggregation reads existing in-memory `CryptoEndpoint` attributes and serializes them via `json.dumps(default=str)` — no new network listeners, auth paths, or trust boundaries.

## Threat Flags

None.

## Known Stubs

None. `email_scan_json` is now fully populated on every host scanned through `scan_email_targets`; the column is ready for consumption by Phase 35 (CBOM) and Phase 36 (Dashboard).

## Next Phase Readiness

- **Phase 35 (CBOM):** can read `crypto_endpoints.email_scan_json` directly to enumerate per-port email TLS posture without re-scanning.
- **Phase 36 (Dashboard):** the Data-in-Motion tab can render the JSON directly (one card per host with a 7-row port table).
- **Phase 32 SC-1:** now satisfied — *"scan results accessible in DB `email_scan_json` column"* — closing the gap surfaced by `VERIFICATION.md`.

## Self-Check

- `.planning/phases/32-email-scanner/32-08-SUMMARY.md` exists: FOUND
- `quirk/scanner/email_scanner.py` exists: FOUND
- `tests/test_email_scanner.py` exists: FOUND
- `tests/test_email_run_scan_wiring.py` exists: FOUND
- Commit `4d444f9` (Task 1 RED) in git log: FOUND
- Commit `b87e56b` (Task 1 GREEN) in git log: FOUND
- Commit `065b1d1` (Task 2 test) in git log: FOUND
- Full email regression suite (36 tests): PASS
- `python -m compileall quirk run_scan.py`: PASS

## Self-Check: PASSED

---
*Phase: 32-email-scanner*
*Completed: 2026-04-27*
