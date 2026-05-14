# Phase 66: Dashboard Scan History + Clone/Compare - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 66 gives operators a dedicated `/scans` history page where every scan QUIRK has ever produced is listed, any prior scan can be re-launched with one click ("Clone configuration"), and any two scans can be compared side-by-side to see exactly what changed. Three concrete deliverables:

1. **`/scans` history page** — full scan list with date, target, profile, score, and finding counts by severity; checkboxes for compare selection; "Clone" button per row.
2. **Clone configuration** — pre-fills `/scan/new` with the source scan's target, profile, and calibration; for CLI-launched scans (no `scan_jobs` row), target is reconstructed from `CryptoEndpoint.host` with an amber notice.
3. **`/compare` diff page** — score delta header + tabbed diff view (Findings added/removed, Subscores all-6-pillars, Endpoints with posture changes and disjoint-target sections); backed by a new `GET /api/compare?a=X&b=Y` backend endpoint.

**In scope:** Extend `/api/scans` (enrich ScanSession, remove LIMIT 10), new `GET /api/compare` endpoint, `/scans` React page, `/compare` React page, checkbox selection UX, clone pre-fill logic, reconstructed-target notice.

**Out of scope:** Scan deletion (future UX phase), per-scan permalink sharing beyond compare URL, bulk export of multiple scans, pagination UI (scrollable table is sufficient), multi-user scan ownership.

</domain>

<decisions>
## Implementation Decisions

### D-01: History API — Extend /api/scans

Extend the existing `/api/scans` endpoint rather than adding a new one. Changes:
- Remove `LIMIT 10` — return **all sessions**, no cap.
- Add to `ScanSession` schema: `score` (int), `profile` (str | null), `calibration` (str | null), `target` (str | null), `finding_counts` (FindingCounts: {high, medium, low}).
- `ScanSelector` in the sidebar already calls `/api/scans` — it gets the richer data for free, with no UI change required (it only reads `scan_id`, `scanned_at`, `total_endpoints`).

### D-02: Per-Session Score — Inline Computation

Compute `score` inline per session in the backend handler using the same pattern as Phase 64's `GET /api/trends/timeline`:
1. `_fetch_session_endpoints(db, ts)` (existing helper in `quirk/intelligence/trends.py`)
2. `build_evidence_summary(endpoints)` → `compute_readiness_score(evidence)` → extract `score`

No schema change. ~30ms per session; acceptable for a consulting dashboard with < 100 scans.

### D-03: Finding Counts — Reuse Trends Severity Bucketing

Finding counts per session use the existing `_bucket_for_severity()` / `_count_by_bucket()` helpers from `quirk/intelligence/trends.py`:
- `CRITICAL + HIGH` → `"high"`
- `MEDIUM` → `"medium"`
- `LOW` → `"low"`
- `INFO` → excluded

Consistent with `/api/trends/timeline` bucketing established in Phase 64.

### D-04: Clone Configuration — Always Available, Reconstruct for CLI Scans

The "Clone configuration" button appears on every row. Data source priority:
1. **Dashboard-launched scan** (has matching `scan_jobs` row via `scan_run_id`): use `scan_jobs.target`, `scan_jobs.profile`, `scan_jobs.calibration` directly.
2. **CLI-launched scan** (no `scan_jobs` row): derive target by joining `DISTINCT CryptoEndpoint.host` for that session (comma-separated); default `profile = "standard"`, `calibration = "balanced"`.

On navigating to `/scan/new` with a reconstructed target, show an amber info notice above the Targets field:
> "Targets reconstructed from scan results — review before submitting."

The field is fully editable; the notice informs the operator to validate the reconstructed host list.

### D-05: Compare Selection — Checkboxes + Sticky Compare Button

