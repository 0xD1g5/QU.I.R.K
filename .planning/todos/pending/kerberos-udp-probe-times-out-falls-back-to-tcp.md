# Kerberos UDP AS-REQ probe times out against the lab KDC; enctype enumeration via UDP is unexercised

**Filed:** 2026-09-17 (demo-prep, multihost connector coverage)
**Priority:** P3 — the connector still produces a finding via TCP
**Status:** open, not diagnosed

## What happens

Scanning `mh-kdc` (10.80.0.42, Samba AD DC, realm QUIRK.LAB) logs:

```
KDC UDP probe transport failed for '10.80.0.42': timed out
Kerberos scan: 1 endpoints from 1 targets
```

The connector falls back to TCP, which succeeds, and records one `KERBEROS` endpoint with
`service_detail="kerberos-no-preauth"`. So the Identity tab is populated and the demo path works —
but whatever the UDP path would have enumerated (enctypes) is never exercised against this lab.

## What is known

- TCP 88 and 389 both answer from inside the subnet (`socket.connect` succeeds).
- A crude UDP probe (8 null bytes to :88) also timed out, but that proves little — a KDC would
  correctly drop a malformed datagram rather than reply, so this may be a bad test rather than
  evidence of a missing listener.
- `88/udp` is declared in the compose `expose:` block for documentation parity with the
  Dockerfile's `EXPOSE`. On a bridge network `expose` does not gate container-to-container
  traffic either way, so that declaration is not the cause.
- Not established: whether Samba is binding UDP 88 at all in this configuration, whether the
  connector's AS-REQ is malformed for this KDC, or whether something in the Docker bridge drops
  the datagram.

## Why it is P3

The finding the demo needs (`kerberos-no-preauth`) is produced. This is a coverage gap in the
lab's exercise of the connector, not a user-facing defect — but it means any future change to the
Kerberos UDP path has no lab coverage and would pass unnoticed.

## Suggested first step

`docker exec` into the KDC and check for a UDP 88 listener (`ss -lnup`, after installing
`iproute2` — the image has neither `ss` nor `netstat`). If Samba is not binding UDP, that is a
lab-config fix; if it is, the probe itself needs looking at.
