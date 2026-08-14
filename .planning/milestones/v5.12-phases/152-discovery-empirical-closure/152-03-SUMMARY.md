---
phase: 152-discovery-empirical-closure
plan: 03
subsystem: discovery
tags: [nmap, chaos-lab, empirical-closure, verification-override, tech-debt]
dependency-graph:
  requires:
    - segmented-network chaos lab profile (Plan 152-01)
  provides:
    - Empirical DOES-NOT-REPRODUCE verdict for the Phase 144 nmap timing artifact
    - Reusable chunked-vs-direct nmap discovery comparison script
  affects:
    - .planning/milestones/v5.11-MILESTONE-AUDIT.md
    - .planning/STATE.md
tech-stack:
  added: []
  patterns:
    - Chunked-vs-direct nmap comparison mirroring run_scan.py's real batch loop honestly (liveness pre-pass + discovery_timing_template_for_batch), diffed against a non-throttled direct run, restricted to a defined "live" host set before diffing
key-files:
  created:
    - quantum-chaos-enterprise-lab/segmented-network/compare_discovery.py
    - .planning/phases/152-discovery-empirical-closure/152-DISC09-FINDING.md
  modified:
    - .planning/milestones/v5.11-MILESTONE-AUDIT.md
    - .planning/STATE.md
decisions:
  - "VERDICT: DOES NOT REPRODUCE (3/3 live-fire runs) - no mitigation implemented in quirk/discovery/nmap_provider.py, per CONTEXT.md's conditional-outcome branch; the file is provably unchanged (git diff --stat empty)"
metrics:
  duration: "~35 minutes"
  completed: 2026-08-14
---

# Phase 152 Plan 03: Discovery Empirical Closure Summary

Empirically settled the Phase 144 nmap adaptive RTT/timing-engine artifact (a permanently
user-accepted VERIFICATION override from v5.11) using the DISC-09 `segmented-network` chaos
lab profile built in Plan 152-01. Built a repeatable chunked-vs-direct comparison script, ran
it 3 independent times against the live Docker lab, and got an identical `segnet-live`
open-port set on both sides every time - **VERDICT: DOES NOT REPRODUCE**. No code change was
needed in `quirk/discovery/nmap_provider.py`; both v5.11-era ledgers (`v5.11-MILESTONE-AUDIT.md`
tech_debt block and `STATE.md` Deferred Items) were updated to close the loop and remove the
stale "OPEN (needs real hardware)" language.

## What Was Built

### Task 1: Repeatable chunked-vs-direct comparison script

`quantum-chaos-enterprise-lab/segmented-network/compare_discovery.py` - runnable via
`docker compose exec segnet-prober python /quirk/quantum-chaos-enterprise-lab/segmented-network/compare_discovery.py`
(committed at `2fc7c32`). Builds the full 64-host target list (2 `segnet-live` static IPs +
the `10.71.0.0/26` representative dead range from Plan 152-01), then:

- **Chunked side:** mirrors `run_scan.py`'s real production batch loop
  (`run_scan.py:1464-1537`) honestly - a Phase 145 liveness pre-pass narrows the batch to
  responsive hosts, then `discovery_timing_template_for_batch()`/`discovery_timeout_for_batch()`
  select the same `-T4`/timeout the production code would for this batch size, and
  `run_nmap_discovery()` sweeps with that template applied via `extra_args`.
- **Direct side:** a single non-chunked, non-timing-throttled `run_nmap_discovery()` call
  against the identical full target list (no liveness pre-pass narrowing, no `-T` template
  injected - nmap's own default timing).
- **Diff:** restricted to `segnet-live` hosts *before* the diff runs (`_is_segnet_live()`
  filter applied to both sides' open-port sets first, diff second - never post-hoc), per
  152-CONTEXT.md's Pitfall 4 (dead-subnet non-findings are expected/correct, never
  suppressions).

Both sides reuse `quirk.discovery.nmap_parser.parse_nmap_xml` via `run_nmap_discovery()` - no
hand-rolled XML parsing. Each run writes a structured JSON report (target counts, chunked/direct
open-port sets, live-only subsets, and "reproduction candidates") to
`quantum-chaos-enterprise-lab/segmented-network/runs/`.

### Task 2: 3 independent live-fire runs - 152-DISC09-FINDING.md

Brought up the `segmented-network` profile (`segnet-gateway`, `segnet-live-tls`,
`segnet-live-ssh`, `segnet-prober`) via `docker compose --profile segmented-network up -d`.
Rebuilt `segnet-prober`'s image (the build context excludes `quantum-chaos-enterprise-lab/`
via `.dockerignore` - see Deviations) and copied `compare_discovery.py` into the running
container via `docker compose cp` for execution, since a full rebuild-per-iteration wasn't
needed for a script that isn't part of the shipped image.

Ran `compare_discovery.py` 3 times (2026-08-14T02:21:03Z, 02:21:19Z, 02:21:24Z) against the
same lab topology, same 64-host target list, same ports (443, 2222). All 3 runs: chunked
`segnet-live` open-port set == direct `segnet-live` open-port set == `{10.70.0.10:443,
10.70.0.11:2222}`. **0 reproduction candidates in all 3 runs.**

