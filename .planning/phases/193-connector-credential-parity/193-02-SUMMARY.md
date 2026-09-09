---
phase: 193-connector-credential-parity
plan: 02
subsystem: infra
tags: [config, credentials, env-vars, run_scan, redaction]

# Dependency graph
requires:
  - phase: 192
    provides: quirk/config_redaction.py's CREDENTIAL_REGISTRY / credential_is_set / redact_config
provides:
  - env_fallback for adcs_password, pg_scanner_password, mysql_scanner_password, snmp_community
  - run_scan.py consumption-site fallback wired to the four new QUIRK_* env vars
affects: [193-06 (dashboard credential transport injects these env vars into the scan subprocess)]

# Tech tracking
tech-stack:
  added: []
  patterns: [config-value-or-env fallback idiom (config wins, env is the operator override), run-time AST-pin test guarding a production expression against drift]

key-files:
  created:
    - tests/test_run_scan_credential_env_fallback.py
  modified:
    - quirk/config_redaction.py
    - run_scan.py
    - tests/test_config_redaction_registry.py

key-decisions:
  - "Mirrored the existing vault_token config-or-env fallback shape exactly at all four sites rather than introducing a new pattern"
  - "Registry-completeness assertion is run-time-derived (iterates CREDENTIAL_REGISTRY) rather than a hand-written list of 6 names, per CLAUDE.md's standing rule"
  - "AST-pin test parses run_scan.py at test-run time and walks for os.environ.get(...) calls rather than regexing file text, since run_scan.py's prose/docstrings mention these env-var names too"

patterns-established:
  - "config-value-or-env fallback: `cfg.connectors.X or os.environ.get(\"QUIRK_X\", default)` — config always wins, env is only consulted when the field is falsy"

requirements-completed: [PARITY-03]

# Metrics
duration: ~20min
completed: 2026-09-09
---

# Phase 193 Plan 02: Connector Credential Env-Fallback Parity Summary

**Closed the D-09 env-var-fallback gap for adcs_password, pg_scanner_password, mysql_scanner_password, and snmp_community by extending CREDENTIAL_REGISTRY and mirroring the existing vault_token pattern at all four run_scan.py consumption sites.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-09T00:00:00Z (approx)
- **Completed:** 2026-09-09
- **Tasks:** 2 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- All six `CREDENTIAL_REGISTRY` entries now carry a non-empty `env_fallback`; the four previously-bare connector credential fields gained `QUIRK_ADCS_PASSWORD`, `QUIRK_PG_SCANNER_PASSWORD`, `QUIRK_MYSQL_SCANNER_PASSWORD`, `QUIRK_SNMP_COMMUNITY`
- Four `run_scan.py` consumption sites now resolve config-then-env with their original defaults preserved (`"public"` for snmp_community, `None` for the three passwords); diff was 19 changed lines in `run_scan.py`, under the 20-line ceiling
- `credential_is_set()`/`redact_config()` needed zero logic change — both already read `entry.env_fallback` generically, confirmed by test
- Tests assert both precedence directions per field (config wins; env used when config unset; documented default when neither present) plus an AST-based pin proving each production site still contains the expected `os.environ.get("QUIRK_...")` call

## Task Commits

1. **Task 1: Add env_fallback names to CREDENTIAL_REGISTRY and env fallbacks at the four run_scan.py sites** - `0e7ba15c` (feat)
2. **Task 2: Tests for the four fallback sites and the extended registry** - `894e38e6` (test)

**Plan metadata:** (this commit)

## Files Created/Modified
- `quirk/config_redaction.py` - Added `env_fallback` third-positional-argument to the four bare `CredentialField("connectors", ...)` entries; added a Phase 193 comment explaining the addition
- `run_scan.py` - Four minimal, additive `or os.environ.get("QUIRK_...", default)` fallback expressions at the pre-existing consumption sites (~2842, ~3345, ~3354, ~3658); `os` already imported at module scope, no new import added
- `tests/test_config_redaction_registry.py` - Added a run-time-derived registry-completeness assertion (`test_every_registry_entry_has_a_nonempty_env_fallback`) plus parametrized `credential_is_set` precedence cases and a `redact_config` env-only-set case for the four new fields
- `tests/test_run_scan_credential_env_fallback.py` (new) - Precedence coverage for the four fields via a real `quirk.config.load_config()` round-trip on temp YAML (never a hand-rolled stand-in object, never a full scan run), plus an `ast.parse`/`ast.walk`-based pin proving each production site's `os.environ.get("QUIRK_...")` call is genuinely present, with a falsifiability self-test showing the AST detector correctly reports absence on a synthetic snippet lacking the call

## Decisions Made
- Kept `vault_token`'s `"VAULT_TOKEN"` and `security.api_token`'s `"QUIRK_API_TOKEN"` unchanged — pre-existing published names, not touched by this plan
- Used `getattr(cfg.connectors, field, default) or os.environ.get(env_var, default)` as the single canonical resolution expression mirrored in both the test helper and every production site, so the test can honestly claim to represent production behavior
- Test config YAML fixtures explicitly populate `assessment`/`scan`/`output` required fields (discovered mid-task: `load_config()` requires the full schema, not just `connectors:` — a bare `assessment: {name: test}` block is insufficient since `AssessmentCfg`/`ScanCfg`/`OutputCfg` have no defaults for several fields)

## Deviations from Plan

None - plan executed exactly as written. The `load_config()` required-field discovery above was normal test-fixture debugging, not a deviation from the plan's intent (Task 2's own `<read_first>` already flagged `load_config` as the recommended approach).

## Issues Encountered
- Initial test YAML fixtures used only a partial `assessment:` block, which raised `TypeError: AssessmentCfg.__init__() missing 3 required positional arguments`, then `ScanCfg.__init__() missing 2 required positional arguments`. Resolved by adding the full minimal required field set (`data_classification`, `report_owner`, `timezone` for assessment; `concurrency`, `ports_tls` for scan; `directory`, `db_path` for output) to the test fixture builder. No production code was affected.

## User Setup Required

None - no external service configuration required. This plan sets up the config-side fallback plumbing; the dashboard-side env-var injection that actually populates these variables at runtime is plan 193-06's scope.

## Next Phase Readiness
- Plan 193-06 (dashboard credential transport) can now inject `QUIRK_ADCS_PASSWORD`, `QUIRK_PG_SCANNER_PASSWORD`, `QUIRK_MYSQL_SCANNER_PASSWORD`, `QUIRK_SNMP_COMMUNITY` into the scan subprocess environment and have all four consumption sites honor it, exactly like the existing `VAULT_TOKEN` precedent
- No blockers identified

---
*Phase: 193-connector-credential-parity*
*Completed: 2026-09-09*

## Self-Check: PASSED

All claimed created/modified files exist on disk and both task commits (`0e7ba15c`, `894e38e6`) are present in git history.
