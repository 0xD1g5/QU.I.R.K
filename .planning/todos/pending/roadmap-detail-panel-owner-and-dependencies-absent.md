---
type: todo
created: 2026-09-21
source: phase-206 plan 08 (COV-04); filed at plan 206-08 close
priority: low
requirement: none (UAT-7-15 / UAT-7-16 partial-coverage input, not itself a requirement)
---

# `roadmap.tsx`'s node detail panel renders no owner and no dependency list — two UAT-7-16 bullets and one UAT-7-15 bullet are unmet

`docs/UAT-SERIES.md`'s UAT-7-16 ("Roadmap Page — Node Detail Panel") lists five Pass Criteria
bullets. Three are met by the product and are asserted by the new vitest node
(`src/dashboard/src/pages/__tests__/roadmap-node-detail-panel.test.tsx`): item title, timeframe,
and `Why:` evidence text. **Two are unmet:**

- "Owner placeholder shown"
- "Dependency list shown (if any)"

UAT-7-15 ("Roadmap Page — DAG Visualization") is hit by the same absence twice over, in its third
and fourth bullets:

- "Clicking a node shows detail panel with `Why:` text and owner placeholder" — the panel and the
  `Why:` text exist; the **owner placeholder** does not.
- "Dependencies shown as directed edges" — directed edges exist and carry arrowheads, but they are
  **phase-sequencing** edges, not per-item dependency edges (see below).

## Evidence (live source, 2026-09-21)

```
$ grep -rni "owner" src/dashboard/src/pages/roadmap.tsx src/dashboard/src/types/api.ts
(no matches)
$ grep -rni "depend" src/dashboard/src/pages/roadmap.tsx
(no matches)
```

- The detail panel (`roadmap.tsx:279-331`) renders exactly: the title, a phase/timeframe badge, an
  optional closure-state badge, an optional score-lift badge, and the optional `why` paragraph.
  There is no owner element and no dependency list.
- `RoadmapNode` (`src/dashboard/src/types/api.ts:126-141`) has no `owner` field and no
  `dependencies` field, so there is no data to render even if the panel wanted to.
- The API schema agrees: `quirk/dashboard/api/schemas.py` `RoadmapNode` carries
  `id/title/timeframe/why/phase/closure_state/slug/score_lift` and nothing else.

### The dependency-edge finding is separate and slightly worse

`roadmap.tsx` **ignores `data.roadmap.edges` entirely**. It synthesizes its own two edge families
in the `useEffect` at `roadmap.tsx:107-142`: invisible within-phase rank edges (`rankOnly: "true"`)
that force same-phase nodes into one column, and visible cross-phase edges (`rankOnly: "false"`)
connecting the last node of each horizon to every node in the next horizon. Those visible arrows
encode **NOW → NEXT → LATER sequencing**, not "item B depends on item A".

The backend does not model item dependencies either: `quirk/dashboard/api/routes/scan.py:1316-1321`
builds `RoadmapEdge(source=..., target=..., reason="Phase dependency")` for exactly the two
phase-to-phase transitions. So there is no dependency graph anywhere in the stack — frontend or
backend — for the panel or the DAG to show.

## Why this matters

An operator reading the roadmap DAG sees arrows and will reasonably read them as prerequisite
relationships between remediation items. They are not. Nothing in the UI distinguishes "do this
before that" from "these fall in different time horizons". The missing owner field is the lesser
issue (a placeholder is cosmetic until an ownership model exists), but the dependency-edge
mismatch is an honest-representation problem in a consulting deliverable.

## What a real fix would look like

1. **Owner:** decide whether ownership is real data (a new `owner` field on the API's `RoadmapNode`,
   sourced from config or a future assignment model) or a literal placeholder string. If it stays a
   placeholder, render it as one — plainly unset, never a fabricated name. Note this repo's standing
   convention against placeholder chips that read as claims (see the `closure_state` / `score_lift`
   null-handling comments in `roadmap.tsx`); an "Owner: —" line is acceptable, an invented owner is
   not.
2. **Dependencies:** either (a) model real item-to-item dependencies in
   `quirk/intelligence/remediation.py`, surface them through `RoadmapEdge.reason`, and have
   `roadmap.tsx` consume `data.roadmap.edges` instead of synthesizing edges; or (b) if no dependency
   model is wanted, relabel the visual so the arrows read as phase sequencing (legend text, edge
   label, or `aria-label` copy) and amend UAT-7-15's bullet rather than leaving the mismatch.

## Acceptance (for whoever picks this up)

- An owner element in the detail panel backed by a defined data source or an explicit unset
  placeholder.
- Either real dependency edges consumed from `data.roadmap.edges`, or an explicit relabel of the
  existing phase-sequencing arrows.
- vitest assertions extending `roadmap-node-detail-panel.test.tsx` (owner) and
  `roadmap-dag-visualization.test.tsx` (dependency edges).
- Once built, UAT-7-16 can move from partial-PASS to full PASS, and UAT-7-15's third and fourth
  bullets can drop out of the carve-out list in
  `.planning/phases/206-dashboard-ui-coverage-drain/red-proof/206-RED-PROOF-roadmap.md`.
