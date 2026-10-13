---
type: todo
created: 2026-10-13
source: Phase 224 GC2 re-audit (ledger part 224-05, docs/report-interpretation.md §10.4 SNMP column)
priority: medium
area: quirk/scanner/hardware_scanner.py (Step 3 SNMPv3 ladder), quirk/scanner/snmp_scanner.py, CBOM quirk:hw-snmp-* properties
status: pending
resolves_phase: null
---

# An SNMPv3 authNoPriv success is labelled `v3 noAuthNoPriv`, and unnegotiated protocol names are recorded

`quirk/scanner/snmp_scanner.py:430-436` sets `snmp_security_level` to one of three values on a v3 success:
`noAuthNoPriv` (no auth key), `authPriv` (auth + priv key) or `authNoPriv` (auth key, no priv key). The
label mapping at `quirk/scanner/hardware_scanner.py:506-510` has only two outcomes:

    SNMP_MODE_V3_AUTH_PRIV if _v3_result.get("snmp_security_level") == "authPriv" else SNMP_MODE_V3_NOAUTH

So an **authenticated** but unencrypted (authNoPriv) session is reported as `v3 noAuthNoPriv`, which every
surface (HTML/DOCX/dashboard SNMP column, CBOM `quirk:hw-snmp-version`) presents as "no authentication".
`docs/report-interpretation.md` §10.4 now documents this (the label covers authNoPriv too). A credential
with no `priv_key_env` is a valid config: `quirk/config.py:936` only validates `priv_protocol` when
`priv_key_env` is set.

Second effect: `quirk/scanner/hardware_scanner.py:513-515` copies `_v3_cred.auth_protocol` /
`_v3_cred.priv_protocol` onto the device on **every** v3 success. Those fields default to `"SHA"` / `"AES"`
(`quirk/config.py:927`, `:929`), so a noAuthNoPriv or authNoPriv device still gets
`quirk:hw-snmp-priv-protocol=AES` (and noAuthNoPriv gets `quirk:hw-snmp-auth-protocol=SHA`) in the CBOM
(`quirk/cbom/builder.py:1124-1135`), naming protocols that were never negotiated.

- [ ] Add a third label (e.g. `v3 authNoPriv`) to `snmp_scanner.py`'s mode constants and to the label maps in
      `html_renderer.py:187`, `docx_renderer.py:39`, `src/dashboard/src/pages/hardware-badge-labels.ts` (`snmpLabel`).
- [ ] Record `snmp_auth_protocol` only when an auth key was used and `snmp_priv_protocol` only when a priv key was used.
- [ ] Then update §10.4 of docs/report-interpretation.md (the `v3 auth+priv` / `v3 noAuthNoPriv` rows).

## Feasibility & Effort

- **Feasibility: CONFIRMED.** The two-way ternary is at `quirk/scanner/hardware_scanner.py:506-510`; the
  three-way security level already exists at `quirk/scanner/snmp_scanner.py:430-436`; the unconditional
  protocol copy is `hardware_scanner.py:513-515`. The bulk-sweep path carries the same two-way mapping
  (`run_scan.py:2959-2960` `if _v3_result.get("snmp_security_level") == "authPriv" else SNMP_MODE_V3_NOAUTH`)
  and must be fixed together (CONFIRMED).
- **Effort: S/M.** One new constant, three label maps, two conditional assignments, plus tests; M if the
  dashboard badge styles and the CBOM golden fixtures need regenerating.
- **Unknowns:** whether any stored scans already carry `v3 noAuthNoPriv` for authNoPriv devices (no
  back-migration is possible without the original credential).
- **Spike:** not needed.
