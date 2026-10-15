---
type: todo
created: 2026-10-13
source: Phase 224 GC3 sweep (ledger parts 224-12/224-13, docs/configuration.md Connector disposition (missing extras))
priority: low
area: quirk/util/optional_extra.py, quirk/scanner/snmp_scanner.py
status: pending
resolves_phase: null
owner: "999.127"
---

# `enable_snmp` without `[hw]` gives no `missing_extra` advisory

Kerberos, S/MIME and AD CS emit a `missing_extra` advisory row when their extra is absent. `pysnmp`
has no REGISTRY entry in `quirk/util/optional_extra.py` (the registry block around :80-160), so
`enable_snmp` without `[hw]` only logs a warning per probe (`quirk/scanner/snmp_scanner.py:651-656`). This may be
intended, because `[hw]` is a deliberate opt-in (pyproject excludes it from `[all]`). docs/configuration.md
now states the difference.

- [ ] Product call: add a REGISTRY entry so the report shows the gap, or keep the log-only behaviour.

## Feasibility & Effort

- **Feasibility: LIKELY.** The registry pattern is used by the other extras.
- **Effort: S.**
- **Unknowns:** whether an advisory should fire when SNMP was not explicitly enabled (see the
  fingerprint-snmp-probe-ignores-enable-snmp todo).
- **Spike:** no.
