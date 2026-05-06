---
phase: 47-nmap-discovery-multi-target-wizard
plan: "01"
subsystem: target-ingestion
tags: [multi-target, parser, cli, wizard, tdd]
dependency_graph:
  requires: []
  provides:
    - quirk.util.targets.parse_target_tokens
    - quirk.util.targets.load_targets_file
    - quirk.util.targets.apply_targets_file_override
    - run_scan --targets-file CLI flag
    - wizard single syntax-routed prompt
  affects:
    - quirk/interactive.py (wizard prompt block)
    - run_scan.py (argparse + override block)
tech_stack:
  added:
    - quirk/util/targets.py (stdlib only: ipaddress)
  patterns:
    - TDD (RED tests first, then GREEN implementation)
    - D-02 _in_file flag suppressing nested @file routing
    - D-03 REPLACE semantics for CLI flag override
key_files:
  created:
    - quirk/util/targets.py
    - tests/test_targets_parser.py
    - tests/test_run_scan_targets_file.py
  modified:
    - quirk/interactive.py
    - run_scan.py
decisions:
  - "Parser in quirk/util/targets.py (not co-located in interactive.py) — two callers need it (wizard + CLI --targets-file)"
  - "D-02 nested @file suppressed via _in_file=True kwarg; @-tokens from files treated as bare hosts"
  - "CIDR branch guards against tokens starting with '@' (absolute file paths contain '/') to avoid false CIDR match when _in_file=True"
  - "apply_targets_file_override placed in quirk/util/targets.py (pure cfg-mutation, no UI concern) — keeps run_scan.py importable independently for test isolation"
  - "Integration tests import apply_targets_file_override directly — avoid run_scan.py import side-effects (SQLAlchemy, scanners)"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-04"
  tasks_completed: 3
  tasks_total: 3
  files_created: 3
  files_modified: 2
---

# Phase 47 Plan 01: Multi-Target Parser + --targets-file CLI Flag Summary

**One-liner:** Syntax-routed multi-target parser (CSV/@file/CIDR) in `quirk/util/targets.py` shared by a collapsed wizard prompt and new `--targets-file` CLI flag that REPLACES config targets.

## What Was Built

### Task 1: `quirk/util/targets.py` (TDD)

New module with three public functions:

**`parse_target_tokens(raw: str) -> tuple[list[str], list[str]]`**
- Splits on comma, routes each trimmed token per D-01:
  - Starts with `@` at top-level only → `load_targets_file()` + recursive parse with `_in_file=True`
  - Contains `/` and does NOT start with `@` → CIDR validation via `ipaddress.ip_network(strict=False)` → cidrs list
  - Otherwise → fqdns_or_ips list (bare host, FQDN, IP, or `@`-token from file)
- D-02 nested @file policy: enforced by `_in_file` flag; tokens originating from a file are never re-routed through @-prefix loading. A line starting with `@` inside a targets file becomes a literal bare host token (documented in code with `# D-02: no nested @file` comment).
- The CIDR branch is also guarded by `not token.startswith("@")` — critical for absolute file paths (e.g., `@/tmp/extra.txt` contains `/` but should NOT hit the CIDR branch when `_in_file=True`).

**`load_targets_file(path: str) -> str`**
- Reads file, strips blank lines and `#`-prefixed lines, returns survivors comma-joined
- Raises `FileNotFoundError("Targets file not found: {path}")` on missing file (D-05)

**`apply_targets_file_override(cfg, targets_file_path: str) -> None`**
- D-03: REPLACES `cfg.targets.fqdns` and `cfg.targets.cidrs` with parsed file contents
- Does NOT merge — existing config values are discarded
- Pure cfg-mutation with no UI concern → placed in `quirk/util/targets.py`

**9 unit tests** in `tests/test_targets_parser.py` covering all MULTI-01..05 acceptance criteria.

### Task 2: Wizard + CLI Wiring (TDD integration tests)

**Wizard before (4 prompts):**
```python
cidrs = _prompt_list("CIDR blocks", [])
fqdns = _prompt_list("FQDNs", [])
include_ips = _prompt_list("Specific IPs to include", [])
exclude_ips = _prompt_list("IPs to exclude", [])
```

**Wizard after (1 syntax-routed prompt, D-01):**
```python
raw_targets = _prompt(
    "Targets (CSV, @file, or CIDR; e.g. 'host1,10.0.0.0/24,@hosts.txt')",
    default="",
)  # D-01
fqdns, cidrs = parse_target_tokens(raw_targets)  # D-01: routes each token
include_ips = _prompt_list("Specific IPs to include", [])
exclude_ips = _prompt_list("IPs to exclude", [])
```

