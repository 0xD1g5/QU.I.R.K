# 152-DISC09-FINDING: Phase 144 nmap timing-artifact empirical closure

**Date:** 2026-08-14
**Phase:** 152-discovery-empirical-closure (Plan 152-03)
**Requirement:** DISC-10
**Lab profile:** `segmented-network` (DISC-09, Plan 152-01)

## Background

Phase 144's live end-to-end verification reported 0 open ports on a `127.0.0.1` host
that had 5 genuinely open ports, inside a ~1024-host, ~99.9%-silent loopback-alias
discovery batch. It was attributed to nmap's adaptive RTT/timing engine reacting to a
synthetic, overwhelmingly-silent target list — a condition real routed networks don't
reproduce, since dead hosts on a real segment answer with TCP RST or ICMP-host-unreachable
rather than staying silent. The item was accepted via a user-signed VERIFICATION override
and left `OPEN (needs real hardware)` in `.planning/milestones/v5.11-MILESTONE-AUDIT.md`.

This finding empirically settles that open item using the DISC-09 `segmented-network`
chaos lab profile (Plan 152-01) — a genuine two-subnet routed topology (`segnet-live`,
real TLS/SSH services; `segnet-dead`, iptables-REJECT gateway producing real RST/
ICMP-unreachable) — instead of the loopback-alias approach that produced the original
artifact.

## Strict reproduction definition (quoted from 152-CONTEXT.md)

> "real open ports on live hosts missed/suppressed by adaptive RTT/timing throttling
> during chunked discovery, confirmed by diffing chunked-discovery output against a
> direct nmap run of the same segment. Any other kind of missed port does not count as
> reproduction."

Per 152-CONTEXT.md's explicit Pitfall 4, the diff is restricted to `segnet-live` hosts
only — dead-subnet non-findings are expected/correct, never suppressions.

## Method

`quantum-chaos-enterprise-lab/segmented-network/compare_discovery.py` (Task 1 of this
plan) drives both sides of the comparison against the same 64-host target list
(2 `segnet-live` hosts — `10.70.0.10:443`, `10.70.0.11:2222` — plus the `10.71.0.0/26`
representative dead range, 62 addresses, verified live in Plan 152-01 as 100% RST/closed).

**Post-review correction (152-REVIEW.md WR-01, applied after this finding's 3 runs):**
of those 62 dead-range addresses, `10.71.0.2` is `segnet-gateway`'s own IP on
`segnet-dead` — a probe to it is answered by the gateway's own `INPUT` chain (ordinary
"no listener" RST), not the `FORWARD`-chain `REJECT` rule this lab exists to verify. The
"100% RST/closed" figure for the 62-address dead range above is accurate as a raw nmap
result but conflates 61 genuine REJECT-rule hits with 1 gateway-self INPUT-chain hit.
`compare_discovery.py` now excludes `10.71.0.2` from its dead-range sweep (61 addresses,
63-host total target list); this does not change the verdict below, since the diff that
produces the verdict was always restricted to `segnet-live` hosts only and never counted
dead-range results toward reproduction candidates.

- **Chunked side:** mirrors `run_scan.py`'s real production batch loop
  (`run_scan.py:1464-1537`) honestly — a Phase 145 liveness pre-pass
  (`run_nmap_liveness_check`) narrows the batch to responsive hosts, then the batch's
  size drives `discovery_timing_template_for_batch()`/`discovery_timeout_for_batch()`
  exactly as production selects them (`-T4` for this 64-host batch, since it is below
  `_DISCOVERY_T4_MAX_BATCH_SIZE`=256), and `run_nmap_discovery()` sweeps with that
  template applied via `extra_args`. Since the lab's ~66-host target list is far below
  the real per-batch chunk size (`_MAX_HOSTS_PER_CIDR`=1024), it forms a single batch —
  matching how any real-world scan under 1024 hosts already runs in production today,
  not an invented batch size.
- **Direct side:** a single non-chunked, non-timing-throttled `run_nmap_discovery()`
  call against the identical full 64-host target list — no liveness pre-pass narrowing,
  no `-T4`/`-T3` template injected, nmap's own default timing only. This is the
  "ground truth" side.

