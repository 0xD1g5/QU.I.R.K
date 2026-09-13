---
type: todo
created: 2026-09-13
source: multihost chaos-lab work (999.110 thin slice) — found while trying to make a demo score worse
priority: P2
requirement: null
resolves_phase: null
---

# Readiness-score ratio penalties divide by PROBE count, not assessable endpoints

Found empirically, not by reading: every attempt to lower a lab readiness score by adding badly
configured hosts either did nothing or made the score **go up**.

## The mechanism

`quirk/intelligence/scoring.py`:

```python
225:  endpoints = max(0, _as_int(totals.get("endpoints", 0)))
227:  denom = endpoints if endpoints > 0 else 1
...
390:  assessable_endpoints = max(0, _as_int(evidence.get("assessable_endpoint_count", endpoints)))
392:  endpoints_assessed = _endpoints_assessed(assessable_endpoints)
```

Every subscore penalty is `-_ratio(count, denom) * weight`. **`denom` is `totals.endpoints`.**
`assessable_endpoint_count` exists and is computed — but is used ONLY for the
`endpoints_assessed` predicate, never as the denominator.

`_endpoints_assessed`'s own docstring warns: *"Callers must pass the ADVISORY/CLOSED-excluded count
(`assessable_endpoint_count`), not `totals.endpoints`"*. That warning is honoured for the predicate
and not for `denom`.

## Measured on the `multihost` lab profile (2026-09-13, live scans)

| ports_tls probed | totals.endpoints | assessable_endpoint_count | plaintext_http_count | Hygiene | Score |
|---|---|---|---|---|---|
| 10 ports | **219** | **27** | 10 | 19/25 | 91/100 |
| 2 ports  | **54**  | **18** | 7  | 19/25 | 89/100 |

With `denom = 219`, ten plaintext-HTTP endpoints score
`-(10/219) * 18.0 = -0.82` against a 25-point budget.
With `denom = assessable_endpoint_count = 27` the same evidence scores
`-(10/27) * 18.0 = -6.7` — roughly a **7-point swing on one subscore**.

`totals.endpoints` ≈ hosts × probed ports (26 × ~9 ≈ 234, observed 219), i.e. it tracks **probes**,
including ports where nothing was found. So:

- **Widening `ports_tls` raises a scan's readiness score** without changing a single real weakness.
- Adding badly configured hosts raises numerator AND denominator, so the score barely moves —
  observed directly: 4 weak-TLS hosts (RSA-1024, SHA-1, broken chain, plaintext) plus 6 plaintext
  intranet hosts took HIGH findings from 3 to 11 and left Hygiene at exactly 19/25 and the score at
  exactly 91/100.

## Why this matters beyond a demo

If `denom` should be the assessable count, then **reported scores are systematically flattered in
proportion to how many ports a scan probes** — a deep scan would score better than a shallow one on
identical infrastructure. That is the opposite of the intended signal and it is the same class of
defect the v5.20 "Release & Correctness Drain" milestone existed to find.

It may also be deliberate: a ratio over *all* probed surface is a defensible "share of estate"
metric, and `assessable_endpoint_count` was added in Phase 184.1 for the narrower purpose its
comment describes ("...100/100 EXCELLENT headline"). **This todo does not assert a bug — it asserts
an unverified inconsistency that needs a decision**, because one of the two readings has to be wrong.

## Feasibility & Effort

- **Feasibility: CONFIRMED** — both values are computed in the same function, four lines apart, and
  the divergence is reproducible with the `multihost` profile at two port-list widths.
- **Effort: M, not S.** Changing `denom` moves EVERY score the product has ever emitted. It needs:
  a decision on which denominator is correct; golden-fixture regeneration (CBOM fixtures and
  `score-strings.json` are generator-drift-gated); a red-proof that the new denominator changes a
  known scan in the predicted direction; and a check on `_apply_weighted_impacts`' 25-point clamp
  interaction, since larger penalties will now saturate more often.
- **Do NOT "fix" this to make a demo score worse.** A score that drops because the lab got worse is
  honest; a score that drops because the scorer was nudged is not.
- **Spike needed: no** — but a written decision on denominator semantics is a prerequisite.

## Reproduction

```bash
cd quantum-chaos-enterprise-lab
PROFILE_ARGS="--profile multihost" ./lab.sh up
docker exec chaoslab-mh-prober-1 quirk --config /scan-config.yaml \
  --allow-internal-targets --allow-cleartext-broker-probe
# then edit multihost-scan-config.yaml's ports_tls to [443,80] and re-run:
# totals.endpoints drops 219 -> 54 and the score drops 91 -> 89 on IDENTICAL infrastructure.
```
