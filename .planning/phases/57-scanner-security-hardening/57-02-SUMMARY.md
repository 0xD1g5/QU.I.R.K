---
phase: 57-scanner-security-hardening
plan: "02"
subsystem: config
tags: [security, config, cli, harden]
dependency_graph:
  requires: []
  provides: [SecurityCfg, BrokerCredential, AppConfig.security, AppConfig.broker_credentials, apply_security_cli_overrides]
  affects: [quirk/config.py, quirk/config_template.yaml, quirk/models.py, run_scan.py]
tech_stack:
  added: []
  patterns: [dataclass-frozen, defensive-loading, opt-in-cli-override]
key_files:
  created: [tests/test_security_config.py]
  modified: [quirk/config.py, quirk/config_template.yaml, quirk/models.py, run_scan.py]
decisions:
  - "D-04: SecurityCfg all default False; CLI flags are opt-in only (never flip True->False)"
  - "D-05: BrokerCredential frozen dataclass; pass_env is env-var NAME not inline password"
  - "D-06: scan_error_category docstring extended to include invalid_input"
  - "apply_security_cli_overrides exported as module-level function for unit testability"
metrics:
  duration: "2m"
  completed: "2026-05-09"
  tasks_completed: 2
  files_changed: 5
---

# Phase 57 Plan 02: Security Config Plumbing Summary

Config plumbing for Phase 57 security hardening: SecurityCfg/BrokerCredential dataclasses, YAML blocks, --allow-* CLI flags with opt-in-only override semantics.

## What Was Built

### Task 1: SecurityCfg + BrokerCredential + config_template.yaml + models.py

Added `SecurityCfg` dataclass to `quirk/config.py` with three bool knobs, all defaulting to `False`:

```python
@dataclass
class SecurityCfg:
    allow_internal_targets: bool = False        # CR-04
    allow_cleartext_broker_probe: bool = False  # CR-06
    allow_insecure_jwks: bool = False           # CR-01
```

Added `BrokerCredential` frozen dataclass:

```python
@dataclass(frozen=True)
class BrokerCredential:
    user: str
    pass_env: str  # env-var NAME, never inline password
```

Extended `AppConfig` with:
```python
security: SecurityCfg = field(default_factory=SecurityCfg)
broker_credentials: Dict[str, BrokerCredential] = field(default_factory=dict)
```

`config_from_dict` loads both blocks defensively:
- Missing `security:` block defaults to `SecurityCfg(False, False, False)`
- Non-bool YAML values coerced via `bool(...)`
- Missing `broker_credentials:` block defaults to `{}`
- Non-dict credential entries silently skipped

`config_template.yaml` now documents both the `security:` block (with all three knobs set to `false`) and the `broker_credentials:` map (shipped commented out by default).

`quirk/models.py` `CryptoEndpoint.scan_error_category` docstring extended to include `invalid_input` (D-06 — Wave 2 rejection rows depend on this category).

### Task 2: --allow-* CLI flags + apply_security_cli_overrides

Added three `store_true` CLI flags to `run_scan.py`:
- `--allow-internal-targets` (dest: `allow_internal_targets`) — CR-04
- `--allow-cleartext-broker-probe` (dest: `allow_cleartext_broker_probe`) — CR-06
- `--allow-insecure-jwks` (dest: `allow_insecure_jwks`) — CR-01

Added module-level `apply_security_cli_overrides(cfg, args) -> None`:

```python
def apply_security_cli_overrides(cfg, args) -> None:
    if getattr(args, "allow_internal_targets", False):
        cfg.security.allow_internal_targets = True
    if getattr(args, "allow_cleartext_broker_probe", False):
        cfg.security.allow_cleartext_broker_probe = True
    if getattr(args, "allow_insecure_jwks", False):
        cfg.security.allow_insecure_jwks = True
```

Key invariant: CLI flags can only flip `False -> True`. An absent flag (default=False) does NOT override a `True` value loaded from YAML. Wired in post-config-load block after `apply_targets_file_override`.

## Tests

`tests/test_security_config.py` (10 tests, all passing):

| Test | What It Covers |
|------|---------------|
| `test_security_block_missing_defaults_safe` | Missing security: block → SecurityCfg(False, False, False) |
| `test_security_block_partial_load` | Partial security: block → only named knobs set |
| `test_broker_credentials_load` | broker_credentials: map loaded correctly |
| `test_broker_credentials_missing_defaults_empty` | Missing block → empty dict |
| `test_broker_credential_is_frozen` | FrozenInstanceError on mutation |
| `test_security_non_bool_coerced` | Int YAML values coerced via bool() |
| `test_broker_credentials_non_dict_entry_skipped` | Non-dict entries skipped defensively |
| `test_cli_flag_flips_false_to_true` | CLI flag flips False → True |
| `test_cli_absent_does_not_flip_true_to_false` | Absent CLI flag does not flip True → False |
| `test_cli_help_mentions_three_flags` | All three flags present in run_scan.py source |

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `b2e89a3` | test | RED: failing tests for SecurityCfg + BrokerCredential + CLI overrides |
| `0e07ff4` | feat | GREEN: SecurityCfg + BrokerCredential + config_template.yaml + models.py + CLI flags |

## Deviations from Plan

None — plan executed exactly as written. Both Task 1 and Task 2 are committed as separate RED/feat commits (tests written first, implementation second). The test file covers both tasks since the CLI override tests are logically part of the config loading story.

## Known Stubs

None. All fields are fully wired and loaded.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| (none) | — | All surfaces documented in plan threat_model; no new untracked surfaces introduced |

## Self-Check: PASSED

- [x] `tests/test_security_config.py` exists: `b2e89a3`
- [x] `quirk/config.py` modified: `0e07ff4` — SecurityCfg + BrokerCredential + AppConfig fields
- [x] `quirk/config_template.yaml` modified: `0e07ff4` — security: + broker_credentials: blocks
- [x] `quirk/models.py` modified: `0e07ff4` — invalid_input in scan_error_category docstring
- [x] `run_scan.py` modified: `0e07ff4` — three --allow-* flags + apply_security_cli_overrides
- [x] All 10 pytest tests pass
- [x] `python -m compileall` exits 0 on all modified files
- [x] `python run_scan.py --help` shows all three flags
- [x] Import smoke test: `from quirk.config import SecurityCfg, BrokerCredential, config_from_dict; from run_scan import apply_security_cli_overrides` — exits 0
