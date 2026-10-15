---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS (fork E); ledger rows DCL-OPS-B-0353, DCL-OPS-B-0365 (docs/operators-guide.md §10 and §10.5)
priority: low
area: run_scan.py (discovery cache save/load around the nmap batch loop)
status: pending
resolves_phase: null
owner: "999.136"
---

# A `--cache --resume` rerun drops the original run's liveness-skipped hosts from its record

The whole-discovery cache stores only targets and ports (`run_scan.py:2478`,
`save_cache(..., {"targets": ..., "ports": ..., "mode": "nmap"})`). A rerun with `--cache --resume` loads it
(`run_scan.py:2215`), skips the nmap batch loop, and so runs no liveness pre-pass and writes no `liveness_skip` or
`privilege_fallback` rows. Hosts the first run skipped are absent from the rerun's record, and its
"Hosts undetermined" count is 0. The per-batch resume cache already solved this for checkpointed batches
(`run_scan.py:2308-2318`, Phase 163 T-163-01); the whole-discovery cache never got the same treatment.

Probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc3-ops-E-liveness-cache-probe.sh`, loopback
only): run 1 `--discovery nmap --cache` on 127.0.0.1 + 127.0.0.2 -> `127.0.0.2 liveness_skip` and one
`privilege_fallback` row; run 2 with `--cache --resume` -> "Using cached discovery results", zero liveness rows for
run 2.

The operators-guide now documents the exception instead of saying a skipped host is never dropped.

- [ ] Store the batch's liveness advisories in the discovery cache and replay them on a cache hit (mirror
      `serial_to_liveness` use at `run_scan.py:2316-2318`).
- [ ] Test: cache-hit run reports the same `Hosts undetermined` count as the run that wrote the cache.

## Feasibility & Effort

- **CONFIRMED** by the probe and by `run_scan.py:2215` (cache load), `run_scan.py:2220-2222` (cache-hit branch
  uses only `targets`) and `run_scan.py:2478` (save without liveness).
- **LIKELY** effort **S**: `serial_to_liveness` / the liveness serializer already exist for the per-batch cache;
  add a `liveness` key to the save and replay it in the cache-hit branch. **UNKNOWN**: whether the
  `privilege_fallback` advisory should be replayed (it describes the original run's privileges). No spike needed.
