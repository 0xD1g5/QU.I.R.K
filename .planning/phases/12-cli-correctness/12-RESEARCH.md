# Phase 12: CLI Correctness - Research

**Researched:** 2026-04-06
**Domain:** Python CLI correctness — version string normalization, config template alignment, documentation placeholder cleanup
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Version Strings (CLI-04)**
- D-01: Canonical version is `4.1.0` for all surfaces — bump from 4.0.0 to 4.1.0 as part of this phase. This aligns with the v4.1 milestone.
- D-02: The following locations must all read `4.1.0`:
  - `quirk/__init__.py` — `__version__ = "4.1.0"`
  - `quirk/reports/writer.py` — `PLATFORM_VERSION = "4.1.0"`, `INTELLIGENCE_VERSION = "4.1.0"`
  - `quirk/cbom/builder.py` — `PLATFORM_VERSION = "4.1.0"`
- D-03: `quirk/config.py` default `intelligence_version = "4.0.0"` should also be updated to `"4.1.0"` for consistency with new installs.

**Install Documentation (CLI-03)**
- D-04: Replace the `[owner]` GitHub install URLs in `docs/getting-started.md` with a local editable install workflow (`pip install -e .`).
- D-05: The replacement install section should be:
  ```
  git clone <your-repo-url>
  cd quirk
  pip install -e .
  ```
  And for dashboard support: `pip install -e '.[dashboard]'` + `playwright install chromium`.
- D-06: `<your-repo-url>` is a deliberate placeholder — keep it generic. Do not hardcode a specific GitHub handle.

**Config Template Field Alignment (CLI-01)**
- D-07: Verify that `quirk/config_template.yaml` produces zero TypeError when loaded via `load_config()`. Phase 8 fixed the major mismatches; this phase confirms and resolves any residual field issues (e.g., `enable_windows_adcs` was flagged as still present in Phase 8's VERIFICATION.md — confirm it's gone or remove it).
- D-08: No new config fields to add — the template is for a new user's first scan, so it should only include the fields a user actually needs to edit. Optional advanced fields stay documented but commented.

**`quirk scan` Reference Cleanup (CLI-02)**
- D-09: Phase 8 already verified zero `quirk scan` references remain in `quirk/` and `docs/`. Phase 12 re-verifies this and adds a grep check to the test suite or verification criteria to prevent regression.
- D-10: The correct invocation is `quirk --config config.yaml` — already in `init_cmd.py` and `docs/getting-started.md`. Confirm the Getting Started guide's "Quick Start" section is the authoritative path for new users.

### Claude's Discretion
- Whether to add a regression grep to CI or just to VERIFICATION.md — either is acceptable.
- Minor prose improvements to `docs/getting-started.md` while updating the install section are fine.
- Order of version string updates (all in one commit vs separate commits per file) — one clean commit preferred.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-01 | User's generated config has correct field names after `quirk init` (no startup crashes on first run) — BACK-40 | config_template.yaml field audit; `enable_windows_adcs` already removed (Phase 8 gap resolved before research); `config_from_dict()` dict-comprehension strip is defense-in-depth |
| CLI-02 | User can run `quirk scan` to initiate a scan from the CLI — BACK-41 | Re-confirmed: zero `quirk scan` references in `quirk/*.py` and `docs/*.md`; note is about removing wrong references, not adding `scan` subcommand |
| CLI-03 | User's generated config contains no `[owner]` placeholder after `quirk init` — BACK-47 | `[owner]` confirmed present in `docs/getting-started.md` lines 22 and 28; config_template.yaml already clean (uses `./docs/configuration.md`) |
| CLI-04 | User sees consistent version number (4.x) across CLI output, reports, and CBOM stamps — BACK-48 | All four version locations verified with current values; target: `4.1.0` everywhere |
</phase_requirements>

---

## Summary

Phase 12 is a targeted correctness-fix phase with four discrete, well-scoped changes. All affected files have been read and verified against the current codebase. No architectural decisions are required — the patterns for version constants, config loading, and documentation structure are already established.

**Current state (confirmed by direct code inspection):**
- `quirk/__init__.py` — `__version__ = "4.0.0"` (needs bump to `4.1.0`)
- `quirk/reports/writer.py` — `PLATFORM_VERSION = "4.0"`, `INTELLIGENCE_VERSION = "4.0.0"` (needs update to `"4.1.0"` for both)
- `quirk/cbom/builder.py` — `PLATFORM_VERSION = "4.0"` (needs update to `"4.1.0"`)
- `quirk/config.py` — `intelligence_version = "4.0.0"` default (needs update to `"4.1.0"`)
- `quirk/config_template.yaml` — clean: `enable_windows_adcs` is already absent (Phase 8 gap was already resolved before this phase)
- `docs/getting-started.md` — `[owner]` placeholder on lines 22 and 28 (needs replacement with `pip install -e .` workflow)
- Zero `quirk scan` references in `.py` and `.md` source files (already clean from Phase 8; one reference in a spec doc is intentional historical documentation)

