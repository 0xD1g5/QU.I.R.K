---
phase: 31-trend-analysis
fixed_at: 2026-04-26T00:00:00Z
review_path: .planning/phases/31-trend-analysis/31-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 31: Code Review Fix Report

**Fixed at:** 2026-04-26T00:00:00Z
**Source review:** .planning/phases/31-trend-analysis/31-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-01: Schema documentation wire format does not match implementation

**Files modified:** `docs/intelligence-schema.md`
**Commit:** 1d8e3fc
**Applied fix:** Replaced the nested `sessions.current_ts` / `sessions.previous_ts` structure and nested `new_finding_counts`/`resolved_finding_counts` objects with the correct flat field names: `current_session_ts`, `previous_session_ts`, `new_high`, `new_medium`, `new_low`, `resolved_high`, `resolved_medium`, `resolved_low`. Updated both the full two-session example and the single-session (D-06) example.

---

### WR-02: `setError` called without `cancelled` guard in `useTrendsData`

**Files modified:** `src/dashboard/src/hooks/useTrendsData.ts`
**Commit:** c41884b
**Applied fix:** Wrapped the `setError(...)` call in the `!resp.ok` branch with `if (!cancelled)` guard, matching the pattern used by every other state mutation in the hook.

---

### WR-03: `formatTs(null)` silently produces the Unix epoch date

**Files modified:** `src/dashboard/src/pages/trends.tsx`
**Commit:** 96e5a9d
**Applied fix:** Refactored `formatTs` to assign `new Date(iso)` to a variable and added `if (isNaN(d.getTime())) return "—"` before calling `toLocaleString()`, guarding against malformed timestamp strings that would otherwise produce `"Invalid Date"` output.

---

### WR-04: `new_high` badge label misleads for CRITICAL findings

**Files modified:** `src/dashboard/src/pages/trends.tsx`
**Commit:** 362ab0b
**Applied fix:** Changed both the New Findings and Resolved Findings high-bucket badges from `SEVERITY_STYLES.HIGH` / label `"HIGH"` to `SEVERITY_STYLES.CRITICAL` / label `"CRITICAL/HIGH"`, accurately reflecting that CRITICAL and HIGH severities are both bucketed into this count.

---

_Fixed: 2026-04-26T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
