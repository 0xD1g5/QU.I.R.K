# Research: RabbitMQ / AMQP TLS Scanning for QU.I.R.K. v4.4

**Researched:** 2026-04-27
**Milestone:** v4.4 Data in Motion
**Overall confidence:** HIGH (official RabbitMQ docs, sslyze docs, live verification against existing codebase)

---

## 1. RabbitMQ TLS Probe — Best Python Approach

### Verdict: Use sslyze `ServerScanRequest` to port 5671 as primary path, raw SSL socket as fallback

Port 5671 (AMQPS) is a **direct TLS** port — the TLS handshake begins immediately upon TCP connection, with no STARTTLS negotiation and no AMQP application-layer framing before the TLS record layer. This means sslyze works on port 5671 identically to how it works on port 443.

**Why sslyze wins over pika:**

| Approach | TLS Version | Cipher List | Cert Chain | Key Type | Auth Needed |
|----------|------------|-------------|------------|----------|-------------|
| sslyze `ServerScanRequest` | All versions (SSL2–TLS1.3) | Full accepted/rejected list | Yes, with chain depth | Yes | No |
| Raw `ssl.wrap_socket` | One version (negotiated) | One cipher (negotiated) | Yes (if verify=NONE) | Yes | No |
| `pika.BlockingConnection` | One version (negotiated) | One cipher | Indirectly | No | Yes — hits AMQP AUTH after TLS |

`pika` is the wrong tool for scanning. It opens a TCP connection, performs the TLS handshake, then immediately sends an AMQP 0-9-1 protocol header and enters the AMQP authentication exchange. RabbitMQ will close the connection within ~10 seconds if no AMQP auth completes. The TLS layer succeeds but the pika API surface doesn't expose cipher or cert details directly — you'd need to reach into the underlying socket. Use pika only if you need to verify the broker is *functionally* accepting AMQP connections after TLS.

**sslyze pattern — reuse the existing QUIRK integration verbatim:**

```python
from sslyze import (
    Scanner as SslyzeScanner,
    ServerScanRequest,
    ServerNetworkLocation,
    ServerNetworkConfiguration,
    ScanCommand,
    ScanCommandAttemptStatusEnum,
    ServerScanStatusEnum,
)

def scan_rabbitmq_tls(host: str, port: int = 5671, timeout: int = 10):
    """
    Probe AMQPS port. No StartTLS enum — port 5671 is direct TLS.
    No tls_opportunistic_encryption needed.
    """
    scan_request = ServerScanRequest(
        server_location=ServerNetworkLocation(hostname=host, port=port),
        network_configuration=ServerNetworkConfiguration(
            tls_server_name_indication=host,   # SNI for hostname; omit for IPs
            network_timeout=timeout,
        ),
        scan_commands={
            ScanCommand.CERTIFICATE_INFO,
            ScanCommand.SSL_2_0_CIPHER_SUITES,
            ScanCommand.SSL_3_0_CIPHER_SUITES,
            ScanCommand.TLS_1_0_CIPHER_SUITES,
            ScanCommand.TLS_1_1_CIPHER_SUITES,
            ScanCommand.TLS_1_2_CIPHER_SUITES,
            ScanCommand.TLS_1_3_CIPHER_SUITES,
            ScanCommand.ELLIPTIC_CURVES,
        },
    )
    scanner = SslyzeScanner(per_server_concurrent_connections_limit=2)
    scanner.queue_scans([scan_request])
    results = list(scanner.get_results())
    if not results:
        return None
    result = results[0]
    if result.scan_status != ServerScanStatusEnum.COMPLETED:
        return None   # port closed or not TLS
    return result.scan_result
```

**No `tls_opportunistic_encryption` parameter is needed.** That parameter is only for STARTTLS protocols (SMTP, IMAP, FTP, LDAP, Postgres, RDP, XMPP). AMQP 5671 is "raw TLS" — sslyze treats it identically to HTTPS on 443.

