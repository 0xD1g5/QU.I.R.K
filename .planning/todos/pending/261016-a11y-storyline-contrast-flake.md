---
type: todo
created: 2026-10-16
source: Phase 229 CI (Dashboard Quality run 38851566456, first attempt at 00446a92)
priority: low
area: src/dashboard/tests/a11y/run-a11y.mjs; findings-storyline page (dark theme)
status: pending
resolves_phase: null
owner: "999.118"
---

# The axe sweep reported a one-off color-contrast violation on findings-storyline (dark) with no dashboard change

The required "Axe + Console Gate" job failed once at `00446a92`:
`[a11y] FAIL [findings-storyline]: color-contrast count 1 exceeds baseline 0` (dark theme). A re-run of
the same job at the same sha passed, and every later run passed. `git diff 0e25abca..00446a92 --
src/dashboard quirk/dashboard/static` was empty and the sweep uses a static frontend fixture
(`VITE_A11Y_FIXTURE=1`), so the code under test did not change. The measurement is nondeterministic.

Likely cause (unconfirmed): a colour probe sampled during a CSS `transition-colors` animation (see the
memory note on waiting out transitions in colour probes). A green re-run is a sample, not health: this job
is REQUIRED, so a recurrence blocks phase closes.

- [ ] Reproduce (run `npm run a11y:check:dark` repeatedly under CPU contention) and capture the failing
      node, its foreground/background colours and the computed contrast ratio.
- [ ] If transition timing: make the harness wait for transitions to settle (or disable transitions in
      the fixture build) before running axe, with a test that fails without the wait.

## Feasibility & Effort

- **Feasibility: LIKELY.** The harness exists; the symptom is recorded once.
- **Effort: S** if transition timing; **M** if it needs a deterministic rendering mode.
- **Unknowns:** which element; whether it recurs.
- **Spike:** a 20-run repetition loop first.
