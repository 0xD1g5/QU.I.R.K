# Expected Scanner Results — hwcompat Oracle

**Profile:** `hwcompat`
**Phase:** 127 — Hardware Fingerprinting Foundation
**Requirement:** HWCOMPAT-02 (lab-validated fingerprinting)
**Status:** Authoritative oracle for Phase 127 hwcompat chaos lab validation.

Hardware findings are **advisory-only** — no score impact (D-01).
`vendor=Unknown` rows are **never suppressed** (D-06).

Host assumed: `127.0.0.1`

## How to Run

```bash
PROFILE_ARGS="--profile hwcompat" ./lab.sh up
```

---

## Services

| Service | Host Port | Container Port | Protocol | Purpose |
|---------|-----------|----------------|----------|---------|
| hwcompat-ssh | 20221 | 2222 | SSH | OpenSSH banner — unrecognized pattern → vendor=Unknown |
| hwcompat-http | 20222 | 80 | HTTP | HPE-iLO5 management headers → vendor=HPE, model=iLO5 |
| hwcompat-snmp | 20223 | 161/udp | SNMP | Cisco IOS sysDescr → vendor=Cisco, fingerprint_method=snmp |

---

## Profile: hwcompat

```bash
PROFILE_ARGS="--profile hwcompat" ./lab.sh up
```

### hwcompat-ssh — Port 20221 (SSH, Unknown-vendor path)

**Expected result:**

| Field | Expected Value |
|-------|---------------|
| host | 127.0.0.1 |
| port | 20221 |
| vendor | Unknown |
| model | null |
| fingerprint_method | ssh_banner |
| confidence | unknown |
| pqc_status | unknown |
| eol_date | null |

**Rationale:**
The `lscr.io/linuxserver/openssh-server:10.2_p1-r0-ls225` image emits a banner of the form
`SSH-2.0-OpenSSH_9.x` (or similar generic OpenSSH version string). No entry in `HARDWARE_MATRIX`
matches this generic pattern — Cisco, Juniper, HPE, and Palo Alto entries require vendor-specific
substrings in the SSH version string that OpenSSH does not include.

Result: `vendor="Unknown"`, `confidence="unknown"`, `fingerprint_method="ssh_banner"`.

Per D-06, `vendor=Unknown` rows are **never suppressed** — operators see this device in the
advisory report so they can track unidentified endpoints in their environment.

This service exercises the **unknown-banner code path** (unrecognized SSH banner → fallback Unknown).
A future phase can substitute a custom-built container with a spoofed Cisco banner string
(`SSH-2.0-Cisco-1.25`) for high-confidence positive-path Cisco testing.

---

### hwcompat-http — Port 20222 (HTTP, HPE positive-vendor path)

**Expected result:**

| Field | Expected Value |
|-------|---------------|
| host | 127.0.0.1 |
| port | 20222 |
| vendor | HPE |
| model | iLO5 |
| fingerprint_method | http_mgmt |
| confidence | high |
| pqc_status | unsupported |
| eol_date | (per HARDWARE_MATRIX HPE-iLO5 entry) |

**Rationale:**
The nginx container serves the following headers on `http://127.0.0.1:20222/`:
- `X-Device-Model: HPE-iLO5`
- `Server: iLO/5.0`
- HTML `<title>HPE Integrated Lights-Out 5</title>`

The `/api/system/info` endpoint returns JSON: `{"model":"HPE-iLO5","vendor":"HPE","version":"5.0.0"}`.

The `HARDWARE_MATRIX` HPE-iLO5 entry matches on `X-Device-Model: HPE-iLO5` header →
`vendor="HPE"`, `model="iLO5"`, `confidence="high"` (exact model matched from HTTP header),
`fingerprint_method="http_mgmt"`.

HPE iLO 5 does not support PQC algorithms → `pqc_status="unsupported"`.
`eol_date` is populated from the `HARDWARE_MATRIX` HPE-iLO5 entry per `hardware_meta.py`.

This service exercises the **known-vendor positive code path** (HTTP management header match → HPE).

---

### hwcompat-snmp — Port 20223/UDP (SNMP, Cisco positive-vendor path)

**Expected result:**

| Field | Expected Value |
|-------|---------------|
| host | 127.0.0.1 |
| port | 20223 |
| vendor | Cisco |
| model | (per HARDWARE_MATRIX Cisco IOS entry, or null if not mapped) |
| fingerprint_method | snmp |
| confidence | high |
| pqc_status | unsupported |
| eol_date | (per HARDWARE_MATRIX Cisco IOS 15.x entry) |

**sysDescr OID (1.3.6.1.2.1.1.1.0):** `"Cisco IOS Software, Version 15.2(4)M3, RELEASE SOFTWARE (fc2)"`
**sysName OID (1.3.6.1.2.1.1.5.0):** `"cisco-sim-hwcompat"`
**sysObjectID OID (1.3.6.1.2.1.1.2.0):** `1.3.6.1.4.1.9.1.1` (Cisco Enterprise OID)

