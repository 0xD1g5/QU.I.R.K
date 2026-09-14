---
type: todo
created: 2026-09-14
source: 999.115 P1-P6 property suite (task 8, commit e1716d78) — found by test P5c, not by a defect report
priority: medium  # LATENT, not live: unreachable from today's producer. Medium because the thing preventing it is an incidental coupling in a different module that nothing pins.
requirement: null
resolves_phase: null
---

# Score drivers can be attributed to a domain the headline explicitly did not assess

`compute_readiness_score()` builds its client-facing driver list by concatenating **all six**
domains' impacts unconditionally:

```python
all_drivers = (
    hygiene_drivers + modern_tls_drivers + identity_trust_drivers
    + agility_drivers + dar_drivers + motion_drivers
)
```

It never consults the `_dar_assessed()` / `_motion_assessed()` / `_identity_assessed()` predicates
that, a few lines earlier, decide which domains enter the headline at all. So a domain whose
subscore is reported as `None` — meaning the score makes **no claim** about it and it is excluded
from the rescale denominator entirely — can still supply the **single largest driver** shown to the
client.

Reproduced by `tests/test_score_properties.py::test_p5c_no_driver_is_attributed_to_a_domain_excluded_from_the_headline`
(`xfail(strict=True)`). With `data_at_rest` unassessed and `dar_db_plaintext_count: 30`, the
returned drivers lead with `"Database plaintext connections"` while `subscores["data_at_rest"]` is
`None`.

## Why this is filed as LATENT, not live

Every `dar_*` and `motion_*` counter in `quirk/intelligence/evidence.py` is incremented inside the
same per-endpoint loop that increments `protocol_counts` (`evidence.py:183` vs the `elif proto ==`
chain at 295-355). So today a non-zero `dar_db_plaintext_count` **implies** `POSTGRESQL` in
`protocol_counts`, which implies `_dar_assessed()` is true, which implies the domain is in the
headline. The invariant holds — by coincidence of code layout, in a different module, with nothing
asserting it.

**That is the reason to fix it rather than close it.** The scorer's own contract permits the
incoherence; a second producer writing these counters from outside that loop — a cloud connector
reporting unencrypted S3 buckets or an unencrypted EKS cluster via API rather than via a port
probe, which is exactly the shape of the DAR connectors — would break the coupling silently, with
no test failing. This is the same defect shape CLAUDE.md records five times over: a safety property
that is real but resting on a hand-verified, unpinned coincidence.

## Fix shape

Filter `all_drivers` by the same `category_table` assessed flags that already produce `subscores`,
rather than by a second hand-maintained list of which domains are which. The `category_table` dict
already pairs each domain's score with its assessed boolean — the drivers should be carried in the
same structure so the two cannot drift. Do **not** fix it by teaching `evidence.py` to keep the
counters coupled; that preserves the coincidence instead of removing the dependence on it.

## Feasibility & Effort

- **CONFIRMED** — the defect is reproduced by an executing test; the reachability analysis is
  backed by named line numbers in `evidence.py` read at filing time.
- **Effort: S.** One structural change inside `compute_readiness_score()`, no schema change, no
  report-surface change (drivers already flow through a single list). Blast radius is any test
  pinning driver contents for an unassessed domain — expected to be zero, since no such fixture
  exists today.
- **Unknowns:** whether any report surface *wants* to show an unassessed domain's drivers as
  context. Check `quirk/reports/content_model.py` and the executive surfaces before assuming not.
- **Spike needed:** no.

## Closing condition

Delete the `xfail(strict=True)` marker on `test_p5c_...` and let it stand as a green gate. Note
that strict mode will force this: once fixed, the test XPASSes and the suite fails until the marker
is removed.
