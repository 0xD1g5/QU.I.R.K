---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS fork B2; ledger row DCL-OPS-B-0234 (docs/operators-guide.md §9.1.1 fallback ladder step 3)
priority: medium
area: run_scan.py (bulk SNMP sweep result persistence), quirk/scanner/snmp_scanner.py (scan_snmp_targets)
status: pending
resolves_phase: null
owner: "999.130"
---

# The SNMP sweep stores a "success" Unknown device row for hosts that never answered SNMP

The operators-guide said that when neither SNMPv3 nor v2c answers, "no SNMP finding is recorded for that host". Live
probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc2-ops-b2-snmp-none-row-probe.py`: TLS-only
listener on 127.0.0.1:4433, nothing on UDP 161, scan with `--enable-snmp`) left this row in `hardware_devices`:

```
('127.0.0.1', 161, 'Unknown', 'snmp', 'none', None, 'success', 'Tier N/A')
 host        port  vendor    method  snmp_version sysdescr probe_status remediation_tier
```

Path: `scan_snmp_targets` (`quirk/scanner/snmp_scanner.py:703-731`) returns one dict per host, responder or not; the
v2c branch labels it `none` (`run_scan.py` `SNMP_MODE_V2C if _v2c_res.get("snmp_sysdescr") else SNMP_MODE_NONE`), the
v3 branch always appends a row; then every result with no existing device becomes a new `HardwareDevice`
(`run_scan.py:3043` "SNMP-only hit") with `probe_status="success"` (`:3067`) and `remediation_tier="Tier N/A"` (`:3062`).
So every TLS/PQC-only host in an `--enable-snmp` scan inflates the hardware device count with an Unknown device that
reads as "EOL before the PQC window", and its probe status claims success for a probe that got nothing.

Related but distinct: `261013-doc224-snmp-only-hardware-devices-skip-assign-tier.md` (tier for hosts that DO answer).

- [ ] Skip creating a new row when the SNMP result has no `snmp_sysdescr` (or record it with a non-success
      `probe_status` and no tier), and decide whether existing rows should keep `snmp_version="none"`.
- [ ] Test: a non-responding TLS-only host produces no new `hardware_devices` row.
- [ ] Then narrow the operators-guide §9.1.1 step 3 text back.

## Feasibility & Effort

- **CONFIRMED** by the live probe above and by reading `run_scan.py:2990-3001` (v2c labelling), `:3020-3074`
  (row creation) and `quirk/scanner/snmp_scanner.py:703-731`.
- Effort **S**: a guard on `_snmp_res.get("snmp_sysdescr")` before the "SNMP-only hit" branch, plus a test.
  **UNKNOWN**: whether the dashboard Hardware page or any chaos-lab oracle (`expected_results_*.md`) counts these rows;
  grep before changing. No spike needed.