On the `/scans` table, each row has a checkbox. UX rules:
- Selecting exactly 2 rows enables a sticky "Compare" button (top of table, or floating action bar).
- Attempting to check a 3rd row automatically unchecks the oldest checked row (radio-like window of 2).
- The "Compare" button is disabled when 0 or 1 rows are selected.

### D-06: Compare Navigation — Dedicated /compare Route

Clicking "Compare" navigates to `/compare?a=<scan_id>&b=<scan_id>` — a new React Router route. The URL is bookmarkable and shareable. The operator uses browser back to return to `/scans`.

### D-07: Compare Backend — New /api/compare Endpoint

New `GET /api/compare?a=<scan_id>&b=<scan_id>` endpoint in the scan router. The backend computes the full diff and returns a structured `CompareResponse`. Keeping diff logic in Python ensures it is unit-testable and consistent between runs.

`CompareResponse` fields:
- `scan_a`: `{scan_id, scanned_at, score}` summary for scan A
- `scan_b`: `{scan_id, scanned_at, score}` summary for scan B
- `score_delta`: `int` (scan_a.score − scan_b.score)
- `subscore_deltas`: `{hygiene, modern_tls, identity_trust, agility_signals, data_at_rest, data_in_motion}` — all 6 keys, each an int delta (can be 0)
- `added_findings`: list of findings present in scan A but not scan B (with severity, host, description)
- `removed_findings`: list of findings present in scan B but not scan A
- `endpoints_only_in_a`: list of hosts that appear in scan A but not scan B
- `endpoints_only_in_b`: list of hosts that appear in scan B but not scan A
- `changed_endpoints`: list of hosts in both scans where cipher list, cert, or protocol posture changed

Finding identity for added/removed: a finding is identified by `(host, algorithm_or_protocol, finding_type)` — same combination in both sessions = not added/removed, even if finding text differs slightly.

### D-08: Diff View Layout — Score Header + Tabbed Sections

The `/compare` page layout:
- **Top header card**: "Scan A: [date] — Score A" and "Scan B: [date] — Score B" side by side, with Δ score and up/down arrow between them (green for positive delta, red for negative).
- **Tabs** (3):
  1. **Findings** — "Added ({N})" section (severity badge + host + description per row) and "Removed ({N})" section.
  2. **Subscores** — Table showing all 6 pillar deltas always (even if Δ = 0). Columns: Pillar | Score A | Score B | Δ. Pillar names use UI-friendly aliases (Hygiene, Modern TLS, Identity Trust, Agility, Data at Rest, Data in Motion).
  3. **Endpoints** — Three sections: "Changed ({N})" (hosts with posture diff), "Only in A ({N})", "Only in B ({N})". Disjoint hosts flagged as "not present in other scan".

### Claude's Discretion

- **Tab default**: Open on the Findings tab by default (most actionable for a consultant reviewing a regression).
- **Empty state for each tab**: Show a friendly "No added findings" / "No removed findings" / "No changed endpoints" message rather than hiding the tab.
- **Score delta color**: Green if scan A > scan B (improvement relative to baseline B), red if scan A < scan B.
- **`/api/compare` auth**: Read-only endpoint — `require_auth` only (no CSRF needed), same pattern as `GET /api/jobs/{id}` from Phase 65.
- **`/api/compare` 400 handling**: Return HTTP 400 if `a == b` (comparing a scan to itself) with message "Cannot compare a scan to itself."
- **`ScanSession.profile` and `.calibration` for CLI scans**: Set to `null` in the API response; the `/scans` UI renders null as "—".

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements
- `.planning/REQUIREMENTS.md` §UI-HIST-01, §UI-HIST-02 — exact acceptance criteria
- `.planning/ROADMAP.md` §Phase 66 — goal statement, success criteria, UI hint

