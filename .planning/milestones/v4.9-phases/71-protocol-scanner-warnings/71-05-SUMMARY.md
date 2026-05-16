---
phase: 71-protocol-scanner-warnings
plan: 05
subsystem: protocol-scanners
tags: [phase-71, proto-05, wr-11, wr-12, wr-13, wr-14, cleanup, internal-contract]
requires: []
provides:
  - "ScanCfg.motion_concurrency knob (default 50)"
  - "Unified optional-dep extras-error message format"
  - "target_expander: stable dedup + /22 CIDR cap + IP normalization"
affects:
  - quirk/config.py
  - quirk/scanner/email_scanner.py
  - quirk/scanner/broker_scanner.py
  - quirk/scanner/container_scanner.py
  - quirk/scanner/source_scanner.py
  - quirk/scanner/target_expander.py
  - run_scan.py
  - tests/test_credential_leakage.py
  - tests/test_extras_concurrency_expander.py
  - .planning/audit-2026-05-08/AUDIT-TASKS.md
tech-stack:
  added: []
  patterns:
    - "dict.fromkeys() stable dedup"
    - "ipaddress.ip_address(x) normalization for str/IPv4Address parity"
    - "ScanCfg-driven ThreadPool max_workers"
key-files:
  created:
    - tests/test_extras_concurrency_expander.py
  modified:
    - quirk/config.py
    - quirk/scanner/email_scanner.py
    - quirk/scanner/broker_scanner.py
    - quirk/scanner/container_scanner.py
    - quirk/scanner/source_scanner.py
    - quirk/scanner/target_expander.py
    - run_scan.py
    - tests/test_credential_leakage.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
  deleted:
    - quirk/discovery/tls_scanner.py
decisions:
  - "Plumbed motion_concurrency as an explicit keyword argument (default 50) on each scan_*_targets function, rather than reading cfg directly inside the scanner modules. Preserves their existing test surface (none of these functions take a cfg) and keeps the dependency-injection-style call shape used elsewhere in the scanner package."
  - "For container_scanner.py / source_scanner.py, the unified extras message references quirk[cbom] plus the system binary install (syft / semgrep). These tools are not pip-extras themselves but they feed the CBOM pipeline, so the cbom extra is the closest legitimate quirk[...] tag."
  - "tests/test_credential_leakage.py had a path-literal reference to the deleted quirk/discovery/tls_scanner.py in its MODIFIED_FILES parametrize list. Removed (commented) that entry rather than letting the parametrized test FileNotFoundError on a non-existent path. Rule 3 deviation."
metrics:
  duration_minutes: 18
  completed_date: 2026-05-15
  tasks_completed: 5
  files_changed: 9
  tests_added: 16
---

# Phase 71 Plan 05: Cross-Cutting Protocol-Scanner Cleanup Summary

Closes the final four WARNING rows of the Phase 71 protocol-scanner sweep:
WR-11 (extras messaging), WR-12 (ThreadPool concurrency knob), WR-13 (dead-code
deletion), WR-14 (target_expander hardening). Internal-contract only — no
schema, no scan output, no CLI behavior change at default settings.

## Deliverables

### WR-12 — `ScanCfg.motion_concurrency` knob

`quirk/config.py` gains a `motion_concurrency: int = 50` field on `ScanCfg`,
slotted alongside `tls_concurrency`, `ssh_concurrency`,
`fingerprint_concurrency`. Both the dataclass field-list AND the explicit
`__init__` signature/assignment block were updated.

Four hardcoded `min(len(tasks), 50)` (and one `min(len(all_tasks), 50)`)
literals replaced:

- `quirk/scanner/email_scanner.py:532` — `scan_email_targets`
- `quirk/scanner/broker_scanner.py:475` — `scan_kafka_targets`
- `quirk/scanner/broker_scanner.py:574` — `scan_rabbitmq_targets`
- `quirk/scanner/broker_scanner.py:801` — `scan_redis_targets`

Each of the four `scan_*_targets` functions now accepts a
`motion_concurrency: int = 50` keyword argument (default preserves prior
behavior exactly — no operational change unless an operator opts in via YAML).
`run_scan.py` wires `cfg.scan.motion_concurrency` into all four call sites.

### WR-11 — Unified extras-error message format

All four scanners now emit a consistent warning when an optional dependency is
missing, matching the Phase 41 / Phase 45 precedent format
`"X is not installed — pip install 'quirk[Y]' to enable Z scanning"`:

| File | Dep | Extras tag |
|------|-----|------------|
| `email_scanner.py:131` | sslyze | `quirk[motion]` |
| `broker_scanner.py:147` | sslyze | `quirk[motion]` |
| `container_scanner.py:74` | syft (system) | `quirk[cbom]` + `brew install syft` |
| `source_scanner.py:51` | semgrep (system) | `quirk[cbom]` + `pip install semgrep` |

Behavior is unchanged — these are degrade-and-warn paths, not raise-and-abort
paths. Only the message text was unified.

