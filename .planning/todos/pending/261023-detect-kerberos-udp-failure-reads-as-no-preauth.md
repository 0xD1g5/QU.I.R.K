---
type: todo
created: 2026-10-23
source: Phase 230 DETECT-02 (plan 230-02 live KDC measurement; D-08a); supersedes the premise of kerberos-udp-probe-times-out-falls-back-to-tcp.md
priority: high
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

## Live re-measurement 2026-10-23 (round 3)

Source: 230-REVIEW-R3 family 5 (independent reviewer). Only `samba-dc` was started, mapped to `127.0.0.1:18088`
(tcp and udp). The real `_probe_kdc` and the real `scan_kerberos_targets` ran with `KDC_PORT=18088`, so the UDP leg was
real and went through Docker Desktop's UDP proxy. `timeout=3`. Raw output: `live_run1.txt` (n=10) and `live_run2.txt`
(n=20) in the round-3 scratch directory. The code was at `17767cf9` (QUIRK-framed TCP, before the round-3 fixes).

- **TCP drops are about half, not one in three.** Every drop had the same shape: zero bytes, then FIN, which is
  `KerberosTransportError(answered=False)`, "closed the connection after 0 of 4 reply bytes". Direct `_probe_kdc` series:
  run 1 5/10, 5/10 and 7/10; run 2 10/20, 10/20 and 5/20. Overall 42 of 90, about 47%.
- **False `kerberos-no-preauth` rate (run 2, n=20):** Administrator in realm `QUIRK.LAB` gave 7/20 (run 1: 5/10).
  `nobody` gave 12/20 (run 1: 3/10). The IP-realm scan (n=1) gave it once in run 2.
- **Every false row came from the UDP leg.** None came directly from TCP. Two UDP causes: (a) a Docker Desktop UDP
  proxy timeout (16 `KDC UDP probe transport failed ... timed out` log lines in run 2), and (b) a code-6
  (principal-unknown) answer over UDP. Case (b) returns `[]` **with no log line at all**, because
  `_probe_kdc_udp` returns `[]` for any non-25 code without logging. In the `nobody` run, 4 of the 12 false rows had no
  log.
- **What the false row does.** The `kerberos-no-preauth` placeholder has `cert_pubkey_alg=None`, so no severity is
  attached. `_derive_identity_findings` derives no finding for it (re-checked 2026-10-23: returns `[]`). Its
  `service_detail` still states that this KDC answered the probe principal without requiring pre-authentication. That
  claim means the principal is AS-REP-roastable, and it is false for this KDC. It also counts as assessed (see
  `261023-detect-kerberos-placeholder-rows-count-as-assessed`).
- **Priority raised to high.** The rate is 35-60% per scan on the lab. The mislabel is the opposite of the truth.

Round-3 mitigation (fix commits on `v528-open`, not a fix for this todo). The TCP probe is now retried once after a
zero-byte close or reset, before UDP. At a ~50% independent drop rate, that should cut UDP entries to about 25%.
This has not been re-measured live. UDP `[]` semantics are unchanged; this todo still owns them.

UDP is now reached only on these paths (completed in 230-REVIEW-R4 WR-02/IN-02; the same set as the operators guide
and the lab oracle):
- a TCP connect failure (refused, timed out, unreachable, or a name that does not resolve);
- a silent peer, or a send failure;
- any other socket error before the first reply byte (`kind="error"`, e.g. EHOSTUNREACH after connect);
- a zero-byte close or reset after which the one retry also gets no reply byte (it closes, resets, runs out of the
  remaining deadline, or fails to connect, send or read), or that cannot be retried: under 0.25 s of the first
  attempt's reply deadline left (R4 WR-01: the retry shares that deadline), or the address the first attempt reached
  is unknown (230-REVIEW-R5: the retry connects only to that address);
- a KRB_ERROR whose code is not 25 or 6.

An unresolvable name reaches UDP, whose `sendto` fails the same way and returns `[]`, so it too reads as
`kerberos-no-preauth` today.

Any decoder exception on a TCP reply now gets the honest unrecognised-reply row and never reaches UDP (230-REVIEW-R3
WR-01).

### Also in scope: UDP probe is IPv4-only (230-REVIEW-R3 IN-04)

The TCP probe handles IPv6: the first attempt uses `socket.create_connection` (any family), and the one retry reconnects to the full recorded 4-tuple sockaddr in `AF_INET6`, so a scoped link-local KDC keeps its `scope_id` (230-REVIEW-R6 WR-01). `_probe_kdc_udp` hardcodes
`socket.AF_INET`, so `_probe_kdc_udp('::1', ...)` fails with `[Errno 8] nodename nor servname` and returns `[]`. An
IPv6 target therefore reaches this defect on every TCP outcome that falls back to UDP. This predates round 2. The fix
belongs with this todo's UDP return-contract change: resolve with `getaddrinfo` and use the returned family.

- [ ] UDP probe resolves the address family (`getaddrinfo`) instead of hardcoding `AF_INET`; add an IPv6 loopback test.
- [ ] A code-6 UDP reply logs, and maps to the principal-unknown row (mirrors TCP), not `[]`.
