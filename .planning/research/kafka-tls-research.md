# Kafka TLS Scanning Research

**Project:** QU.I.R.K. v4.4 Data in Motion — Kafka broker TLS auditor
**Researched:** 2026-04-27
**Confidence:** HIGH (sslyze integration pattern), MEDIUM (AdminClient config retrieval), HIGH (port conventions), MEDIUM (chaos lab setup), HIGH (quantum risk classification)

---

## Section 1: Kafka TLS Connection Probing

### Recommendation: Raw SSL socket probe + sslyze handoff

For QU.I.R.K.'s agentless, pip-installable, offline-capable model, **do not use kafka-python or confluent-kafka as the TLS probe mechanism**. Use the same approach as the existing `tls_scanner.py` — sslyze with a `ServerNetworkLocation` pointed at port 9093, falling back to Python's stdlib `ssl` module.

### Why not kafka-python

`kafka-python` (pure Python) has `KafkaAdminClient` with `describe_configs()`, which can pull broker config keys (see Section 3). But it requires establishing a Kafka protocol connection, not just a TLS handshake. The library sends a Kafka API Versions request before any SSL negotiation is complete, which can fail when the broker enforces mTLS or restricts SASL. It adds a heavyweight dependency for something sslyze already handles better.

`kafka-python` v2.x/v3.x status: the upstream repo (dpkp/kafka-python) has been largely unmaintained. A community fork `kafka-python-ng` exists but is not widely adopted. **Do not add as a required dependency.**

### Why not confluent-kafka

`confluent-kafka` wraps `librdkafka` (C/C++). It is not pure Python — it requires compiled binary wheels. On Alpine Linux and some CI environments, installation fails. This breaks QU.I.R.K.'s offline-capable, pip-clean install requirement. `confluent-kafka` does have a robust `AdminClient.describe_configs()` that returns broker SSL config. Reserve this as an **optional extras group** (`pip install quirk[kafka]`) alongside `kafka-python`, only activated when the user opts into admin API enrichment.

### Primary probe: sslyze (already a QU.I.R.K. dependency)

sslyze's `ServerNetworkLocation` accepts any `(hostname, port)`. Port 9093 is just another TLS endpoint — no Kafka protocol awareness needed for cipher enumeration and cert extraction. This is the correct integration point because:

- QU.I.R.K. already has sslyze wired and working in `tls_scanner.py`
- sslyze enumerates all TLS versions, cipher suites, and cert chain — exactly what QUIRK needs
- No new pip dependency required for the core path
- Works offline (sslyze operates over raw sockets)

### Fallback probe: stdlib `ssl` socket

When sslyze is unavailable (same fallback logic as `tls_scanner.py`), use a raw SSL socket. This is already the established pattern.

### Minimal TLS handshake probe pattern

```python
import ssl
import socket
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, ec


KAFKA_TLS_PORTS = [9093, 9094]  # 9093=SSL, 9094=SASL_SSL (MSK uses different; see Section 4)


def probe_kafka_tls(host: str, port: int, timeout: int = 10) -> dict:
    """
    Raw SSL socket probe for Kafka TLS — no Kafka protocol required.
    Returns dict with tls_version, cipher, cert info, and error if any.
    Mirrors the _scan_one_fallback() pattern in tls_scanner.py.
    """
    result = {"host": host, "port": port, "tls_ok": False}

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # scanner — we want to connect even with self-signed
    # Allow legacy TLS for detection purposes
    ctx.minimum_version = ssl.TLSVersion.TLSv1
    ctx.set_ciphers("ALL:@SECLEVEL=0")

    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as tls_sock:
                result["tls_ok"] = True
                result["tls_version"] = tls_sock.version()       # e.g. "TLSv1.2"
                cipher_info = tls_sock.cipher()                  # (name, protocol, bits)
                result["cipher"] = cipher_info[0] if cipher_info else None
                result["cipher_bits"] = cipher_info[2] if cipher_info else None

                # DER cert — parse with cryptography library
                der = tls_sock.getpeercert(binary_form=True)
                if der:
                    cert = x509.load_der_x509_certificate(der, default_backend())
                    result["cert_subject"] = cert.subject.rfc4514_string()
                    result["cert_issuer"] = cert.issuer.rfc4514_string()
                    result["cert_not_after"] = cert.not_valid_after_utc
                    pubkey = cert.public_key()
                    if isinstance(pubkey, rsa.RSAPublicKey):
                        result["cert_pubkey_alg"] = "RSA"
                        result["cert_pubkey_size"] = pubkey.key_size
                    elif isinstance(pubkey, ec.EllipticCurvePublicKey):
                        result["cert_pubkey_alg"] = "ECDSA"
                        result["cert_pubkey_size"] = pubkey.key_size

    except ssl.SSLError as e:
        msg = str(e)
        if "certificate required" in msg.lower() or "handshake failure" in msg.lower():
            result["error"] = "MTLS_REQUIRED"
        elif "wrong version" in msg.lower():
            result["error"] = "NOT_TLS"
        else:
            result["error"] = f"TLS_ERROR: {msg}"
    except ConnectionRefusedError:
        result["error"] = "CONNECTION_REFUSED"
    except TimeoutError:
        result["error"] = "TIMEOUT"

    return result
```

