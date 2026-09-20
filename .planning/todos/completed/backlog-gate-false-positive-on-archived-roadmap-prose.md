---
type: todo
created: 2026-09-13
source: Phase 205 close-out (orchestrator), while auditing main's CI baseline
priority: P2
requirement: null
resolves_phase: null
target: next milestone (v5.25) — filed at operator's request 2026-09-13
---

# `test_back_star_ci_enforced_leg` false-positives on `BACK-51` prose in an archived roadmap

**This is the last non-environmental red on `main`.** It has been carried as "pre-existing, small and
separate" across Phases 203/204/205 without ever being diagnosed. It is diagnosed now.

## What fails

```
FAILED tests/test_backlog_reconciliation_gate.py::test_back_star_ci_enforced_leg
  1 BACK-* ID(s) found neither closed-with-evidence nor listed in
  .planning/HORIZON.md's Open-Item Ledger:
    - BACK-51::Phases (source: .planning/milestones/v5.23-ROADMAP.md)
```

## Root cause — a false positive, NOT an unclosed item

`BACK-51` **is** properly closed, with full evidence, at `.planning/HORIZON.md:49`: resolved
2026-09-11 by Phase 201 plan 03 (LIFT-04), `categorize_waves()` deleted outright, standing regression
guard `tests/test_roadmap_categorization_unification.py` added.

The gate keys entries as `f"{back_id}::{title}"`
(`tests/test_backlog_reconciliation_gate.py:247,272`). The offending key `BACK-51::Phases` is that ID
found under a heading resolving to `Phases` in the **archived** `v5.23-ROADMAP.md` — a narrative prose
mention at line 167 ("…LIFT-01..LIFT-05 all Complete, BACK-51 closed by recorded decision"). HORIZON's
closure row carries a different title, so the `(ID, title)` pair never matches and the ID reads as
unclosed.

The title-keying is **deliberate**, not a bug: the module docstring records that it exists because
"`BACK-68` names two unrelated items across different eras." This is that trade-off biting.

## The fix that would be WRONG

Escaping `BACK-51` with U+2011, the way Phase 198 GATE-04 handled `BACK‑1`/`BACK‑900`/`BACK‑9999`.
That precedent was for **fake worked-example IDs**. `BACK-51` is a real requirement; hiding a real ID
from the gate defeats the gate's purpose. Do not reach for that precedent here.

Also wrong: adding `BACK-51` to HORIZON's Open-Item Ledger. It is closed, not open.

## Three real options (operator decision pending)

| Option | Effect | Cost |
|---|---|---|
| **(b) RECOMMENDED** — stop enumerating *narrative prose* in archived `milestones/*-ROADMAP.md`; structured rows only | Targets the actual cause; prevents recurrence at every future milestone archive | Narrower gate coverage over archives |
| (a) treat an ID whose HORIZON row says `CLOSED` as closed regardless of title | Fixes this and any recurrence broadly | Weakens the ID-reuse protection the keying was added for |
| (c) reword the one prose line in the archived file | One line, zero gate change | Guarantees a repeat at the next archive |

(b) is recommended because it matches the standing project lesson that **archived roadmaps are
historical records** — mining their prose for live obligations is what produces this. See the
memory note "Archived roadmaps silently swallow backlog items."

## Feasibility & Effort

- **Feasibility: CONFIRMED** — root cause is a known line range and a known keying decision; both
  read and reproduced 2026-09-13 (`pytest tests/test_backlog_reconciliation_gate.py::test_back_star_ci_enforced_leg`
  reproduces in 0.70s locally).
- **Effort: S** — one predicate change in the gate's source enumeration, plus a regression test
  proving a genuinely-unclosed `BACK-*` in a *live* (non-archived) source is still caught. That
  negative control is mandatory: narrowing a gate's enumeration to make it green is the exact
  anti-pattern Phase 204's COV-02 work was about.
- **Unknowns:** whether any *other* archived-file prose mention is currently masked by the same
  keying (enumerate before fixing — do not assume this is the only one).
- **Spike needed: no.**

## Why it is not urgent for the 2026-09-18 demo

It is a planning-bookkeeping gate misreading its own archive. It is not a product defect and does not
touch scanner behaviour. If asked, that is an accurate answer.

---

## RESOLVED 2026-09-20 — option (b′), a refinement of the recommended (b)

Fixed in `tests/test_backlog_reconciliation_gate.py`
(`_drop_archived_prose_duplicates` + `_is_archived_roadmap`). `main` is green on
`test_back_star_ci_enforced_leg` for the first time since Phase 203.

**Two corrections to the analysis above, both found by measuring rather than reasoning:**

1. **Option (b) as written — "structured rows only" — would have broken the gate.** No
   BACK-* ID in the entire tracked corpus has a real `| BACK-N | Title |` table row; all 27
   enumerated keys are bare mentions. A rows-only enumeration returns ZERO IDs while tracked
   files still contain the literal `BACK-`, which fails
   `test_non_vacuity_guard_over_tracked_sources` — the exact T-189-10 vacuous-pass shape the
   guard exists to catch. The implementable form is narrower: suppress bare mentions whose
   sources are *all* archived `milestones/*-ROADMAP.md`.

2. **Even narrowed, (b) silently dropped `BACK-86` from gate coverage entirely** — it is cited
   nowhere but `v5.23-ROADMAP.md` prose. That is the "archived roadmaps swallow backlog items"
   failure this repo has already been bitten by, reintroduced by the fix for a different one.

**(b′) adds a third clause: drop only for IDs ALSO cited outside an archived roadmap.**

| | keys | IDs covered | offenders | non-vacuity guard |
|---|---|---|---|---|
| before | 27 | 10 | 1 | ok |
| (b) literal | 0 | 0 | 0 | **fails** |
| (b) narrowed | 17 | 9 (**loses BACK-86**) | 0 | ok |
| **(b′) shipped** | 18 | **10** | 0 | ok |

**The stated unknown is resolved:** enumerating via the gate's own computation (never from the
pytest failure message, per the standing anti-pattern) showed `BACK-51` alone minting 8 keys and
`BACK-89` 6 — one per heading cited under. Only one happened to be an offender; the other 26
found matching evidence by luck, not design.

**Mutation-proven, not merely green.** Removing the `cited_elsewhere` clause reddens
`test_archived_roadmap_only_id_keeps_its_coverage`; removing the `table_row` clause reddens
`test_archived_roadmap_table_row_survives_narrowing`. The first draft of that second test was
itself vacuous — it stayed green under mutation because shape-2 suppression meant its fixture
ID could never have a second key — and was rewritten with two table rows until it bit. The
mandatory negative control
(`test_archived_prose_narrowing_still_catches_a_live_unclosed_id`) proves a genuinely-unclosed
ID in a live source still offends.

11 passed, 0 failed.
