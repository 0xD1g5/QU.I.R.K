---
type: todo
created: 2026-10-13
source: Phase 224 GC2 re-audit (ledger rows DCL-ARCH-0273, DCL-ARCH-0257; docs/architecture.md §12 Hardware Scanning)
priority: medium
area: run_scan.py (bulk SNMP sweep, SNMP-only HardwareDevice creation)
status: pending
resolves_phase: null
owner: "999.130"
---

# Devices found only by the bulk SNMP sweep are stored as `Tier N/A` without `assign_tier()`

With `--enable-snmp`, run_scan.py runs a bulk SNMP sweep over every host seen by the TLS, SSH and PQC phases
(`run_scan.py:2877` `if getattr(cfg.connectors, "enable_snmp", False):`, host set built at `:2879`). When a host
answers and has no device in `_hw_batch`, a new `HardwareDevice` is created with a hard-coded tier:
`run_scan.py:3062` `remediation_tier="Tier N/A",` (with `pqc_status="unknown"` at `:3050` and `confidence="medium"`
at `:3051`). `assign_tier()` is never called on that row. The only `assign_tier` call sites are `run_scan.py:2763`
(SSH-stage batch) and `run_scan.py:814` (OT/ICS supplement).

`assign_tier()` would return `Tier 2` for that input (unknown status, medium confidence falls to the conservative
fallback at `quirk/scanner/hardware_tier.py:84` `return "Tier 2"`). `Tier N/A` means "end-of-life before 2030,
decommission plan" (`hardware_tier.py:59`). The stored tier flows unchanged to the dashboard
(`quirk/dashboard/api/routes/scan.py:856` `tier = getattr(d, "remediation_tier", None) or "Tier N/A"`) and to the CBOM
`quirk:hw-remediation-tier` property (`quirk/cbom/builder.py:1102`). So a TLS-only host that answers SNMP is shown as
needing no remediation, even when `apply_eol_date()` (called at `run_scan.py:3074`) found no EOL date.

- [ ] Call `assign_tier(_snmp_dev)` after `apply_eol_date(_snmp_dev)` at `run_scan.py:3074` instead of the
      hard-coded `Tier N/A`.
- [ ] Add a test: an SNMP-only device with no EOL date gets `Tier 2`; one with a pre-2030 EOL gets `Tier N/A`.
- [ ] Then drop the "stored as `Tier N/A` without passing through `assign_tier()`" sentence from
      `docs/architecture.md` §12, and the "A device found only through SNMP is not classified yet" sentence from
      `docs/getting-started.md` (Optional: Hardware Scanning; added by the Phase 224 FD round after audit 3 found
      DCL-GETSTARTED-0112 WRONG).

## Feasibility & Effort

**CONFIRMED.** The hard-coded value is at `run_scan.py:3062`. `grep -rn "assign_tier(" run_scan.py` returns only
`:814` and `:2763`. `persist_and_reconcile` (`quirk/scanner/hardware_drift.py:356`) does not recompute tiers; it only
imports `TIER_ORDER` (`hardware_drift.py:28`). Effort **S**: a one-line change plus one test. Unknown: whether any
UAT or chaos-lab oracle expects `Tier N/A` for an SNMP-only device; grep `expected_results_*.md` for `Tier N/A`
before changing it. No spike needed.