**sslyze ScanCommands available (v6.x):**
- `CERTIFICATE_INFO` — full cert chain, subject, issuer, SAN, sig alg, public key type/size, expiry, chain validation against Mozilla/Apple trust stores
- `SSL_2_0_CIPHER_SUITES`, `SSL_3_0_CIPHER_SUITES`, `TLS_1_0_CIPHER_SUITES`, `TLS_1_1_CIPHER_SUITES`, `TLS_1_2_CIPHER_SUITES`, `TLS_1_3_CIPHER_SUITES` — each returns `accepted_cipher_suites` (list) and `rejected_cipher_suites`
- `ELLIPTIC_CURVES` — list of supported named curves
- `ROBOT`, `HEARTBLEED`, `OPENSSL_CCS_INJECTION`, `SESSION_RENEGOTIATION` — vulnerability checks
- `TLS_FALLBACK_SCSV`, `TLS_COMPRESSION`, `TLS_EXTENDED_MASTER_SECRET`

**Recommended minimum command set for broker scanner:**

```python
scan_commands = {
    ScanCommand.CERTIFICATE_INFO,
    ScanCommand.TLS_1_0_CIPHER_SUITES,
    ScanCommand.TLS_1_1_CIPHER_SUITES,
    ScanCommand.TLS_1_2_CIPHER_SUITES,
    ScanCommand.TLS_1_3_CIPHER_SUITES,
    ScanCommand.ELLIPTIC_CURVES,
}
# SSL 2.0/3.0 optional — RabbitMQ on modern Erlang (26+) rejects them at the
# server side anyway, but including them costs little and catches ancient brokers.
```

**Fallback (when sslyze unavailable):** Use `ssl.create_default_context()` with `CERT_NONE` and `wrap_socket()` to port 5671 — same pattern already in `tls_capabilities.py`. This gives one negotiated version and one cipher suite.

**Data available without credentials:**
- Full TLS certificate (subject, issuer, SAN, expiry, sig alg, pubkey type/size)
- All supported TLS versions and cipher suites
- Elliptic curve support
- RabbitMQ broker version is NOT exposed at TLS layer (need management API or AMQP banner for that)

**What happens to the connection after TLS:** RabbitMQ expects an AMQP protocol header within ~10 seconds. sslyze completes its scan and disconnects cleanly before that window expires, so there is no error on the broker side in normal operation.

---

## 2. RabbitMQ Management API

### Verdict: All endpoints require HTTP Basic Auth — no unauthenticated reads. Use with default guest:guest as best-effort.

The RabbitMQ Management HTTP API (port 15672) uses HTTP Basic Authentication for every endpoint. There are no documented unauthenticated endpoints, including health checks. The `/api/health/checks/*` family all return 401 without credentials.

**What the API exposes with credentials:**

| Endpoint | Returns | Relevant to scanner |
|----------|---------|---------------------|
| `GET /api/overview` | Listeners (non-HTTP), cluster name, RabbitMQ + Erlang versions, ssl_options | YES — listener list shows port 5672/5671 active |
| `GET /api/nodes` | Per-node listeners, ssl config, socket stats | YES — ssl_options per node |
| `GET /api/health/checks/certificate-expiration/1/days` | Cert expiry check | Indirect |
| `GET /api/listeners` | All active listeners across cluster | YES — most direct |

**`/api/overview` listener example (authenticated):**

```json
{
  "listeners": [
    {"node": "rabbit@host", "protocol": "amqp", "ip_address": "0.0.0.0", "port": 5672},
    {"node": "rabbit@host", "protocol": "amqp/ssl", "ip_address": "0.0.0.0", "port": 5671}
  ]
}
```

**Scanner strategy:**

