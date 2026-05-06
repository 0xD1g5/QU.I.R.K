# Phase 32 — Email Scanner Expected Results

**Lab:** Postfix + Dovecot (Docker Compose profile `email`)
**Phase:** 32 — Email TLS Scanner
**Requirements covered:** EMAIL-01 through EMAIL-12
**Last updated:** 2026-04-27
**Captured against:** sslyze 6.3.1 (primary path), Python 3.14, OpenSSL 3.x

## Lab Setup

Boot the dedicated email chaos profile:

```bash
make -C labs/email certs
docker compose --profile email --file quantum-chaos-enterprise-lab/docker-compose.yml up -d --build
```

Wait ~30s for both containers to report healthy:

```bash
docker compose --profile email --file quantum-chaos-enterprise-lab/docker-compose.yml ps
```

Expected status:

```
quirk-chaos-postfix-email   Up (healthy)   0.0.0.0:30025->25/tcp, 0.0.0.0:30465->465/tcp, 0.0.0.0:30587->587/tcp
quirk-chaos-dovecot-email   Up (healthy)   0.0.0.0:30110->110/tcp, 0.0.0.0:30143->143/tcp, 0.0.0.0:30993->993/tcp, 0.0.0.0:30995->995/tcp
```

## Port Map

| Host port | Container port | Service                 | Notes                                                  |
| --------- | -------------- | ----------------------- | ------------------------------------------------------ |
| 30025     | 25             | Postfix SMTP (STARTTLS) | starttls-downgrade-risk MEDIUM expected (when port 25) |
| 30465     | 465            | Postfix SMTPS           | implicit TLS                                           |
| 30587     | 587            | Postfix submission      | STARTTLS, port-587 (no downgrade-risk finding)         |
| 30143     | 143            | Dovecot IMAP (STARTTLS) | TLS 1.3 default — see Dovecot caveat                   |
| 30993     | 993            | Dovecot IMAPS           | implicit TLS — TLS 1.3 default                         |
| 30110     | 110            | Dovecot POP3 (STLS)     | TLS 1.3 default                                        |
| 30995     | 995            | Dovecot POP3S           | implicit TLS — TLS 1.3 default                         |

## Expected Scan Output

Captured live against the booted lab on 2026-04-27. The scanner is invoked
via `scan_one_email(host, host_port, label, starttls_enum, timeout, ...)`
(see "Reproducing" below for the recommended invocation).

| Host port | Protocol      | TLS version | Cipher suite                   | Cert subject               | Cert pubkey | PFS   |
| --------- | ------------- | ----------- | ------------------------------ | -------------------------- | ----------- | ----- |
| 30025     | SMTP-STARTTLS | TLSv1.2     | TLS_RSA_WITH_ARIA_256_GCM_SHA384 | CN=postfix.chaos.local     | RSA-2048    | False |
| 30465     | SMTPS         | TLSv1.2     | TLS_RSA_WITH_ARIA_256_GCM_SHA384 | CN=postfix.chaos.local     | RSA-2048    | False |
| 30587     | SMTP-STARTTLS | TLSv1.2     | TLS_RSA_WITH_ARIA_256_GCM_SHA384 | CN=postfix.chaos.local     | RSA-2048    | False |
| 30143     | IMAP-STARTTLS | TLSv1.3     | TLS_CHACHA20_POLY1305_SHA256   | CN=dovecot.chaos.local     | RSA-2048    | False*|
| 30993     | IMAPS         | TLSv1.3     | TLS_CHACHA20_POLY1305_SHA256   | CN=dovecot.chaos.local     | RSA-2048    | False*|
| 30110     | POP3-STARTTLS | TLSv1.3     | TLS_CHACHA20_POLY1305_SHA256   | CN=dovecot.chaos.local     | RSA-2048    | False*|
| 30995     | POP3S         | TLSv1.3     | TLS_CHACHA20_POLY1305_SHA256   | CN=dovecot.chaos.local     | RSA-2048    | False*|

\* Dovecot rows: `tls_pfs_supported=False` is reported by sslyze because the lab's
cipher allowlist contains no ECDHE/DHE suites. Under TLS 1.3 the scanner does NOT
emit a non-PFS finding (D-12 — TLS 1.3 always provides forward secrecy at the
protocol level via key-share, regardless of the legacy PFS flag).

