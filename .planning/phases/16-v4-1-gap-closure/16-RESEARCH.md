# Phase 16: v4.1 Gap Closure - Research

**Researched:** 2026-04-07
**Domain:** Python packaging (pyproject.toml), interactive CLI defaults, TDD scaffold patterns
**Confidence:** HIGH

---

## Summary

Phase 16 closes two specific gaps found by the v4.1 milestone audit (2026-04-08). Both gaps are
small, surgical changes to two files. The primary research question is not "which library to use"
but "exactly what is broken, what the fix looks like, and how to write RED tests that prove each
gap before fixing it."

**Gap 1 (CLI-04):** `pyproject.toml` line 7 still declares `version = "4.0.0"`. The
`quirk/__init__.py` module-level `__version__` is already `"4.1.0"`, but
`importlib.metadata.version("quirk")` — the source of truth for `pip show quirk` — reads the
installed package manifest, which comes from `pyproject.toml`. Confirmed live: running
`python3 -c "import importlib.metadata; print(importlib.metadata.version('quirk'))"` returns
`4.0.0` in the current environment. No existing test currently catches this discrepancy; all
existing version tests assert against `quirk.__version__` (module attribute), not against the
package metadata.

**Gap 2 (SCORE-04):** `quirk/interactive.py` line 165 defaults the output directory prompt to
`"output"` and line 166 defaults `db_path` to `"output/quirk.db"`. The dashboard reads
intelligence JSON from `QUIRK_OUTPUT_DIR` env var (default `"./quirk-output"`, confirmed in
`quirk/dashboard/api/routes/scan.py:334`). An interactive-mode user who accepts the default
writes scan results to `./output/`; the dashboard looks in `./quirk-output/` and finds nothing,
silently falling back to `profile="balanced"` regardless of what the user selected in the wizard.
No existing test covers the interactive mode output directory default value.

**Primary recommendation:** Write two RED tests in a new `tests/test_v41_gap_closure.py` file
(Plan 1), then apply the two minimal fixes (Plan 2): bump `pyproject.toml` to `"4.1.0"` and
change `interactive.py` defaults from `"output"` / `"output/quirk.db"` to `"quirk-output"` /
`"quirk-output/quirk.db"`.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-04 | User sees consistent version number (4.x) across CLI output, reports, and CBOM stamps — including `pip show quirk` / `importlib.metadata.version()` | `pyproject.toml:7` has `version = "4.0.0"`; fix is one line; RED test asserts `importlib.metadata.version("quirk") == "4.1.0"` |
| SCORE-04 | Dashboard passes scan-time profile kwarg to `compute_readiness_score()` so dashboard and CLI report scores match | Dashboard code path already correct (Phase 14); gap is that interactive defaults write to `./output/` while dashboard reads from `./quirk-output/`; fix is changing two default strings in `interactive.py` |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- Follow PEP 8 for all Python changes.
- Keep diffs minimal — avoid unnecessary refactors.
- After changes, run `python -m compileall` and relevant tests.
- Stack: Python 3.11+, FastAPI, React + shadcn/ui + Tailwind, SQLite.

---

## Standard Stack

No new libraries are required. This phase touches two existing files.

### Core Files Touched

| File | Current State | Required State |
|------|---------------|----------------|
| `pyproject.toml` line 7 | `version = "4.0.0"` | `version = "4.1.0"` |
| `quirk/interactive.py` line 165 | `_prompt("Output directory", "output")` | `_prompt("Output directory", "quirk-output")` |
| `quirk/interactive.py` line 166 | `_prompt("SQLite DB path", "output/quirk.db")` | `_prompt("SQLite DB path", "quirk-output/quirk.db")` |

### Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run | `python3 -m pytest tests/test_v41_gap_closure.py -v` |
| Full suite | `python3 -m pytest -q` |
| Current baseline | 229 passed, 0 failed |

---

## Architecture Patterns

### TDD Pattern Used in This Project

Every prior phase in v4.1 used a two-plan TDD structure:

- **Plan 1 (RED scaffold):** Write tests that assert the desired end-state. Tests MUST FAIL
  against current code to prove the gap exists. Tests are committed with a comment explaining
  what makes them RED.
