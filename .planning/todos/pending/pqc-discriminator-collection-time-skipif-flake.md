---
type: todo
created: 2026-09-12
source: phase-202 close-out full-suite run (orchestrator investigation)
priority: medium
requirement: none (test-infrastructure defect, unrelated to any phase's scope)
---

# `test_pqc_discriminator.py`'s live-lab skip is evaluated at COLLECTION time but probed at EXECUTION time — so it FAILS instead of skipping whenever lab state changes mid-suite

**Found 2026-09-12** during phase 202's definitive full-suite run. Phase 202 touched **zero** files in
this path (`git diff --name-only <base>..HEAD | grep -iE "pqc|discrimin"` → empty), so this is
pre-existing and independent.

## What happened

The full suite reported 3 failures where the documented baseline is 1:

```
FAILED tests/test_hardware_staleness.py::test_hardware_matrix_not_stale          <- known, deferred
FAILED tests/test_pqc_discriminator.py::TestPqcDiscriminatorPositive::test_probe_detects_oqs_nginx
FAILED tests/test_pqc_discriminator.py::TestPqcDiscriminatorPositive::test_probe_detects_negotiated_group_string
```

Run in isolation immediately afterward: **7 passed, 2 skipped** — the two nodes skip correctly. Port
39444 was `ConnectionRefusedError` at that moment, and `docker ps` listed no containers.

## Root cause

`_oqs_nginx_up()` (`tests/test_pqc_discriminator.py:101`) opens a socket to `127.0.0.1:39444`. It is
called **inside the decorator expression**:

```python
@pytest.mark.skipif(
    not _oqs_nginx_up(),          # <-- evaluated at MODULE IMPORT / COLLECTION time
    reason="oqs-nginx chaos-lab profile is not running ...",
)
def test_probe_detects_oqs_nginx(self):
    result = probe_pqc_hybrid(OQS_NGINX_HOST, OQS_NGINX_PORT, timeout=15)   # <-- runs ~18 min later
```

Decorator arguments evaluate at import. The probe runs at execution. In an 18-minute suite those are
far apart — and critically, **the suite itself mutates the infrastructure the skip depends on**:
`tests/test_chaos_lab_idempotency.py` runs `./lab.sh up` with
`PROFILE_ARGS="--profile {profile}"` for every profile `docker compose config --profiles` reports,
`oqs-nginx` included, then tears each down.

So the gate is structurally unreliable in either direction:
- reachable at collection, gone at execution -> **FAIL** (what happened here)
- down at collection, up at execution -> **silently skipped** while the lab was actually available,
  so the positive arm never runs and nobody notices

## Why this matters beyond the noise

It manufactures phantom entries in the full-suite failing-node SET, and this project's close-out
discipline is built on comparing SETS against a known baseline. A flaky node that appears only in long
runs is exactly the kind of thing that gets mis-attributed to whatever phase happens to be closing —
which is what nearly happened here, and what the orchestrator had to rule out by reading the skip's
evaluation timing rather than trusting either "pre-existing" or "regression."

## Fix shape (not prescriptive)

Move the reachability check to **execution** time so the decision is made when the dependency is
actually needed. Either:
- a fixture (`@pytest.fixture` calling `_oqs_nginx_up()` and `pytest.skip(...)` inside the test), or
- `pytest.importorskip`-style in-body guard: first line of each test does
  `if not _oqs_nginx_up(): pytest.skip(...)`.

Both make the skip honest at the moment of use. Prefer whichever matches this repo's existing
live-infra conventions — `tests/test_skip_registry.py` governs honest-skip registration and
`@pytest.mark.live_infra` already exists as a marker, so check how other live-infra tests do it and
follow that rather than inventing a third pattern.

**Audit the sibling cases in the same pass:** any other test calling a reachability/availability helper
inside a `skipif` expression has the identical defect. Find them by scanning for a function call inside
a `skipif` argument rather than by grepping a remembered list — this repo has been bitten five times by
hand-maintained site lists (CLAUDE.md records four in the GSD toolchain; the staleness catalog list was
found incomplete on 2026-09-12).

## Acceptance

- Both nodes SKIP (never FAIL) when the lab is down at execution, regardless of collection-time state.
- Both nodes RUN when the lab is up at execution, even if it was down at collection.
- A sibling audit is performed by source scan, and any further collection-time-evaluated availability
  guards are converted the same way.
- The full-suite failing-node SET returns to exactly
  `{tests/test_hardware_staleness.py::test_hardware_matrix_not_stale}` on a clean checkout with the lab
  down — and that claim is verified by a real run, not asserted.