**`--targets-file` CLI flag in `run_scan.py`:**
- Added adjacent to `--config` at the argparse block (~L224)
- Override block inserted after broker-target plumbing and before `init_db`:
  ```python
  # Phase 47 / D-03: --targets-file REPLACES cfg.targets.fqdns + cidrs (does NOT merge)
  if getattr(args, "targets_file", None):
      apply_targets_file_override(cfg, args.targets_file)  # D-03
  ```

**4 integration tests** in `tests/test_run_scan_targets_file.py` covering D-03/MULTI-03, D-05/MULTI-05, and Risks #3 nmap-target regression.

### Task 3: Verification

Full test suite run. Results:
- New tests: 13 passed (9 parser + 4 integration)
- Full suite: 742 passed, 2 skipped (excluding 2 pre-existing failures documented below)
- `python -m compileall quirk/ run_scan.py` clean
- Manual smoke: `parse_target_tokens('a.com,10.0.0.0/24')` → `(['a.com'], ['10.0.0.0/24'])`
- Manual smoke: `python run_scan.py --help | grep targets-file` returns `--targets-file`

## Commits

| Hash | Message |
|------|---------|
| `d525a1c` | feat(47-01): add syntax-routed multi-target parser (MULTI-01,02,04,05) |
| `0869fa7` | feat(47-01): wire --targets-file CLI flag and wizard syntax prompt (MULTI-03, D-01..D-05) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CIDR routing false-match on @file path tokens when _in_file=True**
- **Found during:** Task 1 GREEN — test_at_file_no_nested_at_prefix failed
- **Issue:** When `_in_file=True`, a token like `@/tmp/some/path.txt` contains `/` and was hitting the CIDR branch (before the `@`-prefix check was skipped), causing `ipaddress.ip_network()` to raise `ValueError: Invalid target: '@/...'` instead of treating it as a bare host.
- **Fix:** Added `and not token.startswith("@")` guard to the CIDR branch condition: `elif "/" in token and not token.startswith("@"):`. Tokens starting with `@` — which includes nested @file references from inside files (D-02) — always fall through to the bare-host branch.
- **Files modified:** `quirk/util/targets.py`

## Pre-existing Test Failures (Out of Scope)

Two pre-existing failures found during Task 3 regression sweep. Both confirmed present before any Phase 47 code was written:

1. **`tests/test_cbom_schema_validation.py::test_cbom_validates_against_cyclonedx_1_6[broker]`** — requires `cyclonedx-python-lib[json-validation]` extra not yet installed; owned by Plan 47-03.
2. **`tests/test_interactive_mode.py` — 4 tests** — MINIMAL_INPUTS sequence misaligned with actual prompt order; pre-existing (same 4 failures before and after our changes, confirmed by stash test).

Documented in `.planning/phases/47-nmap-discovery-multi-target-wizard/deferred-items.md`.

## Test Coverage Matrix

| Req ID | Test | Status |
|--------|------|--------|
| MULTI-01 | test_csv_split | PASS |
| MULTI-02 | test_at_file_strips_comments_and_blanks, test_mixed_csv_with_cidr_and_file_token | PASS |
| MULTI-03 | test_targets_file_replaces_config_fqdns | PASS |
| MULTI-04 | test_cidr_routes_to_cidrs | PASS |
| MULTI-05 | test_malformed_cidr_raises_with_token, test_missing_file_raises_with_path, test_missing_file_token_raises_with_path, test_targets_file_missing_path_surfaces_clear_error, test_targets_file_malformed_cidr_surfaces_clear_error | PASS |
| D-02 | test_at_file_no_nested_at_prefix | PASS |
| Risks #3 | test_targets_file_cidr_produces_same_nmap_targets_as_yaml_config | PASS |

## Known Stubs

None. All parser functions are fully implemented and wired. `cfg.targets.cidrs` populated by the parser flows unchanged into `quirk/scanner/target_expander.py:14` (CIDR expansion) and `run_scan.py:55-60` (`_build_nmap_target_list` passes raw CIDR strings to nmap).

## Threat Flags

No new security-relevant surface beyond what the plan's threat model covers. All inputs are validated before any network dispatch:
- Malformed CIDRs → ValueError before scan (T-47-01 mitigated)
- Missing @files → FileNotFoundError before scan (T-47-02 accepted)
- cfg.targets.cidrs flows into list-form nmap args (no shell=True) downstream

## Self-Check: PASSED

| Item | Status |
|------|--------|
| quirk/util/targets.py | FOUND |
| tests/test_targets_parser.py | FOUND |
| tests/test_run_scan_targets_file.py | FOUND |
| commit d525a1c | FOUND |
| commit 0869fa7 | FOUND |
