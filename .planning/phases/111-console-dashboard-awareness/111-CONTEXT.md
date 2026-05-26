# Phase 111: Console Dashboard Awareness - Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase makes the distributed scanner **visible on the console dashboard**. A consultant can:
see a **sensor registry** (ID, segment, version, last-seen, status badge); **filter findings and
CBOM by segment**; and **immediately notice incomplete coverage** — per-segment score gauges
alongside the org-wide gauge, plus a `coverage_warning` banner when a merge ran with sensors
missing. It spans the FastAPI backend (a sensor-registry endpoint, a `?segment=` filter param,
exposing the merged-result / coverage data from `merge_runs`) and the React dashboard (a Sensors
page, a shared segment filter, per-segment gauges, and the coverage banner).

**Out of scope (downstream):** chaos-lab E2E validation (Phase 112). The merge engine and
`merge_runs` table already exist (Phase 110); this phase only READS them.

</domain>

<decisions>
## Implementation Decisions

### Sensor Registry (DASH-01)
- **Surface:** a new **top-level "Sensors" page/route** in the dashboard nav (not a sub-panel).
- **Backend:** a new **`GET /api/sensor/registry`** returning each enrolled sensor's
  `sensor_id`, `segment`, `sensor_version`, `last_push_at`, and a computed `status`.
- **Status badge:** **green** = within cadence; **stale** = overdue (`now > last_push_at + 2×cadence`);
  **unknown** = never pushed (`last_push_at` is None).
- **Reuse Phase 110 overdue logic** (the `_build_coverage_warning` / overdue computation in
  `quirk/merge/scan.py`) — share it, do not duplicate.

### Segment Filter (DASH-02)
- **Backend:** an optional **`?segment=<label>` query param** on `/api/scan/latest`,
  `/api/findings`, and `/api/cbom` (omitted = all segments).
- **Pydantic:** add **nullable `sensor_id`/`segment`** fields to the affected response models —
  backward-compatible (single-host scans have NULL segment and are unaffected).
- **Frontend:** a **shared segment dropdown** (populated from distinct segments) reused across the
  findings and CBOM views.
- **Default:** **"All segments"**; the filter must not break NULL-segment (local) scans.

### Merged-View Data Source (DASH-03 wiring)
- **New `GET /api/merge/latest`** reads the **latest `merge_runs` row** (org-wide `score`,
  `coverage_warning_json`, `merged_at`, `endpoint_count`, `sensor_count`). This honors the Phase 110
  cross-phase contract: the merged result is surfaced via `merge_runs`, **NOT** via `MAX(scanned_at)`.
- **coverage_warning banner:** shown on the dashboard when the latest `merge_runs.coverage_warning`
  is non-null (parse `coverage_warning_json`).
- **No merge yet (single-host only):** graceful — the dashboard shows the org-wide gauge only and no
  banner; `/api/merge/latest` returns an empty/`null` shape the frontend tolerates.

### Per-Segment Gauges & Component Reuse (DASH-03)
- **Reuse the existing `ScoreGauge` component** (`src/dashboard/src/components/gauges/ScoreGauge.tsx`)
  with the correct `maxValue` — one gauge per segment alongside the org-wide gauge.
- **Recharts mounting:** keep chart children **statically mounted** (toggle via fill/stroke opacity),
  never conditionally mount/unmount (project rule — Recharts static-children requirement).
- **Visual layout/arrangement is deferred to the UI-SPEC** design contract (generated next).

### Build & Verify (project rules)
- `.tsx` edits require **`npm run build` in `src/dashboard/`** before they're visible (FastAPI serves
  pre-built statics). Plans must include the build step.
- Render-parity tests assert field/column PRESENCE + content-model, NOT visual appearance; gate
  visual fidelity on the UI-SPEC + human UAT (generate a real artifact and open it).

### Claude's Discretion
- Exact `/api/sensor/registry` and `/api/merge/latest` response-model field names.
- The segment dropdown's empty/all representation; nav placement order of the Sensors page.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/dashboard/src/components/gauges/ScoreGauge.tsx` — the org-wide score gauge to reuse per-segment.
- `src/dashboard/src/lib/api.ts` + `src/dashboard/src/hooks/useScanData.ts` / `useScanList.ts` —
  the API client + data-fetch hook patterns to mirror for registry/merge/segment-filter calls.
- `src/dashboard/src/pages/*.tsx` (e.g. `data-at-rest.tsx`, `findings.tsx`, `cbom.tsx`) — page +
  skeleton + nav patterns; `data-at-rest.tsx` is the closest analog for adding a new top-level page.
- `quirk/dashboard/api/routes/scan.py` (`get_latest_scan` @ ~L958, `_derive_findings`, `_derive_cbom`)
  — where the `?segment=` filter and nullable fields attach.
- `quirk/dashboard/api/routes/sensor.py` (Phase 109) — the existing sensor router to add `/registry` to.
- `quirk/merge/scan.py` — `_build_coverage_warning` / overdue logic to reuse for registry status;
  `MergeRun` model (`quirk/models.py` ~L338) for `/api/merge/latest`.

### Established Patterns
- Routers registered/mounted in `quirk/dashboard/api/app.py`; response models in
  `quirk/dashboard/api/schemas.py`.
- The DAR tab (`data-at-rest.tsx`) is the reference for a previously-added dashboard page (DASH-05 pattern).

### Integration Points
- `/api/merge/latest` reads the Phase 110 `merge_runs` table; `/api/sensor/registry` reads the
  `sensors` table (Phase 107) + Phase 110 overdue logic.

</code_context>

<specifics>
## Specific Ideas

- The coverage_warning banner is the single most important "don't be misled" affordance — a merged
  score based on incomplete sensor coverage must be visually unmistakable (DASH-03).
- Segment filter and nullable fields must be strictly backward-compatible: existing single-host
  (NULL segment) scans render exactly as before.

</specifics>

<deferred>
## Deferred Ideas

- Chaos-lab E2E validation of the dashboard awareness flow (Phase 112).

## FLAGGED FOR RESEARCH/PLANNING

- **Per-segment score source.** The `MergeRun` table (Phase 110) persists only the **org-wide**
  `score` + `coverage_warning_json` — it does NOT store `per_segment_scores`. DASH-03's per-segment
  gauges therefore have no stored source. Resolve during research/planning:
  (a) **`/api/merge/latest` re-assembles the union and computes per-segment scores on read** (reusing
      `merge_scan`'s union-assembly + running `compute_readiness_score` per segment) — keeps Phase 110
      untouched, self-contained in 111, at the cost of recompute-on-read (acceptable for on-prem
      single-tenant volume). **← recommended default.**
  (b) Add an additive `per_segment_scores_json` column to `merge_runs` and have `merge_scan` populate
      it (compute-once, cheap reads, but reopens Phase 110's merge_scan).
  Pick (a) unless research shows the recompute cost is unacceptable; either way per-segment scoring
  MUST be Option A (each segment's findings re-scored through the engine, never an average).

</deferred>
