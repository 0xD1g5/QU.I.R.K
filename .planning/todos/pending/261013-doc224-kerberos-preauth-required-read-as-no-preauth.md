---
type: todo
created: 2026-10-13
source: Phase 224 front-door verification (FD-OVW); ledger rows DCL-OVERVIEW-0188, DCL-OVERVIEW-0057 (docs/quirk-overview.md Identity Protocol Scanning)
priority: high
area: quirk/scanner/kerberos_scanner.py (_probe_kdc), tests/test_kerberos_scanner.py
status: pending
resolves_phase: 230
owner: DETECT-02
---

# Kerberos etype enumeration never runs against a KDC that requires pre-authentication

`_probe_kdc` (`quirk/scanner/kerberos_scanner.py:127-171`) calls impacket's `sendReceive` and expects it to raise
`KerberosError(KDC_ERR_PREAUTH_REQUIRED)`, whose `e-data` carries PA-ETYPE-INFO2. With the pinned impacket
(`pyproject.toml:78` `"impacket>=0.13.0,<0.14"`, installed 0.13.0), `sendReceive` raises only when the error code is
**not** `KDC_ERR_PREAUTH_REQUIRED`; for that code it returns the raw reply. `_probe_kdc` then reaches
`return []  # Unexpected AS-REP without preauth` (`:144`), and `scan_kerberos_targets` records a single
`service_detail="kerberos-no-preauth"` placeholder (`:387`). The etype map (`:46-54`) is never applied, the UDP path
(`:318`) never runs (it only runs when the TCP probe raises), and the identity-subscore and dashboard Kerberos
findings never see an etype. Pre-authentication is the normal configuration for AD and MIT KDCs, so this is the
common case, and the row name tells the operator the opposite of the truth.

Probe (`work/probes/fd-ovw-kerberos-probe.py` in the phase directory): a fake KDC on 127.0.0.1:18888 answers any
AS-REQ with KRB_ERROR 25 and PA-ETYPE-INFO2 for etypes [23, 17, 18, 1]; the scanner's real `sendReceive` is pointed at
it. Output: the KDC received one 145-byte AS-REQ, and the scanner returned `kerberos-no-preauth`.
`KerberosError(packet=decoder.decode(reply, asn1Spec=KRB_ERROR())[0]).getErrorCode()` on the same reply is 25.

The 2026-09-17 lab observation in `kerberos-udp-probe-times-out-falls-back-to-tcp.md` (Samba AD DC recorded as
`kerberos-no-preauth`) matches this root cause; that todo's "TCP succeeds" reading is wrong.

`tests/test_kerberos_scanner.py` patches `_probe_kdc` wholesale (`:112`), so no test drives `sendReceive`.

- [ ] In `_probe_kdc`, treat a returned reply as a possible KRB_ERROR: decode it, and if the code is 25 parse the
      PA-ETYPE-INFO2 / PA-ETYPE-INFO the same way the `except KerberosError` branch does. Keep the AS-REP case.
- [ ] Add a test that drives the real `sendReceive` against a local fake KDC (the probe above is a template).
- [ ] Then drop the known-issue sentence from docs/quirk-overview.md (Identity Protocol Scanning) and re-check
      the Kerberos rows in docs/operators-guide.md and the chaos-lab Kerberos oracle, and correct the UDP todo.

## Feasibility & Effort

- **CONFIRMED** by the probe above and by reading `quirk/scanner/kerberos_scanner.py:127-171` and impacket
  0.13.0 `impacket/krb5/kerberosv5.py` `sendReceive` (raises only on `!= KDC_ERR_PREAUTH_REQUIRED`, else `return r`).
- Effort **S**: about 15 lines in `_probe_kdc` plus one test. Unknown: whether impacket <0.13 raised for code 25
  (the `METHOD_DATA` import fallback at `kerberos_scanner.py:5-11` shows the module was written for impacket <0.13 too); the fix should
  handle both shapes. No spike needed.
