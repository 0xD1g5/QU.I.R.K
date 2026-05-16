---
phase: 75-api-cli-core-warnings
plan: 04
subsystem: api-cli-core
tags: [interactive, validate, routes, hostname-validation, eof-safety, path-traversal]
requires: [APCL-04]
provides:
  - "EOF-safe _prompt_int + bounded retry"
  - "Exposure prompt 3-retry reprompt with fail-loud"
  - "Declared ConnectorsCfg.enable_nmap field (setattr removed)"
  - "validate.py expects intelligence-{stamp}.json"
  - "qramm_cmd env override try/except + logger.warning"
  - "QUIRK_OUTPUT_DIR path-traversal guard (helper landed in 75-02)"
  - "parse_target_tokens RFC-1123 hostname validation + IP fallback"
affects:
  - quirk/interactive.py
  - quirk/config.py
  - quirk/validate.py
  - quirk/cli/qramm_cmd.py
  - quirk/dashboard/api/routes/scan.py
  - quirk/util/targets.py
tech-stack:
  added: []
  patterns:
    - "Function-entry default-range validation (D-11)"
    - "Bounded retry-budget reprompt (D-12)"
    - "Declared dataclass field replacing setattr injection (D-13)"
    - "Realpath + CWD-descent + .. reject path-traversal guard (D-16, init_cmd.py:21-40 precedent)"
    - "RFC-1123 hostname regex + ipaddress.ip_address fallback ladder (D-17)"
key-files:
  created:
    - tests/test_interactive_validate_routes.py
  modified:
    - quirk/interactive.py
    - quirk/config.py
    - quirk/validate.py
    - quirk/cli/qramm_cmd.py
    - quirk/util/targets.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "D-11 RESEARCH A3: return in-range default on EOFError (no new InteractivePromptAborted exception); preserves caller contract"
  - "D-13 single setattr removal at interactive.py:273 per user prompt directive (run_scan.py:626 setattr left intact — now safe against a declared field)"
  - "D-16 _resolve_output_dir helper was landed in Plan 75-02 (commit dacb578); this plan inherits it — no further change needed"
  - "D-17 hostname validation skips tokens starting with '@' to preserve D-02 in-file-targets grammar (Rule 3 auto-fix to avoid regressing test_at_file_no_nested_at_prefix)"
metrics:
  duration: ~25min
  completed: 2026-05-15
---

# Phase 75 Plan 04: APCL-04 — Interactive + Validate + Routes Hardening Summary

**One-liner:** Closed seven WARNING-severity audit findings (WR-10..WR-16) across interactive wizard, config dataclass, output validation, QRAMM CLI, scan route, and target parser — input hardening only, zero new pip dependencies.

## What Changed

### D-11 (WR-10) — `_prompt_int` EOF safety
Rewrote `quirk/interactive.py::_prompt_int` (lines 49-79). Function-entry guard raises `ValueError` if `default` is outside `[minv, maxv]`. `try/except (EOFError, KeyboardInterrupt)` returns the in-range default cleanly (RESEARCH A3 — backward-compatible with existing callers). Bounded 3-attempt retry loop; falls through to default after retries exhausted. Switched from the legacy `_prompt(...)` wrapper to a direct `input()` call so that test-mocked `EOFError` propagates correctly.

### D-12 (WR-11) — Exposure prompt reprompt
Added new helper `_prompt_exposure(default: int = 2) -> int` to `quirk/interactive.py`. 3-retry loop accepting only `{"1", "2", "3"}`. Invalid input prints `Invalid choice {raw!r}; expected 1, 2, or 3.` and reprompts. `EOFError`/`KeyboardInterrupt` returns the default. After 3 invalid retries raises `ValueError("Exposure selection exhausted retry budget")`. Updated the assessment-context block (lines 206-216) to call the helper.

### D-13 (WR-12) — `ConnectorsCfg.enable_nmap` declared field
Added `enable_nmap: bool = False` field to `quirk/config.py::ConnectorsCfg` dataclass (line 199). Removed the single `setattr(cfg.connectors, "enable_nmap", _enable_nmap_wizard)` site at `quirk/interactive.py:273` per user prompt directive, replacing with normal assignment `cfg.connectors.enable_nmap = _enable_nmap_wizard`. The remaining `setattr` at `run_scan.py:626` is now safe (setting a declared dataclass field) and was intentionally left intact per the "single surgical removal" scope.

### D-14 (WR-13) — `validate.py` artifact list
Added `f"intelligence-{stamp}.json"` to the `expected_files` list in `quirk/validate.py::validate_run` (line 118). Validate now fails loud on incomplete output that lacks the intelligence artifact.

### D-15 (WR-14) — `qramm_cmd` env override try/except
Wrapped `datetime.date.fromisoformat(override)` in `quirk/cli/qramm_cmd.py::_resolve_today` with `try/except (ValueError, KeyError) as e: logger.warning("QRAMM cmd env override invalid: %s", e)` and fall-through to `datetime.date.today()`. Added `import logging` + module-level `logger = logging.getLogger(__name__)`.

Note: The actual env var is `QUIRK_CI_STALENESS_OVERRIDE_DATE` (not `QUIRK_QRAMM_TODAY` as in the plan example). Followed actual call site; warning message text matches plan/acceptance criteria.

### D-16 (WR-15) — `QUIRK_OUTPUT_DIR` path-traversal guard
Helper `_resolve_output_dir() -> Path` in `quirk/dashboard/api/routes/scan.py` was already landed by Plan 75-02 (commit dacb578). Helper mirrors `quirk/cli/init_cmd.py:21-40` (Phase 58 / CR-01 precedent): realpath + CWD-descent + `..` reject + `is_dir` + `os.R_OK`. WR-15 closes by inheritance.