- **Plan 2 (GREEN fixes):** Apply the minimal code changes that make the RED tests pass. No
  other changes. Commit confirms all tests pass.

For Phase 16, Plan 1 tests will be RED because:
- `importlib.metadata.version("quirk")` returns `"4.0.0"` (pyproject.toml not yet bumped)
- `interactive_config()` output directory default is `"output"` (not yet `"quirk-output"`)

### How Prior Gap Closure Phases Wrote RED Tests

Phase 12 pattern (from `test_cli_correctness.py` and `test_packaging.py`):
- Tests that check source file content use `pathlib.Path(...).read_text()` and assert substrings.
- Tests that check runtime module state import directly from the module.
- Tests that check `importlib.metadata` use `importlib.metadata.version("quirk")`.

Phase 10 pattern (from `test_gap_closure_packaging.py`):
- Tests that check `pyproject.toml` content read the file as text and assert substrings.
- This is an alternative approach — for CLI-04, asserting via `importlib.metadata` is more
  authoritative because it tests the actual installed state, not just file content.

### Test File Naming Convention

Prior gap closure test files: `tests/test_gap_closure.py`, `tests/test_gap_closure_packaging.py`,
`tests/test_hygiene.py`, `tests/test_scoring_correctness.py`.

For Phase 16, use: `tests/test_v41_gap_closure.py`

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Check installed package version | Custom file parser for pyproject.toml | `importlib.metadata.version("quirk")` | Standard Python 3.8+ API; reads the actual installed egg-info/dist-info, not source |
| Assert pyproject.toml content | Custom TOML parser | Read file as text, assert substring; or use `tomllib` (Python 3.11+) | For a single assertion, substring match on `version = "4.1.0"` is simpler and already used in prior tests |

---

## Common Pitfalls

### Pitfall 1: importlib.metadata vs quirk.__version__

**What goes wrong:** Writing tests that only assert `quirk.__version__ == "4.1.0"`. This already
passes. The gap is specifically that `importlib.metadata.version("quirk")` returns `"4.0.0"` —
the package manifest is stale. A test that only checks the module attribute will stay GREEN even
with the broken pyproject.toml.

**How to avoid:** The RED test must call `importlib.metadata.version("quirk")` directly.

### Pitfall 2: Reinstall Required to Verify CLI-04 Fix

**What goes wrong:** After bumping `pyproject.toml` to `"4.1.0"`, running `python3 -c
"import importlib.metadata; print(importlib.metadata.version('quirk'))"` still returns `"4.0.0"`
because the installed egg-info has not been updated.

**How to avoid:** After the pyproject.toml change, reinstall the package:
```bash
pip install -e . --quiet
```
This regenerates `quirk.egg-info/PKG-INFO` with the new version. The test will then pass.

**Important:** The pytest test using `importlib.metadata.version("quirk")` will also be RED until
the package is reinstalled. This is expected — it proves the gap exists. Plan 2 must include a
reinstall step before verifying GREEN.

### Pitfall 3: interactive.py MINIMAL_INPUTS Alignment

**What goes wrong:** The existing `test_interactive_mode.py` has a `MINIMAL_INPUTS` constant
where index 10 is `"output"` (the current default acceptance for output dir) and index 11 is
`"output/quirk.db"`. After the fix, `interactive.py` prompts with default `"quirk-output"` but
the MINIMAL_INPUTS still provides `"output"` at index 10.

**Impact:** This actually does NOT break existing tests because the user is providing explicit
values — `"output"` still works as a user-provided value. The existing tests will continue to
pass. The only behavioral change is the *default* shown to the user, not what they can type.

**How to avoid:** The Phase 16 RED test should explicitly assert the *default value* used in the
prompt — either by inspecting `interactive.py` source text for `"quirk-output"` as the default,
or by running `interactive_config()` with empty input at that position and checking the resulting
`cfg.output.directory`. The source-inspection approach is more direct and avoids mock complexity.

### Pitfall 4: db_path Must Stay Consistent with out_dir

**What goes wrong:** Changing only the `out_dir` default to `"quirk-output"` but leaving
`db_path` as `"output/quirk.db"`. The db_path and output directory defaults should be consistent.