Both sides reuse `quirk.discovery.nmap_parser.parse_nmap_xml` (via `run_nmap_discovery`)
for all XML parsing — no hand-rolled parsing.

## Results — 3 independent runs

All 3 runs used the same lab topology, same 64-host target list, same ports (443, 2222),
same nmap args per side — comparable runs per 152-CONTEXT.md's requirement. Raw JSON
reports and per-run nmap XML are preserved as live-fire evidence (see Evidence Retention
below).

| Run | Timestamp (UTC) | Chunked `segnet-live` open | Direct `segnet-live` open | Reproduction candidates |
|-----|------------------|------------------------------|------------------------------|--------------------------|
| 1 | 2026-08-14T02:21:03Z | `10.70.0.10:443`, `10.70.0.11:2222` | `10.70.0.10:443`, `10.70.0.11:2222` | none |
| 2 | 2026-08-14T02:21:19Z | `10.70.0.10:443`, `10.70.0.11:2222` | `10.70.0.10:443`, `10.70.0.11:2222` | none |
| 3 | 2026-08-14T02:21:24Z | `10.70.0.10:443`, `10.70.0.11:2222` | `10.70.0.10:443`, `10.70.0.11:2222` | none |

In every run, the chunked side's `segnet-live` open-port set was identical to the direct
side's `segnet-live` open-port set — zero suppressed ports across all 3 runs.

### Observed non-candidate artifact (documented, not a reproduction)

All 3 runs also reported `10.71.0.1:2222` open on both the chunked and direct sides.
`10.71.0.1` is Docker's own auto-assigned bridge-network gateway address for the
`segnet-dead` network (the subnet config specifies only the `10.71.0.0/24` CIDR, so
Docker allocates `.1` to its own bridge interface) — it is not a `segnet-dead` "dead
host" in the DISC-09 topology sense, and per the strict reproduction definition it is
outside `segnet-live` entirely. It was excluded from the diff by the `_is_segnet_live()`
filter (applied before the diff, not after — see `compare_discovery.py`'s
`_is_segnet_live` docstring) in all 3 runs, consistent with 152-CONTEXT.md's Pitfall 4.
It does not affect the verdict below.

## Verdict

**VERDICT: DOES NOT REPRODUCE**

Across 3 independent live-fire runs against a genuine routed segment with real
RST/ICMP-unreachable dead-host behavior, the chunked discovery batch loop's
production timing template (`-T4` for this batch size) and liveness pre-pass produced
an identical `segnet-live` open-port set to a direct, non-throttled nmap run every
time — zero suppressed ports, zero intermittent misses. This confirms the Phase 144
root-cause analysis: the original artifact was specific to the synthetic
loopback-alias, ~99.9%-silent batch (a condition unassigned-loopback-alias labs
produce but real routed networks do not, since real dead hosts answer with RST/
ICMP-unreachable rather than staying silent). It is not a property of nmap's adaptive
RTT/timing engine reacting to real network behavior, and it does not manifest against
a realistic segmented network. No scoped mitigation is warranted; `quirk/discovery/
nmap_provider.py` is unchanged by this plan.

## Evidence retention

Raw evidence (3x `compare-*.json` reports + their underlying `nmap-discovery-*.xml` /
`nmap-liveness-*.xml`) was generated inside `segnet-prober` at
`/quirk/quantum-chaos-enterprise-lab/segmented-network/runs/` during this plan's
live-fire execution and is not committed to the repository (transient, regeneratable
via `docker compose exec segnet-prober python
/quirk/quantum-chaos-enterprise-lab/segmented-network/compare_discovery.py` against the
`segmented-network` profile at any time) — this finding document is the durable,
citable record of the 3-run result.

## Ledger cross-references

- `.planning/milestones/v5.11-MILESTONE-AUDIT.md` — Phase 144 tech-debt row updated from
  `OPEN (needs real hardware)` to a closure note citing this finding.
- `.planning/STATE.md` — Deferred Items ledger updated with a RESOLVED row citing this
  finding.