**Primary recommendation:** Execute four atomic tasks in sequence — version bump (4 files), getting-started install section rewrite, config template verification + test, and regression grep check. All 199 existing tests are GREEN baseline.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses | stdlib | AppConfig / ScanCfg / ConnectorsCfg type definitions | Project pattern — all config types use dataclasses |
| PyYAML | installed | `yaml.safe_load()` in `load_config()` | Established project parser |
| rich | >=13.0.0 | CLI output in `init_cmd.py` | Already a core dependency |
| pytest | installed | Test framework | Project standard — all existing tests use pytest |

### Supporting

No new libraries required. All work is string-value changes and doc edits within the established stack.

### Alternatives Considered

None — the implementation approach (update string literals, edit markdown) has no meaningful alternatives.

---

## Architecture Patterns

### Version Constant Pattern (Established — DO NOT CHANGE)

Version strings are **intentionally duplicated** across three files to avoid circular imports. The comment in `builder.py` and `writer.py` states this explicitly. The pattern is:

```
quirk/__init__.py:        __version__ = "4.1.0"          ← imported by run_scan.py for CLI output
quirk/reports/writer.py:  PLATFORM_VERSION = "4.1.0"     ← embedded in summary table + executive report
                          INTELLIGENCE_VERSION = "4.1.0"  ← embedded in intelligence JSON
quirk/cbom/builder.py:    PLATFORM_VERSION = "4.1.0"     ← stamped into CycloneDX component version field
quirk/config.py:          intelligence_version = "4.1.0"  ← default for new installs via IntelligenceCfg
```

**Do NOT import `__version__` from `quirk/__init__.py` into `writer.py` or `builder.py`** — the circular-import comment documents an intentional architectural decision from prior phases.

### Config Loading Pattern (Established)

```python
# From quirk/config.py — config_from_dict() already handles:
ConnectorsCfg(
    **{k: v for k, v in (raw.get("connectors") or {}).items()
       if k != "enable_windows_adcs"}  # backward-compat strip
)
```

The template and dataclass are already aligned. The dict-comprehension strip is defense-in-depth for older config files in the wild — it should stay in place even after the template is verified clean.

### Getting Started Install Pattern (New for CLI-03)

Replace GitHub pip URL with dev-install pattern:

```markdown
## 1. Install

Clone the repository and install in editable mode:

\`\`\`bash
git clone <your-repo-url>
cd quirk
pip install -e .
\`\`\`

For dashboard support (PDF export, web UI):

\`\`\`bash
pip install -e '.[dashboard]'
playwright install chromium   # Required for PDF export — one-time step
\`\`\`

Verify the install:

\`\`\`bash
quirk --help
\`\`\`
```

The two `[owner]` occurrences to replace are at lines 22 and 28 of `docs/getting-started.md`.

### Test Pattern (Established)

Existing tests in `tests/test_cli_version.py` and `tests/test_cli_init.py` cover CLI invocation. New tests for Phase 12 should follow the same subprocess-based integration test style:

```python
# Pattern from tests/test_cli_version.py
result = subprocess.run(
    [sys.executable, "run_scan.py", "--version"],
    capture_output=True, text=True,
)
output = result.stdout + result.stderr
assert re.search(r"QU\.I\.R\.K\. v\d+\.\d+\.\d+", output)
```

### Anti-Patterns to Avoid

- **Importing `__version__` from `quirk/__init__.py` in `writer.py` or `builder.py`:** Creates circular import. Update the string literals in place.
- **Using `"4.0"` (without patch version) vs `"4.1.0"` (with patch):** `writer.py` and `builder.py` currently have `"4.0"` (two-component). These should be updated to `"4.1.0"` (three-component) to match `__version__` format.
- **Hardcoding a specific GitHub handle** in `docs/getting-started.md`: D-06 explicitly prohibits this; use `<your-repo-url>` as the clone placeholder.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Circular import avoidance | Import chain from `__init__.py` | String literal duplication with comment | Established project decision — comment documents intent |
| YAML config validation | Custom field validator | Trust `config_from_dict()` + dict comprehension | Already handles unknown fields cleanly |
| Regression prevention | Complex CI integration | Simple grep in VERIFICATION.md or a one-line pytest test | Proportionate to the risk level |

---