```python
import requests
from requests.auth import HTTPBasicAuth

def probe_management_api(
    host: str,
    mgmt_port: int = 15672,
    username: str = "guest",
    password: str = "guest",
    timeout: int = 5,
) -> dict | None:
    """
    Best-effort management API probe. Returns None on connection error or auth failure.
    Default guest:guest works on fresh/dev RabbitMQ installs.
    """
    url = f"http://{host}:{mgmt_port}/api/overview"
    try:
        resp = requests.get(url, auth=HTTPBasicAuth(username, password), timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            listeners = data.get("listeners", [])
            has_plaintext = any(
                ln.get("protocol") == "amqp" for ln in listeners
            )
            has_tls = any(
                ln.get("protocol") == "amqp/ssl" for ln in listeners
            )
            return {
                "rabbitmq_version": data.get("rabbitmq_version"),
                "erlang_version": data.get("erlang_version"),
                "listeners": listeners,
                "has_plaintext_amqp": has_plaintext,
                "has_tls_amqp": has_tls,
            }
        elif resp.status_code == 401:
            return {"auth_failed": True}   # management plugin present but wrong creds
    except requests.exceptions.ConnectionError:
        pass   # management plugin not running
    return None
```

**Detecting plaintext AMQP (port 5672) alongside TLS:**

The cleanest method is a raw TCP connection to port 5672 followed by sending the AMQP 0-9-1 protocol header (`b'AMQP\x00\x00\x09\x01'`) and checking for a response. If the port is open and responds to the header, plaintext AMQP is active. No credentials needed for this check.

```python
import socket

AMQP_091_HEADER = b'AMQP\x00\x00\x09\x01'

def detect_plaintext_amqp(host: str, port: int = 5672, timeout: int = 3) -> bool:
    """
    Returns True if plaintext AMQP is accepting connections on this port.
    Sends AMQP 0-9-1 header; expects a Connection.Start frame (starts with 0x01).
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(AMQP_091_HEADER)
            data = sock.recv(8)
            # AMQP frame type 1 = METHOD frame (Connection.Start)
            return len(data) > 0 and data[0] == 0x01
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False
```

**Severity logic:** If `detect_plaintext_amqp()` returns True, emit a HIGH severity finding: "Plaintext AMQP on port 5672 active alongside or instead of TLS."

---

## 3. AMQP 1.0 vs 0-9-1 — Protocol Version Impact on TLS Probing

### Verdict: No impact on TLS probing. Both versions share the same port 5671, and both use direct TLS identically.

**Key facts:**
- Both AMQP 0-9-1 and AMQP 1.0 share port 5671 on RabbitMQ
- The protocol selection (0-9-1 vs 1.0) happens via the AMQP protocol header sent *after* TLS completes
- The AMQP protocol header for 0-9-1 is `AMQP\x00\x00\x09\x01`; for 1.0 it is `AMQP\x00\x01\x00\x00`
- sslyze never reaches the AMQP layer — it only speaks TLS, then disconnects

**For Azure Service Bus (AMQP 1.0 only):** Azure Service Bus exposes AMQP 1.0 on `<namespace>.servicebus.windows.net:5671`. The TLS layer is identical — sslyze scans it the same way. The distinction between protocol versions is irrelevant for the scanner.

**Python library landscape (for context only — not used in QUIRK scanner):**

| Library | Protocol | Use case |
|---------|----------|----------|
| `pika` | AMQP 0-9-1 | RabbitMQ client |
| `amqp` (celery dep) | AMQP 0-9-1 | Celery transport |
| `azure-servicebus` | AMQP 1.0 | Azure Service Bus client |
| `qpid-proton` | AMQP 1.0 | General AMQP 1.0 |

None of these are needed for the scanner — sslyze + raw socket covers all probing needs.

---

## 4. Port Conventions — Default Scan Targets

### Recommended default port list for the broker scanner:

| Port | Protocol | Default | Scan Action |
|------|----------|---------|-------------|
| 5671 | AMQPS (TLS) | YES | sslyze TLS probe |
| 5672 | AMQP plaintext | YES | TCP probe for protocol header — finding if open |
| 15672 | Management HTTP | YES | Best-effort GET /api/overview with guest:guest |
| 15671 | Management HTTPS | YES | sslyze TLS probe (management TLS cert may differ from broker cert) |
| 5551 | RabbitMQ Stream TLS | OPTIONAL | sslyze probe — same treatment as 5671 |
| 5552 | RabbitMQ Stream plain | OPTIONAL | TCP probe |
| 61614 | STOMP TLS | OPTIONAL | sslyze probe |
| 8883 | MQTT TLS | OPTIONAL | sslyze probe |

