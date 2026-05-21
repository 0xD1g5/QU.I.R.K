---
phase: 78-html-pdf-injection-hardening
plan: 01
subsystem: reports / util
tags: [hardening, sanitization, nh3, chokepoint, HARDEN-06, HARDEN-03]
requires: []
provides:
  - quirk.util.sanitize.sanitize_scanner_text
  - nh3>=0.2.17 (core dep)
affects:
  - pyproject.toml
tech-stack:
  added:
    - nh3>=0.2.17 (Rust/Ammonia HTML allowlist sanitizer)
  patterns:
    - module-independent chokepoint helper (mirrors quirk/util/safe_exc.py)
    - strict text-only nh3 allowlist (tags=set(), attributes={}, clean_content_tags=set())
    - pre-nh3 URL-scheme regex strip for plain-text URL neutralization
key-files:
  created:
    - quirk/util/sanitize.py
    - tests/test_sanitize_scanner_text.py
  modified:
    - pyproject.toml
decisions:
  - "Override nh3 default clean_content_tags to empty set so <script>x</script> renders as 'x' (preserve text content) — matches must_have contract and Plan 01 verify command"
  - "URL strip runs BEFORE nh3 (nh3 has no plain-text URL stripper)"
  - "nh3 declared as core (non-optional) project dep — every render path needs it"
status: complete
completed: 2026-05-16
---

# Phase 78 Plan 01: Sanitize Chokepoint + nh3 Dependency Summary

One-liner: Establish `quirk/util/sanitize.py::sanitize_scanner_text` as the single source of truth for scanner-text sanitization, wire `nh3>=0.2.17` as a core project dep, and cover the chokepoint with 14 unit tests.

## Files Created

- **`quirk/util/sanitize.py`** (70 lines)
  Module-independent helper. Public surface: `sanitize_scanner_text(value) -> str`. Pipeline: `None → ""`; `str()` coercion in try/except; `_URL_RE.sub("", text)` strips `http(s)`, `javascript`, `data`, `vbscript`, `file`, `ftp` schemes; `nh3.clean(text, tags=set(), attributes={}, clean_content_tags=set())`. Module docstring carries the chokepoint invariant contract per HARDEN-02/03.

- **`tests/test_sanitize_scanner_text.py`** (94 lines, 14 tests)
  Unit tests for every behavior listed in the plan: None handling, int coercion, script-tag content preservation, img/onerror strip, six URL-scheme tests (explicit per scheme — no parametrize), control-char passthrough, idempotency, nh3 importability, and `tomllib`-parsed assertion that `bleach` is absent from `[project] dependencies`.

## Files Modified

- **`pyproject.toml`** — Inserted `"nh3>=0.2.17",` in the `[project] dependencies` block immediately after the `signxml>=4.4.0` line. No other edits.

## Tests Added / Run

- **Added:** 14 tests in `tests/test_sanitize_scanner_text.py`
- **Run:** `pytest tests/test_sanitize_scanner_text.py -x -q` — **14 passed**, 0 failed, 0.02s wall.

## Verification Results

| Verify command | Result |
|---|---|
| `grep -n '^\s*"nh3>=0.2.17"' pyproject.toml` | line 31 ✓ |
| `grep -q "bleach" pyproject.toml` | (no output — bleach absent) ✓ |
| `python -c "import tomllib; tomllib.loads(open('pyproject.toml','rb').read().decode())"` | parses ✓ |
| `python -m compileall quirk/` | clean ✓ |
| `python -c "from quirk.util.sanitize import sanitize_scanner_text"` | succeeds ✓ |
| `pytest tests/test_sanitize_scanner_text.py -x -q` | 14 passed ✓ |

## Deviations from Plan

**1. [Rule 1 — Bug / API fidelity] Added `clean_content_tags=set()` to nh3.clean() invocation**

- **Found during:** Task 2 verification (the plan's own `python -c "... assert sanitize_scanner_text('<script>x</script>')=='x' ..."` check).
- **Issue:** nh3's default `clean_content_tags` includes `script`, `style`, etc., which causes their *content* (not just the tags) to be removed entirely. With only `tags=set(), attributes={}`, `sanitize_scanner_text("<script>x</script>")` returned `""`, not `"x"`. This contradicted the plan's stated must_have ("tags stripped, content kept — per nh3 strict-text-only"), the Task 2 inline assertion, and the Task 3 `test_script_tag_stripped_content_preserved` assertion.
- **Fix:** Added a module-level `_NH3_CLEAN_CONTENT_TAGS: Final[set[str]] = set()` constant and pass it to `nh3.clean()`. With an empty `clean_content_tags`, nh3 strips the tags but preserves the textual content for every element — exactly matching the plan's contract.
- **Files modified:** `quirk/util/sanitize.py` only (no test or pyproject change).
- **Rationale:** This is a fidelity fix to nh3's actual API surface (verified against `nh3.readthedocs.io` and direct probing). The PATTERNS.md / RESEARCH.md sketch omitted `clean_content_tags`, but the plan's behavioral contract is unambiguous and required this override. Documented with an inline comment in `sanitize.py`.

No other deviations. No checkpoints triggered. No auth gates.

## Requirements Closed

- **HARDEN-06** (full) — `nh3>=0.2.17` declared as a core (non-optional) project dependency; `bleach` absence asserted by test.
- **HARDEN-03** (foundation only) — chokepoint module exists and is covered by unit tests; caller wiring (Jinja `| sanitize` filter, executive.py / writer.py / html_renderer.py edits) lands in Plans 02–05.

## Commit

`feat(78-01): sanitize chokepoint + nh3 dependency` — files: `pyproject.toml`, `quirk/util/sanitize.py`, `tests/test_sanitize_scanner_text.py`.

Commit SHA: `c40a9bd`

## Self-Check: PASSED

- `quirk/util/sanitize.py` exists ✓
- `tests/test_sanitize_scanner_text.py` exists ✓
- `pyproject.toml` contains `nh3>=0.2.17` ✓
- `pyproject.toml` does NOT contain `bleach` ✓
- 14/14 unit tests pass ✓
- `python -m compileall quirk/` clean ✓
