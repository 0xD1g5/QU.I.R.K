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

## Advisory-Only Note

Hardware findings do not enter `SCORE_WEIGHTS` or `compute_readiness_score()` (D-01).
They appear in the advisory section of the QUIRK report only.

The hwcompat lab profile validates both code paths in `hardware_scanner.py`:
1. **Unknown path** (hwcompat-ssh): unrecognized banner → `vendor=Unknown`, never suppressed
2. **Known-vendor path** (hwcompat-http): HTTP header match → `vendor=HPE`, `model=iLO5`

---

## Image Notes

| Service | Image | Tag | CHAOS-05 Compliant |
|---------|-------|-----|---------------------|
| hwcompat-ssh | lscr.io/linuxserver/openssh-server | 10.2_p1-r0-ls225 | Yes (pinned) |
| hwcompat-http | nginx | 1.28.0 | Yes (pinned) |
