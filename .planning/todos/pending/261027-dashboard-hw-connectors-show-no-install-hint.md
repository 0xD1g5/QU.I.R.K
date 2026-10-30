---
type: todo
created: 2026-10-27
source: Phase 232 code review (WR-01)
priority: P3
area: quirk/dashboard/api/connector_availability.py, quirk/util/optional_extra.py
status: pending
owner: 999.127
---

# Dashboard shows no install hint for the SNMP, Modbus and BACnet connectors

**Owner phase:** 999.127 (source/container scanning and extras advisories — wrong or missing missing-extra
advisories are that cluster's subject)

When `pysnmp`, `pymodbus` or `bacpypes` is absent, `probe_connector()` returns
`reason='quirk.scanner.snmp_scanner._PYSNMP_AVAILABLE is False'` and `install_hint=''` for
`enable_snmp` / `enable_modbus` / `enable_bacnet`. The `[hw]` extra is deliberately not an
`optional_extra.REGISTRY` entry (it is excluded from `[all]`), so the hint lookup finds nothing, and the
dashboard connector panel tells the operator a module flag is False without telling them what to install.

The CLI does tell them: since Phase 232 (POLISH-02, `01200b71`) the scanners print
`pip install 'quirk-scanner[hw]'`. The docstring at `connector_availability.py:96-100` used to claim the reason
named the extra; Phase 232's review-fix commit corrected it to describe the actual behaviour.

## Feasibility & Effort

- **Feasibility:** CONFIRMED. Either give these three sources a `hint_extra` that resolves to a hint without
  joining `[all]`, or special-case `hw` in `_registry_entry`. `tests/test_connector_availability_mapping.py`
  pins the hint contract and must be extended.
- **Effort:** S. A dashboard check (`/settings` connector panel) needs the bundle rebuilt only if the
  frontend changes; the API change alone does not.
- **Unknowns:** whether `hw` should become a REGISTRY entry with an `in_all=False` flag; decide at fix time.