**Rationale:**
The Net-SNMP container (alpine:3.19 + net-snmp) serves the standard SNMP MIB-II OIDs on UDP port 161
(mapped to host port 20223). The sysDescr string `"Cisco IOS Software, Version 15.2(4)M3..."` matches
the `HARDWARE_MATRIX` Cisco pattern (substring `"Cisco IOS Software"` or vendor OID prefix `1.3.6.1.4.1.9`).

The scanner (queried with `--enable-snmp --snmp-community public`) retrieves sysDescr via GET
on OID `1.3.6.1.2.1.1.1.0` → `vendor="Cisco"`, `fingerprint_method="snmp"`, `confidence="high"`.

Cisco IOS 15.2 does not support PQC algorithms → `pqc_status="unsupported"`.

This service exercises the **SNMP positive code path** (sysDescr OID match → Cisco vendor detection).
Scan command:
```bash
python run_scan.py --target 127.0.0.1 --ports 20223 --enable-snmp --snmp-community public
```

**Community string:** `public` (read-only, hardcoded in snmpd.conf for lab-only use)
**Build:** Local (`build: ./hwcompat-snmp/`), `FROM alpine:3.19` — CHAOS-05 compliant (pinned base image)

---

## CBOM Component Hierarchy

As of Phase 134 (CBOM-01), each hardware endpoint in the CBOM is represented as a
**DEVICE → FIRMWARE** component pair rather than a flat FIRMWARE component.

### Structure

```
ComponentType.DEVICE  (identity/summary layer)
  bom_ref:    hw/device/{host}:{port}
  name:       "{vendor} {model}"  e.g. "Cisco ASA-5506"
              (fallback: "Unknown Device at {host}:{port}" when both vendor and model are "Unknown")
  properties: quirk:hw-tier = remediation_tier value
  components:
    ComponentType.FIRMWARE  (operational-detail layer)
      bom_ref:    hw/firmware/{host}:{port}
      name:       hw:{host}:{port}  (IPv6: hw:[{host}]:{port})
      properties: quirk:hw-vendor
                  quirk:hw-model
                  quirk:hw-pqc-supported
                  quirk:hw-remediation-tier
                  quirk:hw-bridge-status   (conditional — only when bridge_status is non-null)
                  quirk:hw-snmp-oid        (conditional — only when snmp_sysdescr is non-null)
```

### Example (hwcompat-http HPE iLO5)

DEVICE bom_ref: `hw/device/127.0.0.1:20222`
DEVICE name: `HPE iLO5`
FIRMWARE bom_ref: `hw/firmware/127.0.0.1:20222`
FIRMWARE name: `hw:127.0.0.1:20222`

### Example (hwcompat-snmp Cisco IOS)

DEVICE bom_ref: `hw/device/127.0.0.1:20223`
DEVICE name: `Cisco <model>` (or model from HARDWARE_MATRIX Cisco entry)
FIRMWARE bom_ref: `hw/firmware/127.0.0.1:20223`
FIRMWARE name: `hw:127.0.0.1:20223`
FIRMWARE property `quirk:hw-snmp-oid`: `1.3.6.1.4.1.9.1.1` (Cisco Enterprise OID)

### Example (hwcompat-ssh Unknown vendor)

DEVICE bom_ref: `hw/device/127.0.0.1:20221`
DEVICE name: `Unknown Device at 127.0.0.1:20221`
FIRMWARE bom_ref: `hw/firmware/127.0.0.1:20221`
FIRMWARE name: `hw:127.0.0.1:20221`

---

## Advisory-Only Note

Hardware findings do not enter `SCORE_WEIGHTS` or `compute_readiness_score()` (D-01).
They appear in the advisory section of the QUIRK report only.

The hwcompat lab profile validates all three code paths in `hardware_scanner.py`:
1. **Unknown path** (hwcompat-ssh): unrecognized banner → `vendor=Unknown`, never suppressed
2. **Known-vendor path via HTTP** (hwcompat-http): HTTP header match → `vendor=HPE`, `model=iLO5`
3. **Known-vendor path via SNMP** (hwcompat-snmp): sysDescr OID match → `vendor=Cisco`, `fingerprint_method=snmp`

---

## Image Notes

| Service | Image | Tag | CHAOS-05 Compliant |
|---------|-------|-----|---------------------|
| hwcompat-ssh | lscr.io/linuxserver/openssh-server | 10.2_p1-r0-ls225 | Yes (pinned) |
| hwcompat-http | nginx | 1.28.0 | Yes (pinned) |
| hwcompat-snmp | local build (`./hwcompat-snmp/`) | FROM alpine:3.19 | Yes (pinned base image in Dockerfile) |
