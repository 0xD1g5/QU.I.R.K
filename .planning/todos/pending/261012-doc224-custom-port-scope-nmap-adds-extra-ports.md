---
type: todo
created: 2026-10-12
source: Phase 224 doc-claim ledger (DOC-04, D-10); ledger rows DCL-CONFIG-B-* (configuration.md Port Scope / Custom port spec)
priority: low
area: run_scan.py (nmap discovery port list), dashboard custom port scope
status: pending
resolves_phase: null
---

# "Custom scope means exactly these ports" is false when nmap discovery is on

The Port Scope section says a `custom` scope scans exactly the ports you list. With the nmap checkbox on, `run_scan.py`
builds the nmap port list as `select_nmap_port_list(cfg, available) + [22, 80, 8080, 8000]` and passes the sorted set to
`nmap -p <csv>`, so four ports the operator never listed (22, 80, 8000, 8080) are probed. With nmap off, the builtin
discovery uses exactly `scan.ports_tls` (`quirk/scanner/target_expander.py`). The dashboard's custom scope already goes to
the trouble of disabling the email and broker connectors to avoid leaking ~7 unrequested ports, so this is the same class
of leak.

`docs/configuration.md` now documents the four extra ports.

- [ ] For `custom` scope (and for any explicit `scan.ports_tls` narrowing) drop the hard-coded extra ports, or make them
      conditional on the profile.
- [ ] Add a test: custom scope `443` + nmap on passes only `443` to nmap.
- [ ] Update the Port Scope section and regenerate `docs/quirk-master-guide.md`.

## Feasibility & Effort

**CONFIRMED** by reading `run_scan.py` (search `_base_ports = select_nmap_port_list(`). Effort **S**. Unknown: the 22/80
additions may be there on purpose so the SSH and plaintext-HTTP findings still appear on a TLS-only list; decide the
intended behaviour before removing them, and note that `top1000`/`all` scopes are unaffected (they use `port_spec_override`).
