---
phase: 103-siem-export
plan: "01"
subsystem: siem
tags: [cef, formatter, whitelist, isec-03, siem, tdd]
dependency_graph:
  requires: []
  provides:
    - quirk.siem.formatter (to_cef_finding, build_cef_event, _CEF_SEVERITY)
    - quirk.siem (package)
  affects:
    - Plans 103-02, 103-03 (consume formatter contract)
tech_stack:
  added: []
  patterns:
    - ISEC-03 explicit whitelist (named .get() extraction only, no exclusion-list)
    - Two-function CEF escaping (header: backslash+pipe; extension: backslash+equals+newlines)
    - Backslash-first escape ordering (injection guard)
    - _slugify fallback for missing category/id field
key_files:
  created:
    - quirk/siem/__init__.py
    - quirk/siem/formatter.py
    - tests/test_siem_cef.py
    - tests/test_siem_payload_whitelist.py
  modified: []
decisions:
  - "to_cef_finding uses explicit named .get() extraction (ISEC-03) — no exclusion-list comprehension"
  - "Two distinct escape functions — header escapes backslash+pipe only; extension escapes backslash+equals+newlines"
  - "Backslash replaced FIRST in both escape functions to prevent double-escape of already-escaped chars"
  - "signature falls back to slugified title when category/id absent (confirmed from actual findings JSON)"
  - "test_pipe_in_title_escaped asserts the escaped form directly, not via naive split (str.split is not a CEF parser)"
metrics:
  duration_minutes: 5
  completed_date: "2026-05-25"
  tasks_completed: 2
  files_created: 4
---

# Phase 103 Plan 01: CEF Formatter + Whitelist Summary

**One-liner:** Pure-stdlib CEF:0 formatter with two-function escaping (backslash-first), ISEC-03 explicit per-finding whitelist, and _slugify fallback for findings with no category key.

## What Was Built

### Task 1: Failing tests — CEF formatter + whitelist (RED)

Created `tests/test_siem_cef.py` and `tests/test_siem_payload_whitelist.py` covering all plan behaviors. Both files failed with `ModuleNotFoundError: No module named 'quirk.siem'` as expected.

**test_siem_cef.py tests (30):**
- 8-field header count; CEF:0 prefix, QUIRK vendor, scanner product, version field
- Severity map: CRITICAL=10, HIGH=8, MEDIUM=5, LOW=3; unknown/missing defaults to 3
- `_CEF_SEVERITY` dict exported and correct
- Header escaping: pipe becomes `\|`, backslash becomes `\\`, equals NOT escaped in header
- Extension escaping: equals becomes `\=`, backslash becomes `\\`, `\n`/`\r\n`/`\r` become literal `\n`
- Backslash-first ordering: input `\|` yields `\\|` (not `\\\|`)
- Category fallback: slugified title when category absent; id used before slug; `category` used directly when present; empty title gives "unknown"

**test_siem_payload_whitelist.py tests (15):**
- ALLOWED_FIELDS / FORBIDDEN_FIELDS frozensets defined at module level
- to_cef_finding returns dict; allowed fields present; no forbidden fields; no unknown pass-through
- host and port survive the whitelist; host survives salted finding
- cert_pem, cert_sans, private_key excluded from to_cef_finding output
- compliance excluded from to_cef_finding output
- build_cef_event string: no "SECRET"/PEM header from cert_pem; no private_key PEM header; no "compliance" key or framework values; host and port are present

### Task 2: Implement formatter.py to pass tests (GREEN)

Created `quirk/siem/__init__.py` (package marker) and `quirk/siem/formatter.py` implementing all required functions:

- `_cef_escape_header(value)`: `replace("\\", "\\\\")` then `replace("|", "\\|")` — backslash first
- `_cef_escape_extension(value)`: backslash first, then `=`, then `\r\n`/`\r`/`\n` in CRLF-before-CR order
- `_slugify(title)`: lowercase, `re.sub(r"[^a-z0-9]+", "-")`, strip hyphens, default to "unknown"
- `_CEF_SEVERITY`: `{"CRITICAL": 10, "HIGH": 8, "MEDIUM": 5, "LOW": 3}`
- `to_cef_finding(finding)`: explicit `.get()` extraction for severity, host, port, title, category (with fallback chain: category → id → _slugify(title)), description[:256], recommendation[:256]
- `build_cef_event(finding, version)`: calls `to_cef_finding` first, then assembles `CEF:0|QUIRK|scanner|{version}|{signature}|{name}|{sev}|{ext}` with correct escape functions per field type

Manual verification confirmed: `cert_pem="SECRET"` does not appear in CEF output; pipe in title produces `\|` in name field; CRITICAL maps to severity 10.

**45 tests pass; compileall clean; zero new pip deps.**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_pipe_in_title_escaped assertion corrected**

- **Found during:** Task 2 (first GREEN test run)
- **Issue:** The original test asserted `len(line.split("|")) == 8` after a title with a pipe character. `str.split("|")` is not a CEF parser — it splits on the raw `|` byte, which is present as part of the escaped `\|` sequence (two separate characters: `\` and `|`). This produced 9 fields and a false failure.
- **Fix:** Changed the assertion to verify the escaped form `\|` appears in the raw line, and separately verified that `_cef_escape_header("TLS|Failure") == r"TLS\|Failure"`. The real CEF parser (SIEM receiver) interprets `\|` as a literal pipe in the value, not as a field separator.
- **Files modified:** `tests/test_siem_cef.py`
- **Commit:** ed802f5

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | 65daf27 | Both test files failing with ModuleNotFoundError |
| GREEN (feat) | ed802f5 | 45 tests pass, compileall clean |
| REFACTOR | N/A | No refactor needed |

## Known Stubs

None. All functions are fully implemented and tested.

## Threat Flags

No new threat surface introduced beyond what is documented in the plan's `<threat_model>`. The formatter is pure string transformation with no I/O, network, or auth surface. T-103-01 (CEF injection), T-103-02 (information disclosure), and T-103-03 (DoS via large payloads) are all mitigated and tested.

## Self-Check: PASSED

Files exist:
- quirk/siem/__init__.py: FOUND
- quirk/siem/formatter.py: FOUND
- tests/test_siem_cef.py: FOUND
- tests/test_siem_payload_whitelist.py: FOUND

Commits exist:
- 65daf27: FOUND (RED phase)
- ed802f5: FOUND (GREEN phase)