Wrote `.planning/phases/152-discovery-empirical-closure/152-DISC09-FINDING.md`
(gitignored - `.planning/` is excluded from this public repo per PUBREPO-PLANNING-EXCL,
not tracked by git; internal planning artifact only) containing: the quoted strict reproduction
definition, the 3-run evidence table, a note on an observed non-candidate artifact
(`10.71.0.1:2222` - Docker's own auto-assigned `segnet-dead` bridge-network gateway address,
correctly excluded by the live-only filter, not a `segnet-dead` "dead host"), and the explicit
verdict line `**VERDICT: DOES NOT REPRODUCE**` with rationale.

### Task 3: Ledger closure (DOES NOT REPRODUCE branch)

Per CONTEXT.md's conditional-outcome instructions, the `DOES NOT REPRODUCE` branch fired:

- **`quirk/discovery/nmap_provider.py`: NO CHANGE.** `git diff --stat -- quirk/discovery/nmap_provider.py`
  is empty - verified as part of this task's acceptance criteria.
- **`.planning/milestones/v5.11-MILESTONE-AUDIT.md`:** the Phase 144 tech_debt row updated
  from `"OPEN (needs real hardware): ..."` to a closure note citing `152-DISC09-FINDING.md`
  and the 3-run result; the DISC-09 lab-profile tech_debt row updated from `"DEFERRED BY
  DECISION..."` to `"SHIPPED (Phase 152, 2026-08-14)..."`; the prose "Remaining Tech Debt"
  table's two corresponding rows struck through with a closure note, and the "5 items"
  summary line updated to "5 items originally; 2 closed by Phase 152".
- **`.planning/STATE.md`:** added a new "Resolved (2026-08-14)" row under Deferred Items
  citing `152-DISC09-FINDING.md` and the resolution mechanism, ahead of the carried-forward
  2026-08-11 re-triage table (left otherwise untouched - this is a net-new addition, not an
  edit of an existing row, per the plan's read_first instruction).

Verification: `! grep -q "OPEN (needs real hardware)" .planning/milestones/v5.11-MILESTONE-AUDIT.md`
-> `LEDGER_CLOSED`. `grep -c "152-DISC09-FINDING" .planning/STATE.md` -> `1`.
`python -m compileall quirk/discovery/nmap_provider.py` -> clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `segnet-prober`'s image build excludes `quantum-chaos-enterprise-lab/` entirely**
- **Found during:** Task 2's first live-fire attempt (`docker compose exec segnet-prober ls
  /quirk/quantum-chaos-enterprise-lab/segmented-network/` -> "No such file or directory").
- **Issue:** the repo root's `.dockerignore` excludes `quantum-chaos-enterprise-lab` from
  every build context (`# Tests + dev tooling` section) - `sensor.Dockerfile`'s `COPY . /quirk/`
  never copies `compare_discovery.py` into the image, even after a full `docker compose build
  segnet-prober`, since Docker's own build context construction applies `.dockerignore` before
  `COPY` ever runs.
- **Fix:** used `docker compose cp compare_discovery.py segnet-prober:/quirk/quantum-chaos-enterprise-lab/segmented-network/compare_discovery.py`
  to inject the script into the already-running container for execution, rather than modifying
  `.dockerignore` (which would ship the entire chaos lab directory tree into the production
  sensor image - a scope change well beyond this task, and the sensor image is not meant to
  carry lab-only tooling). `compare_discovery.py` remains a lab-only dev script executed via
  `docker compose cp` + `exec`, exactly as any other manual chaos-lab verification script.
- **Files modified:** none (execution-only workaround, no source change).
- **Commit:** N/A (no code change - this is a runtime-only injection step, documented here for
  reproducibility).

### Verify-command / environment notes (documented, not a defect)

- `docker compose --profile segmented-network up -d` (no service list) also started this repo's
  **default-profile** containers already defined without a `profiles:` key, and one
  (`tls-modern`) collided on host port 443 with an already-running container from a prior
  session. Recovered by scoping `up -d` to the 4 explicit `segmented-network` services
  (`segnet-gateway segnet-live-tls segnet-live-ssh segnet-prober`) instead of a bare
  `--profile` flag - no destructive command was used, no other lab state was affected.
- Lab teardown used scoped `docker compose stop`/`rm -f` on the 4 `segmented-network` services
  only (never a bare `docker compose down`), per the housekeeping precedent set in
  152-01-SUMMARY.md.
- All 3 runs also observed `10.71.0.1:2222` reported open by nmap on the `segnet-dead` side -
  Docker's own auto-assigned bridge-network gateway IP for that network, not a lab-defined dead
  host. Correctly excluded from the reproduction-candidate diff by the `segnet-live`-only filter
  (documented in the finding doc's "Observed non-candidate artifact" section); no action needed.

## Self-Check: PASSED

Verified files exist:
```
FOUND: quantum-chaos-enterprise-lab/segmented-network/compare_discovery.py
FOUND: .planning/phases/152-discovery-empirical-closure/152-DISC09-FINDING.md (gitignored, main-repo path - not tracked by git in this public repo per PUBREPO-PLANNING-EXCL)
```

Verified commits exist:
```
FOUND: 2fc7c32
```

Verified no unintended code change:
```
git diff --stat -- quirk/discovery/nmap_provider.py  ->  (empty - confirmed unchanged)
```
