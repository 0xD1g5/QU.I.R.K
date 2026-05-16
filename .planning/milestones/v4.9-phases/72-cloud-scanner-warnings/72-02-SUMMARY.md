---
phase: 72-cloud-scanner-warnings
plan: 02
subsystem: scanner-cloud
tags: [azure, k8s, keyvault, gke, audit-closure, WR-03, WR-06, WR-17, WR-20]
requires: []
provides: [CLOUD-02]
affects: [scanner.azure_connector, scanner.k8s_connector]
tech_stack_added: []
tech_stack_patterns: [fail-soft logger.v, fresh-dict-per-branch, explicit-None-filter, identity-tuple-sanitization]
key_files_created:
  - tests/test_azure_keyvault.py
key_files_modified:
  - quirk/scanner/azure_connector.py
  - quirk/scanner/k8s_connector.py
  - tests/test_k8s_connector.py
  - .planning/audit-2026-05-08/AUDIT-TASKS.md
decisions: [D-12, D-13, D-14, D-15]
metrics:
  tasks_completed: 3
  commits: 4
  tests_added: 14
  tests_passing: 32
  files_modified: 4
  files_created: 1
  duration: ~25min
completed: 2026-05-15
---

# Phase 72 Plan 02: Azure + K8s data-correctness Summary

Closed CLOUD-02 by fixing four locked data-correctness defects (D-12/13/14/15) in the Azure KeyVault and Kubernetes connectors, with RED→GREEN test coverage for each and the corresponding audit-ledger rows (WR-03/06/17/20) flipped to `Phase 72 | [x] closed`.

## What Was Built

### Task 1 — Azure KeyVault `key_size` per key type (WR-03 / D-12)

`quirk/scanner/azure_connector.py::_scan_keyvault_keys` no longer reads `properties.key_size` unconditionally (which returned `None` for RSA/EC because `KeyProperties` does not expose key material). It now derives `key_size` per key type:

- **RSA / RSA-HSM** → `key.n.bit_length()` (with `key.key_size` as a fallback when `.n` is absent)
- **EC / EC-HSM** → curve-name lookup in the new module-scope `_AZURE_EC_CURVE_SIZES` map (`P-256` → 256, `P-384` → 384, `P-521` → 521, `secp256k1` → 256)
- **OCT / OCT-HSM** → existing `getattr(key, "key_size", None)` retained
- **Unknown** → `None` + DEBUG message via `logger.v(...)` (project convention; spec said `logger.debug` but the project's logger uses `.v()`)

Constant `_AZURE_EC_CURVE_SIZES` is module-private per D-25's no-new-helper directive — no new helper module introduced.

### Task 2 — K8s connector triple-fix (WR-06/17/20 / D-13/14/15)

`quirk/scanner/k8s_connector.py`:

- **D-13 (WR-06)** — `_emit_inaccessible_finding` now applies `cluster_name = (cluster_name or "").replace(":", "")` at function entry, before the cluster name is embedded in the `host="k8s://{...}"` identity. Single-site fix; no propagation to other emit functions per D-25.
- **D-14 (WR-17)** — `_enumerate_secret_types` replaces the silent `s.type or "Opaque"` coercion with an explicit two-pass approach: collect raw types, count Nones for a DEBUG log via `logger.v`, then build the `Counter` over `(t for t in secret_types if t is not None)`. None and Opaque are now semantically distinct in the count signal (RESEARCH Pitfall 4).
- **D-15 (WR-20)** — `_scan_gke_encryption` builds `dat_scan_json` as a **fresh dict in each branch**: the encrypted branch includes `key_name` plus `encrypted: True`; the unencrypted branch explicitly omits `key_name` and sets `encrypted: False`. Inline comment marks the contract (`# NOTE: no key_name key — the unencrypted path must NOT include it (Phase 72 D-15).`). Eliminates the prior cross-branch leak where `getattr(db_enc, "key_name", "")` would echo a stale value on the unencrypted code path.

### Task 3 — Tests + audit-ledger flip

- **`tests/test_azure_keyvault.py`** (NEW, 9 tests) — RSA 2048/4096 bit_length, EC P-256/P-384/P-521/secp256k1 curve map, OCT 256, unknown key type leaves None and triggers `logger.v` debug log, EC unknown curve leaves None.
- **`tests/test_k8s_connector.py`** (+5 tests) — colon-strip happy path, empty cluster_name fallback, Counter excludes None with DEBUG-log assertion, unencrypted `dat_scan_json` omits `key_name`, encrypted `dat_scan_json` includes `key_name` (positive guard).
- **`.planning/audit-2026-05-08/AUDIT-TASKS.md`** — WR-03/06/17/20 rows flipped to `Phase 72 | [x] closed` with per-row evidence citations. `git diff --stat` confirms exactly 4 line changes.

## Test Results

```
tests/test_k8s_connector.py .......................     23 passed
tests/test_azure_keyvault.py .........                   9 passed
============================== 32 passed in 0.53s ==============================
```

All pre-existing 18 k8s tests continue to pass — the D-14 change did not regress any fixture that relied on None→Opaque coercion (there were none; the prior tests used explicit type strings).

## Decisions Made

- **D-12** — RSA via `bit_length()` with `key.key_size` fallback (defensive — `KeyProperties` shape may vary per SDK version). EC via curve-name map with `getattr(key, "crv", None) or getattr(key, "curve", None)` (handles both legacy and current SDK attribute names).
- **D-13** — Single-site colon strip at function entry; identity is the `host="k8s://{cluster_name}"` field.
- **D-14** — `logger.v(...)` used instead of the spec's `logger.debug(...)` to match project convention (`.v` is the project-wide logger method).
- **D-15** — Both branches build the dict explicitly; minor key duplication (`cluster`, `provider`, `current_state`) accepted per D-25's "minimal diff" lens vs introducing a helper.

## Deviations from Plan

**None substantive.** Two minor adaptations:

1. **Logger method name** — Plan said `logger.debug(...)`. Project convention is `.v()` (verified across `azure_connector.py`, existing `k8s_connector.py`, etc.). Used `.v()`. Not a deviation in intent — the spec called for a DEBUG-level message, which `.v()` is.
2. **Variable naming** — Plan said `kt = str(getattr(properties, "key_type", "") or "").lower()` but `_scan_keyvault_keys` iterates `key` (a `KeyProperties` object); there is no separate `properties` variable in scope. Used the existing `key_type_str` (already built one line earlier) and lowered it. Behavior is identical; the plan's wording is satisfied semantically.

No Rule 1/2/3 auto-fixes were triggered. No Rule 4 architectural change required.

## Known Stubs

None.

## Files Touched

| File | Change | LOC delta |
|------|--------|-----------|
| `quirk/scanner/azure_connector.py` | per-type `key_size` derivation + `_AZURE_EC_CURVE_SIZES` constant | +35 / −1 |
| `quirk/scanner/k8s_connector.py` | colon strip + None filter + fresh dat_scan_json | +36 / −12 |
| `tests/test_azure_keyvault.py` | NEW — 9 tests | +148 |
| `tests/test_k8s_connector.py` | +5 tests (colon strip ×2, None filter, dat_scan_json ×2) | +123 |
| `.planning/audit-2026-05-08/AUDIT-TASKS.md` | 4 WR rows flipped | +4 / −4 |

## Commits

- `3151cf3` — fix(72-02): populate Azure KeyVault key_size per key type (WR-03, D-12)
- `5d7a4c0` — fix(72-02): K8s data correctness — colon strip, None filter, fresh dat_scan_json (WR-06/17/20)
- `c3ba1d4` — test(72-02): WR-03/06/17/20 coverage for Azure KeyVault + K8s fixes
- `7ca4ac7` — docs(72-02): flip WR-03/06/17/20 audit rows to Phase 72 closed

## Self-Check: PASSED

- [x] `quirk/scanner/azure_connector.py` modified — `_AZURE_EC_CURVE_SIZES` (line 44) + `bit_length` (line 71) present
- [x] `quirk/scanner/k8s_connector.py` modified — colon strip (line 368), None filter (line 308), D-15 comment (line 153) present
- [x] `tests/test_azure_keyvault.py` exists with 9 passing tests
- [x] `tests/test_k8s_connector.py` extended with 5 passing tests (23 total in file)
- [x] AUDIT-TASKS.md `grep -cE "scanners-cloud/WR-(03|06|17|20).*Phase 72.*\[x\] closed"` returns 4
- [x] All 4 commits exist in `git log --oneline`
- [x] `python -m compileall quirk/scanner/azure_connector.py quirk/scanner/k8s_connector.py` clean
- [x] `pytest tests/test_azure_keyvault.py tests/test_k8s_connector.py -x` → 32 passed
- [x] No files outside the locked WR-03/06/17/20 scope modified (D-25 compliance)