## Common Pitfalls

### Pitfall 1: Two-component vs three-component version strings

**What goes wrong:** `writer.py` and `builder.py` use `"4.0"` (two-component), not `"4.0.0"` (three-component). A mechanical find-replace of `"4.0"` → `"4.1.0"` would also catch the string `"4.0.0"` if done carelessly.
**Why it happens:** The constants were initialized with different precision at different phases.
**How to avoid:** Update each constant individually by line reference. `writer.py` line 23 (`PLATFORM_VERSION = "4.0"`) and line 25 (`INTELLIGENCE_VERSION = "4.0.0"`) — two separate strings needing different source values.
**Warning signs:** After update, grep for `"4.0"` or `"4.0.0"` to confirm none remain.

### Pitfall 2: `config.py` has two places that reference `"4.0.0"`

**What goes wrong:** The `IntelligenceCfg` dataclass default on line 72 (`intelligence_version: str = "4.0.0"`) AND `config_from_dict()` on line 122 uses `intel_raw.get("intelligence_version", "4.0.0")` as the fallback. Both need updating.
**Why it happens:** The fallback value in `config_from_dict()` is a string literal, not a reference to the dataclass default.
**How to avoid:** Update both occurrences when editing `quirk/config.py`.

### Pitfall 3: `enable_windows_adcs` in config_template.yaml is already gone

**What goes wrong:** Phase 8 VERIFICATION.md flagged this as a gap. Researching the current file reveals the field is **already absent** from `quirk/config_template.yaml`. A plan that includes "remove `enable_windows_adcs`" as an action would be a no-op.
**How to avoid:** CLI-01 task should be framed as "verify absence and confirm no TypeError" — run `python3 -c "from quirk.config import load_config; ..."` rather than "delete field."

### Pitfall 4: `[owner]` is in `docs/getting-started.md` only, not in `config_template.yaml`

**What goes wrong:** Phase 8 CONTEXT.md mentioned `[owner]` in config_template.yaml. Direct inspection confirms the template now uses `./docs/configuration.md` as the documentation URL — no `[owner]` present. The only `[owner]` occurrences requiring action are in `docs/getting-started.md` (lines 22 and 28).
**How to avoid:** Scope the doc fix to `docs/getting-started.md` only.

### Pitfall 5: The spec doc reference to `quirk scan` is intentional historical documentation

**What goes wrong:** `grep -rn "quirk scan"` across the whole repo hits `docs/superpowers/specs/2026-04-06-next-milestones-design.md` because it describes the BACK-41 bug. This is a design document, not user-facing content.
**How to avoid:** The regression grep check should scope to `quirk/` and `docs/` with `--include="*.py" --include="*.md" --include="*.yaml"` to exclude spec/historical files — or explicitly exclude `docs/superpowers/`.

---

## Code Examples

### Version constants — current vs target

```python
# quirk/__init__.py (current → target)
__version__ = "4.0.0"   # → "4.1.0"

# quirk/reports/writer.py (current → target)
PLATFORM_VERSION = "4.0"          # → "4.1.0"
INTELLIGENCE_VERSION = "4.0.0"    # → "4.1.0"

# quirk/cbom/builder.py (current → target)
PLATFORM_VERSION = "4.0"          # → "4.1.0"

# quirk/config.py — two places (current → target)
intelligence_version: str = "4.0.0"                                   # line 72 → "4.1.0"
intel_raw.get("intelligence_version", "4.0.0")                        # line 122 → "4.1.0"
```

### Regression grep command (verified working)

```bash
grep -rn "quirk scan" quirk/ docs/ --include="*.py" --include="*.md" --include="*.yaml"
# Should return: no matches (exit 1)
```

### Config load validation command

```bash
python3 -c "
from quirk.config import load_config
cfg = load_config('quirk/config_template.yaml')
print('OK — no TypeError')
print('version:', cfg.intelligence.intelligence_version)
"
```

### Version consistency check