### Existing Scan History API
- `quirk/dashboard/api/routes/scan.py` — `list_scans()` at `GET /api/scans` (extend this); `get_latest_scan()` pattern for session window query (the `scanned_at >= ts && < ts + 1s` window); `_cert_expiry_key()` as an example of session-local computation
- `quirk/dashboard/api/schemas.py` — `ScanSession` (extend with score, profile, calibration, target, finding_counts); `ScanLatestResponse` (reference for what a full session contains); `FindingCounts` (check if this model already exists or needs to be added)

### Phase 64 Score Computation Pattern (PRIMARY for D-02)
- `.planning/phases/64-trend-analysis-foundation/64-CONTEXT.md` §D-04 — inline per-session score computation; `build_evidence_summary()` → `compute_readiness_score()` pattern; same ~30ms/session budget applies here
- `quirk/intelligence/trends.py` — `_fetch_session_endpoints()`, `_bucket_for_severity()`, `_count_by_bucket()` — all reused for D-02 and D-03
- `quirk/intelligence/scoring.py` — `compute_readiness_score()` return shape: `{score, subscores: {hygiene, modern_tls, identity_trust, agility_signals, data_at_rest, data_in_motion}}`
- `quirk/intelligence/evidence.py` — `build_evidence_summary()` (input to scoring)
- `quirk/dashboard/api/routes/trends.py` — existing `_list_session_timestamps()` session enumeration pattern (reference for how sessions are grouped)

### Phase 65 scan_jobs Table (PRIMARY for D-04 clone data source)
- `.planning/phases/65-dashboard-initiated-scan/65-CONTEXT.md` §D-02 — `scan_jobs` table schema; `scan_run_id` column links a job to its `CryptoEndpoint` session
- `quirk/models.py` — `ScanJob` model; join `scan_jobs` on `scan_run_id = scan_id` (the ISO timestamp) to recover `target`, `profile`, `calibration` for dashboard-launched scans

### Phase 65 Auth Pattern (for /api/compare)
- `.planning/phases/65-dashboard-initiated-scan/65-CONTEXT.md` §D-10 — read-only routes require only `require_auth` (no CSRF); same applies to `GET /api/compare`
- `quirk/dashboard/api/middleware/auth.py` — `require_auth` dependency

### Phase 62 Hook Cancellation Pattern (for new hooks)
- `.planning/phases/62-react-hook-cancellation-pattern/62-CONTEXT.md` — HOOK-01..04 patterns; any new hooks (`useScanHistory`, `useCompareData`) MUST follow `let cancelled = false` + `return () => { cancelled = true }`

### Frontend Patterns
- `src/dashboard/src/hooks/useScanList.ts` — existing hook calling `/api/scans`; Phase 66 extends the response shape but the hook remains the canonical data source for scan list
- `src/dashboard/src/components/ScanSelector.tsx` — reads `scan_id`, `scanned_at`, `total_endpoints` from sessions; new fields in `ScanSession` are additive and do not break this component
- `src/dashboard/src/hooks/useSelectedScan.ts` + `src/dashboard/src/components/ui/` — shadcn/ui primitives (Checkbox, Badge, Tabs, Button) available for the /scans table and /compare view
- `src/dashboard/src/types/api.ts` — `ScanSession` TypeScript interface (extend with new fields); add `CompareResponse`, `CompareFinding`, `CompareEndpoint` interfaces
- `src/dashboard/src/App.tsx` — register `/scans` and `/compare` routes here; add "Scan History" nav link in sidebar

