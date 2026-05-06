---
phase: 49-compliance-mapping
plan: 02
subsystem: engine + compliance
tags: [compliance, risk-engine, pci-dss, hipaa, fips, phase-49]
requires:
  - quirk/engine/risk_engine.py:_build_finding (chokepoint from Phase 48 D-02)
  - quirk/dashboard/api/schemas.py:FindingItem
provides:
  - quirk.compliance.COMPLIANCE_MAP (24 keys, parens preserved on 2 fixed-string entries)
  - quirk.compliance.UNMAPPED_TITLES (7 allow-listed titles with inline justification)
  - quirk.compliance.TITLE_PREFIX_ALIASES (7 entries, one per f-string title)
  - quirk.compliance.STALENESS_THRESHOLD_DAYS = 365
  - quirk.compliance.status_report() (text + json formats)
  - quirk.engine.risk_engine._normalize_for_compliance (longest-prefix-first)
  - finding dict 'compliance' key (eager attachment per D-02)
  - FindingItem.compliance DTO field (forward-compat for BACK-72)
affects:
  - every finding produced by quirk/engine/risk_engine.py (now 7-key dicts)
tech-stack:
  added: []
  patterns:
    - eager attachment at chokepoint (D-02)
    - longest-prefix-first normalization (Pitfall 1)
    - frozenset allow-list for intentional non-mapping (D-04)
key-files:
  created:
    - quirk/compliance/__init__.py
  modified:
    - quirk/engine/risk_engine.py
    - quirk/dashboard/api/schemas.py
    - tests/test_risk_engine.py
decisions:
  - D-01 implemented: COMPLIANCE_MAP keyed by literal emitted title (parens preserved)
  - D-02 implemented: eager compliance attachment via _build_finding (chokepoint)
  - D-04 implemented: STALENESS_THRESHOLD_DAYS=365 + UNMAPPED_TITLES with inline reasons
  - Pitfall 1 fixed: 7 f-string title prefixes routed through TITLE_PREFIX_ALIASES
metrics:
  duration: ~6 minutes
  completed: 2026-05-05
  tasks_completed: 2
  files_changed: 4
requirements: [COMPLY-01, COMPLY-02, COMPLY-03, COMPLY-04, COMPLY-06, COMPLY-07]
---

# Phase 49 Plan 02: Compliance Mapping Module + Eager Attachment Summary

JSON-citable PCI/HIPAA/FIPS compliance refs are now eagerly attached to every finding via the `_build_finding` chokepoint, with three of four Wave 0 RED gates (schema, freshness, title-join) flipped GREEN.

## What Was Built

### Task 1 — `quirk/compliance/__init__.py` (new, 243 lines)

Built per D-01 + D-04 + Pitfall 1:

- `COMPLIANCE_MAP: Dict[str, List[Dict[str, Any]]]` — 24 finding-title keys mapping to flat lists of `{framework, control, version, last_verified, source_url}` dicts.
  - Two parens-in-key entries preserved verbatim: `"Legacy TLS versions allowed (TLS 1.0/1.1)"` and `"Plaintext Redis listener (no auth)"`.
  - Six canonical-form entries that serve as `TITLE_PREFIX_ALIASES` resolution targets (e.g., `"End-of-life in container image"`).
- `TITLE_PREFIX_ALIASES: Dict[str, str]` — 7 source-text prefixes routed to canonical keys, one per f-string title in `risk_engine.py` (lines 90, 105, 127, 143, 161, 178, 190).
- `UNMAPPED_TITLES: FrozenSet[str]` — 7 intentionally-unmapped titles, each preceded by an inline `# ` comment justifying omission (per D-04 mandate).
- `STALENESS_THRESHOLD_DAYS = 365`.
- `_PHASE_49_VERIFIED = "2026-05-05"` — single source of truth for initial `last_verified`. (T-49-06 mitigation: in 365 days, every entry trips the freshness gate, forcing re-verification.)
- Helper builders `_pci`, `_hipaa`, `_fips` to keep the data block DRY.
- `status_report(format="text"|"json")` — prints per-framework version + oldest `last_verified` + source URL. Uses `min(last_verified)` per framework as the worst-case staleness signal.

