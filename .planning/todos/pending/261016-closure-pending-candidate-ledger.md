---
type: todo
created: 2026-10-16
source: Phase 229 code review, iteration 2 (229-REVIEW WR-01, WR-02, IN-01), deferred at iteration 3
priority: medium
area: quirk/intelligence/closure.py (closure candidate selection, clause (d))
status: pending
resolves_phase: null
owner: "999.138"
---

# A pending closure candidate can be stranded or dropped, so a fixed finding stays Not Verified

**Owner:** 999.138 (closure evidence)

Phase 229 carries a refused closure candidate onto the current scan as a `not_observed` row, so a
later scan can still close it. Three shapes still leave a fixed finding unclosable. All three are
under-claims: none can close a finding that is not fixed. They are documented in
`docs/operators-guide.md` §16 "Known limitations".

1. **Stranded after a service change (review WR-01).** For a carried row, clause (d) uses the
   detecting scan's protocols only when the adjacent prior scan has no asset row at that host:port
   (`quirk/intelligence/closure.py:536`). After an `UNKNOWN` interlude, or a cached-fingerprint
   scan during which the port moved to TLS, the adjacent prior scan sees `UNKNOWN` or `TLS`. In fast
   mode the finding is then refused on every later scan. Reviewer probe `probe_it2.py` P1, re-run
   after the iteration-3 fixes: `s2 refused_probe 2`, then `s3`, `s4` and `s5` each `refused_probe 3`,
   with h7 `['not_observed']` on every scan. As a control, a direct HTTP-to-TLS move closes
   (`{'closed': 2}`). P2 (a cached-fingerprint scan) refuses on s2, s3 and s4.
2. **Dropped by a scan-level refusal (review WR-02).** Carry-forward runs only inside the per-row
   loop. A scope mismatch, a signature-version gap, a missing target-set digest
   (`closure.py:357`), a missing snapshot (`:442`), the `run_scan.py` skip on a failed persist and
   the exception handler all return first. The next scan reads only its adjacent prior scan, so
   every pending candidate disappears. P3: `s2 refused_probe 2` with h7 `['not_observed']`, then
   `s3 {'refused_scope_mismatch': 1}` with h7 `[]`, then s4 has h7 fixed but gives `{'unchanged': 14}`
   with h7 `[]`.
3. **Carried forever at a decommissioned endpoint (review IN-01).** A host that leaves service
   gives `refused_absent_endpoint` on every later scan (`closure.py:508`) and gains one more
   `not_observed` row each scan. P8 gave 11 h7 rows over 11 scans, and s11's burndown is
   `not_observed 2`. There is no operator action to retire such a finding.

- [ ] Item 1: for a carried row, always resolve families from the detecting scan when one exists
      (the reviewer's suggested change). Add three-scan tests for P1 and P2.
- [ ] Item 2: select candidates independently of adjacency. Use the latest non-closed row per
      `(slug, finding_fingerprint)` across comparable earlier scans, or carry pending rows forward
      on a scan-level refusal. Add a test with a scope-mismatch scan between the refusal and the
      recheck.
- [ ] Item 3: decide whether an operator retire action is wanted. It must ship GUI and CLI together
      (dashboard-first positioning) and must never write `closed`.

## Feasibility & Effort

- **Item 1: CONFIRMED** by the P1 and P2 probe output above and by `closure.py:536`. Effort **S**:
  a change of about four lines plus two tests. Legacy D-04 `not_observed` rows find no detecting
  row (OPEN_LIKE excludes them), so they keep today's rule. No spike needed.
- **Item 2: CONFIRMED** by P3 and the early returns at `closure.py:357` and `:442`. Effort **M**.
  Unknown: whether "comparable" should mean comparable with the current scan or with the scan that
  detected the finding. A short design note should come before the code; no spike needed.
- **Item 3: CONFIRMED** by P8. Effort **M**, because it is a new operator action on two surfaces.
  **UNKNOWN** whether operators want it at all, so this is a PM-review decision first.
