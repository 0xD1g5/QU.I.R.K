---
phase: 59
plan: 01
subsystem: util
tags: [credential-leakage, security, safe_str, LEAK-01, tdd]
dependency_graph:
  requires: []
  provides: [quirk.util.safe_exc.safe_str]
  affects: [quirk/util/safe_exc.py, tests/test_safe_exc.py]
tech_stack:
  added: []
  patterns: [compiled-regex-tuple, module-independence, try-except-str-collapse]
key_files:
  created:
    - quirk/util/safe_exc.py
    - tests/test_safe_exc.py
  modified: []
decisions:
  - "LEAK-01: safe_str returns class-name-only on any sensitive pattern match — no partial redaction"
  - "Module independence: zero cross-imports from other quirk.util modules (mirrors Phase 57 D-02/D-03)"
  - "_SENSITIVE_PATTERNS covers 6 patterns: Vault s./hvs. tokens, connection-string passwords, GCP ADC paths, Authorization headers, long base64 (40+ chars)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-10"
  tasks: 2
  files: 2
---

# Phase 59 Plan 01: safe_str Credential-Scrubbing Helper Summary

## One-liner

Credential-safe exception stringification via `safe_str(exc)` with compiled regex tuple stripping Vault tokens, DB connection passwords, GCP ADC paths, and Authorization headers.

## What Was Built

### Task 1: RED — Failing test corpus (d60b083)

Created `tests/test_safe_exc.py` with 8 unit tests covering the full `safe_str` specification:

| Test | Verifies |
|------|---------|
| `test_safe_str_default` | Benign exception returns `ClassName: message` |
| `test_safe_str_scrubs_vault_token` | `s.` token prefix triggers class-only return |
| `test_safe_str_scrubs_connection_password` | `scheme://user:pass@host` triggers class-only return |
| `test_safe_str_scrubs_gcp_adc` | `.config/gcloud/` path triggers class-only return |
| `test_safe_str_scrubs_authorization_header` | `Authorization: Bearer ...` triggers class-only return |
| `test_safe_str_scrubs_long_base64` | 40+ char base64-shaped token triggers class-only return |
| `test_safe_str_benign_passthrough` | `ConnectionRefusedError` passes through with message intact |
| `test_safe_str_handles_str_raise` | `str(exc)` raising collapses to class name only |

Tests confirmed RED (ModuleNotFoundError) before implementation.

### Task 2: GREEN — Implementation (d199e40)

Created `quirk/util/safe_exc.py`:

- `_SENSITIVE_PATTERNS: Final[tuple[re.Pattern[str], ...]]` — 6 compiled patterns
- `safe_str(exc: BaseException) -> str` — public API; returns class-name-only on sensitive match or `str()` failure; returns `ClassName: message` otherwise
- Zero cross-imports from other `quirk.util` modules
- All 8 tests pass

## Deviations from Plan

None — plan executed exactly as written.

## TDD Gate Compliance

- RED gate: `test(59-01)` commit d60b083 — tests fail with ModuleNotFoundError
- GREEN gate: `feat(59-01)` commit d199e40 — all 8 tests pass

## Known Stubs

None — `safe_str` is fully implemented and wires directly to the regex patterns.

## Threat Flags

No new threat surface introduced. Plan closes T-59-01 and T-59-02 from the threat register:
- T-59-01 (Information Disclosure / regex coverage): All 6 pattern families implemented and test-asserted
- T-59-02 (Information Disclosure / str raise): try/except wraps `str(exc)` with class-name fallback
