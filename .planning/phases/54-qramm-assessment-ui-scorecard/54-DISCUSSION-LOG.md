# Phase 54: QRAMM Assessment UI & Scorecard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-07
**Phase:** 54-qramm-assessment-ui-scorecard
**Areas discussed:** Session lifecycle, Auto-fill confirmation UX, Question layout, Scorecard access

---

## Session Lifecycle

**Question 1: Resume vs. always start fresh**

| Option | Description | Selected |
|--------|-------------|----------|
| Resume it | Auto-load most recent in-progress session; explicit "New Assessment" to start fresh | ✓ |
| Always start fresh | Each visit creates a new session; old sessions accumulate silently | |
| Ask first | Modal on load offering resume or start fresh | |

**User's choice:** Resume it (recommended option)
**Notes:** No additional notes.

---

**Question 2: Single vs. multiple sessions**

| Option | Description | Selected |
|--------|-------------|----------|
| Single active session | One session at a time; "New Assessment" archives old and creates fresh | ✓ |
| Multiple sessions | Session picker UI per client/engagement | |

**User's choice:** Single active session
**Notes:** User explicitly noted: "lets proceed with single, but add multiple sessions as a feature request for the future" — deferred to backlog.

---

## Auto-fill Confirmation UX

**Question 1: Click = confirm vs. explicit Confirm button**

| Option | Description | Selected |
|--------|-------------|----------|
| Click = confirm (silent) | Clicking any radio on an auto-filled question silently confirms it | |
| Explicit Confirm button | Two-step: select radio → click Confirm button to write answer_value | ✓ |
| You decide | Defer to Claude | |

**User's choice:** Explicit Confirm button
**Notes:** No additional notes.

---

**Question 2: Per-question vs. bulk confirm**

| Option | Description | Selected |
|--------|-------------|----------|
| Per-question only | Confirm button per question; encourages individual review | ✓ |
| Both: per-question + bulk | "Accept all CVI suggestions" button at top of CVI tab | |

**User's choice:** Per-question only (recommended option)
**Notes:** No additional notes.

---

## Question Layout

**Question 1: Grouped by practice area vs. flat list**

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped by practice area | 3 collapsible sections per tab, each showing [X/10] progress | ✓ |
| Flat scrolling list | Continuous list of 30 questions with no grouping | |

**User's choice:** Grouped by practice area (recommended option)
**Notes:** User selected the preview showing section headers with answer counts.

---

**Question 2: All expanded vs. first expanded only**

| Option | Description | Selected |
|--------|-------------|----------|
| All expanded | All 3 sections open on tab load | ✓ |
| First expanded, rest collapsed | Only first incomplete section open; others expand on click | |

**User's choice:** All expanded (recommended option)
**Notes:** No additional notes.

---

## Scorecard Access

**Question 1: 5th tab vs. separate route**

| Option | Description | Selected |
|--------|-------------|----------|
| 5th tab in assessment | CVI / SGRM / DPE / ITR / Scorecard tabs; Calculate Score inside Scorecard tab | ✓ |
| Separate route | Assessment at /qramm/assessment, Scorecard at /qramm/scorecard | |

**User's choice:** 5th tab in assessment (recommended option)
**Notes:** User selected the tab-layout preview.

---

**Question 2: Industry benchmark data source**

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded per industry sector | Static lookup: sector from Org Profile → benchmark scores per dimension | ✓ |
| Always show N/A | Skip benchmark column until real data exists | |
| Derive from Org Profile multiplier | Back-calculate from multiplier (not statistically meaningful) | |

**User's choice:** Hardcoded per industry sector (recommended option)
**Notes:** No additional notes.

---

## Claude's Discretion

None — all areas had clear user selections.

## Deferred Ideas

- **Multiple sessions per client/engagement** — user explicitly requested this be noted as a future feature. Phase 54 proceeds with single active session only.
