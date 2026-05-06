---
phase: 47-nmap-discovery-multi-target-wizard
reviewed: 2026-05-04T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - quirk/util/targets.py
  - quirk/interactive.py
  - run_scan.py
  - quirk/discovery/nmap_provider.py
  - quirk/util/optional_extra.py
  - quirk/cbom/writer.py
  - quirk/reports/writer.py
  - pyproject.toml
  - tests/test_targets_parser.py
  - tests/test_run_scan_targets_file.py
  - tests/test_nmap_provider.py
  - tests/test_run_scan_budget_guard.py
  - tests/test_optional_extra.py
  - tests/test_cbom_writer_validation.py
findings:
  critical: 1
  warning: 3
  info: 3
  total: 7
status: issues_found
---

# Phase 47: Code Review Report

**Reviewed:** 2026-05-04
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 47 delivers multi-target parsing, nmap discovery integration, a TTY-aware probe-budget guard, and post-write CBOM JSON schema validation. The core token-routing logic in `targets.py` is sound and well-tested. The nmap provider, cbom writer validation, and optional-extra registry additions are structurally correct. However, there is one BLOCKER: the interactive wizard's nmap toggle is unconditionally overwritten by the CLI `--discovery` flag, making the prompt dead for triggering an actual nmap scan. There are also three warnings covering a vacuous test assertion, an `all_broker_eps in dir()` dead-else, and an unhandled non-`MissingOptionalDependencyException` exception path in the CBOM writer. Three informational findings round out the review (redundant `cbom` optional extra, memory materialization of large CIDR host lists in `projected_probe_count`, and dead `_enable_nmap_wizard` variable intermediate).

---

## Critical Issues

### CR-01: Interactive wizard nmap toggle is overwritten by CLI default — prompt is dead for triggering nmap discovery

**File:** `run_scan.py:316`

**Issue:** `interactive_config()` stores the user's nmap choice in `cfg.connectors.enable_nmap` via `setattr` (interactive.py:269). Immediately after, `run_scan.py:316` unconditionally overwrites this attribute:

```python
setattr(cfg.connectors, "enable_nmap", args.discovery == "nmap")  # D-09
```

Because `--discovery` defaults to `"builtin"` (argparse line 237), this always evaluates `False` in an interactive session (the user never passes `--discovery nmap` when going through the wizard). The actual discovery branch at line 338 (`if args.discovery == "nmap":`) also checks `args.discovery`, not `cfg.connectors.enable_nmap`. The net result is that the wizard prompt at interactive.py:139 ("Run nmap port discovery first?") has **no effect** on whether nmap actually runs; it only influences `probe_missing_extras` advisory emission (which is also suppressed by the overwrite).

A user who answers "Yes" to the interactive nmap prompt will receive builtin discovery, with no warning that their choice was ignored.

**Fix:** In the interactive path, honour the wizard's choice instead of unconditionally overwriting it. One approach is to let the wizard choice win when no explicit `--discovery` flag was supplied:

```python
# After interactive_config() returns, respect the wizard toggle if the user
# didn't explicitly pass --discovery on the CLI.
wizard_nmap = getattr(cfg.connectors, "enable_nmap", False)
cli_nmap = args.discovery == "nmap"
effective_nmap = cli_nmap or (not used_config_file and wizard_nmap)
setattr(cfg.connectors, "enable_nmap", effective_nmap)
# Then guard the discovery branch on the same bool:
# if effective_nmap:   (or adjust args.discovery to match)
```

Alternatively, when the wizard returns `enable_nmap=True`, set `args.discovery = "nmap"` (mutating the namespace) before the overwrite line, so the rest of the flow stays consistent.

---

## Warnings

### WR-01: Vacuous assertion in `test_at_file_no_nested_at_prefix` provides no regression protection

**File:** `tests/test_targets_parser.py:84`

**Issue:** Line 84 reads:

```python
assert str(inner) not in fqdns or f"@{inner}" in fqdns or f"@{inner}".lstrip("@") not in [h for h in fqdns if "/" not in h and not h.startswith("@")]
```

The first disjunct (`str(inner) not in fqdns`) is always `True` because `fqdns` contains `@/path/to/nested.txt` (with the `@` prefix) while `str(inner)` is `/path/to/nested.txt` (without). Since any `True` in an `or`-chain short-circuits, the assertion trivially passes regardless of what `fqdns` actually contains. The meaningful regression protection (line 86, `real-host.com not in fqdns`) is correct; this extra assertion adds no value but may mislead future readers into thinking D-02 is more thoroughly validated than it is.

**Fix:** Remove line 84 entirely or replace it with the intended assertion:

```python
# Assert that the nested @file token is kept as a bare-host string (@ preserved),
# NOT silently dropped or loaded.
assert any(h.startswith("@") and "nested" in h for h in fqdns), (
    "D-02: @-prefixed line inside a file must be kept as a bare host (@ preserved)"
)
```

### WR-02: Dead `else []` branch at `run_scan.py:976` (`all_broker_eps in dir()` is always True)

**File:** `run_scan.py:976`

**Issue:** `all_broker_eps` is unconditionally assigned at line 922:

