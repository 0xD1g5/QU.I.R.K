---
phase: 111-console-dashboard-awareness
fixed_at: 2026-05-25T23:30:00Z
review_path: .planning/phases/111-console-dashboard-awareness/111-REVIEW.md
iteration: 2
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 111: Code Review Fix Report

**Fixed at:** 2026-05-25T23:30:00Z
**Source review:** .planning/phases/111-console-dashboard-awareness/111-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 1
- Fixed: 1
- Skipped: 0

## Fixed Issues

### WR-NEW-01: `_derive_cbom` never sets `segment` on `CbomComponent` — CBOM segment dropdown is permanently empty

**Files modified:** `quirk/dashboard/api/routes/scan.py`, `tests/test_derive_cbom_segment.py`, `quirk/dashboard/static/assets/index-7597FI3G.js`, `quirk/dashboard/static/index.html`
**Commit:** `124bc37`
**Applied fix:**

Added a `"segments"` set to every `algo_map` entry across all four algorithm
extraction branches in `_derive_cbom` (cert_pubkey_alg, tls_version, SSH audit
JSON, JWT/cloud JSON). Each branch now calls
`algo_map[alg]["segments"].add(ep_segment)` alongside the existing `"sources"`
accumulation.

A `ep_segment` normalization line was added at the top of the per-endpoint loop:

```python
ep_segment: str | None = ep.segment if isinstance(ep.segment, str) else None
```

This guards against `MagicMock` objects used in existing SSH tests
(`_make_ssh_endpoint` uses `MagicMock(spec=CryptoEndpoint)` without setting
`segment`), which would otherwise produce a pydantic `ValidationError` when
inserted into the segments set and later emitted into `CbomComponent.segment`.

In the return list comprehension, the segment is resolved:

```python
segment=(
    next(iter(_segs))
    if len(_segs := info.get("segments", set()) - {None}) == 1
    else None
),
```

`None` values are stripped from the segments set before the length check; if
exactly one named segment remains the component is stamped with it; otherwise
`segment=None` (cross-segment or NULL-only endpoints remain unattributed).

The frontend `CbomPage.distinctSegments` memo filters for non-null strings, so
the segment `<Select>` dropdown will now correctly populate for distributed scan
data.

The static dashboard was rebuilt (`npm run build`) and the resulting asset
rename (`index-77lmDpqy.js` to `index-7597FI3G.js`) is included in the commit.

**New test file:** `tests/test_derive_cbom_segment.py` — 6 unit tests covering:
- Single-segment endpoints: component.segment stamped correctly
- NULL-only endpoints: component.segment = None
- Two named segments: component.segment = None
- NULL + one named segment: component.segment = named segment (None stripped before len check per reviewer's intent)
- Three segments: component.segment = None
- Two algorithms in separate segments: each stamped independently

**Verification results:**
- `python -m compileall quirk run_scan.py`: PASS
- `pytest tests/test_derive_cbom_segment.py tests/test_dashboard_segment_filter.py tests/test_dashboard_wiring.py -q`: 15 passed
- `npx tsc --noEmit` (src/dashboard): PASS
- `npm run build` (src/dashboard): PASS (built in 792ms)
- Pre-existing failures (7): test_cbom_classifier_coverage, test_cbom_motion_endpoints, test_cbom_motion_golden (email/broker/kafka), test_cbom_schema_validation, test_codesign_cbom — confirmed pre-existing; identical count before and after fix.

---

_Fixed: 2026-05-25T23:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
