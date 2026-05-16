---
phase: 72-cloud-scanner-warnings
plan: 04
subsystem: engine
tags: [cache, profiles, integrity, hardening, cloud-scanner, warnings]
requirements: [CLOUD-04]
status: complete
completed: 2026-05-15
dependency_graph:
  requires: []
  provides:
    - cache._read_json malformed-JSON safety (returns None instead of raising)
    - cache.scope_hash includes cfg.connectors (toggling enable_email/enable_broker invalidates cache)
    - quirk/engine/profiles.py # eof integrity marker
    - Defensive sidecar contract: scope_hash pops `_user_set_fields` (no-op until PLAN 05 D-02 lands)
  affects:
    - 72-05 (PLAN 05 / D-02): ConnectorsCfg._user_set_fields sidecar — exact name and module path documented below
tech_stack:
  added: []
  patterns:
    - json.load wrapped in try/except (JSONDecodeError, UnicodeDecodeError)
    - dataclasses.asdict(cfg.connectors) recursive serialization for cache scope hashing
    - Defensive dict.pop("_user_set_fields", None) — works whether or not D-02 has landed
    - module-level logger = logging.getLogger(__name__) convention added to cache.py
key_files:
  modified:
    - quirk/engine/cache.py
    - quirk/engine/profiles.py
    - tests/test_cache.py
    - .planning/audit-2026-05-08/AUDIT-TASKS.md (rows WR-15, WR-16, WR-21)
  created: []
decisions:
  - D-18 (WR-15) — _read_json returns None on corrupt JSON; file left on disk for forensics
  - D-19 (WR-16) — scope_hash includes connectors via dataclasses.asdict; sidecar popped defensively
  - D-06 (WR-21) — profiles.py Pitfall-5 path: file intact, # eof marker appended
  - D-25 — only _read_json, scope_hash, and the EOF marker line touched (no incidental cleanup)
metrics:
  duration: ~15 minutes
  tasks: 3
  commits: 3 (4 including the audit-ledger flip piggybacked on commit 8a13153 from PLAN 72-01)
  tests_added: 10 (14 total in tests/test_cache.py)
---

# Phase 72 Plan 04: CLOUD-04 (Cache + scope_hash + profiles.py integrity) Summary

**One-liner:** Closed 3 cloud-scanner WARNINGs (WR-15, WR-16, WR-21) by adding a malformed-JSON guard to `cache._read_json`, including `cfg.connectors` in `cache.scope_hash` (with a defensive sidecar pop for forward-compat with PLAN 05 / D-02), and verifying `quirk/engine/profiles.py` integrity per D-06 with a `# eof` marker.

## What Was Built

### Task 1 — cache.py (D-18 + D-19)

**`quirk/engine/cache.py`** (90 → 115 lines):

- Added module-level `logger = logging.getLogger(__name__)` and a `dataclasses` import.
- `_read_json(path)` now wraps `json.load` in `try/except (json.JSONDecodeError, UnicodeDecodeError)`:
  - On failure: logs `WARNING` (`Cache file %s corrupt — ignoring: %s`) and returns `None`.
  - File is intentionally left on disk (D-18 forensics rationale — no `os.remove`).
- `load_cache(...)` now guards `if obj is None: return None` before reading `_cached_at`, so a corrupt cache file is transparently treated as a cache miss.
- `scope_hash(...)` now includes a `connectors` key in its hash input:
  ```python
  connectors_dict = {}
  if getattr(cfg, "connectors", None) is not None and dataclasses.is_dataclass(cfg.connectors):
      connectors_dict = dataclasses.asdict(cfg.connectors)
      connectors_dict.pop("_user_set_fields", None)
  parts = { ... "connectors": connectors_dict }
  ```
  Toggling `cfg.connectors.enable_email` / `enable_broker` (or any other connector flag) now flips the hash and invalidates the cache. The `dataclasses.is_dataclass` guard tolerates test cfgs that use `SimpleNamespace`-style stubs.

