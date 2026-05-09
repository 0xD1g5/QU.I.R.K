---
phase: 57-scanner-security-hardening
plan: "05"
subsystem: scanner
tags: [security, argv-injection, input-validation, semgrep, syft, cr-02, cr-03]
dependency_graph:
  requires: [57-01]
  provides: [HARDEN-SCAN-03, HARDEN-SCAN-04]
  affects: [quirk/scanner/source_scanner.py, quirk/scanner/container_scanner.py]
tech_stack:
  added: []
  patterns:
    - "validate-before-spawn: validate_repo_path / validate_image_ref called before subprocess.run"
    - "POSIX -- argv separator inserted before user-supplied path/ref argument"
    - "rejection-row CryptoEndpoint with scan_error_category=invalid_input"
key_files:
  created:
    - tests/scanner/test_source_hardening.py
    - tests/scanner/test_container_hardening.py
  modified:
    - quirk/scanner/source_scanner.py
    - tests/test_source_scanner.py
decisions:
  - "Existing tests used non-existent /path/to/repo — patched os.path.isdir to True to restore intent without adding real paths"
  - "syft argv reordered from [exe, image_ref, -o, json] to [exe, -o, json, --, image_ref] for POSIX -- placement"
metrics:
  duration: "~3 minutes"
  completed: "2026-05-09"
  tasks_completed: 2
  files_changed: 4
---

# Phase 57 Plan 05: Scanner Input Hardening (source + container) Summary

**One-liner:** semgrep/syft argv-injection guard using validate_repo_path and validate_image_ref with POSIX -- separator, closing CR-02 and CR-03.

## What Was Built

### Task 1: source_scanner.scan_source_repo hardening (CR-02 / HARDEN-SCAN-03)

`scan_source_repo` now calls `validate_repo_path` from `quirk.util.subprocess_input` at the very
top of the function — before `shutil.which` and before `subprocess.run`. The check order
matches the validator: leading-dash -> path-traversal -> shell-metachar -> existence.

Rejected inputs return a single `CryptoEndpoint` with:
- `host` = redacted_preview (<=32 chars, control chars stripped per D-08)
- `protocol` = "SOURCE"
- `scan_error` = reason code (e.g., "path_traversal", "shell_metachar", "leading_dash", "nonexistent_path")
- `scan_error_category` = "invalid_input"
- `port` = 0

The `subprocess.run` argv was changed from `[exe, "--json", "--config", "p/cryptography", repo_path]`
to `[exe, "--json", "--config", "p/cryptography", "--", repo_path]`, adding the POSIX `--`
separator as defense-in-depth against argument injection on inputs that might slip through
validation in future.

**Tests:** `tests/scanner/test_source_hardening.py` — 8 tests covering:
- 6 parametrized rejection cases (path_traversal x2, shell_metachar x2, leading_dash x2)
- nonexistent_path rejection
- argv `--` terminator placement verification with real `tmp_path`

### Task 2: container_scanner.scan_container_image hardening (CR-03 / HARDEN-SCAN-04)

`scan_container_image` now calls `validate_image_ref` from `quirk.util.subprocess_input` before
any subprocess is spawned. Validates OCI image reference format, rejects `dir:`, `file:`,
leading dashes, and shell metacharacters.

Rejected inputs return a single `CryptoEndpoint` with:
- `host` = redacted_preview (<=32 chars)
- `protocol` = "CONTAINER"
- `scan_error` = reason code (e.g., "invalid_image_ref", "leading_dash", "shell_metachar")
- `scan_error_category` = "invalid_input"
- `port` = 0

The `subprocess.run` argv was reordered from `[exe, image_ref, "-o", "json"]`
to `[exe, "-o", "json", "--", image_ref]`, moving image_ref to the last positional argument
after the POSIX `--` separator.

**Tests:** `tests/scanner/test_container_hardening.py` — 10 tests covering:
- 8 parametrized rejection cases (invalid_image_ref x3, leading_dash x2, shell_metachar x3)
- argv `--` terminator placement verification
- registry image ref format passes (ghcr.io/org/repo:1.2.3)

## Integration Points

| Function | Validator | Import |
|----------|-----------|--------|
| `scan_source_repo` | `validate_repo_path` | `from quirk.util.subprocess_input import validate_repo_path` |
| `scan_container_image` | `validate_image_ref` | `from quirk.util.subprocess_input import validate_image_ref` |

## Rejection Row Shape

```python
CryptoEndpoint(
    host=result.redacted_preview,       # <=32-char sanitized preview (D-08)
    port=0,
    protocol="SOURCE" or "CONTAINER",
    scan_error=result.reason,           # reason-code constant
    scan_error_category="invalid_input",
    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```

## Argv Terminator Placement

```python
# semgrep (source_scanner.py)
[exe, "--json", "--config", "p/cryptography", "--", repo_path]

# syft (container_scanner.py)
[exe, "-o", "json", "--", image_ref]
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Regression Fix] Existing source_scanner tests used non-existent paths**
- **Found during:** Task 1 GREEN phase
- **Issue:** `tests/test_source_scanner.py` uses `/path/to/repo` which `validate_repo_path` now rejects with `nonexistent_path` — 5 existing tests would fail
- **Fix:** Added `patch("os.path.isdir", return_value=True)` to each existing test to preserve the original test intent (testing scan logic, not path existence)
- **Files modified:** `tests/test_source_scanner.py`
- **Commit:** 96b9a36

**2. [Rule 1 - Correct] syft argv reorder**
- **Found during:** Task 2 GREEN phase
- **Issue:** Original syft call was `[exe, image_ref, "-o", "json"]` — placing image_ref before flags, which would put `--` in the wrong position
- **Fix:** Reordered to `[exe, "-o", "json", "--", image_ref]` per plan's `<interfaces>` section and test expectation
- **Files modified:** `quirk/scanner/container_scanner.py`
- **Commit:** a5570ce

## Test Coverage

| Test file | Tests | Result |
|-----------|-------|--------|
| tests/scanner/test_source_hardening.py | 8 | PASS |
| tests/scanner/test_container_hardening.py | 10 | PASS |
| tests/test_source_scanner.py | 5 | PASS (no regression) |
| tests/test_container_scanner.py | 4 | PASS (no regression) |
| **Total** | **27** | **27 PASS** |

## TDD Gate Compliance

- RED commit (source): 62302d9 — `test(57-05): add failing tests for source_scanner argv-injection guard (RED)`
- GREEN commit (source): 96b9a36 — `feat(57-05): harden source_scanner with validate_repo_path + argv -- separator (GREEN)`
- RED commit (container): 86b186d — `test(57-05): add failing tests for container_scanner argv-injection guard (RED)`
- GREEN commit (container): a5570ce — `feat(57-05): harden container_scanner with validate_image_ref + argv -- separator (GREEN)`

## Known Stubs

None — all rejection logic and argv hardening fully wired.

## Threat Flags

No new threat surface introduced. T-57-13, T-57-14, T-57-15 from the plan's threat model are mitigated by this plan.

## Self-Check: PASSED

Files:
- FOUND: quirk/scanner/source_scanner.py
- FOUND: quirk/scanner/container_scanner.py
- FOUND: tests/scanner/test_source_hardening.py
- FOUND: tests/scanner/test_container_hardening.py

Commits:
- 62302d9 (RED source)
- 96b9a36 (GREEN source)
- 86b186d (RED container)
- a5570ce (GREEN container)
