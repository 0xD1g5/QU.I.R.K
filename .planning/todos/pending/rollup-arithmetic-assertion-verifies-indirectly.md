---
type: todo
created: 2026-09-22
source: Phase 208 code review (208-REVIEW.md, WR-01)
priority: low  # the red-proofed mutation IS caught; this closes a narrow residual window, and the test is materially stronger than what it replaced
requirement: COV-07
resolves_phase: null
---

# `test_score_decomposition_render.py`'s rollup-arithmetic assertion verifies `rollup_computed_score()` only indirectly

The rollup test asserts the format-exact **uncapped** sentence plus `"capped to" not in html`,
which pins *which Jinja branch rendered* (`report.html.j2:523/525`). On the uncapped path the
template emits `{{ total_score }}`, not `{{ rollup_computed }}` — so the assertion proves the
branch selection was correct without ever reading the computed rollup value itself.

That is enough to catch the mutation it was red-proved against, and it is already the **second**
version of this assertion: the first accepted `"66 / 100"` appearing anywhere in the HTML and
stayed green under mutation, because the capped branch emitted the same substring from
`total_score` while `rollup_computed` was corrupted. See `208-RED-PROOF.md` cycle 5 and
`208-02-SUMMARY.md`.

## The residual gap

A bug in `rollup_computed_score()` whose wrong output **coincidentally still equals
`total_score`** for this fixture would render the same uncapped sentence and pass. The fixture's
`score` deliberately equals the correct rollup, which is what makes the two values
indistinguishable in the output.

## Feasibility & Effort

- **CONFIRMED** — `report.html.j2:523/525` read directly 2026-09-22; the uncapped branch emits
  `total_score`.
- **Effort: S.**
- Fix shape: add one case whose fixture makes `rollup_computed != total_score` (i.e. drives the
  **capped** branch), and assert the capped sentence's own numbers. That distinguishes the two
  values by construction instead of relying on which branch fired, and red-proof it against the
  same `rollup_computed_score` arithmetic mutation used in cycle 5.
- Do **not** close this by strengthening the existing uncapped assertion — the two values are
  equal on that path by design, so no assertion there can separate them.

Also recorded in the same review, deliberately NOT filed as a todo: the six-label presence test
does not bind each value to its own row label, so a value swap between two rows would go
undetected. That is this project's standing **presence-not-appearance** convention, disclosed in
the test's own docstring, and visual fidelity is gated on human UAT — see
[[feedback_report_render_tests_presence_not_appearance]]. Changing it is a convention decision,
not a defect fix.
