---
type: todo
created: 2026-10-23
source: Phase 230 review round R12 (WR-01, IN-02, IN-04, IN-05), the 230-REVIEW-R12.md findings
priority: medium
area: quirk/scanner/kerberos_scanner.py (_probe_ldap_anon, _invalid_target_reason, _classify_kdc_reply), quirk/config.py (kerberos_probe_principal)
status: pending
resolves_phase: null
owner: "999.136"
---

# Kerberos scanner: LDAP leg time bound, plus three input/decoder hardening items

Phase 230 fixed R12's CR-01, CR-02, WR-02, WR-03, WR-04, WR-05, IN-01 and IN-03. These four remain. Each is pre-existing, and none of them produces `kerberos-no-preauth`.

- [ ] **WR-01, LDAP leg not time-bounded.** `receive_timeout` is per `recv`, not a deadline. A loopback peer sending one byte every 0.4 s stretched a 1 s timeout to 71.8 s. Fix it the way the TCP Kerberos leg was fixed (`_recv_exact` uses a deadline): run against a monotonic deadline or a worker thread with a hard join, and pass `get_info=ldap3.NONE` to drop ldap3's schema round trips. Name resolution is also unbounded on every leg; record that, or bound it.
- [ ] **IN-02, short-form IPv4.** A target of `"0"` fails `ipaddress.ip_address`, so it is treated as a name, and `getaddrinfo("0")` gives `0.0.0.0`, the local host. Reject names made only of digits and dots that are not a strict IP literal.
- [ ] **IN-04, backslash in the probe principal.** impacket reads `CORP\Administrator` as an escape and sends `CORPAdministrator`. The KDC answers code 6, which is an honest row, but `probe_principal` records the configured string. Reject `\` at config load, with a hint to use `Administrator` or `Administrator@REALM`.
- [ ] **IN-05, decoder remainder discarded.** `decoder.decode(r, ...)[0]` accepts a valid KRB_ERROR or AS-REP followed by trailing bytes. Treat a non-empty remainder as `KerberosUnrecognisedReply`. Not a demonstrated defect (code read only).

## Feasibility & Effort

- WR-01 is **CONFIRMED** (R12 loopback measurement), effort **M**: deadline plumbing through ldap3, plus a loopback slow-drip test.
- IN-02 and IN-04 are **CONFIRMED** by code read and a snippet, effort **S** each.
- IN-05 is **UNKNOWN** in practice, effort **S**. Its real-decode test is impacket-only, so it is local-only in CI, like `TestKerberosPreauthWire`.
