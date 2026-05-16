# Phase 55: QRAMM Compliance Mapping View - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 55-qramm-compliance-mapping-view
**Areas discussed:** Relevance score formula, Framework data home, Coverage ceiling mechanism

---

## Relevance Score Formula

### Q1: How should per-practice relevance scores be derived?

| Option | Description | Selected |
|--------|-------------|----------|
| Static weights × session scores | Pre-defined 0–1 weight per practice→framework pair × session dimension score | ✓ |
| Static tier only (High/Medium/Low) | Hard-code H/M/L tiers; same table for every consultant regardless of scores | |
| Session score ÷ dimension max | Normalize dimension score directly; all practices in a dimension get same score | |

**User's choice:** Static weights × session scores  
**Notes:** Recommended option; user confirmed without modification.

---

### Q2: Where do the weights live and at what scale?

| Option | Description | Selected |
|--------|-------------|----------|
| 0.0–1.0 float per pair, Python dict | `quirk/qramm/compliance_map.py` — server-side, exposed via new API endpoint | ✓ |
| 0.0–1.0 float per pair, TypeScript constants | TS file in frontend; no API endpoint needed | |
| Integer tier (1/2/3), Python dict | Same server-side approach but integer tiers | |

**User's choice:** 0.0–1.0 float per pair, Python dict  
**Notes:** Recommended option; keeps framework data server-side alongside the rest of the qramm module.

---

### Q3: What to show when no active session exists?

| Option | Description | Selected |
|--------|-------------|----------|
| Static weights only, no session scores | Show full table with `relevance_score: null`; banner explains scores come after assessment | ✓ |
| Empty state / lock gate | Hide table entirely until session exists | |
| Redirect to /qramm | Auto-redirect to Org Profile wizard | |

**User's choice:** Static weights only, no session scores  
**Notes:** Recommended option; table is useful reference even without a session.

---

## Framework Data Home

### Q1: How should the frontend get both weights AND session scores?

| Option | Description | Selected |
|--------|-------------|----------|
| One endpoint, server merges both | `GET /api/qramm/sessions/{id}/compliance-map` returns pre-computed scores | ✓ |
| Two calls, frontend merges | Separate weights endpoint + score endpoint; frontend multiplies | |
| Static weights in TS, session scores from API | Frontend bakes weights; only score endpoint called | |

**User's choice:** One endpoint, server merges both  
**Notes:** Recommended option; mirrors `/api/qramm/sessions/{id}/score` pattern from Phase 51.

---

### Q2: Endpoint behavior when session has no scores yet?

| Option | Description | Selected |
|--------|-------------|----------|
| Static weights only, scores null | HTTP 200 with `relevance_score: null` per entry | ✓ |
| Refuse with 404 / 409 | Error response until scores calculated | |
| Compute on the fly from raw answers | Inline score computation regardless of explicit Calculate Score | |

**User's choice:** Static weights only, scores null  
**Notes:** Recommended option; keeps frontend render path simple (one path handles both states).

---

## Coverage Ceiling Mechanism

### Q1: How should the scanner coverage ceiling be defined?

| Option | Description | Selected |
|--------|-------------|----------|
| Per-dimension ceiling: only CVI scanner-informed | `SCANNER_COVERAGE = {"CVI": 1.0, "SGRM": 0.0, "DPE": 0.0, "ITR": 0.0}` | ✓ |
| Global hard-coded ceiling constant | Single constant (e.g., 0.25 = 30/120) applied uniformly | |
| You decide | Let planner derive ceiling approach from evidence bridge coverage | |

**User's choice:** Per-dimension ceiling: only CVI is scanner-informed  
**Notes:** Recommended option; accurately reflects that evidence bridge only populates CVI in v4.7.

---

### Q2: Where should the ceiling constant live?

| Option | Description | Selected |
|--------|-------------|----------|
| In quirk/qramm/compliance_map.py alongside weights | `SCANNER_COVERAGE` dict in same module as `QRAMM_COMPLIANCE_WEIGHTS` | ✓ |
| Hard-coded in API endpoint handler | Ceiling inlined in route handler logic | |
| Frontend constant only | Frontend caps displayed values; Python returns raw | |

**User's choice:** In quirk/qramm/compliance_map.py alongside weights  
**Notes:** Single source of truth; when v4.8 extends evidence bridge to SGRM/DPE/ITR, only this dict updates.

---

### Q3: How should the view signal the ceiling?

| Option | Description | Selected |
|--------|-------------|----------|
| Coverage tier badge + footnote | "Scanner-informed" / "Manual only" badges + footnote text; no % shown | ✓ |
| Capped % with disclaimer | Show capped percentage with tooltip/disclaimer | |
| No coverage % at all | Omit all coverage signals; nulls imply scanner blindness | |

**User's choice:** Coverage tier badge + footnote  
**Notes:** Recommended option; avoids the false-precision problem of percentages entirely.

---

## Claude's Discretion

- **View placement:** 6th tab (`[ Compliance Map ]`) within the existing `/qramm/assessment` page. No new route or sidebar entry. Chosen over a separate `/qramm/compliance` route to keep all QRAMM workflow under one URL and avoid sidebar clutter. User skipped this gray area; Claude made the call.

## Deferred Ideas

- Evidence bridge expansion to SGRM/DPE/ITR (QRAMM-F01 — v4.8); `SCANNER_COVERAGE` dict is pre-structured for this
- Coverage percentage display (future phase, once coverage model is more mature)
- `quirk qramm status --format json` (future enhancement; exit code is sufficient machine-readable signal in v4.7)