### sslyze integration (preferred path)

When sslyze is available, reuse the exact `_scan_one_sslyze()` pattern from `tls_scanner.py` — just pass `port=9093` and `host=<kafka_broker>`. sslyze will enumerate all cipher suites across TLS 1.0 through 1.3, extract the cert chain, and return the same `CryptoEndpoint` structure already understood by the CBOM builder.

```python
# In kafka_scanner.py — sslyze path (mirrors tls_scanner._scan_one_sslyze)
from quirk.scanner.tls_scanner import _scan_one_sslyze

def scan_kafka_tls_endpoint(host: str, port: int = 9093, timeout: int = 10, logger=None):
    """Scan a Kafka TLS port using sslyze. Returns CryptoEndpoint or None."""
    ep = _scan_one_sslyze(host=host, port=port, timeout=timeout, include_sni=True, logger=logger)
    if ep is None:
        ep = _scan_one_fallback(host=host, port=port, timeout=timeout, logger=logger)
    if ep:
        ep.service_type = "kafka"  # Tag for dashboard / CBOM differentiation
    return ep
```

**Confidence:** HIGH — sslyze `ServerNetworkLocation` is port-agnostic; this pattern is proven in the existing codebase.

---

## Section 2: Kafka TLS Configuration Surface

### What a Kafka broker exposes via TLS (externally observable)

An external scanner without admin API access can determine:

| Observable | How | Value |
|---|---|---|
| TLS version negotiated | SSL handshake | TLS 1.2 / 1.3 (or 1.0/1.1 if weak) |
| Cipher suite negotiated | `ssl_sock.cipher()` or sslyze | e.g. `TLS_AES_256_GCM_SHA384` |
| All accepted cipher suites | sslyze enumeration | Full list per TLS version |
| Certificate subject / issuer | Cert chain from handshake | Reveals CA type (self-signed vs PKI) |
| Certificate public key algorithm | Cert parse | RSA vs ECDSA, key size |
| Certificate signature algorithm | Cert parse | SHA-256 vs SHA-1 |
| Certificate expiry | Cert parse | Days until expiry |
| mTLS requirement | Handshake failure with no client cert | `ssl.SSLError: certificate required` |
| PLAINTEXT listener presence | Connect to port 9092 without TLS | Connection succeeds or refuses |

### What is NOT externally observable without admin API

- `ssl.client.auth` value (required/requested/none) — inferred only by attempting connection without client cert
- `ssl.enabled.protocols` configured value (vs JVM default) — you see what was negotiated, not what's configured
- `ssl.cipher.suites` explicit list (empty = JVM default, cannot distinguish from explicit list externally)
- `listener.security.protocol.map` — the full listener mapping (PLAINTEXT vs SSL vs SASL_SSL per port)
- `security.inter.broker.protocol` — inter-broker security, not exposed via client connections
- Keystore/truststore type (JKS vs PEM) — internal broker configuration

