---
created: 2026-10-13
title: "exposure-map.test.tsx case (d) asserts console.warn synchronously after waitFor(img) — intermittent CI failure"
area: test
priority: medium
source: Phase 224 CI observation (Dashboard Quality run 38438743247, E2E Smoke job, "Run frontend unit tests")
---

# exposure-map dangling-edge test races its `warn` assertion

`src/dashboard/src/pages/__tests__/exposure-map.test.tsx` case (d) ("drops a dangling edge (endpoint absent from nodes)
instead of crashing the render") waits only for the graph container (`waitFor(() => screen.getByRole("img"))`, ~:128-130)
and then asserts **synchronously** that the warn spy was already called
(`expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining("dropped 1 edge(s)"))`, :139). If the drop warning is
emitted in a later effect than the one that renders the container, a slow runner observes `Number of calls: 0`.

Observed: Dashboard Quality run 38438743247 (E2E Smoke job, frontend unit tests) failed exactly this assertion at
`exposure-map.test.tsx:139:21` (`1 failed | 825 passed`), on a commit with **no diff under `src/`** versus main. The same
source passed in run 38425774674 an hour earlier, and the file passed 5/5 locally (`npx vitest run
src/pages/__tests__/exposure-map.test.tsx` -> `Tests 4 passed (4)` each time). The E2E Smoke job is REQUIRED in
`scripts/branch_ci_state.py`, so this flake can turn a phase's CI observation red.

- [ ] Move the `warnSpy` assertion inside the `waitFor` (or `await waitFor(() => expect(warnSpy).toHaveBeenCalledWith(...))`).
- [ ] Mutation-check: make the component skip the warn and confirm the test still fails.

## Feasibility & Effort

- **Feasibility: CONFIRMED.** Test-only change at `src/dashboard/src/pages/__tests__/exposure-map.test.tsx:139`; the
  component is untouched.
- **Effort: S.**
- **Unknowns:** whether other `*.test.tsx` files share the same "waitFor one thing, then assert a side effect
  synchronously" shape (worth a grep for `waitFor` followed by a bare `toHaveBeenCalled`).
- **Spike:** no.