```bash
python3 -c "
import quirk
from quirk.reports.writer import PLATFORM_VERSION, INTELLIGENCE_VERSION
from quirk.cbom.builder import PLATFORM_VERSION as CBOM_VERSION
from quirk.config import IntelligenceCfg
print('__version__:', quirk.__version__)
print('writer PLATFORM_VERSION:', PLATFORM_VERSION)
print('writer INTELLIGENCE_VERSION:', INTELLIGENCE_VERSION)
print('builder PLATFORM_VERSION:', CBOM_VERSION)
print('config default:', IntelligenceCfg().intelligence_version)
"
# All five lines must print 4.1.0
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `python3 -m pytest tests/test_cli_version.py tests/test_cli_init.py -v` |
| Full suite command | `python3 -m pytest tests/ -v` |

**Baseline:** 199 tests passing before Phase 12 begins.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | `quirk init` generates config with no TypeError on load | integration | `pytest tests/test_cli_correctness.py::test_init_config_loads_without_error -x` | Wave 0 |
| CLI-01 | Template fields match ConnectorsCfg/ScanCfg/TargetsCfg | unit | `pytest tests/test_cli_correctness.py::test_template_field_alignment -x` | Wave 0 |
| CLI-02 | No `quirk scan` references in source/docs | unit/grep | `pytest tests/test_cli_correctness.py::test_no_quirk_scan_references -x` | Wave 0 |
| CLI-03 | No `[owner]` placeholder in getting-started.md | unit | `pytest tests/test_cli_correctness.py::test_no_owner_placeholder -x` | Wave 0 |
| CLI-04 | All version strings are `4.1.0` | unit | `pytest tests/test_cli_correctness.py::test_version_consistency -x` | Wave 0 |
| CLI-04 | `quirk --version` output matches `4.1.0` | integration | `pytest tests/test_cli_version.py::test_version_flag -x` | ✅ (existing, but assertion is regex only — will pass at any 4.x version) |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/test_cli_version.py tests/test_cli_init.py tests/test_cli_correctness.py -v`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green (all 199+ tests) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cli_correctness.py` — new test file covering CLI-01 (template alignment, load without error), CLI-02 (no quirk scan), CLI-03 (no `[owner]`), CLI-04 (version consistency across all constants)

Existing tests (`test_cli_version.py`, `test_cli_init.py`) remain unchanged and continue to provide regression coverage for the init and version flag behaviors.

---

## Environment Availability

Step 2.6: This phase is purely code and documentation edits. No external services, databases, or CLIs beyond Python/pytest are required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All file edits, test runner | ✓ | 3.14.3 | — |
| pytest | Test suite | ✓ | 9.0.2 | — |
| quirk package (editable install) | Integration tests | ✓ | 4.0.0 | — |

No missing dependencies.

---

## Open Questions

1. **Should `test_cli_version.py` be updated to assert the specific `4.1.0` version?**
   - What we know: Current test asserts `r"QU\.I\.R\.K\. v\d+\.\d+\.\d+"` — passes at any version
   - What's unclear: Whether pinning to `4.1.0` in the test is desired or too brittle
   - Recommendation: Leave the existing test flexible (regex); add the strict version check to `test_cli_correctness.py` which is the Phase 12 test file

2. **One commit vs multiple commits for version bump?**
   - What we know: CONTEXT.md D-01 says "one clean commit preferred"
   - Recommendation: Single commit covering all four version-string files — `quirk/__init__.py`, `writer.py`, `builder.py`, `config.py`

---

## Project Constraints (from CLAUDE.md)

These directives apply to all Phase 12 implementation:

- Follow PEP 8 for all Python changes
- Keep diffs minimal — avoid unnecessary refactors (all changes are targeted string-value edits)
- After changes, run `python -m compileall` and relevant tests
- Detection logic is NOT changing — `labs/*/expected_results.md` does not need updating

---

## Sources

### Primary (HIGH confidence)

Direct code inspection of all canonical source files:
- `quirk/__init__.py` — current `__version__ = "4.0.0"` confirmed
- `quirk/reports/writer.py` lines 23-25 — `PLATFORM_VERSION = "4.0"`, `INTELLIGENCE_VERSION = "4.0.0"` confirmed
- `quirk/cbom/builder.py` line 76 — `PLATFORM_VERSION = "4.0"` confirmed
- `quirk/config.py` lines 72 and 122 — both `"4.0.0"` occurrences confirmed
- `quirk/config_template.yaml` — `enable_windows_adcs` absence confirmed; no `[owner]` present
- `docs/getting-started.md` — `[owner]` on lines 22 and 28 confirmed
- `.planning/phases/08-legacy-debt-cleanup/08-VERIFICATION.md` — Phase 8 gap documented and current status verified
- Pytest run: 199 tests GREEN baseline confirmed

### Secondary (MEDIUM confidence)

- `grep -rn "quirk scan" ... --include="*.py" --include="*.md" --include="*.yaml"` — zero matches in actionable source files confirmed
- `grep -rn "\[owner\]" docs/ quirk/` — two occurrences in `docs/getting-started.md` only

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; all patterns are established project conventions
- Architecture: HIGH — version constant pattern, config loading, and test patterns directly read from source
- Pitfalls: HIGH — each pitfall is grounded in actual code state, not inference

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable domain; version strings and file locations won't shift without a commit)