### Security-relevant config keys (for AdminClient path, see Section 3)

| Config Key | Security Relevance | Quantum Risk |
|---|---|---|
| `ssl.enabled.protocols` | Weak if TLSv1.0 or TLSv1.1 present | — |
| `ssl.cipher.suites` | Empty = JVM default (usually strong); explicit weak list is HIGH | RSA key exchange ciphers vulnerable |
| `ssl.client.auth` | `none` = no mTLS = unauthenticated clients | — |
| `ssl.keystore.type` | JKS (older) vs PKCS12/PEM; JKS has weaker key protection | — |
| `listener.security.protocol.map` | PLAINTEXT listener = unencrypted traffic | — |
| `security.inter.broker.protocol` | PLAINTEXT = broker-to-broker unencrypted | — |
| `ssl.endpoint.identification.algorithm` | Empty/disabled = no hostname verification | — |

### Severity classification

| Finding | Severity | Rationale |
|---|---|---|
| TLS 1.0 or TLS 1.1 accepted | HIGH | Deprecated, known weak |
| SSLv3 accepted | CRITICAL | POODLE-vulnerable |
| RSA key exchange cipher (non-ECDHE) in TLS 1.2 | HIGH | No forward secrecy, quantum-unsafe key exchange |
| RSA cert key < 2048 bits | CRITICAL | Trivially breakable |
| RSA cert key = 2048 bits | MEDIUM | Quantum-vulnerable (Shor), migration needed |
| SHA-1 signature algorithm | HIGH | Collision-vulnerable |
| PLAINTEXT listener exposed on 9092 | HIGH | Unencrypted traffic |
| mTLS not required (ssl.client.auth=none) | MEDIUM | Client identity not verified |
| Self-signed cert | MEDIUM | No PKI trust chain |
| Cert expiry < 30 days | HIGH | Imminent outage risk |
| No TLS on expected port | HIGH | Cleartext broker |

---

## Section 3: Kafka Admin API for Security Information

### describe_configs works — with significant caveats

Both `kafka-python` and `confluent-kafka` expose `describe_configs()` on their AdminClient classes.

**kafka-python `KafkaAdminClient.describe_configs()`:**

```python
from kafka import KafkaAdminClient
from kafka.admin import ConfigResource, ConfigResourceType

admin = KafkaAdminClient(
    bootstrap_servers="kafka-broker:9093",
    security_protocol="SSL",
    ssl_cafile="/path/to/ca.pem",
    ssl_certfile="/path/to/client.pem",   # only if mTLS required
    ssl_keyfile="/path/to/client.key",
    ssl_check_hostname=False,             # for scanner use
    request_timeout_ms=10000,
)

resource = ConfigResource(ConfigResourceType.BROKER, "0")
result = admin.describe_configs([resource])
# result: {ConfigResource: {str: ConfigEntry}}
config_map = result[resource].result()  # blocks until future resolves
for key, entry in config_map.items():
    print(f"{key} = {entry.value}  (is_sensitive={entry.is_sensitive})")
```

**confluent-kafka `AdminClient.describe_configs()`** (optional extras path):

```python
from confluent_kafka.admin import AdminClient, ConfigResource, ResourceType

admin = AdminClient({
    "bootstrap.servers": "kafka-broker:9093",
    "security.protocol": "SSL",
    "ssl.ca.location": "/path/to/ca.pem",
})

resource = ConfigResource(ResourceType.BROKER, "0")
futures = admin.describe_configs([resource])
config_map = futures[resource].result()  # dict[str, ConfigEntry]
```

### Key SSL config keys to request

```python
SSL_CONFIG_KEYS = [
    "ssl.enabled.protocols",           # e.g. "TLSv1.2,TLSv1.3" or empty (JVM default)
    "ssl.cipher.suites",               # explicit list or empty (JVM default = all)
    "ssl.client.auth",                 # "none" | "requested" | "required"
    "ssl.keystore.type",               # "JKS" | "PKCS12" | "PEM"
    "ssl.truststore.type",             # "JKS" | "PKCS12" | "PEM"
    "ssl.endpoint.identification.algorithm",  # "https" | "" (disabled)
    "listener.security.protocol.map", # "PLAINTEXT:PLAINTEXT,SSL:SSL,SASL_SSL:SASL_SSL"
    "security.inter.broker.protocol", # "PLAINTEXT" | "SSL" | "SASL_SSL"
    "inter.broker.listener.name",     # listener name for inter-broker
]
```

