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
