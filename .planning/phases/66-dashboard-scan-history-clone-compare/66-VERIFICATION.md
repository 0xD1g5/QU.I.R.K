---
phase: 66-dashboard-scan-history-clone-compare
verified: 2026-05-14T00:00:00Z
status: human_needed
score: 7/7 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Navigate to /scans in the live dashboard and confirm the table renders with date, target, profile, score, and finding-count columns"
    expected: "Table rows visible for each prior scan; Profile and Target columns show '—' for CLI-launched scans"
    why_human: "React page rendering and data-binding can only be confirmed visually in a running browser session"
  - test: "Check exactly two rows in the /scans table and confirm the sticky 'Compare scans' bar appears at page bottom"
    expected: "Sticky bar appears with '2 scans selected' text and a 'Compare scans' button after two checkboxes are ticked"
    why_human: "FIFO checkbox selection state and sticky bar visibility depend on live React state changes"
  - test: "Check a third row and confirm the oldest-checked row is auto-unchecked (FIFO window of 2)"
    expected: "Only the two most recently checked rows remain checked after ticking a third"
    why_human: "Cannot verify checkbox FIFO drop visually from grep or test output alone"
  - test: "Click 'Clone' on a dashboard-launched scan row and confirm /scan/new pre-fills target, profile, and calibration"
    expected: "URL contains target=..., profile=..., calibration=... params; form fields are populated; no amber notice shown"
    why_human: "Pre-fill behavior requires a running dashboard with a real ScanJob-backed session in the DB"
  - test: "Click 'Clone' on a CLI-launched scan row (no ScanJob, profile is null) and confirm the amber 'Targets reconstructed' notice appears above the Targets field"
    expected: "Amber banner with 'Targets reconstructed from scan results' and 'Review the target list before submitting' copy is visible"
    why_human: "Requires a CLI-launched scan in the DB plus live browser rendering of the conditional JSX block"
  - test: "From /scans, select two scans and click 'Compare scans' — confirm landing on /compare with score-delta header card and 3 tabs (Findings, Subscores, Endpoints)"
    expected: "Header shows Scan A score, Scan B score, and a green/red delta badge with icon; tabs are selectable; Findings is the default tab"
    why_human: "Visual tab rendering, badge color, and delta icon direction must be confirmed in a browser"
  - test: "On the /compare page, click 'Subscores' tab and confirm all 6 pillar rows are always visible, including rows with delta = 0"
    expected: "All 6 rows (Hygiene, Modern TLS, Identity Trust, Agility, Data at Rest, Data in Motion) visible with Δ column; zero-delta rows show '±0'"
    why_human: "Row presence for zero-delta cases is a visual contract that cannot be proven from static analysis"
---

# Phase 66: Dashboard Scan History + Clone/Compare Verification Report

