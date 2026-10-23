---
type: todo
created: 2026-10-23
source: Phase 230 DETECT-02 (plan 230-02, D-24; GUI-first positioning 2026-10-12)
priority: medium
area: quirk/dashboard/api/schemas.py (_CONNECTOR_DETAIL_KEY_TYPES), src/dashboard/src/components/ConnectorsPanel.tsx
status: pending
resolves_phase: null
owner: "999.121"
---

# `connectors.kerberos_probe_principal` is YAML-only: no dashboard control

Phase 230 added `connectors.kerberos_probe_principal` (default `Administrator`), the client principal the Kerberos probe
sends in its AS-REQ. It can be set in the YAML config only:

- absent from `quirk/dashboard/api/schemas.py::_CONNECTOR_DETAIL_KEY_TYPES` (`:836`; the only Kerberos key there is
  `kerberos_targets` at `:841`), so the connectors overlay rejects it;
- absent from `src/dashboard/src/components/ConnectorsPanel.tsx` (the `enable_kerberos` group at `:116-117` renders
  only `kerberos_targets`).

QU.I.R.K. is dashboard-first, CLI-complete (2026-10-12): a new setting should ship GUI and CLI together. The operators
guide row says "YAML only" for this key.

- [ ] Add the key to `_CONNECTOR_DETAIL_KEY_TYPES` (str, non-empty, same validation as `ConnectorsCfg`), the job-YAML merge and Effective Config preview.
- [ ] Render a text field in the Kerberos group of `ConnectorsPanel.tsx` (then `npm run build` and lint; statics are committed).
- [ ] Update `docs/operators-guide.md` / `docs/configuration.md` ("YAML only" becomes "settable from the dashboard").

## Feasibility & Effort

- **CONFIRMED**: absence verified by grep at the lines above (2026-10-23).
- **LIKELY** effort **S**: the Tier 2 connector parity mechanism (Phase 197) was built for exactly this shape; one key, one field.
- **UNKNOWN**: whether a lockstep test enumerates connector fields against the overlay map and would flag the omission; it did not go red in Phase 230, so none does.
- **Spike**: no. Owner 999.121 is OPEN (read 2026-10-23) and takes GUI-parity members.
