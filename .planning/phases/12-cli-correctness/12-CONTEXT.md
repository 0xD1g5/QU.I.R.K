# Phase 12: CLI Correctness - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

A new user who runs `quirk init`, follows the Getting Started guide, and executes their first scan
encounters zero crashes, wrong commands, or inconsistent version strings.

Scope: config field alignment verification, `quirk scan` reference cleanup, `[owner]` placeholder
removal, and version string normalization across all output surfaces.

Not in scope: interactive mode UX (Phase 13), scoring correctness (Phase 14), code hygiene (Phase 15).
</domain>

<decisions>
## Implementation Decisions

### Version Strings (CLI-04)
- **D-01:** Canonical version is `4.1.0` for all surfaces — bump from 4.0.0 to 4.1.0 as part of
  this phase. This aligns with the v4.1 milestone and ensures CBOM deliverables carry the correct
  stamp from Phase 12 onward.
- **D-02:** The following locations must all read `4.1.0`:
  - `quirk/__init__.py` — `__version__ = "4.1.0"`
  - `quirk/reports/writer.py` — `PLATFORM_VERSION = "4.1.0"`, `INTELLIGENCE_VERSION = "4.1.0"`
  - `quirk/cbom/builder.py` — `PLATFORM_VERSION = "4.1.0"`
- **D-03:** `quirk/config.py` default `intelligence_version = "4.0.0"` should also be updated to
  `"4.1.0"` for consistency with new installs.

### Install Documentation (CLI-03)
- **D-04:** Replace the `[owner]` GitHub install URLs in `docs/getting-started.md` with a local
  editable install workflow (`pip install -e .`). The tool has no public GitHub release yet —
  a dev-install guide is honest about the current distribution model.
- **D-05:** The replacement install section should be:
  ```
  git clone <your-repo-url>
  cd quirk
  pip install -e .
  ```
  And for dashboard support: `pip install -e '.[dashboard]'` + `playwright install chromium`.
- **D-06:** `<your-repo-url>` is a deliberate placeholder — keep it generic. Do not hardcode a
  specific GitHub handle.

### Config Template Field Alignment (CLI-01)
- **D-07:** Verify that `quirk/config_template.yaml` produces zero TypeError when loaded via
  `load_config()`. Phase 8 fixed the major mismatches; this phase confirms and resolves any
  residual field issues (e.g., `enable_windows_adcs` was flagged as still present in Phase 8's
  VERIFICATION.md — confirm it's gone or remove it).
- **D-08:** No new config fields to add — the template is for a new user's first scan, so it
  should only include the fields a user actually needs to edit (targets, basic scan config, output).
  Optional advanced fields (tls_timeout_seconds, ssh_concurrency, etc.) stay documented but commented.

### `quirk scan` Reference Cleanup (CLI-02)
- **D-09:** Phase 8 already verified zero `quirk scan` references remain in `quirk/` and `docs/`.
  Phase 12 re-verifies this and adds a grep check to the test suite or verification criteria to
  prevent regression.
- **D-10:** The correct invocation is `quirk --config config.yaml` — this is already in
  `init_cmd.py` and `docs/getting-started.md`. Confirm the Getting Started guide's "Quick Start"
  section is the authoritative path for new users.

### Claude's Discretion
- Whether to add a regression grep to CI or just to VERIFICATION.md — either is acceptable.
- Minor prose improvements to `docs/getting-started.md` while updating the install section are fine.
- Order of version string updates (all in one commit vs separate commits per file) — one clean commit preferred.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §CLI Correctness — CLI-01, CLI-02, CLI-03, CLI-04 with BACK ticket refs

### Phase 12 Source Files
- `quirk/__init__.py` — `__version__` definition (single source for `--version` output)
- `quirk/reports/writer.py` — `PLATFORM_VERSION`, `INTELLIGENCE_VERSION` constants (lines 23–25)
- `quirk/cbom/builder.py` — `PLATFORM_VERSION` constant (line 76), used in CBOM metadata stamp
- `quirk/config.py` — `IntelligenceCfg.intelligence_version` default (line 72)
- `quirk/config_template.yaml` — the template copied by `quirk init`
- `quirk/cli/init_cmd.py` — `run_init()` — generates config and prints usage hint
- `docs/getting-started.md` — Getting Started guide with `[owner]` placeholders to fix

### Phase 8 Artifacts (prior state)
- `.planning/phases/08-legacy-debt-cleanup/08-VERIFICATION.md` — documents what was fixed and
  what gaps remained (PLATFORM_VERSION partial fix, enable_windows_adcs residual)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/__init__.py:__version__` — single import used by `run_scan.py` via `from quirk import __version__`
  and passed to `print_banner()` and argparse `--version`. Updating here propagates to CLI output.
- `quirk/cli/banner.py:print_banner(version, quiet)` — accepts version as parameter, no hardcoded string.
  No change needed in banner.py itself.

### Established Patterns
- Version constants are duplicated (not imported from `__init__.py`) in `writer.py` and `builder.py`
  with a comment: "duplicated here to avoid circular imports." This is intentional — maintain the
  pattern, just update the values.
- `config_from_dict()` already strips `enable_windows_adcs` from the YAML dict via dict comprehension.
  Even if `config_template.yaml` still contains it, loading won't crash — but the field should be
  absent from the template for cleanliness.

### Integration Points
- `run_scan.py` → `from quirk import __version__` → `print_banner(__version__)` and `argparse version`
- `write_reports()` in `writer.py` → embeds `INTELLIGENCE_VERSION` in intelligence JSON and
  `PLATFORM_VERSION` in the summary table and executive report
- `build_cbom()` in `builder.py` → stamps `PLATFORM_VERSION` into CycloneDX component version field
</code_context>

<specifics>
## Specific Ideas

- Version: "4.1.0" everywhere — all four strings (`__version__`, two `PLATFORM_VERSION` constants,
  `INTELLIGENCE_VERSION`) become `"4.1.0"`. No partial bumps.
- Install section: `pip install -e .` with `<your-repo-url>` as the clone placeholder (generic,
  not hardcoded to any GitHub handle).
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 12-cli-correctness*
*Context gathered: 2026-04-06*
