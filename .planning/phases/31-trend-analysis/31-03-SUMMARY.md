---
phase: 31-trend-analysis
plan: "03"
subsystem: dashboard-frontend
tags: [react, typescript, trends, frontend, shadcn]
dependency_graph:
  requires: ["31-02"]
  provides: ["TREND-04"]
  affects: ["src/dashboard/src/types/api.ts", "src/dashboard/src/hooks/useTrendsData.ts", "src/dashboard/src/pages/trends.tsx", "src/dashboard/src/App.tsx", "src/dashboard/src/components/sidebar.tsx"]
tech_stack:
  added: []
  patterns: ["React hook with cancelled-flag cleanup", "shadcn Card + Badge + Skeleton + Table", "native details/summary collapsible"]
key_files:
  created:
    - src/dashboard/src/hooks/useTrendsData.ts
    - src/dashboard/src/pages/trends.tsx
  modified:
    - src/dashboard/src/types/api.ts
    - src/dashboard/src/App.tsx
    - src/dashboard/src/components/sidebar.tsx
decisions:
  - "Used native <details>/<summary> instead of shadcn Collapsible — not installed per PATTERNS.md warning"
  - "All untrusted strings rendered as React text children — no raw-HTML injection props used"
  - "score_delta rendered as integer (no .toFixed()) to match Optional[int] Pydantic return type"
  - "useTrendsData uses empty [] deps array — trends endpoint takes no params unlike useScanData"
metrics:
  duration: "~30 minutes (Tasks 1-2)"
  completed: "2026-04-26"
  tasks_completed: 3
  files_created: 2
  files_modified: 3
---

# Phase 31 Plan 03: React Trends Dashboard Summary

React frontend wired to `GET /api/trends` with a `/trends` dashboard page showing scan-over-scan score delta, new/resolved findings counts, and collapsible top-5 sample tables.

## What Was Built

### Task 1: TypeScript types + useTrendsData hook (commit 3abb75d)

`src/dashboard/src/types/api.ts` was extended with two new interfaces mirroring the Plan 02 Pydantic schemas exactly (snake_case fields, `string | null` for datetimes, `number | null` for Optional[int]):

- `SampleFinding` — host, port, protocol, severity
- `TrendReport` — 17 fields covering session timestamps, scores, delta, new/resolved counts per severity, scan error deltas, and two sample arrays

`src/dashboard/src/hooks/useTrendsData.ts` created (49 lines) — mirrors the `useScanData` hook pattern with:
- Returns `{ data: TrendReport | null, loading: boolean, error: string | null }`
- `fetch("/api/trends")` on mount via `useEffect([], [])`
- `cancelled` flag in effect cleanup (no setState after unmount)
- Non-2xx HTTP status sets `error` string; `data` stays null

TypeScript compiled cleanly (`npx tsc --noEmit` zero errors after Task 1).

### Task 2: TrendsPage component + route + sidebar entry (commit 72a1faf)

`src/dashboard/src/pages/trends.tsx` created (162 lines) with four render states:

1. **Loading** — five `<Skeleton>` rows while fetch is in-flight
2. **Error** — single muted-foreground text line; no React error boundary trigger
3. **Baseline** — `previous_session_ts === null` shows centered "Baseline scan" headline with "Run another scan to see your progress over time."
4. **Full report** — header comparing `prev -> current` timestamps (via `toLocaleString()`), then:
   - Score Delta card with `ScoreDeltaBadge` (green positive / red negative / muted "No change" / outline "First scan")
   - New Findings card — HIGH / MEDIUM / LOW count badges
   - Resolved Findings card — HIGH / MEDIUM / LOW count badges
   - Scan errors delta row (muted text)
   - Two `<details>`/`<summary>` collapsible panels ("New Findings top 5" / "Resolved Findings top 5") with 4-column table (Host / Port / Protocol / Severity), Severity rendered via `SEVERITY_STYLES` Badge

`src/dashboard/src/App.tsx` — Route `path="/trends"` added after `/roadmap` route (line 34).

`src/dashboard/src/components/sidebar.tsx` — `TrendingUp` added to lucide-react import; `{ path: "/trends", label: "Trends", Icon: TrendingUp }` appended as last NAV_ITEMS entry.

TypeScript compiled cleanly (`npx tsc --noEmit` zero errors after Task 2).

XSS threat T-31-03-01 is mitigated: all untrusted strings (host, port, protocol, severity) are rendered as React text children — no raw-HTML injection props are used in trends.tsx.

### Task 3: Human-verify checkpoint (approved)

The human-verify checkpoint was reached and approved. Visual verification was deferred to UAT — the operator accepted the checkpoint as approved without running the live dashboard at this time. UAT-SERIES.md covers the rendering states.

## Deviations from Plan

None — plan executed exactly as written. Native `<details>`/`<summary>` used for sample table collapsibles as specified (shadcn Collapsible not installed per PATTERNS.md). All implementation decisions matched plan action blocks verbatim.

## Threat Surface Scan

No new security surface beyond what the plan's threat model covers. All four threats accounted for:

| Threat | Disposition | Status |
|--------|-------------|--------|
| T-31-03-01: XSS via host/port/protocol/severity rendering | mitigate | Mitigated — React text children only, no raw-HTML injection |
| T-31-03-02: Error message info disclosure | accept | Accepted — local-only dashboard |
| T-31-03-03: DoS via large sample tables | mitigate | Mitigated — backend caps at 5; frontend renders at most 5 rows |
| T-31-03-04: Spoofing via same-origin fetch | accept | Accepted — same-origin via Vite proxy |

## Known Stubs

None — all data flows through `useTrendsData` hook to the live `GET /api/trends` endpoint (implemented in Plan 02). No hardcoded empty values or placeholder text in the render path.

## Self-Check: PASSED

Prior agent created commits on branch `worktree-agent-a66baa58`:
- `3abb75d` feat(31-03): add TrendReport types and useTrendsData hook — FOUND
- `72a1faf` feat(31-03): add TrendsPage component, route, and sidebar entry — FOUND

Files verified from branch:
- `src/dashboard/src/types/api.ts` — TrendReport interface confirmed present
- `src/dashboard/src/hooks/useTrendsData.ts` — 49 lines, confirmed present
- `src/dashboard/src/pages/trends.tsx` — 162 lines, confirmed present
- `src/dashboard/src/App.tsx` — TrendsPage import + Route confirmed
- `src/dashboard/src/components/sidebar.tsx` — TrendingUp import + NAV_ITEMS entry confirmed