**Commit:** `7f09d4b` — `feat(49-02): add quirk/compliance module with COMPLIANCE_MAP`

### Task 2 — Eager attachment + DTO field

`quirk/engine/risk_engine.py`:
- New imports: `from quirk.compliance import COMPLIANCE_MAP, TITLE_PREFIX_ALIASES`.
- Module-level `_COMPLIANCE_PREFIXES_LONGEST_FIRST` cache (sorted descending by length at load time; O(7) per lookup).
- `_normalize_for_compliance(title)` — single-pass longest-prefix-first match against `TITLE_PREFIX_ALIASES`; verbatim passthrough for non-matching titles.
- `_build_finding` now returns a 7-key dict; the new `compliance` key holds `COMPLIANCE_MAP.get(_normalize_for_compliance(title), [])`. No other behavior changed.

`quirk/dashboard/api/schemas.py`:
- `FindingItem.compliance: List[Dict[str, Any]] = []` added below `category`. The `# DO NOT UNIFY` comment block is untouched.

**Commit:** `c70e6a4` — `feat(49-02): wire eager compliance attachment into _build_finding`

## Verification

```
pytest tests/test_compliance_schema.py        7/7 GREEN  (was 4/4 RED)
pytest tests/test_compliance_freshness.py     1/1 GREEN  (was 1/1 RED)
pytest tests/test_compliance_title_join.py    2/2 GREEN  (was 1/1 RED)
pytest tests/test_pqc_terminology_gate.py    16/16 GREEN (no regression)
pytest tests/test_risk_engine.py             19/19 GREEN (1 test renamed: 6→7 keys)
```

Five sanity invocations (verbatim mapped, parens-in-key mapped, mid-interp alias, end-paren alias, unmapped) all return expected compliance lists.

`grep -niE 'kyber|dilithium|when standards are adopted' quirk/engine/risk_engine.py` → 0 matches.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated `test_returns_six_key_dict` → `test_returns_seven_key_dict`**
- **Found during:** Task 2 verification
- **Issue:** `tests/test_risk_engine.py:108` asserted `set(f.keys()) == {6 keys}`, locking the contract that Phase 49 D-02 explicitly extends with a 7th key.
- **Fix:** Renamed test, updated expected key set to include `"compliance"`, and added a sanity assertion (`f["compliance"] == []` for the unmapped title `"t"`).
- **Files modified:** `tests/test_risk_engine.py`
- **Commit:** `c70e6a4`
- **Justification:** Plan 49-02 must_haves explicitly require `_build_finding` to attach the new key; the failing test was a pre-existing contract that needed to advance with the new contract per D-02.

## Out-of-scope (logged to deferred-items.md)

- `tests/test_cbom_schema_validation.py` — 19 pre-existing failures (Docker chaos-lab fixtures unavailable in CI). Confirmed pre-existing baseline via `git stash` before plan 49-02 changes.
- `tests/test_compliance_cli.py` — 2 RED tests; these stay RED until Plan 49-04 wires the CLI (per user instruction).
- `tests/test_compliance_report_section.py` — 1 RED test; stays RED until Plan 49-03 wires the HTML/PDF renderer (per user instruction).

## Authentication Gates

None.

## Self-Check: PASSED

- File `quirk/compliance/__init__.py` exists ✓
- File `quirk/engine/risk_engine.py` modified ✓
- File `quirk/dashboard/api/schemas.py` modified ✓
- Commit `7f09d4b` exists ✓
- Commit `c70e6a4` exists ✓
- All required exports importable ✓
- All 3 Wave 0 gate tests GREEN ✓
- PQC terminology gate stays GREEN ✓
