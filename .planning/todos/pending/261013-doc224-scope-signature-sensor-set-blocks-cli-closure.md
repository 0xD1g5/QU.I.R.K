---
type: todo
created: 2026-10-13
source: Phase 224 doc-claim ledger (DOC-04), gap closure GC3-OPS (fork F); ledger rows DCL-OPS-GC3F-0007, DCL-OPS-GC3F-0008 (docs/operators-guide.md §15 scope signature bullet)
priority: low
area: quirk/intelligence/scope_signature.py (sensor_set derivation and digest fields)
status: pending
resolves_phase: null
---

# Enrolling or removing a sensor blocks closure between two CLI scans

The scope signature's `sensor_set` is every row of the `sensors` table (`quirk/intelligence/scope_signature.py:188-190`),
not the sensors whose data is in the scan. CLI scan endpoints never carry a `sensor_id` (the module's own comment at
`:184-187`), and sensor-origin findings are excluded from closure tracking entirely. Yet `sensor_set` is a digest input
(`:102`), and closure refuses to compare two scans whose digests differ (`tests/test_closure_verification.py::test_digest_mismatch_refuses`).
So enrolling or revoking a sensor between two otherwise identical CLI scans makes them non-comparable, and every
closure between them is refused, though the CLI scans covered exactly the same ground.

The operators-guide previously said the field records "which sensors contributed"; it now describes the enrolled fleet
and the comparability consequence.

- [ ] Decide whether fleet membership belongs in the comparability digest for CLI-only closure.
- [ ] If not, drop `sensor_set` from the digest fields (keep it as recorded metadata) and bump `SCOPE_SIGNATURE_VERSION`.
- [ ] Add a test: two CLI scans with a sensor enrolled between them can still close a finding.

## Feasibility & Effort

- **CONFIRMED** derivation at `quirk/intelligence/scope_signature.py:190`
  (`session.query(Sensor.sensor_id).all()`), digest membership at `:102`, digest sensitivity by
  `tests/test_scan_scope_signature.py::test_digest_sensitivity_sensor_set` (1 passed, 2026-10-13).
- **LIKELY** effort **S**: remove one key from the digest field tuple plus a version bump; the risk is that every stored
  digest changes, so the first scan after the change cannot close against older scans (a one-time comparability gap,
  same class as any signature-version bump). **UNKNOWN**: whether the sensor-set field was meant to anticipate a
  future per-sensor closure scheme (the §15 "open question"). No spike needed.