### WR-13 — `quirk/discovery/tls_scanner.py` deleted

Pre-deletion grep confirmed zero Python imports of `quirk.discovery.tls_scanner`
across `quirk/` and `tests/`. The only callsite was a path-literal entry in
`tests/test_credential_leakage.py::MODIFIED_FILES` — that entry was removed
(commented with the Phase 71 reference) so the parametrized
`test_all_callsites_import_safe_str` test no longer FileNotFoundErrors on the
deleted path.

The live TLS scanner at `quirk/scanner/tls_scanner.py` (557 lines, the canonical
Phase 46-fixed implementation) is untouched.

### WR-14 — `target_expander.expand_targets()` hardened

Three corrections in `quirk/scanner/target_expander.py`:

1. **Per-CIDR cap (D-01):** `ipaddress.ip_network(cidr, strict=False).num_addresses > 1024` raises `ValueError` BEFORE `.hosts()` is iterated. A misconfigured `/8` now fails loud immediately instead of burning memory enumerating 16M addresses.
2. **Stable dedup (D-14):** Return value is `list(dict.fromkeys(targets))`. Python 3.7+ insertion-order guarantee makes this deterministic and order-preserving; eliminates report drift from the prior `set`-based form.
3. **IP normalization (D-14):** A new `_norm_ip(x)` helper calls `str(ipaddress.ip_address(x))`. Both `include_ips` and `exclude_ips` membership comparisons use it, so exclude filters now match whether the caller supplies `str` or `ipaddress.IPv4Address` entries.

### Tests

`tests/test_extras_concurrency_expander.py` — 16 contract tests:

- 4 × extras-message format (one per scanner module)
- 4 × `ScanCfg.motion_concurrency` (default, override, email source-uses-it, broker source-uses-it)
- 2 × WR-13 file deletion (spec is None; live tls_scanner imports)
- 5 × `expand_targets`: large-CIDR ValueError, small-CIDR allows, stable dedup, IP-type normalization, /22 boundary
- 1 × AUDIT-TASKS row flip verification

All 16 pass: `python -m pytest tests/test_extras_concurrency_expander.py -x -q` → `16 passed in 0.10s`.

### Audit ledger

Rows `scanners-protocol/WR-11`, `WR-12`, `WR-13`, `WR-14` in
`.planning/audit-2026-05-08/AUDIT-TASKS.md` flipped from
`| — | [ ] open |` to `| Phase 71 | [x] closed |`. No other rows touched.

## Deviations from Plan

**[Rule 3 — Blocking] Removed stale entry from `tests/test_credential_leakage.py`**

- **Found during:** Task 3 (delete discovery/tls_scanner.py)
- **Issue:** `MODIFIED_FILES` list contained the literal string `"quirk/discovery/tls_scanner.py"`. The parametrized `test_all_callsites_import_safe_str` calls `path.read_text()` on each entry — would have raised `FileNotFoundError` for every test session after the delete.
- **Fix:** Replaced the path entry with a comment citing Phase 71 / WR-13. Test now parametrizes over 7 files instead of 8.
- **Files modified:** `tests/test_credential_leakage.py`
- **Commit:** 48f16d9

**[Plan-shape adjustment] `motion_concurrency` plumbed as kwarg instead of `cfg.scan.motion_concurrency` read inside scanners**

- **Found during:** Task 1
- **Reasoning:** The plan action text reads `min(len(tasks), cfg.scan.motion_concurrency)` but `cfg` is not in scope inside `scan_email_targets` / `scan_kafka_targets` / `scan_rabbitmq_targets` / `scan_redis_targets` — none of them accept a config object today. Adding an implicit dependency on `cfg` would break their test surface.
- **Resolution:** Each function now takes an explicit `motion_concurrency: int = 50` kwarg; `run_scan.py` passes `cfg.scan.motion_concurrency` at every call site. Honors the audit row intent (operator-configurable max_workers, default 50) while preserving the scanner functions' DI-friendly signatures.
- **Acceptance criteria still satisfied:** `motion_concurrency` token count: config.py=3, email_scanner.py=2, broker_scanner.py=6. Zero `min(len(tasks), 50)` / `min(len(all_tasks), 50)` literals remain.

## Known Stubs

None.

## Threat Flags

None — all surface changes (CIDR cap, IP normalization, dead-file deletion) are
already captured in the plan's `<threat_model>` (T-71-12 through T-71-15).

## Self-Check: PASSED

- FOUND: tests/test_extras_concurrency_expander.py
- FOUND: 6347148 (feat(71-05): motion_concurrency)
- FOUND: 7ffb2c1 (feat(71-05): unified extras messaging)
- FOUND: 48f16d9 (chore(71-05): delete discovery/tls_scanner.py)
- FOUND: eea704f (feat(71-05): target_expander hardening)
- FOUND: 229c07f (test(71-05): contract tests + audit flip)
- MISSING: quirk/discovery/tls_scanner.py (intentionally deleted — WR-13)