**Phase Goal:** Ship scan history list page, scan clone (pre-fill scan-new), and compare-two-scans page in the QUIRK dashboard, backed by enriched GET /api/scans and new GET /api/compare endpoints.
**Verified:** 2026-05-14
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A `/scans` route lists every scan with date, target, profile, overall score, finding counts by severity, and a Clone button that pre-fills `/scan/new` | ✓ VERIFIED | `ScanHistoryPage` exported from `scan-history.tsx`; uses `useScanList` which fetches `/api/scans`; table columns include Score, High/Med/Low badges; `handleClone` navigates to `/scan/new?target=...&profile=...&calibration=...`; route registered in `App.tsx` at `/scans` |
| 2 | Selecting two scans renders a diff view with score delta, per-pillar subscore deltas, added/removed findings, and changed endpoint posture | ✓ VERIFIED | `ComparePage` at `/compare` uses `useCompareData` to fetch `/api/compare`; renders score header card with delta badge, 3 tabs (Findings/Subscores/Endpoints); `PILLAR_LABELS` map covers all 6 pillars; `compare_scans()` route returns `CompareResponse` with `score_delta`, `subscore_deltas`, `added_findings`, `removed_findings`, `changed_endpoints`; all 9 pytest tests GREEN |
| 3 | GET /api/scans returns every session (no LIMIT 10) with enriched fields | ✓ VERIFIED | `list_scans()` rewritten — no `.limit(10)` call found; per-session score via `build_evidence_summary` + `compute_readiness_score`; finding counts via `_count_by_bucket`; ScanJob join for clone data with T-separator prefix match |
| 4 | Dashboard-launched scans recover target/profile/calibration from ScanJob; CLI-launched scans reconstruct target from hosts with profile=null | ✓ VERIFIED | `ScanJob.scan_run_id.like(f"{ts_prefix}%")` join present; fallback constructs `target` from sorted distinct `ep.host` values; `profile=None`, `calibration=None` set for CLI scans; `test_clone_data_recovery` and `test_clone_reconstruction` both pass |
| 5 | GET /api/compare returns CompareResponse with score_delta, 6 subscore deltas, added/removed findings, endpoint diff | ✓ VERIFIED | `compare_scans()` route at `/compare` present; returns `CompareResponse` typed with `SubscoreDelta` (all 6 pillars); composite-key `(host, protocol, severity)` diff for findings; host-set arithmetic for endpoint diff; `test_compare_schema` and `test_compare_endpoint_diff` pass |
| 6 | GET /api/compare?a=X&b=X returns HTTP 400 with detail "Cannot compare a scan to itself." | ✓ VERIFIED | Two occurrences of "Cannot compare a scan to itself" in scan.py (string literal + docstring); `test_compare_self` passes asserting 400 + exact detail string |
| 7 | Clone preload from URL params and amber reconstruction notice ship in scan-new.tsx | ✓ VERIFIED | `useSearchParams` added; lazy `useState` for `targets`, `profile`, `calibration` reads from URL params; `isReconstructed = searchParams.get("reconstructed") === "1"`; amber notice JSX with exact copy "Targets reconstructed from scan results" present |

