# Phase 56: PDF Export & Staleness Enforcement - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08
**Phase:** 56-pdf-export-staleness-enforcement
**Areas discussed:** Radar chart render strategy, QRAMM data fetch for print, No-session fallback, Compliance summary density

---

## Radar Chart Render Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Pure inline SVG polygon | Compute 4-axis radar polygon from dimension scores; static `<svg>` element in print.tsx; no recharts import; predictable at print resolution | ✓ |
| Recharts RadarChart import | Import recharts (already in package.json); reuse same component as dashboard scorecard; adds ~15KB import; risk of animation state on print capture | |

**User's choice:** Pure inline SVG polygon

---

| Option | Description | Selected |
|--------|-------------|----------|
| Session scores only | One polygon from 4 dimension scores; clean and unambiguous | ✓ |
| Session + benchmark overlay | Two polygons (session filled, benchmark dashed); mirrors scorecard tab's benchmark column; more complex SVG math | |

**User's choice:** Session scores only
**Notes:** Benchmark comparisons belong in the interactive dashboard.

---

## QRAMM Data Fetch for Print

| Option | Description | Selected |
|--------|-------------|----------|
| New useQRAMMPrintData() hook | Focused hook returning { scoreResult, complianceRows, loading, error }; mirrors useScanData() pattern; doesn't pollute the live assessment hook | ✓ |
| Extend useQRAMMSession.ts | Add score + compliance-map fetching to existing hook; risk: live QRAMM assessment pages would incur unnecessary fetches | |
| Inline fetch in print.tsx | Fetch directly inside PrintPage() with useEffect/useState; diverges from hook-per-data-source pattern | |

**User's choice:** New useQRAMMPrintData() hook

---

| Option | Description | Selected |
|--------|-------------|----------|
| Most recent scored session | GET /api/qramm/sessions → find most recent entry with score_json populated; most natural for post-assessment PDF export | ✓ |
| Most recent session regardless | Take latest session even if unscored; scorecard would show nulls | |

**User's choice:** Most recent scored session

---

## No-Session Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Show QRAMM section with placeholder | Always render section on new page; when no scored session exists, show "No QRAMM assessment completed" copy | ✓ |
| Omit QRAMM section entirely | PDF identical to pre-v4.7 output when no session; makes QRAMM feel optional | |

**User's choice:** Show QRAMM section with placeholder

---

## Compliance Summary Density

Initial question: framework-level summary only vs framework + top 3 practice areas.

User requested more context on the difference and end-user impact before deciding. Clarification provided:
- **Option A (framework-level only):** 8-row table, executives read it, fits one page, no practice jargon
- **Option B (framework + practice detail):** 3–4 pages, CISO/compliance officer reads it, actionable remediation anchors
- **Option C (both):** Summary table first, then full practice detail for deeper readers

| Option | Description | Selected |
|--------|-------------|----------|
| Executive / board — high-level signal | Framework-level summary only (8 rows) | |
| CISO / compliance officer — actionable detail | Framework + top 3 highest-relevance practice areas | |
| Both — summary first, then detail | 8-row summary table + per-framework practice breakdowns below | ✓ |

**User's choice:** Both — summary first, then detail

---

| Option | Description | Selected |
|--------|-------------|----------|
| Top 3 by relevance score | 3 highest-scoring practices per framework; ~2 pages for detail section | |
| Top 5 by relevance score | More coverage; ~3–4 pages | |
| All practice areas per framework | Complete practice-level coverage; comprehensive but heavy | ✓ |

**User's choice:** All practice areas per framework

---

| Option | Description | Selected |
|--------|-------------|----------|
| Flow continuously | All framework sections flow after summary table; no forced page breaks between frameworks | ✓ |
| Each framework on its own page | Force page break before each framework's detail; easier to navigate when presenting | |

**User's choice:** Flow continuously

---

## Claude's Discretion

None — all areas had explicit user decisions.

## Deferred Ideas

- **Industry benchmark overlay in radar** — User chose session-only polygon; benchmark overlay deferred to a future phase.
- **`/print?session=<id>` URL parameter** — Allow printing a specific session; not needed in v4.7.
- **Staleness enforcement** — Already shipped in Phase 55; confirmed out of scope for Phase 56.