**Commit:** `7a89241 fix(72-04): cache _read_json malformed-JSON guard + scope_hash connectors (WR-15, WR-16)`

### Task 2 — profiles.py EOF marker (D-06)

**D-06 verification sequence executed:**

| Step | Command | Result |
|------|---------|--------|
| 1 | `python -m py_compile quirk/engine/profiles.py` | exits 0 |
| 2 | `git log --oneline -5 -- quirk/engine/profiles.py` | last touch `67b1537` (Phase 33-02 `enable_broker` gating), `9799d8d` (Phase 32-04), `3f0fd55` (qcscan→quirk rename) — no truncation event |
| 3 | `wc -l quirk/engine/profiles.py` | 153 (pre-marker) — matches RESEARCH Pitfall-5 |
| 4 | tail vs git history | identical |

**Pitfall-5 path confirmed: file IS intact.** No reconstruction needed.

**Change:** Appended a single comment line + `# eof` marker as the last two lines:
```python
# Phase 72 D-06 / WR-21: explicit EOF marker confirms file integrity (py_compile + git history verified intact at 153 lines).
# eof
```
Final line count: 155. `tail -1` returns `# eof`. `py_compile` still passes.

**Commit:** `19c5a31 chore(72-04): add # eof marker to profiles.py (WR-21 / D-06)`

### Task 3 — Tests + audit-ledger flip

**`tests/test_cache.py`** (44 → 199 lines, 4 → 14 tests; the 4 existing TTL tests are preserved):

WR-15 / D-18 — malformed-JSON safety (3 tests):
- `test_read_json_returns_none_on_malformed_json` — `{not valid json` → None + WARNING log + file remains on disk (forensics).
- `test_read_json_returns_none_on_unicode_error` — `b"\xff\xfe invalid utf-8 bytes"` → None.
- `test_load_cache_skips_corrupt_file` — corrupt cache file in cache_dir → `load_cache` returns None (no exception).

WR-16 / D-19 — scope_hash connector invalidation (5 tests):
- `test_scope_hash_changes_when_enable_email_flips`
- `test_scope_hash_changes_when_enable_broker_flips`
- `test_scope_hash_stable_for_identical_cfg` (sanity / determinism)
- `test_scope_hash_handles_user_set_fields_sidecar` (injects `frozenset` sidecar; asserts no `TypeError`)
- `test_scope_hash_sidecar_does_not_affect_hash` (sidecar content must be popped, not hashed)

WR-21 / D-06 — profiles.py EOF integrity (2 tests):
- `test_profiles_py_has_eof_marker` — last non-empty line is the literal `# eof`.
- `test_profiles_py_compiles` — `py_compile.compile(path, doraise=True)` succeeds.

A small helper `_make_cfg(connectors)` builds a minimal cfg via `types.SimpleNamespace` for `targets`/`scan` plus a real `ConnectorsCfg`, since `scope_hash` only reads `cfg.targets`, `cfg.scan`, and `cfg.connectors`.

**Result:** 14/14 pass in 0.03s.

**Commit (tests):** `8aef460 test(72-04): cache _read_json malformed-JSON + scope_hash connectors + profiles EOF (WR-15/16/21)`

**Audit-ledger flips** (WR-15, WR-16, WR-21 → `Phase 72 | [x] closed`): the row updates were applied locally but a parallel wave-1 agent (PLAN 72-01) staged and committed the file containing the union of all wave-1 ledger edits in `8a13153 docs(72-01): flip WR-01/02/13/14/19 audit rows to closed under Phase 72`. My 3 row edits are present in that commit with the correct evidence text. `grep -cE "scanners-cloud/WR-(15|16|21).*Phase 72.*\[x\] closed"` returns 3.

## Defensive Sidecar Contract (for PLAN 72-05 / D-02)

PLAN 04 implements `dict.pop("_user_set_fields", None)` defensively in `scope_hash` so that PLAN 05 can land D-02 without touching cache.py again. The exact canonical sidecar that PLAN 05 must add:

- **Attribute name:** `_user_set_fields`
- **Module path:** `quirk.config.ConnectorsCfg._user_set_fields`
- **Type:** `frozenset[str]`
- **Declaration:** `_user_set_fields: frozenset = dataclasses.field(default_factory=frozenset, repr=False, compare=False)` (use `dataclasses.field` since `quirk/config.py` already imports `field` and `dataclasses` separately at the top — verified by reading the file).
- **Population site:** `quirk/config.py:377` loader — after the `ConnectorsCfg(**conn_raw)` construction in `config_from_dict`, assign `connectors_obj._user_set_fields = frozenset(conn_raw.keys())` (the `conn_raw` dict comprehension at line 377 is the post-`_KNOWN_CONNECTOR_KEYS` filtered dict; its keys are the YAML keys the user actually supplied that map to known fields).
- **Semantic:** the frozenset MUST contain exactly the connector field names that appeared in the user's raw YAML `connectors:` block (after filtering by `_KNOWN_CONNECTOR_KEYS`). PLAN 05 / D-02 then uses `if 'enable_email' not in cfg.connectors._user_set_fields:` in `quirk/engine/profiles.py:110-117, 134-141` to skip the standard/deep mutation when the user explicitly set the value (including `enable_email: false`).

The test `test_scope_hash_handles_user_set_fields_sidecar` already exercises the sidecar-pop path by injecting the frozenset directly on `ConnectorsCfg`; PLAN 05 will re-use the same shape from a declared dataclass field.

## Deviations from Plan

None — plan executed exactly as written.

The only nuance worth recording: the audit-ledger flip task expected its own commit, but a parallel wave-1 executor (PLAN 72-01) committed the ledger file before I could `git add` it. Net effect on the audit ledger is identical (my 3 rows are flipped with correct evidence text); only the commit hash is shared with PLAN 72-01's `8a13153`. Not a functional deviation, just a multi-agent race artifact.

## Verification

- `python -m compileall quirk/engine/cache.py quirk/engine/profiles.py` — clean.
- `python -m pytest tests/test_cache.py -x` — 14 passed in 0.03s.
- `tail -1 quirk/engine/profiles.py` — `# eof`.
- `grep -cE "scanners-cloud/WR-(15|16|21).*Phase 72.*\[x\] closed" .planning/audit-2026-05-08/AUDIT-TASKS.md` — 3.

## Commits

| # | Hash | Subject |
|---|------|---------|
| 1 | `7a89241` | fix(72-04): cache _read_json malformed-JSON guard + scope_hash connectors (WR-15, WR-16) |
| 2 | `19c5a31` | chore(72-04): add # eof marker to profiles.py (WR-21 / D-06) |
| 3 | `8aef460` | test(72-04): cache _read_json malformed-JSON + scope_hash connectors + profiles EOF (WR-15/16/21) |
| 4 | `8a13153` | docs(72-01): flip WR-01/02/13/14/19 audit rows to closed under Phase 72 — also carries my WR-15/16/21 flips (multi-agent race; see Deviations) |

## Threat Flags

None — no new network surface, auth path, file access pattern, or schema change introduced. Mitigations applied (T-72-12 cache DoS, T-72-13 stale-cache tampering, T-72-14 file-truncation tampering) are all listed in the plan's threat register; no new STRIDE surface discovered during execution.

## Self-Check: PASSED

- Files present and non-empty:
  - `quirk/engine/cache.py` — FOUND (115 lines).
  - `quirk/engine/profiles.py` — FOUND (155 lines, `# eof` last line).
  - `tests/test_cache.py` — FOUND (199 lines, 14 tests passing).
- Commits exist in `git log --all`:
  - `7a89241` FOUND.
  - `19c5a31` FOUND.
  - `8aef460` FOUND.
  - `8a13153` FOUND (carries audit-ledger flips for WR-15/16/21 alongside 72-01's own).
- Audit-ledger grep for `Phase 72.*[x] closed` rows: WR-15 ✓, WR-16 ✓, WR-21 ✓.
