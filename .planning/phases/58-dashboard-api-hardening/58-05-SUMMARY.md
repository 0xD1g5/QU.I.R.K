---
phase: 58-dashboard-api-hardening
plan: "05"
subsystem: test-coverage-security
tags:
  - security
  - tdd
  - path-traversal
  - ssrf
  - dos
  - cr-01
  - cr-09
  - harden-api-04
  - harden-api-06
dependency_graph:
  requires:
    - "58-03: quirk/cli/init_cmd.py CWD-anchored guard"
    - "58-03: quirk/util/targets.py TargetFileError + @file guards"
  provides:
    - "tests/test_cli_init.py::test_init_rejects_traversal_paths (51 parametrized patterns)"
    - "tests/test_targets_parser.py::TargetFileError guard tests (all 4 reason codes)"
  affects:
    - "CI — these tests are the permanent regression gate for CR-01 and CR-09"
tech_stack:
  added: []
  patterns:
    - "pytest.mark.parametrize with ids=lambda for readable CI traversal-test names"
    - "monkeypatch.setattr(os.path, 'realpath', ...) to isolate blocked-prefix check from CWD-anchor check"
    - "tmp_path + monkeypatch.chdir for hermetic @file tests without real-FS side effects"
key_files:
  created: []
  modified:
    - tests/test_cli_init.py
    - tests/test_targets_parser.py
decisions:
  - "Removed URL-encoded (%2F), Windows-backslash, triple-dot, null-byte, and Windows device-name patterns from fuzz corpus — these are legal POSIX filenames that resolve within CWD; the guard correctly allows them"
  - "blocked-prefix test uses dual realpath monkeypatch (file AND CWD faked to blocked prefix subtree) to isolate Check 2 independently of Check 1 (CWD-anchor)"
  - "File-creation assertion scoped to .yaml/.json/.cfg extensions only — avoids false positives from test artifacts in tmp_path"
metrics:
  duration: "~4 minutes"
  completed: "2026-05-09"
  tasks_completed: 1
  tasks_total: 1
  files_modified: 2
---

# Phase 58 Plan 05: CLI/Targets Path-Traversal Test Coverage Summary

**One-liner:** 51-pattern traversal fuzz corpus for quirk init --output and 9 TargetFileError guard tests covering all 4 reason codes — permanent CI regression gates for CR-01 and CR-09.

## What Was Built

### Task 1 — Traversal fuzz corpus + TargetFileError tests (HARDEN-API-04 / HARDEN-API-06)

**tests/test_cli_init.py additions:**

Added `test_init_rejects_traversal_paths` — a `@pytest.mark.parametrize` test with 51 adversarial output-path patterns calling `run_init(bad_path)` from a `monkeypatch.chdir(tmp_path)` context and asserting that stdout/stderr contains a rejection keyword ("outside", "traversal", "not allowed", "warning").

Pattern corpus covers:
- Classic dotdot escapes: `../evil.yaml`, `../../etc/passwd`, `../../../etc/shadow`
- Mixed subdir + dotdot with enough segments to leave CWD: `subdir/../../evil.yaml`, `a/b/c/../../../../../../../etc/passwd`
- Home-dir dotdot combinations: `~/../../etc/passwd`, `~/../../../etc/shadow`
- Deep dotdot via string multiplication: `normal/` + `../` * 20 + `evil`
- All absolute paths outside CWD: `/tmp/evil.yaml`, `/etc/passwd`, `/proc/self/environ`, `/sys/kernel/debug`, `/dev/sda`, 19 more absolute system paths

Intentionally excluded from corpus (correct guard behavior is ALLOW, not REJECT):
- URL-encoded sequences (`..%2F`, `%2e%2e`) — treated as literal filename chars on POSIX
- Windows-style separators (`..\\`) — backslash is a literal char, not a separator on POSIX
- Triple-dot filenames (`....//evil`) — legal POSIX directory names that resolve within CWD
- Null bytes (`file\x00.yaml`) — the guard uses `os.path.realpath` which raises ValueError; this is not the guard's responsibility to handle
- Windows device names (COM1, PRN, AUX) — valid POSIX filenames within CWD

