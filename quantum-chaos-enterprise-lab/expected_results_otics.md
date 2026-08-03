# Expected Scanner Results — otics Oracle

**Profile:** `otics`
**Phase:** 141 — OT/ICS Fingerprinting (Modbus + BACnet)
**Requirement:** OTICS-04 (chaos-lab profile validates both scanners end-to-end)
**Status:** Authoritative oracle for Phase 141 `otics` chaos lab validation.

Hardware findings (including Modbus/BACnet) are **advisory-only** — no score impact (D-01,
inherited from the hwcompat/SNMP precedent).
`vendor=Unknown`/not-attempted rows are **never suppressed** (D-06 precedent).

Host assumed: `127.0.0.1`

## How to Run

```bash
PROFILE_ARGS="--profile otics" ./lab.sh up
```

---

## Services

| Service | Host Port | Container Port | Protocol | Purpose |
|---------|-----------|-----------------|----------|---------|
| otics-modbus | 502 | 502 | Modbus/TCP | Fragile Schneider Electric M221 PLC simulator — FC 43/14 Read Device Identification |
| otics-bacnet | 47808 | 47808/udp | BACnet/IP | Fragile Johnson Controls FX16 field controller simulator — Who-Is/I-Am + ReadProperty |

Both containers are **behaviorally fragile by design** (D-10): a second concurrent probe or a
malformed frame is reset/dropped immediately rather than served, so the scanner's own D-05
one-strike circuit breaker and OTICS-03 single-in-flight guarantee are what keep these
simulators healthy — not a well-behaved responder that only exercises the identification path.

---

## Scan Command

```bash
python run_scan.py --target 127.0.0.1 --enable-modbus --enable-bacnet
```

(Add `--allow-internal-targets` if the loopback-bind guard requires it, per prior lab runs.)

---

## otics-modbus — Port 502/TCP (Modbus, Schneider Electric M221)

**Expected result:**

| Field | Expected Value |
|-------|-----------------|
| host | 127.0.0.1 |
| port | 502 |
| modbus_vendor | Schneider Electric |
| modbus_model | M221 |
| modbus_firmware | 1.6.2.0 |
| modbus_probe_state | identified |

**Rationale:**
The simulator answers FC 43/14 Read Device Identification (Basic category, `read_code=0x01`,
`object_id=0x00`) with three Basic-category objects: VendorName=`Schneider Electric`,
ProductCode=`M221`, MajorMinorRevision=`1.6.2.0`. `quirk/scanner/modbus_scanner.py` maps
object 0 -> `modbus_vendor`, object 1 -> `modbus_model`, object 2 -> `modbus_firmware`. Since
`modbus_vendor` is non-empty, `modbus_probe_state="identified"`.

This is the port-gated (D-04) Step 4 waterfall entry: `enable_modbus=True AND 502 in
confirmed_open_ports[host]` must both hold for the probe to fire — i.e. port 502 confirmed open
for that host by the existing port/service scan, not the SSH endpoint's own port (fixed in
141-08/141-11; see live-validation note below).

