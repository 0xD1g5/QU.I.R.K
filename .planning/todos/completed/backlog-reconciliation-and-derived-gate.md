---
type: todo
created: 2026-09-05
source: phase-184.2 close-out review (BACK-33/BACK-39 check, then BACK-89 discovery)
priority: high
proposed_as: dedicated phase
resolves_phase: 189
---

# 57 BACK-* items are invisible to every currently-referenced planning doc

The backlog *reads* as drained because **zero** `BACK-*` items are marked
`- [ ]` anywhere. That is an artifact of how they are tracked, not evidence
that they are done: "closed" and "never tracked" both render as absence.

## Measured 2026-09-05

| | count |
|---|---|
| `BACK-*` IDs in archived roadmap backlog tables | **92** |
| Traceably closed (`[x]` line citing the ID in a REQUIREMENTS file) | 35 |
| Explicitly open (`[ ]`) | **0** |
| **Referenced in no REQUIREMENTS file at all** | **57** |
| Referenced in `.planning/HORIZON.md` | **3** (BACK-68, BACK-73, BACK-A11Y-01) |
| Directories under `.planning/backlog/` | 78 |

Derivation used (re-run it rather than trusting this list):
`BACK-*` IDs come from `^\| (BACK-[0-9A-Za-z-]+)` in
`.planning/milestones/*-ROADMAP.md`; closure comes from any `- [x]` line
citing the ID in `.planning/milestones/*-REQUIREMENTS.md` or
`.planning/REQUIREMENTS.md`.

**The 57 unreferenced IDs:** BACK-01 … BACK-26, BACK-34, BACK-35, BACK-42,
BACK-51, BACK-54, BACK-57, BACK-59, BACK-64, BACK-65, BACK-66, BACK-68,
BACK-69, BACK-70, BACK-71, BACK-72, BACK-73, BACK-74, BACK-75, BACK-76,
BACK-77, BACK-79, BACK-80, BACK-81, BACK-82, BACK-83, BACK-84, BACK-86,
BACK-88, BACK-89, BACK-90, BACK-91.

They are a **mix**, and cannot be triaged by ID alone:
- Spot-checked as long-shipped: BACK-10 (`quirk/connectors/gcp_connector.py`),
  BACK-12 (`email_scanner.py`), BACK-18 (`dnssec_scanner.py`).
- Spot-checked as genuinely open: **BACK-89** — see below.

## What proves this matters

**BACK-89** (`.planning/milestones/v5.0-ROADMAP.md:845`), "[P2 — UI] Executive
Summary score vs severity-bar consistency", filed 2026-05-21 from UAT-85-08.
Never cited in a REQUIREMENTS file, never in HORIZON.md, backlog dir
`999.82-executive-summary-score-vs-severity-consistency/` holds only an empty
`.gitkeep`. It was **re-discovered from scratch** on 2026-09-05 by Phase
184.2's chaos-lab run, ~3.5 months later.

Worse: its severity drifted while it was invisible. Filed P2 and explicitly
"not a security-correctness bug", it became a **P1 hard blocker** when Phase
98's fail-closed congruence guard landed — the same contradiction now emits
zero report artefacts. Nobody re-triaged it, because nothing pointed at it.
Tracked now at [[rating-band-critical-floor-halts-reports]].

## Proposed phase scope

1. **Classify all 57** against the live codebase as shipped / genuinely-open /
   obsolete. Record the evidence per item — a grep hit or a phase reference —
   not a bare verdict.
2. **Promote the genuinely-open ones to `HORIZON.md`** so they enter the normal
   PM-review flow at milestone boundaries.
3. **Add a derived gate.** Enumerate `BACK-*` IDs from the archived roadmaps at
   **run time** and fail when any ID is neither closed-with-evidence nor
   HORIZON-listed. Do not hand-write the ID list — this phase found three
   separate stale hand-written lists already (D-10's "three config files",
   `_COVERED_FILES`, a plan's own acceptance regex), and every one was caught
   by a derivation instead. See CLAUDE.md §GSD `state.*` Verb Integrity clause
   (e): "a written list of known sites is not a safeguard."

## Deliberately out of scope

Directory cleanup under `.planning/backlog/`. Dir presence currently carries
**no signal in either direction** — 999.27 and 999.35 persist for completed
work, 999.82 was an empty stub for never-started work. Deleting dirs destroys
the only on-disk ID→slug mapping, so it must not happen until closure evidence
is recorded elsewhere (step 1). Revisit only after the audit lands.

Related: [[project_archived_roadmap_loses_backlog_items]],
[[project_requirement_closed_one_surface_only]], [[feedback_pm_milestone_planning]].

---

## STATUS UPDATE — 2026-09-07 (post-v5.19 boundary)

Steps 1 and 2 EXECUTED at the milestone boundary (PM directive): all 92 IDs classified with
per-item evidence in `.planning/reports/backlog-reconciliation-2026-09-07.md`, and the open
residue promoted into `.planning/HORIZON.md`'s new canonical **Open-Item Ledger** section.
Corrections to this todo's own numbers: the "57 unreferenced" was an overcount by 20 — the
closure grep missed requirement-section-heading promotion (the dominant closure path). True
ledger-invisible count: 37, of which ~29 shipped/obsolete. **Step 3 (derived gate) remains
open** and is the remaining scope of this todo; the gate must key on title+ID (BACK-68 names
two unrelated items) and count heading citations as closure evidence.
