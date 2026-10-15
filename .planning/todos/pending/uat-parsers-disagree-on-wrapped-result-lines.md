---
type: todo
created: 2026-09-13
source: phase-204 close-out (orchestrator), reproduced live while backfilling Series 203
priority: medium
requirement: COV-02 (adjacent — the gate's independence is correct; this is about the divergence it permits)
resolves_phase: null
---

# The two UAT corpus parsers disagree on a hard-wrapped `**Result:**` line

## Reproduced live, 2026-09-13

While backfilling Series 203, the orchestrator wrote `UAT-203-05`'s `**Result:**` annotation
hard-wrapped across six lines — the `- [x] SKIP (GAP — ...` checkbox on the first line, the
parenthetical reason continuing onto the next five. The two parsers that read this corpus
disagreed about it:

| Parser | Verdict on the wrapped case |
|---|---|
| `scripts/uat_corpus.py::iter_cases` | **`UNDISPOSITIONED`** — reported in `reconcile()`'s disposition counts |
| `tests/test_uat_zero_undispositioned_gate.py` (independent re-derived grammar) | **fine** — gate passed 9/9 |

So the standing corpus-integrity gate passed a case that the phase's own parser classified as
having no disposition at all. Reformatting the annotation onto a single line (the house convention
every other case follows) resolved it — `UNDISPOSITIONED` went to 0 and the drain total moved from
76 to 77 as `UAT-203-05` was correctly recognised as a GAP.

## Why this matters, and why it is NOT an argument for sharing a parser

`tests/test_uat_worklist_reconciliation_gate.py` and `tests/test_uat_zero_undispositioned_gate.py`
deliberately re-derive their grammar locally and import nothing from `scripts/`. That independence
is correct and must be preserved — it is the entire reason the COV-02 gate is worth having. A gate
reading the corpus through the generator's parser would let a parser bug hide the same cases from
both, and both would be green while both were wrong. Phase 204's plan `204-04-PLAN.md` states this
as a hard `<independence_rule>`.

The cost of that independence is exactly what showed up here: the witnesses can disagree, and
nothing currently notices when they do. In this instance the divergence was benign — the stricter
parser was right, the house convention is single-line, and the fix was to conform. But the same
divergence pointed the other way is a real hazard:

- A case whose disposition `uat_corpus` can read but the zero-undispositioned gate cannot would
  make the standing gate fail on a correctly-dispositioned case (noisy, self-correcting).
- A case whose disposition the gate accepts but `uat_corpus` reads as `UNDISPOSITIONED` — **the
  case observed here** — silently drops out of the drain total. The corpus looks 100%
  dispositioned, and a real GAP is invisible to the worklist. That is the failure mode COV-01 and
  COV-02 exist to prevent, arriving through the gap between the two parsers rather than through
  either one.

## Suggested fix (S–M)

Add a **cross-parser agreement test** — a third test that runs both grammars over the live corpus
and asserts they classify every case identically, failing with the specific case IDs where they
diverge. This preserves independence (neither parser imports the other; the new test imports both
purely to compare) while making divergence loud instead of silent.

That is the shape that fits this project's precedent: not "make them share code", but "make the
disagreement detectable." `reconcile()`'s own `arithmetic_ok` self-check is the same idea applied
to counts rather than parsers.

A cheaper partial mitigation, worth doing regardless: have `uat_corpus.reconcile()` fail loudly, or
at least surface a named warning, when `UNDISPOSITIONED > 0`. Today it reports the count in a dict
that a human has to notice — the orchestrator only caught this because they read the raw
`reconcile` output rather than trusting the green gate.

## Do NOT

- Do NOT resolve this by making either gate import `scripts/uat_corpus.py`. That trades a detectable
  divergence for an undetectable shared blind spot, and it would undo `204-04-PLAN.md`'s
  `<independence_rule>` and the 204-04b corrective work that hardened it.
- Do NOT "fix" it by loosening `uat_corpus`'s Result-line parsing to accept wrapped annotations
  without first deciding whether wrapped annotations are legal at all. The corpus convention is
  single-line; the stricter parser was arguably right. Decide the convention first, then make both
  parsers enforce whatever is decided.
