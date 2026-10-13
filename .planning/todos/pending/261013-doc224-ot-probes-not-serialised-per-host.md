---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure gc2-OPS fork B2; ledger row DCL-OPS-B-0263 (docs/operators-guide.md §9.4 OT/ICS safety model)
priority: medium
area: quirk/scanner/hardware_scanner.py (fingerprint_hardware / fingerprint_one Steps 4-5)
status: pending
resolves_phase: null
---

# OT/ICS probes are per endpoint, not per host: a multi-SSH-port host gets duplicate, overlapping Modbus/BACnet probes

The OT/ICS safety model promised "QUIRK never has more than one OT/ICS probe outstanding against a given host at a
time". The probes are issued from `fingerprint_one` (Step 4 Modbus at `quirk/scanner/hardware_scanner.py:590`, Step 5
BACnet at `:617`), keyed only on `ep.host`, and `fingerprint_hardware` runs `fingerprint_one` for every endpoint in a
`ThreadPoolExecutor(max_workers=min(8, len(endpoints)))` (`:725-733`) with no per-host dedupe. A host with two SSH
endpoints therefore gets two Modbus and two BACnet probes, and they overlap.

Probe (`.planning/phases/224-doc-claim-ledger-verification/work/probes/gc2-ops-b2-ot-inflight-probe.py`: two SSH
endpoints 10.9.9.9:22 and :2222, both OT flags on, 502 confirmed open, probe functions replaced by 0.5 s recorders):

```
OT probe calls against 10.9.9.9: [modbus, modbus, bacnet, bacnet]
peak concurrent OT probes against the one host: 2
```

For fragile PLC/RTU/BAS gear this doubles the traffic the risk warning is about, and a second probe can land on a
device the first one just tripped (the one-strike breaker is per call, not per host).

- [ ] Probe each host at most once per scan: collect hosts first and run Steps 4-5 once per host (e.g. a per-host lock
      or a host set built before the executor), then copy the result onto every device row for that host.
- [ ] Test: two endpoints on one host -> exactly one Modbus and one BACnet call, never concurrent.
- [ ] Restore the "single in-flight per host" wording in operators-guide §9.4 once true.

## Feasibility & Effort

- **CONFIRMED** by the probe above and by reading `hardware_scanner.py:567-660` and `:719-733`; the OT supplemental
  pass (`run_scan.py:808` `fingerprint_hardware(ot_eps, ..., ot_only=True)`) uses the same executor.
- Effort **S-M**: restructuring Steps 4-5 out of the per-endpoint function touches the device-row population and
  first-match-wins headline promotion. **UNKNOWN**: whether the check-in re-probe path
  (`check_in_fingerprint_devices`) has the same shape. No spike needed.