### Feedback Constraints (MANDATORY)
- Recharts static children: never conditionally mount/unmount chart components — use opacity (not relevant to Phase 66's tables, but noted for any chart additions)
- Dashboard build step: after `.tsx` edits, run `npm run build` in `src/dashboard/` before testing

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `quirk/intelligence/trends.py::_fetch_session_endpoints()` — fetch all `CryptoEndpoint` rows for a given ISO timestamp session; reuse as-is for per-session score and finding count computation
- `quirk/intelligence/trends.py::_bucket_for_severity()` + `_count_by_bucket()` — reuse for finding severity bucketing in enriched `ScanSession`
- `src/dashboard/src/hooks/useScanList.ts` — existing `/api/scans` hook; response shape extends but hook shape need not change (new fields are additive)
- `src/dashboard/src/components/PageSpinner.tsx` — reuse for loading state on `/scans` and `/compare`
- `src/dashboard/src/components/ui/chart.tsx` — ChartContainer if any chart is needed (Subscores tab could show a mini bar comparison; leave to Claude's discretion)
- `src/dashboard/src/hooks/useTimelineData.ts` (Phase 64) — nearest analog for a new `useCompareData` hook (fetch + cancellation pattern)

### Established Patterns
- **Session window query**: `CryptoEndpoint.scanned_at >= ts && < ts + timedelta(seconds=1)` — the authoritative pattern for isolating one scan session in all existing routes
- **ScanSession schema extension**: additive fields with `Optional` / `None` defaults to avoid breaking `ScanSelector` which reads only 3 existing fields
- **Auth on read-only routes**: `GET` routes require only `require_auth`, not `require_csrf` — consistent since Phase 58
- **React Router**: `/scan/new` and `/scan/job/:jobId` added in Phase 65 — add `/scans` and `/compare` following the same route registration pattern in `App.tsx`
- **Sidebar nav**: Phase 65 added "New Scan" as a primary CTA button at the top of the sidebar — "Scan History" should be added as a standard nav link (same style as Executive/Findings/etc.)

### Integration Points
- `quirk/dashboard/api/routes/scan.py` — extend `list_scans()` and add `compare_scans()` route to the existing `router`; no new router file needed
- `quirk/dashboard/api/schemas.py` — extend `ScanSession`; add `CompareResponse`, `CompareFinding`, `CompareEndpoint`, `SubscoreDelta`; add `FindingCounts` if it doesn't already exist
- `quirk/models.py` — join `ScanJob.scan_run_id` to session `scan_id` for clone data recovery
- `src/dashboard/src/App.tsx` — register `/scans` → `<ScanHistoryPage />` and `/compare` → `<ComparePage />`
- `src/dashboard/src/components/sidebar.tsx` — add "Scan History" nav link, pointing to `/scans`

</code_context>

<specifics>
## Specific Ideas

- The `/compare` URL carries both scan IDs as query params (`?a=...&b=...`) making it bookmarkable — a consultant can share a specific comparison with a client.
- When `/api/compare` receives `a == b`, return HTTP 400 with `{"detail": "Cannot compare a scan to itself."}` — prevents a degenerate all-zero diff that would confuse operators.
- The amber reconstruction notice on `/scan/new` (when cloning a CLI scan) should only appear when `scan_jobs` lookup returned no match — not for all clones. Dashboard-launched clones show no notice (the data is exact).
- Finding identity for added/removed detection: use `(host, algorithm_or_protocol, finding_type)` as the composite key — not `finding_id` (those are ephemeral per-scan). This prevents false "added + removed" when the same issue persists across scans with a slightly different message.
- Subscore pillar display names in the Subscores tab: `hygiene` → "Hygiene", `modern_tls` → "Modern TLS", `identity_trust` → "Identity Trust", `agility_signals` → "Agility", `data_at_rest` → "Data at Rest", `data_in_motion` → "Data in Motion" — same aliases used in the existing dashboard trend view.

</specifics>

<deferred>
## Deferred Ideas

- **Pagination UI** — if scan count grows beyond 100, a paginated table would help; deferred as scrollable table is sufficient for consulting engagements
- **Scan deletion** — removing old scans from history; belongs in a future UX polish phase
- **Bulk export** — downloading results for multiple scans at once; separate phase
- **Per-scan permalink page** — viewing a single historical scan via URL (currently only the ScanSelector dropdown navigates to past scans); would complement Phase 66's compare URL scheme

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 66-dashboard-scan-history-clone-compare*
*Context gathered: 2026-05-13*