**Recommended minimum for v4.4:**
- Mandatory: 5671 (AMQPS TLS), 5672 (plaintext detection), 15672 (management API probe)
- Optional: 15671 (management HTTPS)

The config block in `config.yaml` should look like:

```yaml
brokers:
  - host: rabbitmq.internal.example.com
    # Optional management API credentials (best-effort, safe to leave blank)
    management_user: guest
    management_password: guest
    # Ports to probe (defaults shown)
    amqps_port: 5671
    amqp_port: 5672
    management_port: 15672
```

---

## 5. Chaos Lab Docker Image and Weak TLS Configuration

### Verdict: Use `rabbitmq:3.13-management` with a custom `rabbitmq.conf` and self-signed cert. Weak TLS via Erlang `ssl_options`.

**Docker image:** `rabbitmq:3.13-management` (or `rabbitmq:3-management` for latest 3.x). The `-management` tag includes the management HTTP API on port 15672. No separate management container needed.

**Critical constraint:** Modern RabbitMQ (3.x) runs on Erlang 26+. Erlang 26 defaults to TLS 1.2/1.3 only and *removes* support for TLS 1.0/1.1 at the OpenSSL layer. To get genuine TLS 1.1 and TLS 1.0 support for chaos scenarios, you need an older image.

**Recommendation for weak TLS chaos:** Use `rabbitmq:3.12-management` or `rabbitmq:3.11-management` which run on Erlang 25 (still supports TLS 1.0/1.1 in ssl_options).

**Complete Docker Compose service definition:**

```yaml
# profile: broker
rabbitmq-weak-tls:
  image: rabbitmq:3.12-management
  profiles: ["broker"]
  hostname: rabbitmq-weak-tls
  environment:
    RABBITMQ_CONFIG_FILE: /etc/rabbitmq/rabbitmq.conf
  volumes:
    - ./broker/rabbitmq/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro
    - ./broker/rabbitmq/certs:/etc/rabbitmq/certs:ro
  ports:
    - "25671:5671"   # AMQPS (weak TLS)
    - "25672:5672"   # AMQP plaintext (intentionally enabled alongside TLS)
    - "35672:15672"  # Management HTTP
  healthcheck:
    test: ["CMD", "rabbitmq-diagnostics", "ping"]
    interval: 10s
    timeout: 5s
    retries: 10
    start_period: 30s
```

**`broker/rabbitmq/rabbitmq.conf` — weak TLS configuration:**

```ini
# Enable TLS listener
listeners.ssl.default = 5671

# Keep plaintext enabled (security finding: plaintext alongside TLS)
listeners.tcp.default = 5672

# TLS certificate paths
ssl_options.cacertfile = /etc/rabbitmq/certs/ca.crt
ssl_options.certfile   = /etc/rabbitmq/certs/broker.crt
ssl_options.keyfile    = /etc/rabbitmq/certs/broker.key

# Weak TLS versions (TLS 1.0/1.1 enabled — scanner should flag these)
ssl_options.versions.1 = tlsv1.2
ssl_options.versions.2 = tlsv1.1
ssl_options.versions.3 = tlsv1

# No client cert requirement (scanner connects without client cert)
ssl_options.verify            = verify_none
ssl_options.fail_if_no_peer_cert = false

# Weak cipher suites (scanner should flag RC4, 3DES, CBC non-PFS)
ssl_options.ciphers.1 = RC4-SHA
ssl_options.ciphers.2 = DES-CBC3-SHA
ssl_options.ciphers.3 = AES128-SHA
ssl_options.ciphers.4 = AES256-SHA
ssl_options.ciphers.5 = ECDHE-RSA-AES256-GCM-SHA384
ssl_options.ciphers.6 = ECDHE-RSA-AES128-GCM-SHA256

# Management plugin
management.listener.port = 15672
```

**Self-signed cert generation script (`broker/rabbitmq/gen-certs.sh`):**