**Live-validation note (2026-08-03):** Re-validated end-to-end against the real `otics-modbus`
Docker container after 141-11's outer-gate fix landed, running `python run_scan.py
--enable-modbus --enable-bacnet --allow-internal-targets` against a host with **zero** SSH
candidates (`TLS candidates: 5 | SSH candidates: 0 | Other inventory: 13`). Hardware
fingerprinting still ran (`Starting hardware fingerprint: 1 endpoints` /
`hardware fingerprint complete: 1/1 identified` / `Hardware fingerprint: 1 device(s) recorded`)
and the database (`hardware_devices`, id=2, host=127.0.0.1, scanned_at=2026-08-03 14:32:28)
recorded `modbus_vendor=Schneider Electric`, `modbus_model=M221`, `modbus_probe_state=identified`
— matching this oracle exactly. This is a stronger proof than the original 141-07 validation,
which (per 141-10-RESEARCH.md) accidentally relied on an incidental SSH endpoint riding along.

---

## otics-bacnet — Port 47808/UDP (BACnet, Johnson Controls FX16)

**Expected result:**

| Field | Expected Value |
|-------|-----------------|
| host | 127.0.0.1 |
| port | 47808 |
| bacnet_vendor | 5 (Johnson Controls' registered BACnet vendor ID) |
| bacnet_model | FX16 |
| bacnet_firmware | 9.0.1 |
| bacnet_probe_state | identified |

**Rationale:**
The simulator answers a directed-unicast Who-Is with I-Am (`vendorID=5`), then answers
`ReadProperty(model-name)` -> `FX16` and `ReadProperty(firmware-revision)` -> `9.0.1` on the
Device object. `quirk/scanner/bacnet_scanner.py`'s Step 5 gates on `enable_bacnet` alone — the
Who-Is/I-Am round trip itself is the D-04 port-gating confirmation for this UDP-only protocol
(no TCP-scan equivalent exists). Since `bacnet_vendor` is non-empty,
`bacnet_probe_state="identified"`.

**Live-validation note (2026-08-03):** Re-confirmed in the same 141-09 live run described in the
Modbus section above — `bacnet_vendor=5`, `bacnet_model=FX16`, `bacnet_probe_state=identified`
against a host with zero SSH candidates, alongside the Modbus identification.

---

## Fragility / Circuit-Breaker Empirical Validation (D-10, OTICS-03)

Both simulators enforce two fragility rules that the scanner's own safety model must satisfy
without ever tripping them:

1. **Single in-flight only** — a second concurrent Modbus TCP connection (or a second BACnet
   Who-Is/ReadProperty datagram) arriving while one is already being served is reset
   (Modbus: TCP connection closed with no response) or dropped (BACnet: UDP datagram silently
   discarded — the connectionless analog of a reset). OTICS-03 requires the scanner to never
   issue more than one in-flight probe per host, so a correct scanner run against these
   simulators never triggers this path from its own traffic.
2. **Malformed-input reset/drop** — Modbus: any inbound byte stream whose MBAP header has a
   non-zero protocol identifier or an implausible length field is reset immediately, never
   forwarded to the real device-identification logic. BACnet: any inbound datagram that does
   not carry a valid BVLC header (leading byte `0x81`) is dropped before it reaches the real
   Application. A correct scanner (which only ever sends well-formed FC 43/14 / Who-Is
   requests) never triggers this path either.

**Expected forced-concurrent-probe outcome (manual verification, Task 3):** if a human
deliberately opens a second connection/sends a second datagram to either simulator while the
scanner's own probe is in flight, the *scanner's own* one-strike circuit breaker (D-05) records
`modbus_probe_state="aborted_anomalous_response"` or `bacnet_probe_state="aborted_anomalous_response"`
for that probe attempt if the anomalous response reaches it (e.g. an unexpected connection reset
mid-exchange) — this is the distinct abort state (D-13), never masquerading as
`"no_response"`/`"not attempted"`.

---

## Advisory-Only Note

Modbus/BACnet hardware findings do not enter `SCORE_WEIGHTS` or `compute_readiness_score()`
(D-01 precedent, inherited unchanged from SSH/HTTP/SNMP hardware fingerprinting). They appear
in the advisory hardware section of the QUIRK report only, alongside the existing SNMP/Bridge
badges (D-12 — distinct Modbus/BACnet badge columns identify the protocol source at a glance).

---

## Image Notes

| Service | Image | Tag | CHAOS-05 Compliant |
|---------|-------|-----|---------------------|
| otics-modbus | local build (`./otics-modbus/`) | FROM python:3.12-slim | Yes (pinned base image in Dockerfile) |
| otics-bacnet | local build (`./otics-bacnet/`) | FROM python:3.12-slim | Yes (pinned base image in Dockerfile) |

---

## Architecture Note

Each simulator is a small asyncio "gatekeeper" (custom code, enforcing only the D-10 admission
policy) in front of a real protocol-library server: `pymodbus`'s `ModbusTcpServer` handles all
actual Modbus/TCP MBAP/PDU framing and FC 43/14 encode/decode for `otics-modbus`; a real
`bacpypes3` `Application` handles all actual BVLC/NPDU/APDU framing and Who-Is/I-Am/ReadProperty
for `otics-bacnet`. Neither module hand-rolls the underlying protocol — only the raw-socket
fragility admission layer (single-in-flight tracking + malformed-header rejection) is custom,
matching CLAUDE.md's "Don't Hand-Roll" spirit for anything the vetted libraries already do
correctly.