### Critical caveat: sensitive values are redacted

Kafka marks certain configs `is_sensitive=True` (passwords, private key material). SSL config keys themselves are NOT sensitive — their values are returned. However, if `ssl.cipher.suites` is empty (the default), the admin API returns an empty string, not the JVM-resolved list. This means **an empty value does not mean "no cipher restriction" is detectable via admin API** — you must do the handshake-level probe to see what's actually negotiated.

**Practical implication for QU.I.R.K.:** The admin API path is a useful enrichment for config-level findings (e.g., detecting PLAINTEXT inter-broker when the client port uses TLS). But the primary findings engine must be the TLS handshake probe, because:

1. Admin API requires Kafka protocol connectivity (not just TCP+TLS)
2. Admin API may require authentication credentials the scanner doesn't have
3. Empty `ssl.cipher.suites` does not indicate weak ciphers — actual negotiation does
4. Many managed Kafka services (Confluent Cloud, MSK) restrict admin API access

### Graceful degradation design

```python
def enrich_with_admin_api(host: str, port: int, broker_id: str = "0",
                           ssl_cafile=None, ssl_certfile=None, ssl_keyfile=None) -> dict:
    """
    Optional admin API enrichment. Returns {} on any failure.
    Never raises — scanner must continue without admin access.
    """
    try:
        from kafka import KafkaAdminClient
        from kafka.admin import ConfigResource, ConfigResourceType
    except ImportError:
        return {}

    try:
        kwargs = {
            "bootstrap_servers": f"{host}:{port}",
            "security_protocol": "SSL",
            "ssl_check_hostname": False,
            "request_timeout_ms": 8000,
        }
        if ssl_cafile:
            kwargs["ssl_cafile"] = ssl_cafile
        if ssl_certfile:
            kwargs["ssl_certfile"] = ssl_certfile
        if ssl_keyfile:
            kwargs["ssl_keyfile"] = ssl_keyfile

        admin = KafkaAdminClient(**kwargs)
        resource = ConfigResource(ConfigResourceType.BROKER, broker_id)
        result = admin.describe_configs([resource])
        config_map = result[resource].result()
        admin.close()
        return {k: v.value for k, v in config_map.items() if k in SSL_CONFIG_KEYS}
    except Exception:
        return {}
```

**Confidence:** MEDIUM — the API pattern is confirmed from kafka-python and confluent-kafka docs. The behavior of empty `ssl.cipher.suites` (returns "" not the JVM list) is confirmed by Kafka broker config documentation showing "null = all supported cipher suites".

---

## Section 4: Port Conventions

### Standard convention (self-hosted Kafka)

| Port | Protocol | Notes |
|---|---|---|
| **9092** | PLAINTEXT | Default, unencrypted. Always probe — finding an open 9092 on a TLS-advertised broker is a HIGH finding. |
| **9093** | SSL (TLS) | Primary TLS port by convention. Not mandated — operators choose ports. |
| **9094** | SASL_SSL | SASL authentication over TLS. Also appears as SASL_PLAINTEXT on some configs. |
| **9095** | Rarely used | Some operators add a 4th listener for internal traffic. Not standard. |

### Amazon MSK ports (authoritative, from AWS docs)

| Protocol | Internal Port | Public Port |
|---|---|---|
| PLAINTEXT | 9092 | 9092 |
| TLS | 9094 | 9194 |
| SASL/SCRAM | 9096 | 9196 |
| IAM | 9098 | 9198 |

Note: MSK uses 9094 for TLS (not 9093). This is an important difference from self-hosted Kafka. A scanner targeting MSK must probe 9094, not 9093.

### Confluent Cloud

