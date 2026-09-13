---
type: todo
created: 2026-09-13
source: phase-203 close-out verification
priority: medium
requirement: none — test-infrastructure drift, not a product defect
resolves_phase: null
---

# `test_non_vacuity_skipped_substitute_is_flagged` fails under pytest 9.0.2 — the "EMPTY baseline" is stale

`tests/test_uat_disposition_integrity.py::test_non_vacuity_skipped_substitute_is_flagged` fails:

```
AssertionError: expected a SKIPPED report line naming the node and its reason
assert []
```

## This is NOT a Phase 203 regression — proven, not assumed

Re-run at the pre-phase commit `4c743f74` in a detached worktree: **fails identically.** Phase 203
touched `quirk/scanner/hardware_meta.py`, `quirk/scanner/hw_cve.py`, and
`tests/test_hardware_staleness.py`; none are involved.

## Why it still matters

The project's recorded baseline is an **EMPTY failing-node SET** (STATE.md, verified three times on
2026-09-10/11). This node is not in it. So either the baseline has drifted since then, or the
environment has — and a documented-empty baseline that is silently non-empty is exactly the kind of
stale record this project keeps getting bitten by.

**Do not treat "1 failed" as the new normal without closing this.** The value of an empty baseline
is that any failure is a signal; one tolerated exception destroys that property.

## Likely cause

`pytest 9.0.2` is installed. The test spawns a synthetic pytest subprocess containing a
`@pytest.mark.skip(...)` test and asserts that a **`SKIPPED` report line naming the node and its
reason** appears in the output. The assertion that fails is the report-line scrape, while the
`summary["skipped"] == 1` assertion immediately before it **passes** — so the skip is detected, only
its *reporting* is not found. That points at pytest's short-summary (`-rs`) output format changing
in 9.x, not at the substitute-proof logic being wrong.

## What closing this looks like

1. Confirm which pytest version the documented empty baseline was captured against, and whether CI's
   `Linux Full Suite` pins a version (if CI is on 8.x and local is on 9.0.2, this is local-only
   drift and CI is still green — check before assuming a shared break).
2. Fix the report-line scrape to match pytest 9's format, keeping the test's actual purpose intact:
   it exists to prove a skipped substitute is *visibly* flagged, not merely counted. Do not weaken
   it to `summary["skipped"] == 1` alone — that is the vacuity the test exists to prevent.
3. Re-verify the full-suite failing-node SET and update STATE.md's baseline claim with the pytest
   version it was captured under.

## Related

Phase 203's own verification is unaffected: the 10-test staleness gate is 87 passed / 1 failed,
where that 1 is `test_hardware_matrix_not_stale` — a deliberate, recorded deferral (see
`hardware-matrix-source-urls-broadly-rotted.md`), not this node.
