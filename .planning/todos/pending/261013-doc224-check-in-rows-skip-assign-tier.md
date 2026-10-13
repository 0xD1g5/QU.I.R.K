---
type: todo
created: 2026-10-13
source: Phase 224 FD front-door verification (GSI; ledger part 224-03, docs/getting-started.md check-in and Optional: Hardware Scanning)
priority: medium
area: run_scan.py (run_check_in), quirk/scanner/hardware_scanner.py (check_in_fingerprint_devices)
status: pending
resolves_phase: null
---

# `--check-in` re-probe rows never pass through `assign_tier()` and are stored as `Tier N/A`

Found while tracing every `HardwareDevice` writer for the getting-started "CNSA 2.0 remediation tier" fix (sibling
of `261013-doc224-snmp-only-hardware-devices-skip-assign-tier.md`).

`run_check_in` (`run_scan.py:896`) calls `check_in_fingerprint_devices` (`quirk/scanner/hardware_scanner.py`, the
re-probe loop at `:810-860`), which builds each row with `fingerprint_one` (device constructed at
`hardware_scanner.py:377`, no `remediation_tier`). The rows go straight to `persist_and_reconcile`. Nothing sets a
tier, so the column default applies: `quirk/models.py:567` `remediation_tier = Column(..., default="Tier N/A")`.
`grep -rn "assign_tier(" run_scan.py quirk/` finds only `run_scan.py:814` and `:2763`.

Probe (`work/probes/fd-gsi-checkin-tier-probe.sh` in the phase directory, loopback closed port): a known device with
`remediation_tier="Tier 2"` re-probed through `check_in_fingerprint_devices` returns a row with
`remediation_tier None`, which becomes `Tier N/A` on insert. That run's row is `probe_status="failed"`; a successful
re-probe goes through the same constructor, so it should carry the same default (not driven here: it needs a live
device).

Likely consequences (not driven): the dashboard hardware view reads the newest successful row per device
(`quirk/dashboard/api/routes/scan.py:836` `latest_successful_hardware_devices`), so after a check-in a Tier 1/2/3
device would show `Tier N/A` ("EOL before 2030"); and the drift engine's `tier_crossing` comparison
(`quirk/scanner/hardware_drift.py:240`) would see a tier change that is an artefact.

- [ ] Call `assign_tier()` on each re-probed device in `run_check_in` (or inside `check_in_fingerprint_devices`)
      before `persist_and_reconcile`.
- [ ] Test: a successful check-in of a device with no EOL date keeps a computed tier, not `Tier N/A`, and emits no
      `tier_crossing` event.
- [ ] Then drop "and a device re-probed by `--check-in`" from the Tier N/A sentence in `docs/getting-started.md`
      (Optional: Hardware Scanning).

## Feasibility & Effort

- **Feasibility: CONFIRMED** for the missing call (two `assign_tier` call sites, neither on the check-in path;
  model default at `quirk/models.py:567`). **LIKELY** for the dashboard and drift consequences (source read only).
- **Effort: S.** A loop over the returned devices, plus one test.
- **Unknowns:** whether `assign_tier` needs `apply_eol_date()` first on this path (the SNMP-only path calls it at
  `run_scan.py:3074`); check whether `fingerprint_one` already applies EOL.
- **Spike:** no.