### D-17 (WR-16) — RFC-1123 hostname validation
Added module-level `_HOSTNAME_RE` constant to `quirk/util/targets.py` (anchored RFC-1123 regex). Inserted validation ladder into `parse_target_tokens` bare-token branch:
1. Tokens starting with `@` pass through as opaque bare-host strings (preserves D-02 in-file grammar — Rule 3 auto-fix to avoid regressing `test_at_file_no_nested_at_prefix`).
2. `_HOSTNAME_RE.fullmatch(token)` accepts RFC-1123 hostnames.
3. `ipaddress.ip_address(token)` fallback accepts raw IPv4/IPv6 (including `::1`, `2001:db8::1`).
4. Otherwise: `raise ValueError(f"Invalid target token {token!r}: not a valid hostname or IP address")`.

Added `import re` to the imports block.

## Tests

Created `tests/test_interactive_validate_routes.py` with **26 test functions** (plan required ≥14) covering all seven decisions:

| Decision | Test count | Coverage |
|----------|-----------|----------|
| D-11 | 3 | EOF returns default, out-of-range raises, happy path |
| D-12 | 3 | Third-try success + capsys message check, exhaustion raises, EOF returns default |
| D-13 | 2 | Declared field default, setattr static grep check |
| D-14 | 1 | Regex check for `intelligence-{stamp}.json` in source |
| D-15 | 2 | Invalid env logs warning + falls back; valid env parses |
| D-16 | 3 | `/etc` rejected, dotdot rejected, valid tmp_path accepted |
| D-17 | 12 (parametrized) | 7 valid (hostnames + IPs), 5 invalid |

**RED → GREEN cadence:** Test commit `68d31ec` exits non-zero. Implementation commit `dac0967` makes all 26 tests green. No regression on `tests/test_targets_parser.py` (20 passing).

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 68d31ec | test | RED — failing tests for APCL-04 (D-11..D-17) |
| dac0967 | feat | GREEN — implement D-11..D-17 hardening |
| 9548426 | docs | Close WR-10..WR-16 in audit ledger |

## Audit Ledger

Seven rows flipped: `api-cli-core/WR-10..WR-16` → `Phase 75 | [x] closed`.

**Phase-wide closure:** Combined with Plans 75-01 (WR-01..WR-03), 75-02 (WR-04, WR-05, WR-06, WR-09), and 75-03 (WR-07, WR-08, WR-17), **17/17 api-cli-core WARNING rows are now closed under Phase 75.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] D-17 hostname ladder regressed in-file `@`-prefixed token grammar**
- **Found during:** Task 2 verification (`tests/test_targets_parser.py::test_at_file_no_nested_at_prefix`)
- **Issue:** Per D-02, tokens originating inside an `@file` are routed to the bare-host branch with the leading `@` retained. The new RFC-1123 ladder rejected these as invalid hostnames, breaking a passing legacy test.
- **Fix:** Added an early-return branch `if token.startswith("@"): fqdns.append(token)` ahead of the regex check. Preserves D-02 while still enforcing D-17 for non-`@` tokens.
- **Files modified:** `quirk/util/targets.py`
- **Commit:** `dac0967` (folded into GREEN)

**2. [Rule 3 - Discovery] D-16 helper already landed by Plan 75-02**
- **Found during:** Task 2 read-first (commit `dacb578` history)
- **Issue:** `_resolve_output_dir` was already present in `quirk/dashboard/api/routes/scan.py` as part of Plan 75-02's APCL-02 scope (over-broad commit).
- **Fix:** No-op for this plan — WR-15 closes by inheritance. Audit ledger flip is correct.
- **Files modified:** None (no new edit to `scan.py` from this plan)
- **Commit:** N/A

### Auth Gates

None.

## Threat Mitigations

All seven T-75-13..T-75-19 STRIDE entries are mitigated as planned:

- T-75-13 (DoS hang on EOF) — mitigated via D-11 EOF-aware exit + bounded loop
- T-75-14 (silent default) — mitigated via D-12 fail-loud reprompt
- T-75-15 (attribute injection) — mitigated via D-13 declared field
- T-75-16 (silent validate pass) — mitigated via D-14 list extension
- T-75-17 (uncaught exception) — mitigated via D-15 try/except
- T-75-18 (path traversal) — mitigated via D-16 helper (inherited from 75-02)
- T-75-19 (log injection / SSRF via crafted hostname) — mitigated via D-17 RFC-1123 ladder

## Known Stubs

None.

## Self-Check: PASSED

- `quirk/interactive.py` exists, `setattr.*enable_nmap` absent, `cfg.connectors.enable_nmap` present, `Exposure selection exhausted retry budget` present.
- `quirk/config.py` has `enable_nmap: bool = False`.
- `quirk/validate.py` has `intelligence-{stamp}.json`.
- `quirk/cli/qramm_cmd.py` has `QRAMM cmd env override invalid` log message.
- `quirk/util/targets.py` has `_HOSTNAME_RE` definition + usage and `not a valid hostname or IP address` message.
- `tests/test_interactive_validate_routes.py` exists; 26 tests pass.
- AUDIT-TASKS.md: 7 rows WR-10..WR-16 flipped to `Phase 75 | [x] closed`; total api-cli-core WR closed = 17/17.
- Commits 68d31ec, dac0967, 9548426 present in `git log`.
