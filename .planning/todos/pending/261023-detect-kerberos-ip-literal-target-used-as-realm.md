---
type: todo
created: 2026-10-23
source: Phase 230 DETECT-02 (plan 230-02 live KDC measurement, D-27)
priority: medium
area: quirk/scanner/kerberos_scanner.py (_derive_realm), quirk/config.py (kerberos_targets), docs/operators-guide.md
status: pending
resolves_phase: null
owner: "999.136"
---

# A Kerberos target given as an IP literal is used as the realm, so the KDC answers principal-unknown

`_derive_realm` (`quirk/scanner/kerberos_scanner.py:81-98`) returns an IP-literal target uppercased as-is
(`ipaddress.ip_address(stripped)` then `return stripped.upper()`, `:95-97`). `scan_kerberos_targets` passes that as the
realm to `_probe_kdc` (`:334`). A KDC does not host a realm called `127.0.0.1`.

## Live evidence (plan 230-02, 2026-10-23, chaos-lab Samba AD DC reached on 127.0.0.1:18088)

| Probe | Realm | Principal | Result |
|---|---|---|---|
| raw impacket | QUIRK.LAB | Administrator | KRB_ERROR 25, etypes [18] |
| raw impacket | 127.0.0.1 (what `_derive_realm("127.0.0.1")` yields) | Administrator | KRB_ERROR code 6 (principal unknown in realm `127.0.0.1`), 4 of 6; 2 empty |
| scan, target `127.0.0.1` | derived `127.0.0.1` | Administrator | 3 rows `kerberos-etypes-unavailable-principal-unknown`; the rest `kerberos-no-preauth` through the UDP fallback (see the UDP-failure todo) |

So a bare-IP target can never enumerate etypes. There is no explicit-realm option anywhere in `ConnectorsCfg`.
Docs (operators guide, chaos-lab oracle `expected_results_v4.md`) now tell operators to use FQDN targets; that is a
workaround, not a fix.

## Fix options (left unchosen)

- (a) a per-target or global realm setting (`connectors.kerberos_realm`, or `host=realm` target syntax), with GUI parity;
- (b) reverse-lookup the IP to an FQDN and derive the realm from it;
- (c) a pre-probe that reads the realm from the KDC's code-6 reply realm field (the reply echoes the realm it expected).

- [ ] Choose an option, then add a wire test using the existing fake KDC that answers code 6 for a wrong realm.
- [ ] Update the operators guide FQDN note and the chaos-lab oracle when fixed.

## Feasibility & Effort

- **CONFIRMED** defect: `kerberos_scanner.py:95-97` plus the measured code 6 above.
- **LIKELY** effort **M** (option a needs config, dashboard parity per GUI-first, docs, template; option b is S but fragile without PTR records; option c is S-M and the least invasive).
- **UNKNOWN**: whether MIT and Active Directory KDCs also answer code 6 for an unknown realm (measured on Samba only).
- **Spike**: yes, a short one against one more KDC implementation before choosing (c).