```bash
#!/bin/sh
# Generates a self-signed RSA-2048 CA and broker cert for chaos lab
# Place outputs in broker/rabbitmq/certs/

set -e
OUTDIR="$(dirname "$0")/certs"
mkdir -p "$OUTDIR"

# CA
openssl genrsa -out "$OUTDIR/ca.key" 2048
openssl req -new -x509 -days 3650 \
  -key "$OUTDIR/ca.key" \
  -out "$OUTDIR/ca.crt" \
  -subj "/CN=QUIRK-Chaos-CA/O=QUIRK/C=US"

# Broker key + CSR + cert
openssl genrsa -out "$OUTDIR/broker.key" 2048
openssl req -new \
  -key "$OUTDIR/broker.key" \
  -out "$OUTDIR/broker.csr" \
  -subj "/CN=rabbitmq-weak-tls/O=QUIRK-Chaos/C=US"
openssl x509 -req -days 365 \
  -in  "$OUTDIR/broker.csr" \
  -CA  "$OUTDIR/ca.crt" \
  -CAkey "$OUTDIR/ca.key" \
  -CAcreateserial \
  -out "$OUTDIR/broker.crt"

echo "Certs written to $OUTDIR"
```

**Erlang legacy cipher warning:** RC4 support was removed in Erlang 22. If the container's Erlang version is 22+, `RC4-SHA` will be silently ignored. To get genuine RC4 support you would need Erlang 21 (Rabbit 3.7/3.8 era). For v4.4 chaos purposes, using 3DES (`DES-CBC3-SHA`) and non-PFS CBC (`AES128-SHA`, `AES256-SHA`) alongside TLS 1.1 is sufficient to exercise all scanner findings. Document this constraint in `expected_results.md`.

**Expected findings from chaos lab scan:**
- CRITICAL or HIGH: TLS 1.0 and/or 1.1 enabled
- HIGH: 3DES cipher suite present
- HIGH: Non-PFS CBC cipher suites present (AES128-SHA, AES256-SHA)
- HIGH: Self-signed certificate (chain not trusted)
- HIGH: Plaintext AMQP port 5672 open alongside TLS
- MEDIUM: RSA-2048 certificate key (quantum-unsafe public key)

---

## 6. Quantum Risk — RabbitMQ / AMQP TLS Configurations

### Most quantum-vulnerable configurations, in priority order:

**CRITICAL — algorithm quantum-unsafe AND weakens current classical security:**
- TLS 1.0/1.1 with RSA key exchange (no PFS, no forward secrecy, full session decryptable with RSA private key by CRQT)
- Any cipher suite using `RSA` key exchange (e.g., `AES128-SHA`, `AES256-SHA`, `AES128-GCM-SHA256` without ECDHE prefix) — RSA-based key exchange broken by Shor's algorithm

**HIGH — quantum-unsafe (no classical weakness today):**
- ECDHE key exchange with NIST curves (P-256, P-384, P-521) — broken by Shor's algorithm on a CRQT, though still classically secure
- RSA certificate public key (any size, for broker auth) — broken by Shor's algorithm
- DHE key exchange — broken by Shor's algorithm

**MEDIUM — partially quantum-safe (symmetric portion survives):**
- TLS 1.3 with ECDHE + AES-256-GCM — key exchange broken, but AES-256 symmetric portion survives Grover's with 128-bit effective security
- AES-128 in any TLS version — provides only ~64 bits effective security post-Grover

**SAFE (PQC-ready):**
- None in current RabbitMQ default configurations — Erlang/OTP does not yet support ML-KEM (Kyber) or ML-DSA key exchange natively as of 2026

**Classifier mapping to QUIRK CBOM algorithm table:**