Confluent Cloud brokers use port **9092** with `SASL_SSL` — TLS is embedded in the SASL protocol. The port does not distinguish TLS from plaintext. External TLS scanning of Confluent Cloud is limited to cert extraction (the TLS handshake happens at port 9092).

### Recommended default scan ports for QU.I.R.K.

```python
KAFKA_DEFAULT_PORTS = [9092, 9093, 9094, 9096, 9098, 9194]
# 9092: PLAINTEXT detection (finding open plaintext is itself a finding)
# 9093: Self-hosted SSL (most common)
# 9094: Self-hosted SASL_SSL or MSK TLS
# 9096: MSK SASL/SCRAM
# 9098: MSK IAM
# 9194: MSK TLS public
```

For a quick scan, default to probing **9092 and 9093**. Include 9094 in standard and deep profiles.

**Confidence:** HIGH — port 9092/9093/9094 pattern confirmed across Apache Kafka docs, bitnami examples, and MSK documentation. MSK 9094/9194 confirmed from AWS official docs.

---

## Section 5: Chaos Lab Docker Image

### Recommended image: `bitnami/kafka` (latest or pinned to 3.x)

**Why bitnami/kafka over alternatives:**

| Image | Status | TLS Config | Notes |
|---|---|---|---|
| `bitnami/kafka` | Active, well-maintained | `KAFKA_CFG_*` env vars map 1:1 to broker properties | Best for labs — extensive documentation, KRaft mode support |
| `confluentinc/cp-kafka` | Active | `KAFKA_*` env vars via Docker entrypoint script | Heavier image, Confluent-specific extras, good for Confluent Platform testing |
| `wurstmeister/kafka` | Largely unmaintained | `KAFKA_*` env vars | Avoid — no longer receiving updates |
| `apache/kafka` | Official, newer | Minimal config conventions | KRaft-native but less lab tooling |

Bitnami is the right choice for QU.I.R.K.'s chaos lab because:
- `KAFKA_CFG_` prefix maps directly to Kafka broker config keys (e.g., `KAFKA_CFG_SSL_ENABLED_PROTOCOLS`)
- PEM certificate support (`KAFKA_TLS_TYPE=PEM`) avoids JKS/keytool dependency
- KRaft mode eliminates ZooKeeper from the lab stack
- Consistent with how existing chaos lab bitnami images behave

### Chaos lab configuration for weak TLS

```yaml
# docker-compose profile: kafka-tls
# Ports: 9092 (plaintext), 9093 (weak TLS), 9094 (mTLS required)

services:
  kafka-weak-tls:
    image: bitnami/kafka:3.7
    profiles: ["kafka-tls"]
    environment:
      # KRaft mode (no ZooKeeper)
      KAFKA_CFG_NODE_ID: "1"
      KAFKA_CFG_PROCESS_ROLES: "broker,controller"
      KAFKA_CFG_CONTROLLER_QUORUM_VOTERS: "1@kafka-weak-tls:9099"
      KAFKA_CFG_CONTROLLER_LISTENER_NAMES: "CONTROLLER"

      # Listener map: PLAINTEXT on 9092, SSL on 9093, CONTROLLER internal
      KAFKA_CFG_LISTENERS: "PLAINTEXT://:9092,SSL://:9093,CONTROLLER://:9099"
      KAFKA_CFG_ADVERTISED_LISTENERS: "PLAINTEXT://localhost:9092,SSL://localhost:9093"
      KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP: "PLAINTEXT:PLAINTEXT,SSL:SSL,CONTROLLER:PLAINTEXT"
      KAFKA_CFG_INTER_BROKER_LISTENER_NAME: "PLAINTEXT"

      # TLS using PEM (no keytool needed)
      KAFKA_TLS_TYPE: "PEM"
      KAFKA_CFG_SSL_KEYSTORE_LOCATION: "/opt/bitnami/kafka/config/certs/kafka.keystore.pem"
      KAFKA_CFG_SSL_KEY_PASSWORD: ""

      # WEAK TLS — allow TLS 1.1 for scanner validation
      KAFKA_CFG_SSL_ENABLED_PROTOCOLS: "TLSv1.1,TLSv1.2"

      # Weak cipher suite — RC4 forces HIGH/CRITICAL finding
      # Note: modern OpenSSL/JVM may refuse truly broken ciphers; use TLS_RSA_WITH_AES_128_CBC_SHA
      # (RSA key exchange = no forward secrecy, quantum-unsafe key exchange)
      KAFKA_CFG_SSL_CIPHER_SUITES: "TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA"

      # No mTLS on this listener
      KAFKA_CFG_SSL_CLIENT_AUTH: "none"

      # Disable hostname verification (common misconfiguration)
      KAFKA_CFG_SSL_ENDPOINT_IDENTIFICATION_ALGORITHM: ""

    volumes:
      - ./kafka/certs/kafka-weak.pem:/opt/bitnami/kafka/config/certs/kafka.keystore.pem:ro
      - ./kafka/certs/kafka-weak.key:/opt/bitnami/kafka/config/certs/kafka.key:ro
      - ./kafka/certs/ca.pem:/opt/bitnami/kafka/config/certs/kafka.truststore.pem:ro
    ports:
      - "39092:9092"   # PLAINTEXT — finding: unencrypted listener
      - "39093:9093"   # Weak TLS — finding: TLS 1.1 + RSA key exchange ciphers
    healthcheck:
      test: ["CMD-SHELL", "kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null && echo OK"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s
```