**Score:** 7/7 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_dashboard_scan_history.py` | Wave 0 test scaffold (9 tests) | ✓ VERIFIED | 9 tests named exactly per VALIDATION.md; shared-cache SQLite fixture; all 9 pass GREEN |
| `quirk/dashboard/api/schemas.py` | Extended ScanSession + 5 compare types | ✓ VERIFIED | `ScanSession` has `score`, `profile`, `calibration`, `target`, `finding_counts`; `CompareResponse`, `CompareScanSummary`, `SubscoreDelta`, `CompareFinding`, `CompareEndpoint` present; `FindingCounts` not duplicated |
| `quirk/dashboard/api/routes/scan.py` | Enriched `list_scans()` + `compare_scans()` + `_fetch_session_endpoints_1s()` | ✓ VERIFIED | All 3 functions present; no `.limit(10)`; `compute_readiness_score` called 7 times; ScanJob import present |
| `src/dashboard/src/types/api.ts` | Extended ScanSession + 5 TS interfaces | ✓ VERIFIED | `CompareResponse`, `SubscoreDelta`, `CompareScanSummary`, `CompareFinding`, `CompareEndpoint` — all 1 occurrence each; `finding_counts` in ScanSession (2 occurrences) |
| `src/dashboard/src/hooks/useCompareData.ts` | HOOK-01..04 compliant fetch hook | ✓ VERIFIED | 1 `let cancelled = false`; 1 cleanup return; 9 `if (!cancelled)` guards; 0 `AbortController`; fetches `/api/compare` |
| `src/dashboard/src/pages/scan-history.tsx` | ScanHistoryPage with FIFO + Clone + sticky bar | ✓ VERIFIED | `export function ScanHistoryPage`; `useScanList`; FIFO slice logic present; sticky `fixed bottom-0` bar when 2 selected; Clone navigates to `/scan/new`; `reconstructed=1` set on null profile |
| `src/dashboard/src/pages/compare.tsx` | ComparePage with score header + 3 tabs | ✓ VERIFIED | `export function ComparePage`; `useCompareData` + `useSearchParams`; `defaultValue="findings"`; `Scan Comparison` heading; all 6 pillar labels; delta badge variants |
| `src/dashboard/src/pages/scan-new.tsx` | Clone preload + amber notice | ✓ VERIFIED | `useSearchParams` (2 occurrences); `reconstructed` (2); exact copy text present; all 3 param getters present |
| `src/dashboard/src/App.tsx` | /scans + /compare routes registered | ✓ VERIFIED | `ScanHistoryPage` import + route; `ComparePage` import + route; both paths declared |
| `src/dashboard/src/components/sidebar.tsx` | Scan History nav entry with History icon | ✓ VERIFIED | `"Scan History"` label; `History` icon from lucide-react; `"/scans"` path |
| `quirk/dashboard/static/index.html` | Built dashboard assets | ✓ VERIFIED | File exists (1029 bytes); `assets/` directory present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scan-history.tsx` | `/api/scans` | `useScanList` hook | ✓ WIRED | `useScanList` called in `scan-history.tsx`; hook fetches `fetchApi("/api/scans")` confirmed in `useScanList.ts` |
| `scan-history.tsx::handleClone` | `/scan/new?target=...&profile=...&calibration=...&reconstructed=1` | `navigate()` with URLSearchParams | ✓ WIRED | `navigate(\`/scan/new` pattern found; `reconstructed` param set when `s.profile === null` |
| `useCompareData.ts` | `/api/compare?a=...&b=...` | `fetchApi` with cancelled flag guard | ✓ WIRED | `api/compare` string found in hook; `encodeURIComponent` applied to both params |
| `scan-new.tsx` | Amber reconstruction notice | `searchParams.get('reconstructed') === '1'` | ✓ WIRED | `isReconstructed` flag drives conditional JSX render |
| `scan.py::list_scans` | `ScanJob.scan_run_id` | `startswith(ts_prefix)` LIKE join | ✓ WIRED | `ScanJob.scan_run_id.like(f"{ts_prefix}%")` at line 815; uses T-separator isoformat |
| `scan.py::compare_scans` | `compute_readiness_score` | `build_evidence_summary` + scoring pipeline | ✓ WIRED | Both imports present; `compute_readiness_score` called 7 times in scan.py |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `scan-history.tsx` | `sessions` from `useScanList` | `useScanList` → `fetchApi("/api/scans")` → `list_scans()` → DB query + scoring pipeline | Yes — DB query groups `CryptoEndpoint` rows; per-session score computed from evidence pipeline | ✓ FLOWING |
| `compare.tsx` | `data` from `useCompareData` | `useCompareData` → `fetchApi("/api/compare?a=...&b=...")` → `compare_scans()` → DB 1-second window queries | Yes — endpoint rows fetched from DB; scores computed via `compute_readiness_score`; finding/endpoint diffs from set operations | ✓ FLOWING |
| `scan-new.tsx` | `targets`, `profile`, `calibration` | `useSearchParams().get("target" / "profile" / "calibration")` from URL set by `handleClone` in scan-history | Yes — flows from real scan session data via ScanJob join or host reconstruction | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 9 Wave 0 tests pass GREEN | `python -m pytest tests/test_dashboard_scan_history.py -x -q` | `9 passed, 9 warnings in 0.51s` | ✓ PASS |
| Test scaffold collects 9 tests | `python -m pytest tests/test_dashboard_scan_history.py --collect-only -q` | `9 tests collected in 0.25s` | ✓ PASS |
| schemas.py compiles and imports correctly | `python -c "from quirk.dashboard.api.schemas import CompareResponse, ...; s = ScanSession(...); assert s.score == 0 ..."` | `schemas OK` | ✓ PASS |
| No LIMIT 10 in scan.py | `grep -v '^#' scan.py \| grep -c '.limit(10)'` | `0` | ✓ PASS |
| Build artifact present | `ls quirk/dashboard/static/index.html` | File exists (1029 bytes) | ✓ PASS |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| UI-HIST-01 | 66-01, 66-02, 66-03 | `/scans` route lists all scans with date, target, profile, overall score, and a Clone button pre-filling `/scan/new` | ✓ SATISFIED | `ScanHistoryPage` at `/scans` wired to `/api/scans`; Clone navigates with URL params; backend enrichment verified by 4 passing tests |
| UI-HIST-02 | 66-01, 66-02, 66-03 | Compare mode on `/scans` picks two scans and renders a diff view (score deltas, added/removed findings, changed endpoint posture) | ✓ SATISFIED | FIFO 2-scan selection + sticky bar in `scan-history.tsx`; `ComparePage` at `/compare` renders score delta, 3 tabs, all 6 subscore pillars; 5 passing compare tests |

