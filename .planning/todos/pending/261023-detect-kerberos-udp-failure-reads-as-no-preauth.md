---
type: todo
created: 2026-10-23
source: Phase 230 DETECT-02 (plan 230-02 live KDC measurement; D-08a); supersedes the premise of kerberos-udp-probe-times-out-falls-back-to-tcp.md
priority: medium
area: quirk/scanner/kerberos_scanner.py (_probe_kdc_udp, scan_kerberos_targets), tests/test_kerberos_preauth_wire.py
status: pending
resolves_phase: null
owner: "999.132"
---

# A Kerberos UDP-fallback failure is reported as `kerberos-no-preauth`

DETECT-02 fixed the TCP path (a returned KRB_ERROR 25 now yields etypes). A SECOND path to the same false row is
still open and is NOT fixed in Phase 230 (new scope, D-08a).

`scan_kerberos_targets` runs the UDP probe only when the TCP probe raises (`quirk/scanner/kerberos_scanner.py:370-376`,
`except Exception` then `_probe_kdc_udp`). `_probe_kdc_udp` (`:222-258`) returns `[]` for every failure:

- a timeout or socket error (`:249-252`, "best-effort fallback");
- an undecodable reply (`:253-257`);
- any KRB_ERROR whose code is not 25 (`:246-247`), including code 6 (principal unknown).

The caller treats `[]` as "KDC answered without pre-auth" and records `service_detail="kerberos-no-preauth"`
(`:443`). So a transport failure, or a code-6 answer over UDP after a TCP transport failure, reads as "this KDC does
not require pre-authentication", the opposite of unknown.

## Live evidence (plan 230-02, 2026-10-23, chaos-lab Samba AD DC)

- The Samba KDC drops about one in three TCP connections with no reply (reproduced inside the container against
  127.0.0.1:88 and its eth0 IP, 6 empty of 18 each, so it is not Docker's port proxy). `_probe_kdc` then raises
  `struct.error`, the scanner falls to UDP, and for an unresolvable or foreign-held UDP target the probe returns `[]`:
  3 of 8 scans against `dc.quirk.lab` recorded `kerberos-no-preauth` for a KDC that does require pre-auth.
- Scanning `127.0.0.1` produced `kerberos-no-preauth` in 5 of 8 runs through the UDP fallback, which in that run hit
  the macOS KDC on 127.0.0.1:88/udp (environment contamination, not Samba behaviour).
- The 2026-09-17 `mh-kdc` observation in `kerberos-udp-probe-times-out-falls-back-to-tcp.md` is the same row from the
  same path.

## Fix shape (left to the owner)

Make UDP failure and non-25 codes surface as an error or "unavailable" row (a `scan_error`, or a row like
`kerberos-etypes-unavailable-*`), never `[]`. Decide how a code-6 UDP reply maps (it should mirror the TCP
`kerberos-etypes-unavailable-principal-unknown` row). Keep the genuine AS-REP "no pre-auth" row.

- [ ] Add a wire-level test: UDP timeout, undecodable reply and a code-6 reply each must NOT yield `kerberos-no-preauth`.
- [ ] Change `_probe_kdc_udp` (or its caller) so failure is distinguishable from "empty etype list".
- [ ] Update `docs/operators-guide.md` Kerberos section and the `docker-compose.yml` mh-kdc comment (which already names this todo).

## Feasibility & Effort

- **CONFIRMED** defect: `_probe_kdc_udp` lines `:246-257` return `[]`; the row is built at `:443`; live reproduction in 230-02 (3 of 8).
- **LIKELY** effort **S-M**: one return-contract change in `_probe_kdc_udp`, one caller branch, one wire test using the
  existing `_FakeKdc` (TCP only today, so a UDP listener is the added test cost).
- **UNKNOWN**: how many operators fall to UDP in practice (UDP only runs after a TCP raise), and whether any downstream
  reader depends on `kerberos-no-preauth` being produced from the UDP path.
- **Spike**: not needed.