**How to avoid:** Change both lines together:
- Line 165: `"output"` → `"quirk-output"`
- Line 166: `"output/quirk.db"` → `"quirk-output/quirk.db"`

Write a test that checks both defaults are consistent (db_path starts with out_dir).

---

## Code Examples

### RED Test Pattern for CLI-04 (pyproject.toml manifest version)

```python
# Source: Phase 12 pattern (test_packaging.py) + importlib.metadata
import importlib.metadata

def test_package_manifest_version_is_4_1_0():
    """pyproject.toml version must be 4.1.0 so pip show quirk returns 4.1.0.

    RED: importlib.metadata reads the installed egg-info, which still reflects
    pyproject.toml version = "4.0.0" until pyproject.toml is bumped and package
    is reinstalled.
    """
    version = importlib.metadata.version("quirk")
    assert version == "4.1.0", (
        f"importlib.metadata.version('quirk') = {version!r}; "
        f"expected '4.1.0' — bump pyproject.toml version field and reinstall"
    )
```

### RED Test Pattern for SCORE-04 (interactive.py output dir default)

```python
# Source: Phase 12 pattern (test_cli_correctness.py source inspection approach)
import pathlib

def test_interactive_output_dir_default_is_quirk_output():
    """interactive.py must default output dir to 'quirk-output' (matches dashboard default).

    RED: current default is 'output', dashboard reads from './quirk-output/',
    causing silent profile fallback for interactive-mode users.
    """
    source = pathlib.Path("quirk/interactive.py").read_text(encoding="utf-8")
    assert '"quirk-output"' in source or "'quirk-output'" in source, (
        "interactive.py does not contain 'quirk-output' as output dir default — "
        "interactive_config() must default output dir to 'quirk-output' to align "
        "with dashboard QUIRK_OUTPUT_DIR default"
    )
    # Assert the specific prompt line uses "quirk-output" as the default
    assert '_prompt("Output directory", "quirk-output")' in source or (
        "_prompt('Output directory', 'quirk-output')" in source
    ), (
        "interactive.py line 165 does not use 'quirk-output' as the default — "
        "current default is 'output'"
    )
```

### Alternative: Runtime Assertion for SCORE-04

```python
from unittest.mock import patch

def test_interactive_output_dir_default_at_runtime():
    """When user accepts output dir default, cfg.output.directory == 'quirk-output'."""
    # Empty string at position 10 accepts the default
    inputs = [
        "",                         # CIDRs
        "scan.example.com",         # FQDNs
        "",                         # include_ips
        "",                         # exclude_ips
        "",                         # profile (default standard)
        "n",                        # JWT
        "n",                        # container
        "n",                        # source
        "n",                        # AWS
        "n",                        # Azure
        "",                         # output dir — accept default
        "",                         # db_path — accept default
        "",                         # assessment name
        "3",                        # data classification
        "",                         # report_owner
        "7",                        # data_longevity_years
        "2",                        # exposure
        "",                         # crown_jewels
    ]
    with patch("builtins.input", side_effect=inputs):
        cfg, profile = interactive_config()

    assert cfg.output.directory == "quirk-output", (
        f"interactive_config() default output dir is {cfg.output.directory!r}; "
        f"expected 'quirk-output'"
    )
    assert cfg.output.db_path == "quirk-output/quirk.db", (
        f"interactive_config() default db_path is {cfg.output.db_path!r}; "
        f"expected 'quirk-output/quirk.db'"
    )
```

### Plan 2 Fix: pyproject.toml

```toml
# pyproject.toml line 7 — change 4.0.0 to 4.1.0
version = "4.1.0"
```

After this change, reinstall:
```bash
pip install -e . --quiet
```

### Plan 2 Fix: interactive.py

