---
phase: 71-protocol-scanner-warnings
plan: 03
subsystem: discovery/nmap
tags: [security, hardening, audit-close, defusedxml]
requires: [PROTO-03]
provides:
  - "nmap_provider._SAFE_NMAP_ARG_RE allowlist guard"
  - "nmap_provider.default_nmap_ports_csv() consulting union"
  - "nmap_parser defusedxml-backed parsing"
affects:
  - quirk/discovery/nmap_provider.py
  - quirk/discovery/nmap_parser.py
tech-stack:
  added: []
  patterns: [allowlist-defense-in-depth, defusedxml-drop-in]
key-files:
  created:
    - tests/test_nmap_hardening.py
  modified:
    - quirk/discovery/nmap_provider.py
    - quirk/discovery/nmap_parser.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions:
  - "D-03 union: cfg.scan.ports_tls + (22,25,80,88,389,465,587,636,993,995,3389,5671,8080,9092)"
  - "D-04 allowlist regex: ^[A-Za-z0-9._:/=,-]+$"
  - "D-05 drop-in: import defusedxml.ElementTree as ET"
metrics:
  tasks: 3
  tests_added: 22
  completed: 2026-05-15
---

# Phase 71 Plan 03: Nmap Hardening Summary

Closed three protocol-scanner WARNINGs (WR-04, WR-05, WR-06) by composing a
consulting-grade default nmap port CSV, adding a defense-in-depth allowlist
guard on `extra_args`, and switching `nmap_parser` to `defusedxml` to
eliminate XXE / billion-laughs surface.

## What Was Built

### Task 1 — Default port CSV + extra_args allowlist (WR-04 + WR-05)

`quirk/discovery/nmap_provider.py`:

- Added module-level `_SAFE_NMAP_ARG_RE = re.compile(r"^[A-Za-z0-9._:/=,-]+$")`.
  Mirrors the Phase 70 `_SAFE_COL_TYPE_RE` defense-in-depth pattern.
- Added `_FIXED_NMAP_PORTS = (22, 25, 80, 88, 389, 465, 587, 636, 993, 995, 3389, 5671, 8080, 9092)`
  and a `default_nmap_ports_csv(ports_tls)` helper unioning the dynamic TLS
  half with the fixed protocol set (sorted, deduped).
- Replaced the stale fallback CSV (`"22,80,443,8443,9443,10443,5001"`) with a
  call to `default_nmap_ports_csv((443, 8443, 9443, 10443, 5001))` — the
  canonical Phase 47 TLS list.
- Inside `run_nmap_discovery`, before extending `args` with `extra_args`, every
  token is validated; any failure raises `ValueError(f"Unsafe nmap extra arg: {token!r}")`.

**Final port CSV** (with default ports_tls):
`22,25,80,88,389,443,465,587,636,993,995,3389,5001,5671,8080,8443,9092,9443,10443`

Commit: `59ada04`

### Task 2 — defusedxml in nmap_parser (WR-06)

`quirk/discovery/nmap_parser.py`:

```python
# Before
import xml.etree.ElementTree as ET
# After
# defusedxml per audit WR-06 — defuses XXE/billion-laughs on nmap XML output
import defusedxml.ElementTree as ET
```

One-line import swap. `defusedxml.ElementTree` exposes `parse`/`fromstring`
with the same signatures as stdlib ET; no call-site changes needed. defusedxml
was already a core dep (`pyproject.toml`).

Commit: `3d5eed6`

### Task 3 — Tests + audit ledger flip

`tests/test_nmap_hardening.py` (22 tests, all passing):

- `test_safe_nmap_arg_re_accepts_legitimate_args` (parametrized x7)
- `test_safe_nmap_arg_re_rejects_injection` (parametrized x10 — `;`, `$()`,
  backtick, `&&`, `|`, redirects, `$IFS`, newline, whitespace)
- `test_run_nmap_discovery_rejects_unsafe_extra_args` — monkeypatches
  `subprocess.run` to raise; proves validation happens BEFORE subprocess.
- `test_default_port_csv_includes_consulting_set` — asserts every required
  protocol port present and CSV sorted numerically.
- `test_default_port_csv_dedups` — asserts no duplicates when overlap.
- `test_nmap_parser_uses_defusedxml` — `ET.__name__` starts with `defusedxml`.
- `test_nmap_parser_blocks_xxe` — feeds external-entity DOCTYPE; defusedxml
  raises `defusedxml.common.EntitiesForbidden`.

Flipped audit rows `scanners-protocol/WR-04`, `WR-05`, `WR-06` to
`Phase 71 | [x] closed` with per-row evidence.

Commit: `1f9ed04`

## Deviations from Plan

None — plan executed exactly as written. Minor refinement: the consulting
port CSV is exposed as a reusable `default_nmap_ports_csv()` helper rather
than inlined, which also enabled the dedupe regression test.

## Verification

- `python -m compileall quirk/discovery/nmap_provider.py quirk/discovery/nmap_parser.py` — clean.
- `pytest tests/test_nmap_hardening.py -x` — **22 passed in 0.02s**.
- `grep -cE "scanners-protocol/WR-0[456].*Phase 71.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` → **3**.

## Self-Check: PASSED

- `quirk/discovery/nmap_provider.py` — FOUND, contains `_SAFE_NMAP_ARG_RE` + `default_nmap_ports_csv`.
- `quirk/discovery/nmap_parser.py` — FOUND, imports `defusedxml.ElementTree`.
- `tests/test_nmap_hardening.py` — FOUND, 22 tests passing.
- Commit `59ada04` — FOUND (feat: default port CSV + extra_args allowlist).
- Commit `3d5eed6` — FOUND (feat: switch nmap_parser to defusedxml).
- Commit `1f9ed04` — FOUND (test: nmap hardening tests + WR flips).
