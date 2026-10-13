---
type: todo
created: 2026-10-13
source: Phase 224 GC2 re-audit (ledger part 224-05, docs/report-interpretation.md §10.3 / §10.4)
priority: medium
area: quirk/scanner/hardware_scanner.py (fingerprint_one Step 3), run_scan.py (SSH phase hardware fingerprint)
status: pending
resolves_phase: null
---

# Hardware fingerprinting sends an SNMP probe even when `enable_snmp` is false

`enable_snmp` defaults to `false` (`quirk/config.py:371`) and gates only the bulk SNMP sweep
(`run_scan.py:2877` `if getattr(cfg.connectors, "enable_snmp", False):`). The SSH phase calls
`fingerprint_hardware` for every SSH endpoint unconditionally (`run_scan.py:2756`), and its Step 3
(`quirk/scanner/hardware_scanner.py:471` `if device.vendor == "Unknown" and not ot_only:`) sends an SNMP
probe (`probe_snmp_target(host, community="public", ...)`, `hardware_scanner.py:532`) to every SSH host whose
banner and HTTP management page did not identify a vendor. Nothing in that path reads `enable_snmp`.

Observed (isolated HOME, QUIRK_* unset): `fingerprint_hardware([CryptoEndpoint(host="127.0.0.1", port=2222,
protocol="SSH", service_detail="SSH-2.0-UnknownThing_1.0")], timeout=1, cfg=<connectors.enable_snmp=False>)`
returned a device with `snmp_version='none'` (pysnmp installed), i.e. an SNMPv2c `public` probe was sent.

This was the original Phase 133 design (commit c05d79a4: "Wire SNMP as Step 3 cascade ... runs only when
vendor == 'Unknown'"), so it may be intended. But operators read "SNMP is disabled by default" (config
default, `--enable-snmp` flag) as "QUIRK sends no SNMP traffic", and an SNMP `public` community probe to a
host that was not in an SNMP scope can trip IDS rules. docs/report-interpretation.md §10.3 now states the
actual behaviour.

- [ ] Decide: gate Step 3 on `enable_snmp` (or a separate `fingerprint_snmp` switch), or keep it and document
      it in docs/operators-guide.md §9.1 and docs/configuration.md `enable_snmp`.
- [ ] If gated: an unidentified SSH device would then show the em-dash SNMP state instead of `No SNMP`;
      update §10.4's `No SNMP` / em-dash rows.

## Feasibility & Effort

- **Feasibility: CONFIRMED.** The ungated call site is `quirk/scanner/hardware_scanner.py:471`; `cfg` is
  already passed in (`hardware_scanner.py:489` reads `cfg.connectors`), so the flag is available there.
- **Effort: S** for the gate plus a test; documentation updates in two guides.
- **Unknowns:** whether any operator relies on the fallback probe to identify devices without enabling the
  sweep (a behaviour change for them).
- **Spike:** not needed; this is a product decision first.
