# Exposure map renders 1225 edges where 19 exist — 95% duplicates, 32% self-loops

**Filed:** 2026-09-14 (operator asked whether the map has value "when it looks like a spider web")
**Priority:** P1 for demo credibility — the map is a visual centerpiece and is currently unreadable
**Status:** open, fully diagnosed and quantified

## The answer to "is there value here"

**Yes — and the noise is an artifact, not the data.** Key reuse across endpoints is a genuine
high-value consulting finding (one key compromise takes every endpoint sharing it). The map is
currently drowning that finding in edges it should never have drawn.

## Measured, against the live 31-host multihost scan

`GET /api/exposure-map` returns **27 nodes and 1225 edges**. Decomposed:

| Quantity | Count | Share |
|---|---|---|
| Total edges rendered | 1225 | 100% |
| **Self-edges (`source == target`)** | **390** | **32%** |
| Distinct node-pairs actually represented | **56** | 4.6% |
| Duplicate edge rows | 1169 | **95%** |

`10.80.0.11:443 -> 10.80.0.11:443` is drawn **66 times**. An endpoint connected to itself, 66 times
over, is not a finding of any kind.

## Root cause 1 — no scan scoping (the dominant cause)

`derive_key_reuse_edges` -> `compute_key_reuse_clusters(session)` queries `crypto_endpoints` with
**no `scan_run_id` filter**, so it unions every scan in the database — 24 runs here.

Proof: node `10.80.0.1:9443` appears in the map but has **zero rows in the latest scan**. It exists
only in a run from 2026-09-13T22:51 — a different scan, a day earlier, on the single-host lab (the
multihost config deliberately excludes `.1`, the Docker bridge gateway, and 9443 is not a multihost
port). The map is showing a host the current scan never touched.

This is also what produces the self-edges: the SAME endpoint appears once per scan run, all-pairs
pairs those rows against each other, and every such pair collapses to `A -> A` once node ids are
`f"{host}:{port}"`.

## Root cause 2 — all-pairs expansion at a scale the design did not anticipate

`derive_key_reuse_edges`'s own docstring states the assumption:

> "Each cluster contributes one edge per unique pair of members (all-pairs — **the common cluster
> size is 2-3 members**, per 195-RESEARCH.md Open Question 1's recommendation)."

Measured cluster sizes across the unscoped DB: **[33, 28, 16, 15, 8, 8, 8, 4, 2, 2, 2, 2]**. The two
largest alone yield 528 + 378 = 906 edges, 74% of the graph. The documented assumption is violated
by an order of magnitude — but note this is mostly a *consequence* of cause 1, since the inflated
member counts are the same endpoints repeated across runs.

## What it looks like when scoped correctly

Same scan, filtered to the latest `scan_run_id`:

| | Current | Scoped to one scan |
|---|---|---|
| Endpoints carrying a key fingerprint | — | 17 |
| Reuse clusters | 12 | **3** (sizes 5, 4, 3) |
| Edges (all-pairs) | **1225** | **19** |
| Edges (hub-per-key layout) | — | 12 |
| Nodes | 27 | 12 endpoints + 3 key hubs |

**1225 -> 19.** From unreadable to a diagram that tells a story: three shared keys, one spanning five
endpoints. That is exactly the finding the map exists to show.

Note the scoped cluster sizes (5, 4, 3) sit close to the code's documented "2-3 members" assumption
— **all-pairs is a reasonable design once the scoping is fixed.** Cause 2 is not independently
urgent.

## Fix, in priority order

1. **Scope to a single scan.** Filter `compute_key_reuse_clusters` by `scan_run_id`, defaulting to
   the latest, and ideally accept `?scan_id=` so the map matches whichever scan the rest of the
   dashboard is showing. This alone takes 1225 -> 19.
   - Check how `get_latest_scan` resolves "latest" before copying it — it uses a
     `SESSION_BRACKET` time window with no `scan_run_id` filter and has its own merge defect
     (see `cli-dashboard-score-divergence-same-scan.md`). Do not inherit that bug.
2. **Drop self-edges unconditionally.** `source == target` is never meaningful; guard it in
   `derive_key_reuse_edges` regardless of scoping, as defence in depth.
3. **Deduplicate edges** on `(source, target, edge_type)`.
4. **Optional — hub-per-key layout.** Render one node per shared key with an edge to each member
   (star), instead of all-pairs. 12 edges instead of 19 here, and it scales linearly rather than
   quadratically if a real client estate has a 50-endpoint cluster. It also reads better: "this one
   key is used by 5 endpoints" is the actual finding, and a star shows it directly where a clique
   obscures it.

Items 2 and 3 are unambiguous correctness fixes with no judgment call. Item 1 is the one that
matters most. Item 4 is a design improvement worth doing before a real client estate is mapped.

## Demo note (2026-09-18)

Until at least items 1-3 land, the Exposure Map should be **skipped or shown with a caveat** —
it currently implies a density of key reuse that the scanned estate does not have, which is the
opposite of the honesty posture the rest of the product holds to.