All certs verified `Verify return code: 18 (self-signed certificate)` via
`openssl s_client`. Both certificates are RSA-2048, self-signed, 3650-day validity.

## Expected Findings

`evaluate_email_endpoints(endpoints)` returns 4 findings against the captured
endpoint list, **after** rewriting host ports back to standard ports
(30025→25, 30465→465, 30587→587 — the EMAIL-08 STARTTLS-downgrade gate keys
on `port == 25`):

| Severity | Title                                     | Host      | Port | Source         |
| -------- | ----------------------------------------- | --------- | ---- | -------------- |
| MEDIUM   | STARTTLS downgrade risk on SMTP           | localhost | 25   | EMAIL-08       |
| HIGH     | Weak cipher suite on email TLS endpoint   | localhost | 25   | EMAIL-09       |
| HIGH     | Weak cipher suite on email TLS endpoint   | localhost | 465  | EMAIL-09       |
| HIGH     | Weak cipher suite on email TLS endpoint   | localhost | 587  | EMAIL-09       |

**Severity counts:** HIGH = 3, MEDIUM = 1.
**D-11 layering verified:** port 25 emits BOTH the STARTTLS-downgrade MEDIUM AND
the weak-cipher HIGH because the (host, port, title) dedup keys differ.

In addition, the main `evaluate_endpoints()` pass over the same endpoints emits
generic certificate findings sourced from `risk_engine`'s X.509 inspection:

| Severity | Title                                     | Source                                                    |
| -------- | ----------------------------------------- | --------------------------------------------------------- |
| HIGH     | Self-signed certificate                   | risk_engine generic cert-validation finding (one per port)|