### Expected findings from weak lab

| Finding ID | Type | Expected Severity |
|---|---|---|
| KAFKA-01 | TLS 1.1 accepted | HIGH |
| KAFKA-02 | RSA key exchange cipher (no forward secrecy) | HIGH |
| KAFKA-03 | PLAINTEXT listener exposed | HIGH |
| KAFKA-04 | Hostname verification disabled | MEDIUM |
| KAFKA-05 | RSA 2048-bit cert (quantum-vulnerable) | MEDIUM |

### Certificate generation for the lab

Generate a self-signed RSA-2048 cert (intentionally weak for quantum finding validation):

```bash
# Lab cert generation script: quantum-chaos-enterprise-lab/kafka/gen-certs.sh
openssl req -x509 -newkey rsa:2048 -keyout kafka-weak.key -out kafka-weak.pem \
  -days 365 -nodes -sha256 \
  -subj "/CN=kafka-weak.chaos.local/O=QUIRK Lab/C=US" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

### JVM cipher constraint

Modern Java (11+) and OpenSSL refuse to negotiate SSLv3, RC4, and export ciphers by default due to `jdk.tls.disabledAlgorithms`. For the chaos lab, `TLS_RSA_WITH_AES_128_CBC_SHA` is a valid weak cipher that modern JVMs will still negotiate — it uses RSA for key exchange (no forward secrecy) and is quantum-unsafe. This is the correct "weak but negotiable" cipher for scanner validation.

**Confidence:** MEDIUM — bitnami `KAFKA_CFG_*` prefix convention confirmed from official bitnami README and GitHub issues. The JVM cipher restriction caveat is confirmed from Wikimedia's Kafka TLS security review. Exact PEM file path conventions are inferred from bitnami documentation patterns and need lab validation.

---

## Section 6: Quantum Risk in Kafka TLS

### The core quantum vulnerability in Kafka TLS

Kafka's TLS configuration surface has two distinct quantum risk categories:

**Category 1: Key Exchange (Shor-vulnerable)**

TLS 1.2 supports both RSA key exchange (static RSA) and ECDHE (ephemeral key exchange). TLS 1.3 mandates ECDHE-equivalent key exchange only.

- **RSA key exchange** (`TLS_RSA_WITH_*` ciphers): The server's RSA public key is used directly for key transport. A quantum computer running Shor's algorithm can factor the RSA modulus and decrypt the session. **No forward secrecy.** Harvest-now-decrypt-later attacks are directly applicable. **CRITICAL quantum finding.**
- **ECDHE** (e.g., `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384`): Forward secrecy via ephemeral keys. Still Shor-vulnerable (elliptic curve discrete log), but recorded sessions cannot be bulk-decrypted. **HIGH quantum finding** (migration needed, but lower urgency than static RSA).
- **TLS 1.3** (`TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256`): Mandates ECDHE. Still quantum-vulnerable, but forward secrecy mitigates immediate harvest-now-decrypt-later. **MEDIUM quantum finding** (migration needed eventually).

**Category 2: Certificate Key (Shor-vulnerable)**

The broker certificate key type determines long-term identity trust:

- **RSA-1024**: CRITICAL (classically breakable today)
- **RSA-2048**: HIGH quantum risk (Shor's algorithm breaks in polynomial time)
- **RSA-4096**: MEDIUM quantum risk (buys some time, but still Shor-vulnerable)
- **ECDSA P-256**: HIGH quantum risk (ECDLP broken by Shor)
- **Ed25519**: HIGH quantum risk (same ECDLP vulnerability class)
- **ML-KEM / Kyber**: SAFE (NIST PQC standard)

### Common enterprise Kafka deployment patterns and their quantum posture

Based on reviewed Kafka TLS documentation and real-world security reviews:

**Pattern 1: Default JVM cipher suite (most common)**
- `ssl.cipher.suites` = empty (JVM default)
- Java 11+ JVM defaults: TLS 1.3 preferred (`TLS_AES_256_GCM_SHA384`), TLS 1.2 fallback with ECDHE ciphers
- Quantum risk: HIGH (ECDHE is Shor-vulnerable, but forward secrecy present)
- Cert typically RSA-2048 (HIGH quantum risk)

**Pattern 2: Legacy explicit cipher list (older enterprise deployments)**
- Common cipher list: `TLS_RSA_WITH_AES_128_CBC_SHA:TLS_RSA_WITH_AES_256_CBC_SHA`
- No forward secrecy, static RSA key exchange
- Quantum risk: CRITICAL (direct harvest-now-decrypt-later applicable)

**Pattern 3: Hardened with ECDHE-only**
- Explicit: `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384`
- Forward secrecy, modern cipher
- Quantum risk: HIGH (ECDHE key exchange is ECDLP-vulnerable, cert is RSA)

**Pattern 4: TLS 1.3 only**
- `ssl.enabled.protocols = TLSv1.3`
- All TLS 1.3 ciphers use ECDHE-equivalent key schedule
- Quantum risk: MEDIUM (forward secrecy + modern AEAD, but still Shor-vulnerable key exchange)

### NIST PQC classification mapping (for CBOM integration)

Use QU.I.R.K.'s existing `NIST_PQC_TABLE` in `cbom/classifier.py`. The relevant algorithm entries to ensure are present:

| Algorithm | CBOM Classification |
|---|---|
| RSA-2048 (cert key) | `quantum-vulnerable` |
| RSA-4096 (cert key) | `quantum-vulnerable` |
| ECDSA P-256 (cert key) | `quantum-vulnerable` |
| TLS_RSA_WITH_* (cipher) | `quantum-vulnerable` |
| TLS_ECDHE_RSA_WITH_* (cipher) | `quantum-vulnerable` |
| TLS_AES_*_GCM_SHA384 (TLS 1.3) | `quantum-vulnerable` |
| ML-KEM-768 / Kyber | `pqc-safe` |

### Severity scoring for motion_ subscore

```
KAFKA-01: TLS 1.0/1.1 accepted                 → HIGH   (motion_weak_tls_count += 1)
KAFKA-02: RSA key exchange cipher               → HIGH   (motion_no_fs_count += 1)
KAFKA-03: PLAINTEXT listener                    → HIGH   (motion_plaintext_count += 1)
KAFKA-04: Self-signed cert                      → MEDIUM (motion_self_signed_count += 1)
KAFKA-05: RSA-2048 cert key                     → MEDIUM (motion_quantum_vulnerable_count += 1)
KAFKA-06: No mTLS (ssl.client.auth=none)        → MEDIUM (motion_no_mtls_count += 1)
KAFKA-07: Hostname verification disabled         → MEDIUM (motion_hostname_skip_count += 1)
KAFKA-08: Cert expiry < 30 days                 → HIGH   (existing cert expiry logic)
KAFKA-09: RSA-1024 cert key                     → CRITICAL
KAFKA-10: SSLv3 accepted                        → CRITICAL
```

---

## Implementation Notes for QU.I.R.K.

### File to create: `quirk/scanner/kafka_scanner.py`

Structure mirrors `quirk/scanner/db_connector.py`:
- Optional import for `kafka-python` (graceful degradation)
- Primary path: sslyze via reuse of `_scan_one_sslyze()` from `tls_scanner.py`
- Fallback path: stdlib `ssl` socket probe
- Admin API enrichment: optional, wraps in try/except, returns `{}` on failure
- Returns `List[CryptoEndpoint]` with `service_type="kafka"`

### Dependencies

```toml
# pyproject.toml — add to [project.optional-dependencies]
[project.optional-dependencies.kafka]
kafka = ["kafka-python-ng>=2.2.3"]  # optional: admin API enrichment only
# confluent-kafka NOT included (binary wheel, breaks offline installs)
```

sslyze is already a core dependency — no new dep for the primary probe path.

### CBOM integration

The CBOM builder already handles `CryptoEndpoint` with TLS protocol data. Tag Kafka endpoints with `service_type = "kafka"` and ensure the CBOM Pass 1 classifies:
- `cert_pubkey_alg` (RSA → `quantum-vulnerable`)
- `tls_version` (1.0/1.1 → `deprecated-protocol`)
- `cipher` (RSA key exchange → `no-forward-secrecy` + `quantum-vulnerable`)

### mTLS detection

When probing port 9093, the scanner should attempt the handshake **without** a client certificate first. If `ssl.SSLError` with `"certificate required"` or `"handshake failure"` occurs, record `mTLS_required=True` as a finding context (not a severity-raising finding — mTLS is good). Then attempt with any configured client cert/key if provided.

---

## Sources

- [Apache Kafka Broker Configs (v2.6)](https://kafka.apache.org/26/configuration/broker-configs/) — ssl.enabled.protocols, ssl.cipher.suites, ssl.client.auth defaults
- [Amazon MSK Port Information](https://docs.aws.amazon.com/msk/latest/developerguide/port-info.html) — authoritative MSK port table
- [confluent-kafka AdminClient API](https://docs.confluent.io/platform/current/clients/confluent-kafka-python/html/index.html) — describe_configs, ConfigResource, ResourceType
- [Confluent adminapi.py example](https://github.com/confluentinc/confluent-kafka-python/blob/master/examples/adminapi.py) — ConfigResource usage pattern
- [kafka-python AdminClient](https://kafka-python.readthedocs.io/en/master/apidoc/KafkaAdminClient.html) — SSL parameters for TLS broker connection
- [bitnami/kafka Docker Hub](https://hub.docker.com/r/bitnami/kafka) — KAFKA_CFG_* env vars, KAFKA_TLS_TYPE
- [bitnami containers README (GitHub)](https://github.com/bitnami/containers/blob/main/bitnami/kafka/README.md) — SSL configuration reference
- [Kafka Development with Docker Part 8 (Jaehyeon Kim)](https://jaehyeon.me/blog/2023-06-29-kafka-development-with-docker-part-8/) — bitnami SSL docker-compose pattern
- [Wikimedia T182993 Kafka TLS Security Review](https://phabricator.wikimedia.org/T182993) — real-world weak cipher discovery, ECDHE-ECDSA enforcement
- [Harvest Now Decrypt Later: Kafka PQC (Medium)](https://medium.com/@sachinrajakaruna95/harvest-now-decrypt-later-securing-kafka-kubernetes-and-multi-cloud-architectures-for-the-a22f9b922839) — quantum risk framing for Kafka
- [confluent-kafka binary wheel Alpine issues](https://github.com/confluentinc/confluent-kafka-python/issues/649) — confirms why confluent-kafka is not suitable as core dep
- [Quix: Choosing a Python Kafka Client](https://quix.io/blog/choosing-python-kafka-client-comparative-analysis) — kafka-python vs confluent-kafka comparison