| Algorithm extracted | NIST PQC classification | Severity |
|--------------------|-----------------------|----------|
| `RSA` key exchange | UNSAFE | CRITICAL (no PFS) or HIGH |
| `ECDHE` + P-curve | UNSAFE | HIGH |
| `DHE` | UNSAFE | HIGH |
| `RSA` cert pubkey | UNSAFE | HIGH |
| `ECDSA` cert pubkey | UNSAFE | HIGH |
| `AES-128-*` | SAFE (classical) / MEDIUM (post-Q) | LOW |
| `AES-256-*` | SAFE (classical) / LOW (post-Q) | INFO |
| `3DES`, `RC4` | UNSAFE (classically weak) | CRITICAL |
| `TLS 1.0` / `1.1` | N/A (protocol version) | CRITICAL / HIGH |

**Evidence counters to wire into scoring:**
- `motion_broker_weak_tls_count` — count of broker endpoints with TLS 1.0/1.1 or SSL2/3
- `motion_broker_plaintext_count` — count of broker endpoints with plaintext AMQP open
- `motion_broker_weak_cipher_count` — count of endpoints with RC4/3DES/NULL ciphers
- `motion_broker_no_pfs_count` — count of endpoints without PFS (RSA key exchange only)
- `motion_broker_quantum_unsafe_count` — count of endpoints with quantum-unsafe key exchange

---

## 7. Azure Service Bus / AWS SQS — In-Scope vs Out-of-Scope

### Verdict: Include as "cloud message broker TLS audit" — scan via sslyze to their public HTTPS/AMQPS endpoints.

**These are scannable by sslyze without any credentials:**

| Service | Endpoint | Port | TLS type |
|---------|----------|------|----------|
| Azure Service Bus | `<namespace>.servicebus.windows.net` | 5671 | Direct TLS (AMQPS) |
| Azure Service Bus (WebSocket fallback) | `<namespace>.servicebus.windows.net` | 443 | HTTPS |
| AWS SQS | `sqs.<region>.amazonaws.com` | 443 | HTTPS |
| AWS EventBridge | `events.<region>.amazonaws.com` | 443 | HTTPS |

**Scanning approach:**

```python
# Azure Service Bus — direct AMQPS (identical to RabbitMQ scan)
scan_request = ServerScanRequest(
    server_location=ServerNetworkLocation(
        hostname=f"{namespace}.servicebus.windows.net",
        port=5671,
    ),
    ...
)

# AWS SQS — HTTPS endpoint (standard TLS scan, port 443)
scan_request = ServerScanRequest(
    server_location=ServerNetworkLocation(
        hostname=f"sqs.{region}.amazonaws.com",
        port=443,
    ),
    ...
)
```

**Findings expected from real services:**

- Azure Service Bus: TLS 1.2 minimum, ECDHE-RSA ciphers, valid cert from DigiCert — HIGH finding (ECDHE key exchange quantum-unsafe), MEDIUM for CBC compat suites
- AWS SQS: TLS 1.2/1.3, ECDHE-RSA + X25519, AWS-managed cert — similar profile

**Recommendation for v4.4 scope:**

Include as `cloud_broker` sub-category within the broker scanner:
- If `brokers[].type = azure_service_bus`, scan `{namespace}.servicebus.windows.net:5671`
- If `brokers[].type = aws_sqs`, scan `sqs.{region}.amazonaws.com:443`
- The scanner code is identical to the RabbitMQ sslyze path — no special handling needed
- The CBOM entry protocol field should be `"AMQPS"` for Service Bus and `"HTTPS"` for SQS

**Why not out-of-scope:**

The quantum risk is the same regardless of whether the endpoint is self-hosted RabbitMQ or a managed service. ECDHE-RSA key exchange on Azure Service Bus is just as quantum-vulnerable as on RabbitMQ. Consultants auditing enterprises with Azure/AWS message brokers need this surface in their CBOM.

**What to skip:** Do NOT try to enumerate queue/topic contents or use service-specific SDKs (azure-servicebus, boto3 SQS). That requires credentials and is out of scope for agentless TLS audit.

---

## Implementation Notes for QUIRK

### Module placement

```
quirk/scanner/broker_scanner.py    # New module
```

Pattern the module after `db_connector.py`:
- Optional import guard for `pika` (not needed for scanning, but include if adding functional probe)
- `BROKER_SCANNER_AVAILABLE = True` (no optional deps needed — sslyze already in core)
- Expose `scan_broker_targets(targets: list, logger=None, session_start=None) -> List[CryptoEndpoint]`

