---
type: todo
created: 2026-09-17
source: demo-prep, multihost connector coverage; corrected by Phase 230 (D-08a)
priority: low
area: quirk/scanner/kerberos_scanner.py (scan_kerberos_targets, _probe_kdc_udp), quantum-chaos-enterprise-lab (mh-kdc)
status: pending
resolves_phase: null
owner: "999.132"
---

# Kerberos UDP AS-REQ probe times out against the lab KDC; the `kerberos-no-preauth` row came from the UDP path

**Filed:** 2026-09-17 (demo-prep, multihost connector coverage)
**Corrected:** 2026-10-23 (Phase 230, D-08a). The original text read the log as "the connector falls back to TCP, which
succeeds". That reading is **withdrawn**: it had the fallback direction backwards.
**Priority:** P3
**Status:** open, partly diagnosed. Cross-link: `261023-detect-kerberos-udp-failure-reads-as-no-preauth` (owns the defect).

## What happens

Scanning `mh-kdc` (10.80.0.42, Samba AD DC, realm QUIRK.LAB) logged:

```
KDC UDP probe transport failed for '10.80.0.42': timed out
Kerberos scan: 1 endpoints from 1 targets
```

and recorded one `KERBEROS` endpoint with `service_detail="kerberos-no-preauth"`.

What the code actually does (`quirk/scanner/kerberos_scanner.py`):

1. The UDP probe runs **only when the TCP probe raises** (`:370-376`: `except Exception` then `_probe_kdc_udp`). The UDP
   timeout in this log therefore means the TCP probe **raised**. The cause of the TCP raise was not captured. The most
   likely cause is a non-25 KRB_ERROR from a realm derived from an IP literal (`_derive_realm` uses the IP as the realm,
   `:95-97`), which a real KDC answers with code 6 (assumption, unverified for this lab run; measured on a Samba KDC in
   Phase 230, see `261023-detect-kerberos-ip-literal-target-used-as-realm`). A dropped TCP connection (Samba drops about
   one in three, measured in 230-02) is the other candidate.
2. `_probe_kdc_udp` returns `[]` on timeout or decode failure (`:249-257`), and the caller records `[]` as
   `kerberos-no-preauth` (`:443`). So the row in this log came from the UDP **failure**, not from a successful TCP
   exchange: a second false no-preauth path, distinct from DETECT-02 (a returned KRB_ERROR 25 on TCP, fixed in Phase 230
   commit `15e35662`).
3. The earlier claim that this log "matches" the DETECT-02 root cause is also wrong: DETECT-02 is the TCP path
   returning code 25, which never reaches UDP.

## What is known

- TCP 88 and 389 answer from inside the subnet (`socket.connect` succeeds).
- A crude UDP probe (8 null bytes to :88) timing out proves little: a KDC drops a malformed datagram.
- `88/udp` in the compose `expose:` block is documentation parity with the Dockerfile `EXPOSE` and does not gate
  container-to-container traffic.
- Not established: whether Samba binds UDP 88 in this configuration, and why the TCP probe raised in this run.

## Why it is P3

Only the lab demo path shows it. The product defect (UDP failure reads as no pre-auth) is owned by
`261023-detect-kerberos-udp-failure-reads-as-no-preauth`; this file remains as the lab observation and the UDP-listener question.

## Suggested first step

`docker exec` into the KDC and check for a UDP 88 listener (`ss -lnup`; the image has neither `ss` nor `netstat`, so
install `iproute2`). Capture the TCP exception on a re-run (log `tcp_error` at `scan_kerberos_targets`) so the cause of
the TCP raise is recorded rather than assumed.

## Update 2026-10-23 (Phase 230 plan 230-08)

The product defect this file cross-links, a UDP failure reading as `kerberos-no-preauth`, is fixed (fix commit
`2ec5319c`; todo `261023-detect-kerberos-udp-failure-reads-as-no-preauth` is closed). A UDP timeout like the one in the
2026-09-17 log now gives `kerberos-unreachable`. The same Samba image was re-measured through the `kerberos` profile
(65 live scans: UDP answered with etypes or principal-unknown in 8 of the 17 scans that used it; the rest timed out
through Docker Desktop's UDP proxy), so the image does bind UDP 88.

STILL OPEN, and the reason this stays pending: `mh-kdc` itself (10.80.0.42 on the multihost bridge network) was not
re-measured, so whether it binds UDP 88 and why its TCP probe raised in the 2026-09-17 run are still unknown. Next step is
unchanged: `docker exec` into the KDC for a UDP 88 listener and capture `tcp_error` on a re-run.