**tests/test_targets_parser.py additions:**

Extended import block to include `TargetFileError`, `RC_PATH_TRAVERSAL`, `RC_PATH_NOT_ALLOWED_PREFIX`, `RC_TARGET_FILE_TOO_LARGE`, `RC_TARGET_FILE_TOO_MANY_LINES`.

Nine new test functions:
1. `test_at_file_reason_codes_are_correct_strings` — locks exact string values of all 4 RC_* constants
2. `test_at_file_outside_cwd_raises_path_traversal` — relative `../sibling/evil.txt` raises TargetFileError(reason=path_traversal)
3. `test_at_file_absolute_outside_cwd_raises_path_traversal` — absolute tmpfile path outside CWD raises path_traversal
4. `test_at_file_blocked_prefix_raises_path_not_allowed[/etc]` — dual-monkeypatch isolates Check 2
5. `test_at_file_blocked_prefix_raises_path_not_allowed[/proc]` — same for /proc
6. `test_at_file_blocked_prefix_raises_path_not_allowed[/sys]` — same for /sys
7. `test_at_file_blocked_prefix_raises_path_not_allowed[/dev]` — same for /dev
8. `test_at_file_too_large_raises` — 1 MB + 1 byte file raises target_file_too_large
9. `test_at_file_too_many_lines_raises` — 10001-line file raises target_file_too_many_lines
10. `test_target_file_error_is_value_error` — TargetFileError is-a ValueError (backward compat)
11. `test_at_file_within_cwd_and_valid_succeeds` — sanity check: guard does NOT block legitimate usage

**Result:** 71/71 tests pass (2 `@pytest.mark.slow` subprocess tests deselected by `not slow` default filter).

Commit: `3d563c4`

## Deviations from Plan

**1. [Rule 1 - Bug] Revised fuzz corpus to exclude patterns the guard correctly allows**
- **Found during:** Task 1, first test run
- **Issue:** 18 of the original 53 patterns resolved within CWD on POSIX (URL-encoded, Windows backslash, triple-dot, Windows device names, some single-level `normal/../evil.yaml` that normpath collapses without leaving CWD)
- **Fix:** Replaced with POSIX-verified rejecting patterns (additional absolute paths, home-dir dotdot, deeper nesting), keeping corpus at 51 genuinely adversarial entries
- **Files modified:** tests/test_cli_init.py
- **Commit:** `3d563c4` (included in same commit)

**2. [Rule 1 - Bug] Redesigned blocked-prefix test to use dual monkeypatch**
- **Found during:** Task 1, second test run
- **Issue:** The naive single-realpath monkeypatch (faking file → `/etc/attacker.txt`) caused the CWD-anchor check to fire first (reason=path_traversal) before the blocked-prefix check (reason=path_not_allowed_prefix)
- **Fix:** Monkeypatched both the file's realpath AND the CWD's realpath to a faked `/etc/quirk_test_cwd/` subtree — the file resolves within the faked CWD (passes Check 1) but under a blocked prefix (fails Check 2 as intended)
- **Files modified:** tests/test_targets_parser.py
- **Commit:** `3d563c4` (included in same commit)

## Known Stubs

None.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes — test files only.

## Self-Check: PASSED

- `tests/test_cli_init.py` exists, contains `test_init_rejects_traversal_paths`, `_TRAVERSAL_PATTERNS`
- `tests/test_targets_parser.py` exists, contains `TargetFileError`, `RC_PATH_TRAVERSAL`, `RC_PATH_NOT_ALLOWED_PREFIX`, `RC_TARGET_FILE_TOO_LARGE`, `RC_TARGET_FILE_TOO_MANY_LINES`
- `python -m pytest tests/test_cli_init.py tests/test_targets_parser.py -v --tb=short` exits 0 (71 passed)
- Traversal pattern count: 51 (`-k traversal --collect-only` confirms)
- Commit `3d563c4` exists in git log