```python
all_broker_eps = kafka_endpoints + rabbit_endpoints + redis_endpoints
```

The guard at line 976:

```python
broker_findings = evaluate_broker_endpoints(all_broker_eps if 'all_broker_eps' in dir() else [])
```

Because `all_broker_eps` is always in local scope by line 976, `'all_broker_eps' in dir()` is always `True` and the `else []` branch is dead code. Using `dir()` for this check is also semantically unusual and may confuse future maintainers.

**Fix:** Remove the defensive guard and call directly:

```python
broker_findings = evaluate_broker_endpoints(all_broker_eps)
```

### WR-03: CBOM writer validation try-block only catches `MissingOptionalDependencyException` — other exceptions from `validate_str` propagate uncaught and abort the scan

**File:** `quirk/cbom/writer.py:65-84`

**Issue:** The try-block wrapping file-read + validator construction + `validate_str()` catches only `MissingOptionalDependencyException`. If the CycloneDX library or `jsonschema` raises any other exception (e.g., a `RuntimeError`, `SchemaError`, or `OSError` re-reading the just-written file), it propagates uncaught through `write_cbom_files`, bubbles through `write_reports`, and crashes the scan after all scanning work has completed. D-14 states the file must not be deleted on failure; D-15 requires soft-fail. Neither guarantee holds for non-`MissingOptionalDependencyException` errors.

```python
# Current — too narrow
except MissingOptionalDependencyException:
    pass
```

**Fix:** Add a broad fallback that converts unexpected validation errors into a coverage-gap advisory, consistent with D-15:

```python
except MissingOptionalDependencyException:
    pass  # D-16: deps missing; registry probe handles advisory
except Exception as exc:  # noqa: BLE001
    # Unexpected validation error — soft-fail per D-15; do not delete the file
    if error_endpoints is not None:
        from quirk.models import CryptoEndpoint
        error_endpoints.append(
            CryptoEndpoint(
                host="cbom_validator",
                port=0,
                protocol="ADVISORY",
                scan_error=f"CBOM JSON validation error (unexpected): {exc}",
                scan_error_category="coverage_gap",
            )
        )
```

---

## Info

### IN-01: `[cbom]` optional extra is redundant — `cyclonedx-python-lib[json-validation]` is already a base dependency

**File:** `pyproject.toml:16,62`

**Issue:** `cyclonedx-python-lib[json-validation]` is declared in the base `[project.dependencies]` list (line 16) AND identically repeated in the `[cbom]` optional extra (line 62). For any standard install (`pip install quirk`), the `cbom` extra installs nothing new, meaning the `cbom_validator` registry entry in `optional_extra.py` (with `enabled_attrs=()`, always-probe) can never emit an advisory in practice. The advisory path is effectively dead code for all standard deployments.

**Fix:** Either remove the `[cbom]` optional extra (since the validation deps ship with core), or move `cyclonedx-python-lib[json-validation]` out of base deps into the `[cbom]` extra and adjust the CBOM writer/registry accordingly. The current state misleads users who run `pip install quirk[cbom]` expecting it to add capability.

### IN-02: `projected_probe_count` materializes the entire host list for each CIDR via `list(network.hosts())`

**File:** `quirk/util/targets.py:143`

**Issue:** For CIDRs, `projected_probe_count` calls `len(list(network.hosts()))`. For large ranges (e.g. `/8` = ~16 million addresses, `/16` = ~65 k), this materializes a full Python list of `IPv4Address` objects in memory just to take its length. The comment acknowledges `.hosts()` is intentional (Risks #4, to exclude network/broadcast), but `len(list(...))` can be replaced with exact arithmetic.

**Fix:**
```python
host_count = network.num_addresses - 2 if network.version == 4 and network.prefixlen < 31 else network.num_addresses
```
This matches `.hosts()` semantics for IPv4 (/31 and /32 are handled correctly by stdlib — `.hosts()` returns 0 for /32 and 2 for /31 in recent Python). Using arithmetic avoids allocating 16 million objects for a `/8`.

Note: performance issues are generally out of scope for v1, but in this case the materialization can cause the probe-budget prompt itself to hang or OOM for very large CIDRs before the user even confirms, making it a usability correctness concern.

### IN-03: Intermediate `_enable_nmap_wizard` variable in `interactive.py` is unnecessary and misleads readers

**File:** `quirk/interactive.py:217`

**Issue:** Line 217 introduces `_enable_nmap_wizard = enable_nmap` with the comment "capture before cfg construction". But `enable_nmap` is a simple local `bool` assigned at line 139 and never mutated — the capture is redundant. The comment implies a side-effect risk that does not exist, and the extra variable adds cognitive load when tracing the nmap-toggle flow (especially relevant given CR-01 above).

**Fix:** Remove the intermediate and use `enable_nmap` directly:

```python
# Before (unnecessary):
_enable_nmap_wizard = enable_nmap
# ...
setattr(cfg.connectors, "enable_nmap", _enable_nmap_wizard)  # D-06

# After:
setattr(cfg.connectors, "enable_nmap", enable_nmap)  # D-06
```

---

_Reviewed: 2026-05-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