```python
# quirk/interactive.py lines 165-166 — change "output" to "quirk-output"
out_dir = _prompt("Output directory", "quirk-output")
db_path = _prompt("SQLite DB path", "quirk-output/quirk.db")
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/test_v41_gap_closure.py -v` |
| Full suite command | `python3 -m pytest -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-04 | `importlib.metadata.version("quirk")` returns `"4.1.0"` | unit | `python3 -m pytest tests/test_v41_gap_closure.py::test_package_manifest_version_is_4_1_0 -v` | ❌ Wave 0 |
| CLI-04 | `pyproject.toml` source text contains `version = "4.1.0"` | unit | `python3 -m pytest tests/test_v41_gap_closure.py::test_pyproject_version_field_is_4_1_0 -v` | ❌ Wave 0 |
| SCORE-04 | `interactive.py` source text uses `"quirk-output"` as output dir default | unit | `python3 -m pytest tests/test_v41_gap_closure.py::test_interactive_output_dir_default_is_quirk_output -v` | ❌ Wave 0 |
| SCORE-04 | `interactive_config()` default acceptance yields `cfg.output.directory == "quirk-output"` | unit | `python3 -m pytest tests/test_v41_gap_closure.py::test_interactive_output_dir_default_at_runtime -v` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/test_v41_gap_closure.py -v`
- **Per wave merge:** `python3 -m pytest -q`
- **Phase gate:** Full suite green (229+ passing, 0 failing) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_v41_gap_closure.py` — covers CLI-04 and SCORE-04 RED tests

*(No framework install needed — pytest already present and configured.)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pkg_resources.get_distribution("quirk").version` | `importlib.metadata.version("quirk")` | Python 3.8+ | `pkg_resources` deprecated; `importlib.metadata` is stdlib |

---

## Open Questions

1. **Should MINIMAL_INPUTS in test_interactive_mode.py be updated?**
   - What we know: After the fix, interactive.py prompts with default `"quirk-output"`. The existing MINIMAL_INPUTS provides `"output"` at index 10 as the explicit answer. This still works — explicit user input overrides the default.
   - What's unclear: Whether keeping `"output"` in MINIMAL_INPUTS is confusing to future readers.
   - Recommendation: Do NOT change MINIMAL_INPUTS. The existing interactive mode tests are orthogonal — they verify prompt behavior, not the default value. Changing MINIMAL_INPUTS is unnecessary scope creep and risks breaking existing GREEN tests.

2. **Does the pyproject.toml version bump require a CHANGELOG update?**
   - What we know: No CHANGELOG file exists in this repo.
   - Recommendation: No changelog action needed. Update `.planning/REQUIREMENTS.md` checkboxes only.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | All tests | ✓ | 3.14.3 | — |
| pytest | Test runner | ✓ | 9.0.2 | — |
| pip (editable install) | CLI-04 verification | ✓ | bundled with Python | — |
| importlib.metadata | CLI-04 RED test | ✓ | stdlib (Python 3.8+) | — |

**Missing dependencies with no fallback:** None.

---

## Sources

### Primary (HIGH confidence)

- Direct file inspection: `pyproject.toml:7` — confirmed `version = "4.0.0"` via Read tool
- Direct file inspection: `quirk/__init__.py:2` — confirmed `__version__ = "4.1.0"` via Read tool
- Direct file inspection: `quirk/interactive.py:165-166` — confirmed defaults `"output"` and `"output/quirk.db"` via Read tool
- Direct file inspection: `quirk/dashboard/api/routes/scan.py:334` — confirmed `QUIRK_OUTPUT_DIR` default `"./quirk-output"` via Read tool
- Live test execution: `python3 -c "import importlib.metadata; print(importlib.metadata.version('quirk'))"` returned `"4.0.0"` — confirmed gap exists
- Live test execution: `python3 -m pytest -q` — confirmed 229 passed, 0 failed; no test currently covers `importlib.metadata` version or interactive.py output dir default
- `.planning/v4.1-MILESTONE-AUDIT.md` — primary gap specification with exact file/line references

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` — requirements CLI-04 and SCORE-04 descriptions and traceability
- `.planning/ROADMAP.md` Phase 16 section — success criteria statements

### Tertiary (LOW confidence)

None — all findings verified directly against source files.

---

## Metadata

**Confidence breakdown:**
- Gap identification: HIGH — confirmed by direct file inspection and live test run
- Fix locations: HIGH — exact file and line numbers verified
- TDD pattern: HIGH — directly derived from existing Phase 12-15 test files in this repo
- No external library research needed

**Research date:** 2026-04-07
**Valid until:** Indefinite — findings are based on source code inspection, not external APIs