**Note:** `REQUIREMENTS.md` still shows `[ ]` (unchecked) and `Pending` status for UI-HIST-01 and UI-HIST-02 at lines 94-95 and 240-241. The implementations are verified to be complete and working — this is a documentation tracking gap. The REQUIREMENTS.md status table was not updated as part of this phase.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `compare.tsx` (Subscores tab) | Scan A/B columns render `"—"` (intentional — backend CompareResponse only provides deltas, not raw per-scan subscore values) | Info | Acknowledged design decision per PLAN.md Task 4 NOTE; the `SubscoreDelta` is correctly displayed in the Δ column |
| `tests/test_dashboard_scan_history.py` | `datetime.utcnow()` deprecation warning (Python 3.12+) | Warning | 9 deprecation warnings emitted during test run; tests pass; non-blocking for functionality |

No blockers. No stub patterns in production code.

---

### Human Verification Required

The 7 automated checks above cover all backend API contracts, wiring, and data flow. The following behaviors are visual/interactive and require a human with the QUIRK dashboard running.

#### 1. Scan History Table Renders

**Test:** Navigate to `/scans` in the running dashboard.
**Expected:** Table shows all scan sessions with Date, Target, Profile, Score, High/Med/Low severity counts, and a Clone button per row. CLI-launched scans show `—` for Profile and Calibration.
**Why human:** React component rendering and real DB data are required.

#### 2. Sticky Compare Bar Appears with 2 Selections

**Test:** Check exactly two rows in the scan history table.
**Expected:** A sticky bar at page bottom appears reading "2 scans selected" with a "Compare scans" button.
**Why human:** React state-driven conditional rendering requires live interaction.

#### 3. FIFO Auto-Uncheck on 3rd Selection

**Test:** With 2 rows checked, check a third row.
**Expected:** The first-checked row becomes unchecked automatically; only the two most recently checked rows are selected.
**Why human:** FIFO drop behavior is React `useState` state — verifiable only in a live browser.

#### 4. Clone Preload (Dashboard-Launched Scan)

**Test:** Click Clone on a scan row that was launched from the dashboard (has ScanJob record).
**Expected:** `/scan/new` loads with `target`, `profile`, and `calibration` fields pre-filled from the source scan; no amber notice shown.
**Why human:** Requires a real ScanJob row in the DB and live form rendering.

#### 5. Clone Preload — CLI Scan Amber Notice

**Test:** Click Clone on a scan that was launched from the CLI (no profile in the row, shown as `—`).
**Expected:** `/scan/new` shows an amber banner reading "Targets reconstructed from scan results" and "Review the target list before submitting." above the Targets field; target field pre-filled with reconstructed host list.
**Why human:** Requires a CLI-sourced session with no ScanJob row and live conditional JSX rendering.

#### 6. /compare Page — Score Header + 3 Tabs

**Test:** Select two scans on `/scans` and click "Compare scans". Observe the `/compare` page.
**Expected:** Score header card shows Scan A score (left), Scan B score (right), and a centered delta badge with TrendingUp (green) for positive delta or TrendingDown (red) for regression. Three tabs are selectable; Findings is default.
**Why human:** Badge color, icon direction, and tab rendering are visual contracts.

#### 7. Subscores Tab — All 6 Rows Always Visible

**Test:** On `/compare`, click the "Subscores" tab.
**Expected:** Table shows exactly 6 rows — Hygiene, Modern TLS, Identity Trust, Agility, Data at Rest, Data in Motion — with a Δ column. Rows with zero delta show "±0" in muted color. Rows with positive delta show "+N" in green; negative show "−N" in red.
**Why human:** All-rows-always contract and Δ=0 rendering require live browser inspection.

---

### Gaps Summary

No automated gaps were found. All 7 must-have truths are VERIFIED, all 11 artifacts exist and are substantive, all 6 key links are wired, all 9 pytest tests pass, and no blocker anti-patterns are present.

The `human_needed` status reflects 7 visual/interactive behaviors that require a running dashboard session to confirm. These are expected for a UI-heavy phase.

**Documentation note:** `REQUIREMENTS.md` requirement status for UI-HIST-01 and UI-HIST-02 remains `Pending` and unchecked — these should be marked complete and `[x]` respectively as a post-phase housekeeping step. This does not block phase completion.

---

_Verified: 2026-05-14_
_Verifier: Claude (gsd-verifier)_