### CryptoEndpoint field usage

Reuse all existing TLS fields — no new ORM columns needed for the scanning findings themselves. The broker scanner outputs `CryptoEndpoint` objects exactly like the TLS scanner does.

New ORM column needed: `broker_scan_json` (TEXT, nullable) — stores the raw broker scan metadata (management API response, plaintext detection result, broker version). Follow the pattern of `dat_scan_json`.

### Protocol label

Set `ep.protocol = "AMQPS"` for port 5671 scans (not "TLS") so dashboard and CBOM distinguish broker endpoints from web TLS endpoints.

For plaintext AMQP detection: create a separate `CryptoEndpoint` with `protocol = "AMQP"` and severity HIGH — no TLS fields populated, just the finding.

### Severity rules

| Condition | Severity | Finding ID |
|-----------|----------|------------|
| TLS 1.0 enabled | CRITICAL | BROKER-01 |
| TLS 1.1 enabled | HIGH | BROKER-02 |
| SSL 2.0/3.0 enabled | CRITICAL | BROKER-01 |
| Plaintext AMQP open | HIGH | BROKER-03 |
| RC4 / NULL / EXPORT cipher | CRITICAL | BROKER-04 |
| 3DES cipher | HIGH | BROKER-04 |
| No PFS (RSA key exchange) | HIGH | BROKER-05 |
| Self-signed cert | MEDIUM | BROKER-06 |
| Expired cert | HIGH | BROKER-07 |
| RSA cert pubkey < 2048 | CRITICAL | BROKER-08 |
| ECDHE key exchange (quantum) | HIGH | BROKER-09 |
| Management API unauthenticated | MEDIUM | BROKER-10 (if guest:guest works) |

### CBOM integration

Pass 1: Register algorithms from accepted cipher suites (same as TLS scanner — reuse `_pubkey_info()` and NIST PQC table lookups).

Pass 2 skip list: Add `"AMQPS"` and `"AMQP"` to skip lists for X.509 CertificateProperties generation (same pattern as DNSSEC/SAML/Kerberos — avoid hollow CertificateProperties entries when no cert is present for plaintext AMQP finding).

Pass 3: No special handling needed.

---

## Sources

- [RabbitMQ TLS Support](https://www.rabbitmq.com/docs/ssl) — authoritative, current
- [RabbitMQ Networking](https://www.rabbitmq.com/docs/networking) — port list, listener configuration
- [RabbitMQ Management Plugin](https://www.rabbitmq.com/docs/management) — API auth requirements
- [RabbitMQ HTTP API Reference](https://www.rabbitmq.com/docs/http-api-reference) — endpoint list, auth
- [RabbitMQ Troubleshooting TLS](https://www.rabbitmq.com/docs/troubleshooting-ssl) — openssl s_client behavior
- [sslyze Scan Commands](https://blog.adqt.fr/sslyze/documentation/available-scan-commands.html) — ScanCommand enum, result shapes
- [sslyze Running a Scan in Python](https://blog.adqt.fr/sslyze/documentation/running-a-scan-in-python.html) — ServerNetworkConfiguration, ProtocolWithOpportunisticTlsEnum
- [pika TLS examples](https://pika.readthedocs.io/en/stable/examples/tls_mutual_authentication.html) — confirmed pika requires AMQP auth after TLS
- [Azure Service Bus AMQP Guide](https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-amqp-protocol-guide) — port 5671, TLS-first design
- [Azure Service Bus cipher suites](https://learn.microsoft.com/en-us/answers/questions/1397112/what-are-the-ciphersuites-used-in-azure-service-bu) — ECDHE-RSA suite list
- [AWS SQS Security](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-infrastructure-security.html) — TLS 1.2+ required, ECDHE/DHE PFS requirement
- [RabbitMQ Docker TLS Issue](https://github.com/docker-library/rabbitmq/issues/468) — rabbitmq:3-management TLS setup patterns
