---
phase: 36-dashboard-motion-tab
fixed_at: 2026-04-28T00:00:00Z
review_path: .planning/phases/36-dashboard-motion-tab/36-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 36: Code Review Fix Report

**Fixed at:** 2026-04-28
**Source review:** `.planning/phases/36-dashboard-motion-tab/36-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (1 critical + 4 warnings; 3 info findings deferred per scope = critical_warning)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: Variable shadowing — `scan_id` query param overwritten at line 700

**Files modified:** `quirk/dashboard/api/routes/scan.py`
**Commit:** `b6d4d39`
**Applied fix:** Renamed the derived ISO-timestamp local from `scan_id` to `response_scan_id` at line 700, and updated the `ScanMeta(scan_id=...)` constructor call to use the new name. The function-parameter `scan_id` is no longer shadowed inside `get_latest_scan`.

### WR-01: TS `ConfidenceData` declares `factor_breakdown` but Pydantic does not

**Files modified:** `quirk/dashboard/api/schemas.py`, `quirk/dashboard/api/routes/scan.py`
**Commit:** `c834a84`
**Applied fix:** Added `factor_breakdown: Optional[Dict[str, Any]] = None` to the Pydantic `ConfidenceData` model and populated it in `scan.py` from `confidence_raw.get("factor_breakdown", {})` so the FastAPI response matches the TypeScript contract.

### WR-02: `HTTPS/AWS-SQS` protocol rendered in neither Email nor Broker table

**Files modified:** `src/dashboard/src/pages/motion.tsx`
**Commit:** `082f869`
**Applied fix:** Extended `getBrokerFamily` return type to include `"Cloud"` and added a `protocol.startsWith("HTTPS/")` branch. Updated `BrokerGroupedSections` `FAMILIES` array and the initial `grouped` map to include a `"Cloud"` group so HTTPS/AWS-SQS endpoints render in their own broker section.

### WR-03: `VERY_LOW` and `NO_DATA` confidence ratings silently fall through to "Low Confidence"

**Files modified:** `src/dashboard/src/pages/executive.tsx`
**Commit:** `057ff6c`
**Applied fix:** Added explicit `"VERY_LOW" -> "Very Low Confidence"` arm in the badge label ternary chain and changed the final fallback from `"Low Confidence"` to `"No Data"` so `NO_DATA` rating displays correctly.

### WR-04: `_derive_motion_findings` missing `description` and `remediation`

**Files modified:** `quirk/dashboard/api/routes/scan.py`
**Commit:** `8305a02`
**Applied fix:** Populated `description` and `remediation` strings on all four severity branches (plaintext, starttls_warning, legacy TLS, default TLS) of `_derive_motion_findings`, and passed both fields into the `MotionFinding(...)` constructor. Brings the new function in line with `_derive_findings` and `_derive_identity_findings`.

## Skipped Issues

None — all in-scope findings were applied successfully.

---

_Fixed: 2026-04-28_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
