---
phase: 57-scanner-security-hardening
plan: "01"
subsystem: util
tags: [security, ssrf, argv-injection, validator, tdd]
dependency_graph:
  requires: []
  provides:
    - quirk.util.url_allowlist.validate_external_url
    - quirk.util.url_allowlist.ValidationResult
    - quirk.util.subprocess_input.validate_repo_path
    - quirk.util.subprocess_input.validate_image_ref
    - quirk.util.subprocess_input.ValidationResult
  affects:
    - Wave 2 scanner hardening plans (57-02 through 57-06)
tech_stack:
  added: []
  patterns:
    - frozen dataclass ValidationResult (ok, reason, redacted_preview)
    - module-level Final[str] reason-code constants
    - _redact_preview() strip control chars + truncate to 32 chars
    - ipaddress.ip_address for SSRF IP checks (no DNS resolution)
    - re.compile shell metachar pattern for argv injection guard
key_files:
  created:
    - quirk/util/url_allowlist.py
    - quirk/util/subprocess_input.py
    - tests/util/__init__.py
    - tests/util/test_url_allowlist.py
    - tests/util/test_subprocess_input.py
  modified: []
decisions:
  - "metadata IPs (169.254.169.254, fd00:ec2::254) blocked even with allow_internal=True per CR-04 threat model (cloud SSRF cred-theft chain)"
  - "ValidationResult re-defined in subprocess_input (not imported from url_allowlist) for module independence (D-02/D-03)"
  - "Empty string in validate_repo_path returns RC_PATH_TRAVERSAL (p == '' check) not RC_SHELL_METACHAR — semantically a missing target rather than injection attempt"
  - "DNS resolution guard for hostname targets out of scope per CR-04 residual risk (paranoia mode deferred)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-09"
  tasks_completed: 2
  files_created: 5
  tests_added: 43
requirements: [HARDEN-SCAN-02, HARDEN-SCAN-03, HARDEN-SCAN-04, HARDEN-SCAN-06]
---

# Phase 57 Plan 01: Shared Validator Helpers (url_allowlist + subprocess_input) Summary

**One-liner:** SSRF guard (`validate_external_url`) and argv-injection guard (`validate_repo_path` + `validate_image_ref`) as frozen-dataclass validator helpers with parametrized TDD coverage.

## What Was Built

### Task 1: quirk/util/url_allowlist.py + tests (TDD)

Created `quirk/util/url_allowlist.py` exposing:

- `ValidationResult` — frozen dataclass `(ok: bool, reason: str, redacted_preview: str)`.
- Five reason-code constants: `RC_INTERNAL_IP`, `RC_LOOPBACK`, `RC_LINK_LOCAL`, `RC_METADATA_SERVICE_IP`, `RC_SCHEME_PREFIX`.
- `validate_external_url(url, *, allow_internal=False) -> ValidationResult` — rejects RFC1918, loopback, link-local, cloud metadata IPs, and non-http/https schemes. Metadata IPs blocked unconditionally (even with `allow_internal=True`) per CR-04 threat model.
- `_redact_preview()` helper strips ASCII control chars `[\x00-\x1f\x7f]` and truncates to 32 chars (D-08).

Test file `tests/util/test_url_allowlist.py`: 18 tests covering all 11 behaviour cases, `allow_internal=True` bypass semantics, control-char stripping, max-length enforcement, and type assertions.

TDD gate: RED commit `d9e69ab` (import failure) → GREEN commit `ad19093` (18 pass).

### Task 2: quirk/util/subprocess_input.py + tests (TDD)

Created `quirk/util/subprocess_input.py` exposing:

- `ValidationResult` — same frozen dataclass shape (re-defined locally for module independence).
- Five reason-code constants: `RC_SHELL_METACHAR`, `RC_PATH_TRAVERSAL`, `RC_NONEXISTENT_PATH`, `RC_INVALID_IMAGE_REF`, `RC_LEADING_DASH`.
- `validate_repo_path(p) -> ValidationResult` — rejects leading-dash (argv injection), path traversal (`..` / empty), shell metacharacters (`; | & $ \` < > * ? ( ) \\ \s`), non-existent directories.
- `validate_image_ref(r) -> ValidationResult` — rejects leading-dash, `dir:`/`file:` prefixes (Syft/Trivy local-filesystem escape vectors), shell metacharacters, strings not matching OCI distribution-spec regex.
- `_IMAGE_REF_RE` — OCI ref regex: `^[a-zA-Z0-9][a-zA-Z0-9._\-/:@]{0,254}$`.

Test file `tests/util/test_subprocess_input.py`: 25 tests covering all `validate_repo_path` rejection categories, `validate_image_ref` acceptance and rejection cases, redacted_preview quality, and type assertions. Uses `tmp_path` pytest fixture for existing-dir success case.

TDD gate: RED commit `7a47bd9` (import failure) → GREEN commit `6af9ff4` (25 pass).

## Test Results

```
43 passed in 0.03s
```

All tests in `tests/util/` pass. No scanner files modified (verified via `git diff --name-only quirk/scanner/` returns empty).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. Both modules implement the mitigations listed in the plan's STRIDE threat register (T-57-01, T-57-02, T-57-03) and introduce no new attack surface.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (url_allowlist tests) | d9e69ab | PASS — ImportError on collection |
| GREEN (url_allowlist impl) | ad19093 | PASS — 18 tests pass |
| RED (subprocess_input tests) | 7a47bd9 | PASS — ImportError on collection |
| GREEN (subprocess_input impl) | 6af9ff4 | PASS — 25 tests pass |

## Self-Check: PASSED

- `quirk/util/url_allowlist.py` exists: FOUND
- `quirk/util/subprocess_input.py` exists: FOUND
- `tests/util/test_url_allowlist.py` exists: FOUND
- `tests/util/test_subprocess_input.py` exists: FOUND
- Commit d9e69ab: FOUND (test: url_allowlist RED)
- Commit ad19093: FOUND (feat: url_allowlist GREEN)
- Commit 7a47bd9: FOUND (test: subprocess_input RED)
- Commit 6af9ff4: FOUND (feat: subprocess_input GREEN)
