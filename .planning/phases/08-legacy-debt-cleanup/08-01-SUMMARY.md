---
phase: 08-legacy-debt-cleanup
plan: "01"
subsystem: config, cli, cbom, reports, docs
tags: [config-template, version-alignment, cli-fix, debt-cleanup]
dependency_graph:
  requires: []
  provides: [correct-config-template, aligned-version-strings, no-quirk-scan-refs]
  affects: [quirk/config_template.yaml, quirk/cli/init_cmd.py, quirk/dashboard/api/routes/scan.py, docs/getting-started.md, quirk/cbom/builder.py, quirk/config.py, quirk/reports/executive.py, quirk/reports/technical.py]
tech_stack:
  added: []
  patterns: [dataclass-field-alignment, flat-yaml-config]
key_files:
  created: []
  modified:
    - quirk/config_template.yaml
    - quirk/cli/init_cmd.py
    - quirk/dashboard/api/routes/scan.py
    - docs/getting-started.md
    - quirk/cbom/builder.py
    - quirk/config.py
    - quirk/reports/executive.py
    - quirk/reports/technical.py
decisions:
  - "config_template.yaml uses flat connectors block matching ConnectorsCfg field names exactly"
  - "Documentation URL changed from [owner] placeholder to relative path ./docs/configuration.md"
  - "enable_windows_adcs omitted from template (filtered in config_from_dict; ConnectorsCfg has no such field in current code)"
metrics:
  duration_seconds: 115
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_modified: 8
requirements: [D-06, D-07, D-08, D-18]
---

# Phase 08 Plan 01: Config Template, CLI Hints, and Version Alignment Summary

Fix the config template field names to match dataclass constructors, remove all `quirk scan` subcommand references, and align version strings to v4.0/4.0.0.

## What Was Built

A new user who runs `quirk init`, edits targets, and runs `quirk --config config.yaml` will no longer hit a TypeError from mismatched YAML field names. No documentation or help text references the nonexistent `scan` subcommand. All version tags in generated reports and CBOM artifacts agree at v4.0/4.0.0.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix config_template.yaml field names, URL placeholder, and subcommand reference | bb8171e | quirk/config_template.yaml |
| 2 | Remove all 'quirk scan' references and align version strings | 33a23c9 | quirk/cli/init_cmd.py, quirk/dashboard/api/routes/scan.py, docs/getting-started.md, quirk/cbom/builder.py, quirk/config.py, quirk/reports/executive.py, quirk/reports/technical.py |

## Key Changes

### Task 1 — config_template.yaml (D-06, D-07, D-08)

- `targets.ips` -> `targets.include_ips` (matches `TargetsCfg.include_ips`)
- `scan.timeout: 10` -> `scan.timeout_seconds: 10` (matches `ScanCfg.timeout_seconds`)
- `scan.max_workers: 20` -> `scan.concurrency: 20` (matches `ScanCfg.concurrency`)
- Removed `scan.ports_ssh: [22, 2222]` (no such field in `ScanCfg`)
- Added `scan.include_sni: true` (required positional field in `ScanCfg`)
- Replaced three separate commented-out `connectors:` blocks with a single flat `connectors:` mapping matching `ConnectorsCfg` field names (`enable_aws`, `aws_region`, `enable_azure`, `azure_subscription_id`, `azure_keyvault_urls`, `enable_jwt`, `jwt_targets`, `enable_container`, `container_targets`, `enable_source`, `source_targets`)
- Documentation URL changed from `https://github.com/[owner]/quirk/...` to `./docs/configuration.md`
- Run hint changed from `quirk scan --config config.yaml` to `quirk --config config.yaml`

### Task 2 — Subcommand and Version Fixes (D-08, D-18)

- `quirk/cli/init_cmd.py`: post-init run hint fixed to `quirk --config {path}`
- `quirk/dashboard/api/routes/scan.py`: 404 detail message fixed to `quirk --config config.yaml`
- `docs/getting-started.md`: Quick Start code block fixed to `quirk --config config.yaml`
- `quirk/cbom/builder.py`: `PLATFORM_VERSION = "3.9"` -> `"4.0"`
- `quirk/config.py`: `IntelligenceCfg.intelligence_version` default and `config_from_dict` fallback both updated from `"3.9.0"` to `"4.0.0"`
- `quirk/reports/executive.py`: `## Confidence & Coverage (v3.7)` -> `## Confidence & Coverage`
- `quirk/reports/technical.py`: `## TLS Capabilities (v3.6)` -> `## TLS Capabilities` (heading and internal comment)

## Verification Results

1. `python3 -c "import yaml; yaml.safe_load(open('quirk/config_template.yaml'))"` — PASS
2. `grep -rn 'quirk scan' quirk/ docs/ --include='*.py' --include='*.yaml' --include='*.md'` — zero matches
3. `grep -n 'PLATFORM_VERSION' quirk/cbom/builder.py` — shows `"4.0"`
4. `grep -n 'v3\.[0-9]' quirk/reports/executive.py quirk/reports/technical.py quirk/config.py` — zero matches
5. `python3 -m compileall quirk/` — no errors

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cleaned stale version tag in code comment**
- **Found during:** Task 2
- **Issue:** `technical.py` had a section comment `# === TLS Capabilities (v3.6) ===` that contradicted the fixed heading string; would confuse maintainers.
- **Fix:** Updated comment to `# === TLS Capabilities ===` to match the corrected heading.
- **Files modified:** quirk/reports/technical.py
- **Commit:** 33a23c9

## Known Stubs

None. All changes are correctness fixes with no placeholder values flowing to user-visible output.
