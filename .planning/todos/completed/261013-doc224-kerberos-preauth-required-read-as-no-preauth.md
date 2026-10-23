---
type: todo
created: 2026-10-13
source: Phase 224 front-door verification (FD-OVW); ledger rows DCL-OVERVIEW-0188, DCL-OVERVIEW-0057 (docs/quirk-overview.md Identity Protocol Scanning)
priority: high
area: quirk/scanner/kerberos_scanner.py (_probe_kdc), tests/test_kerberos_scanner.py
status: completed
completed: 2026-10-23
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

- [x] In `_probe_kdc`, treat a returned reply as a possible KRB_ERROR: decode it, and if the code is 25 parse the
      PA-ETYPE-INFO2 / PA-ETYPE-INFO the same way the `except KerberosError` branch does. Keep the AS-REP case.
- [x] Add a test that drives the real `sendReceive` against a local fake KDC (the probe above is a template).
- [x] Then drop the known-issue sentence from docs/quirk-overview.md (Identity Protocol Scanning) and re-check
      the Kerberos rows in docs/operators-guide.md and the chaos-lab Kerberos oracle, and correct the UDP todo.

## Feasibility & Effort

- **CONFIRMED** by the probe above and by reading `quirk/scanner/kerberos_scanner.py:127-171` and impacket
  0.13.0 `impacket/krb5/kerberosv5.py` `sendReceive` (raises only on `!= KDC_ERR_PREAUTH_REQUIRED`, else `return r`).
- Effort **S**: about 15 lines in `_probe_kdc` plus one test. Unknown: whether impacket <0.13 raised for code 25
  (the `METHOD_DATA` import fallback at `kerberos_scanner.py:5-11` shows the module was written for impacket <0.13 too); the fix should
  handle both shapes. No spike needed.

## Resolution (Phase 230, 2026-10-23)

- Fix: `15e35662` decodes the KRB_ERROR that impacket 0.13 RETURNS for code 25 through one shared PA-ETYPE parser (the older raised shape still works), probes a configurable principal (`connectors.kerberos_probe_principal`, default `Administrator`; the old hard-coded `nobody` draws code 6 from a real KDC), and reports a code-6 reply as the honest `kerberos-etypes-unavailable-principal-unknown` row instead of `kerberos-no-preauth`.
- Proof is LOCAL-ONLY: `tests/test_kerberos_preauth_wire.py::TestKerberosPreauthWire` (8 passed locally with impacket 0.13.0) drives the real `sendReceive` against a fake KDC and skips in CI's Linux Full Suite (`ci_extras_gap`, registered in `tests/skip_registry.py`, D-07a); no `[identity]` CI leg was added (operator-reserved). `tests/test_kerberos_probe_principal_config.py` (10 passed) runs in CI. Fail-first: wire file 6 failed, 2 passed; three mutations each red.
- Real KDC, measured 2026-10-23 against the chaos-lab Samba AD DC (high-port override; host port 88 is held by the macOS KDC): `Administrator` -> KRB_ERROR 25 with etypes `[18]` only; `nobody` -> code 6; IP-literal realm `127.0.0.1` -> code 6. The lab oracle's RC4/AES128 HIGH rows were not reproducible and were rewritten (`f04f0501`).
- The "same root cause" premise in `kerberos-udp-probe-times-out-falls-back-to-tcp.md` was WRONG (D-08a): that log's TCP leg raised and the `kerberos-no-preauth` row came from `_probe_kdc_udp` returning `[]`. That todo is rewritten and the second false-no-preauth path filed as `261023-detect-kerberos-udp-failure-reads-as-no-preauth`.
- Docs: `40297bbd`, `f04f0501`. UAT-230-03, UAT-230-07.
- Follow-ups filed (not fixed here): `261023-detect-kerberos-udp-failure-reads-as-no-preauth`, `261023-detect-kerberos-ip-literal-target-used-as-realm`, `261023-detect-kerberos-placeholder-rows-count-as-assessed`, `261023-detect-kerberos-probe-principal-dashboard-parity`.
