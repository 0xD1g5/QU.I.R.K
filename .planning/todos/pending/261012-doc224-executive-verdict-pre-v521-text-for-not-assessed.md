---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger row DCL-REPORTINT-0179 (docs/report-interpretation.md section 19.5, honest-absence state)
priority: low
area: src/dashboard/src/components/ExecutiveVerdict.tsx
status: pending
resolves_phase: null
owner: "999.137"
---

# Executive Verdict says "(pre-v5.21 data)" for a scan that assessed no domain

`ExecutiveVerdict.tsx:60-66` maps `null`, `undefined`, `""`, `"NOT_ASSESSED"` and any unrecognised rating to the same
`unavailable` tone, and `ExecutiveVerdict.tsx:138` renders one fixed sentence for all of them:
"Verdict not available for this scan (pre-v5.21 data)." A current scan that assessed zero domains
(`compute_readiness_score()` returns `rating: "NOT_ASSESSED"`, `score: None`) therefore tells the reader its data
is from before v5.21, which is not the cause. `docs/report-interpretation.md` section 19.5 now documents the
discrepancy rather than hiding it.

- [ ] Give the `NOT_ASSESSED` case its own sentence (for example "Verdict not computed: no domain had assessable evidence."),
      reusing `NOT_COMPUTED_STATEMENT` from `quirk/reports/content_model.py` so the wording matches the other surfaces.
- [ ] Update `src/dashboard/src/components/__tests__/ExecutiveVerdict.test.tsx` (it currently pins the shared text) and
      the section 19.5 paragraph in `docs/report-interpretation.md`.

## Feasibility & Effort

**CONFIRMED** (the shared branch is visible at `ExecutiveVerdict.tsx:123-142`; the test at
`ExecutiveVerdict.test.tsx:110` pins `NOT_ASSESSED` to the honest-absence card). Effort **S**. Unknowns: none
material; the dashboard needs `npm run build` and lint after the edit. **Spike**: not needed.
