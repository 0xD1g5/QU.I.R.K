# Phase 202 — Deferred Items

Recorded at phase close (plan 202-08), carried forward honestly per 202-07-SUMMARY.md's Task 3
discharge notes. None of these were fixed in this phase; none block STORY-01/STORY-02.

## 1. Unidentified single frontend test failure (2026-09-12, plan 202-07)

One frontend test failed on the first post-a11y-defect-fix run during plan 202-07's Task 3. The
orchestrator's own log trimming (`tail -5`) discarded the failing test's name before it was read.

**Not reproduced** across 3 subsequent full-suite runs (exit 0 each) or 3 focus-suite runs (40
passed / 2 skipped each, per 202-07-SUMMARY.md). Recorded as unidentified and undiagnosed — not
resolved, not root-caused. If it recurs in a future phase, capture the full test name and output
before any log trimming.

## 2. `data-at-rest` a11y baseline's render-dependent count — third observation

`baseline-data-at-rest-default.json`'s `scrollable-region-focusable`-adjacent count has now been
observed at three different values across three sessions with zero code change to
`data-at-rest.tsx` or `components/ui/table.tsx`:

- 2026-08-27: 1
- 2026-09-02: 2
- 2026-09-12: 1 (this phase, plan 202-07's Task 3 re-run of `npm run a11y:baseline`)

The existing accepted-violation justification already documents this as inherently
render-dependent ("only fires on a container *actually overflowing* at render time"), not a fixed
structural constant. This third observation strengthens the case for replacing the exact-count pin
with a tolerance range in a future phase. Not fixed here — 202-07 restored the local value rather
than committing unrelated baseline churn (`git checkout` on the file after capture).

## 3. 202-03's `git stash --include-untracked` self-reported near-miss

During plan 202-03's execution, the executor ran `git stash --include-untracked`, which the
executor contract prohibits (see CLAUDE.md's destructive-git-operations guidance and this repo's
standing `git stash` prohibition). It was self-reported immediately, popped immediately, and no
work was lost — verified: no stash entries remain, working tree was clean, and `.planning/STATE.md`'s
md5 was unchanged throughout the phase. Recorded here per the standing lesson that a self-reported
near-miss is more useful than a silent one, not because any recovery action is still needed.

## 4. `docs/api-reference.md` deferral — new endpoint entry drafted, not created

Phase 202 adds a new API endpoint, `GET /api/findings/{id}/storyline`, which the Per-Phase
Documentation Checklist maps to `docs/api-reference.md`. That file does not exist in this repo yet.
Per plan 202-08's Task 1 instruction, it was **not** created as a one-endpoint stub. When
`docs/api-reference.md` is eventually created, its entry for this endpoint should read:

- **Method/path:** `GET /api/findings/{finding_id}/storyline`
- **Auth:** required (router-level `Depends(require_auth)`, same as every other dashboard route)
- **Path parameter:** `finding_id` (int) — `CryptoEndpoint.id`, NOT a unique finding identifier
  (see backlog todo on `FindingItem.id` non-uniqueness)
- **Query parameter:** `title` (str, required, `max_length=512`) — the dashboard's own finding
  title for this endpoint; the `(finding_id, title)` pair disambiguates which of an endpoint's
  2-4 findings is being requested (D-06)
- **Response fields (10, zero optional):** `narrative: str | null`, `quantum_impact: str | null`,
  `remediation_guidance: str | null`, `theme_slug: str | null`, `theme_title: str | null`,
  `theme_score_lift: number | null`, `theme_finding_count: number | null`,
  `theme_closed_count: number | null`, `finding_position: null` (always, per UI-SPEC A4 — never
  computed), and the finding's own `title`/`severity`/`host`/`port` echo fields
- **Error responses:** 404 (two distinct fixed details: unknown endpoint vs. unmatched title on a
  known endpoint), 422 (missing/oversized `title`, non-numeric `finding_id`), 500 (one fixed
  `"Storyline lookup failed"` detail, never leaking the underlying exception)
- **Source:** `quirk/dashboard/api/routes/storyline.py`, `quirk/dashboard/api/schemas.py`
  (`FindingStoryline`)
