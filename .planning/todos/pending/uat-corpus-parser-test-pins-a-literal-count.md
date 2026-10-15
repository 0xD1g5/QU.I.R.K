---
type: todo
created: 2026-09-13
source: phase-204 close-out (orchestrator), while backfilling Series 203
priority: low
requirement: COV-01 (adjacent — not a defect in the shipped generator)
resolves_phase: null
---

# `test_uat_corpus_parser.py` pins a literal case count that needs a hand-bump on every corpus growth

`tests/test_uat_corpus_parser.py` has two assertions about the corpus size, one derived and one
frozen:

```python
independent_heading_re = re.compile(r"^### +UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*")
independent_count = sum(1 for line in lines if independent_heading_re.match(line))
cases = list(uat_corpus.iter_cases(lines))
assert len(cases) == independent_count      # derived — never goes stale
assert len(cases) == 887                    # frozen — hand-bumped 878 -> 882 -> 887
```

`test_run_reconcile_against_real_corpus_arithmetic_closes` carries the same frozen pin.

## Why this is worth changing

The frozen pin has required a hand-bump **twice in a single day** — 878 -> 882 when plan 204-05
added Series 204's 4 cases, and 882 -> 887 at Phase 204's close-out when Series 203's 5 backfilled
cases landed. Every future phase that adds UAT cases will trip it again.

It catches nothing the derived assertion does not already catch. The threat it exists to guard
against is "the parser silently drops a class of case IDs" — the defect that started this whole
phase, where a scouting parser's `UAT-<int>-<int>` regex dropped 37 of 878 cases. But
`assert len(cases) == independent_count` detects exactly that, at run time, against whatever the
corpus currently holds, with no maintenance. **Corpus growth is not a defect**, and the frozen pin
cannot tell growth apart from a parser bug — it just fails on both.

## The irony, recorded deliberately

This is Phase 204's own anti-pattern living in Phase 204's own test file. The phase's thesis is that
a derived artifact beats a frozen snapshot, and COV-01/COV-02 exist because a hand-maintained
worklist silently drifted for 40+ series. The same phase shipped a test that freezes a count and
requires a human to notice when it goes stale.

It is at least a *loud* frozen number — the test fails rather than drifting silently, which is
strictly better than the `docs/uat-coverage-gaps.md` header this phase replaced. But "fails loudly
and needs a hand-bump" is still worse than "derives itself."

## Suggested fix (S)

Delete both `assert ... == <literal>` lines. The derived `independent_count` assertion already
covers the real threat. If a belt-and-braces floor is wanted, assert a *lower bound* that will not
need maintenance (`assert len(cases) > 800`) rather than an exact equality.

Do NOT simply widen the pin to a range that happens to fit today — that reproduces the same
maintenance burden with a looser tolerance.

## Do NOT

- Do not remove the `independent_count` cross-check. That one is load-bearing: it is the structural
  guarantee that `uat_corpus.iter_cases` has not silently narrowed its ID grammar, re-derived from
  source on every run, and it is the direct mitigation for the defect that opened this phase.