(Self-signed findings are emitted by the main TLS pipeline, not by
`evaluate_email_endpoints`; severity may be HIGH or MEDIUM depending on the
risk_engine's policy version. See `quirk/engine/risk_engine.py::evaluate_endpoints`.)

## Caveats

### Dovecot 2.3.16 default TLS 1.3

Dovecot 2.3.16 (Ubuntu 22.04 stock) calls `SSL_CTX_set_min_proto_version()`
based on `ssl_min_protocol = TLSv1.2` but never calls
`set_max_proto_version()`. As a result Dovecot defaults to TLS 1.3 when the
client offers it. The lab's cipher excludes (no ECDHE/DHE) only apply to the
TLS 1.2 path; under TLS 1.3 OpenSSL's default cipher suites
(TLS_CHACHA20_POLY1305_SHA256 etc.) are negotiated regardless.

**Impact on findings:** Dovecot ports (30143/30993/30110/30995) emit NO
weak-cipher findings under default scan invocation because the default
negotiation picks TLS 1.3. The Postfix ports (which hard-cap
`smtpd_tls_protocols = TLSv1.2`) do emit the weak-cipher HIGH findings.

**To exercise the TLS 1.2 weak-cipher path on Dovecot:** pin client to TLS 1.2
explicitly (`openssl s_client -tls1_2 -cipher AES256-SHA …`). The lab serves
RSA-AES256-SHA / RSA-AES128-SHA in that case — exactly the weak path the
scanner detects when its enumeration walks TLS 1.2.

See `.planning/phases/32-email-scanner/32-05-SUMMARY.md` "Known Limitation —
Dovecot TLS 1.3 default" for the full rationale.

### OpenSSL 3.x TLS 1.0/1.1 limitation

The scanner host's OpenSSL 3.x library refuses to negotiate TLS 1.0 or TLS 1.1
even when the server offers them. This lab is configured
`ssl_min_protocol = TLSv1.2` to keep behavior deterministic — TLS-1.0/1.1
detection is NOT a Phase 32 expectation. (See
`.planning/phases/32-email-scanner/32-RESEARCH.md` "Pitfall 3".)

### Port 25 cloud egress

If the lab is run on a cloud VM where outbound TCP 25 is blocked, the scanner
reports `tls_blocker_reason: CONNECTION_REFUSED` for that endpoint and does
not emit findings — this is correct behavior per D-03.

### Layered findings on port 25 / 30025

A single port-25 endpoint emits BOTH a MEDIUM downgrade-risk finding AND a
HIGH weak-cipher finding (per D-11). The dashboard's `_dedupe_findings` does
NOT collapse these because they have distinct titles. This is intentional.

### sslyze required for full enumeration

The scanner has two paths:

1. **sslyze (primary):** enumerates ciphers regardless of client preferences.
   Detects RSA-only suites Postfix offers (TLS_RSA_WITH_ARIA_256_GCM_SHA384,
   AES128-SHA, AES256-SHA).

2. **stdlib fallback (secondary):** uses `ssl.create_default_context()`,
   which on modern Python (3.10+) excludes RSA-kex and other weak suites
   from the client's offer list. **Result: stdlib fallback CANNOT see
   Postfix's weak ciphers** — handshake fails with
   `SSLV3_ALERT_HANDSHAKE_FAILURE` and the endpoint records a `scan_error`
   instead of a cipher.

For consulting / regression validation, ensure sslyze is installed
(`pip install sslyze` or `pip install -e .[motion]`) before running the
expected-results comparison.

### Port mapping (lab vs. scanner)

The scanner's `EMAIL_PORTS` table is hardcoded to standard email ports
(25, 465, 587, 143, 993, 110, 995). The chaos lab maps host ports
30025…30995 → container 25…995 to avoid privileged-port binding on macOS.

For end-to-end run via `run_scan.py`, the scanner targets `localhost:25`
etc. — which on macOS without sudo is closed. Two reproducible paths:

- **(recommended) Direct invocation** of `scan_one_email()` with host_port
  arguments — captures the scanner's behavior on the live lab without
  requiring privileged-port forwarding. Used to capture this document.
- **Privileged port forwarding** (`socat tcp-listen:25,fork tcp:localhost:30025`
  with sudo) so `run_scan.py` exercises the full pipeline.

A future plan should consider parameterizing `EMAIL_PORTS` so the scanner can
target non-standard ports without privileged forwarding (tracked as a
Phase-32 followup item — not blocking for EMAIL-12).

## Reproducing

The sanctioned consulting/CI invocation is the full pipeline:

```bash
quirk scan --target localhost --profile standard
# Or, equivalent: any invocation that triggers cfg.connectors.enable_email = True
# Requires: sudo socat to forward 25/465/587/143/993/110/995 → 30025/...
```

For lab-only validation (no privileged ports needed), invoke the scanner
module directly with host-port arguments:

```python
from quirk.scanner.email_scanner import (
    scan_one_email, ProtocolWithOpportunisticTlsEnum,
)
from quirk.engine.risk_engine import evaluate_email_endpoints

LAB_PORTS = [
    (30025, "SMTP-STARTTLS", ProtocolWithOpportunisticTlsEnum.SMTP),
    (30465, "SMTPS",         None),
    (30587, "SMTP-STARTTLS", ProtocolWithOpportunisticTlsEnum.SMTP),
    (30143, "IMAP-STARTTLS", ProtocolWithOpportunisticTlsEnum.IMAP),
    (30993, "IMAPS",         None),
    (30110, "POP3-STARTTLS", ProtocolWithOpportunisticTlsEnum.POP3),
    (30995, "POP3S",         None),
]
endpoints = [
    scan_one_email("localhost", port, label, starttls, timeout=8)
    for port, label, starttls in LAB_PORTS
]
# Optional: rewrite host ports → standard ports so EMAIL-08 (port==25 gate) fires
LAB_TO_STD = {30025: 25, 30465: 465, 30587: 587, 30143: 143, 30993: 993, 30110: 110, 30995: 995}
import copy
mapped = [copy.copy(e) for e in endpoints]
for e in mapped:
    e.port = LAB_TO_STD.get(e.port, e.port)
print(evaluate_email_endpoints(mapped))
```

The findings should match this document within the noise of timestamp /
scan_id fields. If a finding is MISSING that this document specifies, treat
as a regression in the scanner. If an UNEXPECTED finding appears, update
this document if the new finding is correct, or fix the scanner if not.

## Tear-Down

```bash
docker compose --profile email --file quantum-chaos-enterprise-lab/docker-compose.yml down
```
