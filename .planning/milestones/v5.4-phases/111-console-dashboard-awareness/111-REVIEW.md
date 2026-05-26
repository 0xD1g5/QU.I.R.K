---
phase: 111-console-dashboard-awareness
reviewed: 2026-05-25T23:45:00Z
depth: standard
iteration: 3
files_reviewed: 3
files_reviewed_list:
  - quirk/dashboard/api/routes/scan.py
  - tests/test_derive_cbom_segment.py
  - src/dashboard/src/pages/cbom.tsx
findings:
  critical: 0
  warning: 0
  info: 0
  total: 0
status: clean
---

# Phase 111: Code Review Report (Iteration 3 — Final Confirmation)

**Reviewed:** 2026-05-25T23:45:00Z
**Depth:** standard
**Files Reviewed:** 3
**Iteration:** 3 (loop-cap re-review after WR-NEW-01 fix)
**Status:** clean

## Summary

This iteration targeted the single outstanding issue from iteration 2: `WR-NEW-01` (`_derive_cbom`
never populated `CbomComponent.segment`, making the CBOM segment dropdown permanently empty for
distributed scan data). The fix has been applied and is correct. No regressions to the
iteration-1/2 fixes (WR-01..WR-05, IN-01..IN-03) were introduced. No new Critical or Warning
issues were found.

---

## WR-NEW-01 Fix Verification

**File:** `quirk/dashboard/api/routes/scan.py:706–801`

The fix adds a `"segments"` set to every `algo_map` entry across all four algorithm extraction
paths (cert pubkey, TLS version, SSH audit JSON, JWT/cloud JSON). Each path accumulates
`ep_segment` (normalised to `str | None` via `isinstance` guard at line 713, correctly handling
MagicMock and unexpected types). The return comprehension at lines 787–799 uses a walrus-operator
expression to derive the final segment value:

```python
segment=(
    next(iter(_segs))
    if len(_segs := info.get("segments", set()) - {None}) == 1
    else None
),
```

Behaviour is correct in all cases:

| Segments set accumulated | After `- {None}` | `len` | Result |
|---|---|---|---|
| `{"dmz"}` | `{"dmz"}` | 1 | `"dmz"` |
| `{"dmz", "corp"}` | `{"dmz", "corp"}` | 2 | `None` |
| `{None}` (local scans) | `set()` | 0 | `None` |
| `{None, "dmz"}` (mixed) | `{"dmz"}` | 1 | `"dmz"` |

The walrus assignment inside a list comprehension conditional is valid Python 3.8+ syntax. The
variable is scoped to the comprehension expression and is not used elsewhere.

**Test alignment:** All six test cases in `tests/test_derive_cbom_segment.py` are consistent with
the implementation. `test_named_segment_plus_null_segment_yields_none` (line 73) correctly
documents the intentional behaviour — a NULL-segment endpoint does not suppress a single named
segment from being stamped (None is stripped before the cardinality check) — and the assertion at
line 93 matches what the code produces.

**Frontend verification:** `src/dashboard/src/pages/cbom.tsx:452–464`. The `distinctSegments` memo
(line 452) now receives real string values from `CbomComponent.segment` for algorithms that belong
to a single named segment. The `typeof s === "string" && s.length > 0` guard at line 455
correctly excludes null/undefined. The `filteredComponents` memo at line 459 correctly filters
`c.segment === segmentFilter` against these real segment strings. The CBOM segment dropdown will
now be populated for distributed scan data, making the IN-03 structural refactor (lifted segment
filter shared by both Table and Graph tabs) operationally effective.

**No regressions** to the algorithm dedup logic, `source_systems` accumulation, `quantum_safety`
classification, `key_size` inheritance, or any of the findings-derivation paths altered in
iterations 1 and 2.

---

_Reviewed: 2026-05-25T23:45:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 3 (loop cap)_
