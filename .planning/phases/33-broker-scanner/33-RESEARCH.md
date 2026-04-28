# Phase 33: Broker Scanner - Research

**Researched:** 2026-04-27
**Domain:** Message broker TLS posture scanning (Kafka, RabbitMQ/AMQP, Redis, Azure Service Bus, AWS SQS)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Azure Service Bus namespaces and AWS SQS regions supplied via CLI flags + config.yaml. Flags: `--azure-servicebus-namespace <name>` (repeatable) and `--aws-sqs-region <region>` (repeatable). Config keys: `cfg.scanners.broker.azure_namespaces: [...]` and `cfg.scanners.broker.sqs_regions: [...]`.

**D-02:** `broker_scanner.py` does NOT import or call Azure SDK / boto3. Inputs come from CLI/config only.

**D-03:** `scan_rabbitmq_targets()` constructs `{namespace}.servicebus.windows.net:5671` per namespace and probes via sslyze. `ep.protocol = "AMQPS/Azure-ServiceBus"`.

**D-04:** A cloud-target probe function constructs `sqs.{region}.amazonaws.com:443` per region and probes via sslyze. `ep.protocol = "HTTPS/AWS-SQS"`.

**D-05 (deferred):** Auto-discovery of Azure Service Bus namespaces is OUT OF SCOPE for v4.4.

**D-06:** Optional client libraries as sub-extras: `[motion]` declared empty; `[kafka] = ["kafka-python>=2.0"]`; `[redis] = ["redis>=5.0"]`. Install via `pip install quirk[motion,kafka,redis]`.

**D-07:** kafka-python and redis-py imports MUST be guarded (`try: import kafka` / `try: import redis`). Absent library returns basic TLS probe results unchanged.

**D-08:** Auth-failure paths (NOAUTH/NOPERM for Redis, 403/Kafka authorizer denial) degrade silently — log at DEBUG, no finding.

**D-09:** RABBIT-03 uses stdlib `urllib.request` — no `requests` dependency. Auth failure (401) is informational, not error.

**D-10:** Broker scanning runs in `standard` and `deep` profiles only. Adds `cfg.connectors.enable_broker` flag in `apply_profile()` (parallel to `enable_email`).

**D-11:** Footprint warning acknowledged and accepted.

**D-12:** `broker_scan_json` payload is nested per protocol family. Top-level keys: `kafka`, `rabbitmq`, `redis`, `azure_servicebus`, `aws_sqs`. Each value is a list of per-target probe result dicts.

**D-13:** Schema design driven by DASH-03 (Phase 36 Motion tab).

**D-14:** Aggregation onto a single per-scan row at scan-write time in `run_scan.py` (mirrors email_scanner.py:550-599 pattern).

**D-15:** `labs/broker/` uses Bitnami images: `bitnami/kafka:3.6` (or pinned current), `bitnami/rabbitmq:3.12`, `bitnami/redis:7.2`. Env-var-driven weak-TLS. No bind-mounted config files.

**D-16:** Port mapping: Kafka 29092/29093, RabbitMQ 25672/25671, Redis 26379/26380. Plaintext ports intentionally listening.

**D-17:** Self-signed certs generated per `labs/broker/Makefile`. TLS 1.1 minimum, RSA non-PFS ciphers, self-signed RSA-2048. Do NOT reuse `certs/scenarios/`.

**D-18:** Compose profile name = `broker`.

### Claude's Discretion

- Internal helper organization (whether Azure SB + AWS SQS probes are inline in `scan_rabbitmq_targets()` or split into `_scan_azure_servicebus_target` / `_scan_aws_sqs_target` helpers).
- Exact AMQP-header byte sequence handling for RABBIT-02 (timeout values, response parsing depth). Conservative pattern: 2s timeout, accept any `b'AMQP'` prefix in response.
- Whether kafka-python AdminClient enrichment runs over the same TLS connection as sslyze or opens a fresh connection.
- Logging verbosity per port-refused / per-fallback event.
- Whether `--include-broker` / `--no-broker` override flags are wired.

### Deferred Ideas (OUT OF SCOPE)

- Auto-discovery of Azure Service Bus namespaces via Azure SDK.
- AWS SQS auto-region from boto3 Session.
- `--no-broker` opt-out flag.
- Active broker auth probing beyond `guest:guest`.
- Folding `kafka-python` / `redis-py` into `[motion]`.
- `motion_` evidence counters and scoring (Phase 34).
- CBOM integration for broker endpoints (Phase 35).
- Dashboard `/motion` tab (Phase 36).
- DAR dashboard tab (DASH-05 carry-forward from Phase 27).

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STRUCT-01 | All new scanners accept `session_start` parameter | Verified pattern in email_scanner.py; broker_scanner mirrors it |
| STRUCT-02 | All new `[motion]` extras declared in pyproject.toml | pyproject.toml already has `[motion]` stub; adds `[kafka]` and `[redis]` sub-extras |
| STRUCT-03 | Each phase plan includes pyproject.toml diff | Documented in Standard Stack section |
| BROKER-00 | `broker_scan_json` TEXT NULL column on Scan model | db.py _ensure_* pattern verified; add `_ensure_broker_columns()` |
| BROKER-ARCH | Single `broker_scanner.py` with 3 scan_*_targets() functions | db_connector.py verified as exact architectural precedent |
| KAFKA-01 | Probe Kafka TLS on port 9093 via sslyze | sslyze ServerScanRequest works for any TLS port; SNI must be explicit |
| KAFKA-02 | Detect plaintext Kafka on port 9092 via raw TCP probe | TCP connect + recv sufficient; conservative approach documented |
| KAFKA-03 | Probe port 9094 (MSK/SASL_SSL) in standard/deep profiles | Same sslyze path as 9093; port number is the only difference |
| KAFKA-04 | Optional kafka-python AdminClient enrichment | Import guard pattern; `from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType` |
| RABBIT-01 | Probe AMQPS on port 5671 via sslyze | Direct TLS; no STARTTLS; identical to port 443 path |
| RABBIT-02 | Detect plaintext AMQP on port 5672 via AMQP header | `b'AMQP\x00\x00\x09\x01'` + 2s timeout + `b'AMQP'` prefix check |
| RABBIT-03 | Probe RabbitMQ management API GET /api/overview | urllib.request + Basic auth; response fields documented |
| RABBIT-04 | Probe Azure Service Bus `{namespace}.servicebus.windows.net:5671` | sslyze with explicit SNI from hostname; no creds needed |
| RABBIT-05 | Probe AWS SQS `sqs.{region}.amazonaws.com:443` | sslyze with explicit SNI from hostname |
| REDIS-01 | Probe Redis TLS on port 6380 via raw ssl.SSLContext | _try_handshake() pattern from tls_capabilities.py; verified |
| REDIS-02 | Detect plaintext Redis on port 6379 via bare TCP | TCP connect + read RESP inline reply; no auth needed |
| REDIS-03 | Optional redis-py CONFIG GET tls-* enrichment | `r.config_get("tls-*")`; catch `ResponseError` / `AuthenticationError` |
| BROKER-LAB-01 | Chaos lab with 3 weak-TLS broker containers | Image/env var specifics documented; image conflict flagged |
| BROKER-LAB-02 | `labs/broker/expected_results.md` | Documented in Validation Architecture section |

</phase_requirements>

---

## Summary

Phase 33 delivers `quirk/scanner/broker_scanner.py` — a single module following the `db_connector.py` multi-protocol pattern and the `email_scanner.py` 4-function-per-protocol shape. The scanner audits TLS posture on five broker surfaces using three transport mechanics: sslyze for Kafka 9093/RabbitMQ 5671/Azure Service Bus 5671/AWS SQS 443 (all direct TLS, no STARTTLS), raw `ssl.SSLContext` for Redis 6380, and raw TCP for plaintext detection (Kafka 9092, AMQP 5672, Redis 6379). Optional enrichment via kafka-python AdminClient (KAFKA-04) and redis-py CONFIG GET (REDIS-03) are import-guarded sub-extras.

The sslyze API (version 6.2.0 confirmed installed) treats every TLS endpoint identically regardless of upper-layer protocol — the `tls_server_name_indication` parameter in `ServerNetworkConfiguration` must always be set explicitly to the target hostname. SNI is NOT derived automatically from `ServerNetworkLocation.hostname` when `network_configuration=None` is passed; the existing email_scanner.py already enforces this correctly and the broker scanner must mirror it.

There is one image conflict between REQUIREMENTS.md and CONTEXT.md for the chaos lab: REQUIREMENTS.md BROKER-LAB-01 specifies `rabbitmq:3.12-management` (official Docker Hub image) and `redis:7-alpine` (official), while CONTEXT.md D-15 specifies `bitnami/rabbitmq:3.12` and `bitnami/redis:7.2`. CONTEXT.md is authoritative as the locked decision document. The bitnami images require custom `rabbitmq.conf` and `redis.conf` overlays for cipher/TLS-version control because env vars alone do not expose those settings — contradicting D-15's "no bind-mounted config files" constraint. The planner must reconcile this: either use official images (which DO support env-var TLS configuration for RabbitMQ via `RABBITMQ_SSL_*` and Redis via `redis.conf` overlay), or use bitnami images but accept bind-mounted configs. This is the highest-risk planning gap.

**Primary recommendation:** Use official `rabbitmq:3.12-management` and `redis:7-alpine` for the chaos lab (REQUIREMENTS.md BROKER-LAB-01 is the specification document), override the bitnami constraint in D-15 for the two official-image services. For Kafka, use `bitnami/kafka:3.7` (REQUIREMENTS.md) with `KAFKA_CFG_SSL_CIPHER_SUITES` and `KAFKA_CFG_SSL_ENABLED_PROTOCOLS` env vars (these ARE supported by the `KAFKA_CFG_` passthrough mechanism).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Kafka TLS probe (9093/9094) | Scanner module | sslyze library | Direct TLS; sslyze handles cert chain + cipher enumeration |
| Kafka plaintext detection (9092) | Scanner module | Python `socket` | TCP connect probe; no upper-layer protocol needed |
| Kafka AdminClient enrichment | Scanner module (optional) | kafka-python lib | Import-guarded; enriches ep.broker_scan_json only |
| RabbitMQ/AMQPS TLS probe (5671) | Scanner module | sslyze library | Direct TLS; same code path as Kafka 9093 |
| AMQP plaintext detection (5672) | Scanner module | Python `socket` | Send AMQP header, check response bytes |
| RabbitMQ management API enrichment (15672) | Scanner module | stdlib urllib.request | Optional enrichment; no new dep |
| Azure Service Bus TLS probe | Scanner module | sslyze library | Folds into scan_rabbitmq_targets() or helper; direct TLS on 5671 |
| AWS SQS TLS probe | Scanner module | sslyze library | Direct TLS on 443; SNI = sqs.{region}.amazonaws.com |
| Redis TLS probe (6380) | Scanner module | ssl.SSLContext | sslyze cannot speak Redis; raw ssl.wrap_socket() used |
| Redis plaintext detection (6379) | Scanner module | Python `socket` | TCP connect + read RESP reply |
| Redis CONFIG GET enrichment | Scanner module (optional) | redis-py lib | Import-guarded; enriches payload only |
| broker_scan_json aggregation | run_scan.py | broker_scanner.py | Mirrors email_scan_json pattern at email_scanner.py:550-599 |
| Profile gating (broker_enabled) | profiles.py | config.py | Mirrors enable_email pattern; standard+deep only |
| Schema migration | db.py | models.py | _ensure_broker_columns() parallel to _ensure_email_columns() |
| Chaos lab containers | labs/broker/ compose | Makefile cert gen | Port isolation per D-16; profile name `broker` per D-18 |

---

## Standard Stack

### Core (no new deps for the basic TLS probe)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sslyze | 6.2.0 (installed) | Kafka 9093, RabbitMQ 5671, Azure SB 5671, AWS SQS 443 TLS probes | Already a project dep; handles any TLS endpoint regardless of upper-layer protocol |
| ssl (stdlib) | Python 3.11+ | Redis 6380 raw TLS probe; also used in `_try_handshake()` pattern | No new dep; mirrors `tls_capabilities.py` exactly |
| socket (stdlib) | Python 3.11+ | Kafka 9092 plaintext detection, AMQP 5672 plaintext detection, Redis 6379 detection | No new dep |
| urllib.request (stdlib) | Python 3.11+ | RabbitMQ management API GET /api/overview (RABBIT-03, D-09) | No new dep; avoids `requests` |

### Optional Sub-extras (D-06)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| kafka-python | >=2.0 | AdminClient.describe_configs() enrichment (KAFKA-04) | `pip install quirk[kafka]`; import-guarded |
| redis-py | >=5.0 | CONFIG GET tls-* enrichment (REDIS-03) | `pip install quirk[redis]`; import-guarded |

**Version verification:** [VERIFIED: project venv pip show sslyze] — sslyze 6.2.0 installed. kafka-python and redis-py not installed in project venv (expected; they are optional sub-extras).

**pyproject.toml diff (STRUCT-03):**
```toml
[project.optional-dependencies]
# ...existing entries unchanged...
motion = [
    # Phase 32: email scanner — sslyze is a soft import.
    # Phase 33 will add broker deps (kafka-python, etc.) here.  ← REMOVE this comment
]
kafka = [
    "kafka-python>=2.0",
]
redis = [
    "redis>=5.0",
]
```

**Installation:**
```bash
pip install quirk[motion,kafka,redis]
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| kafka-python | confluent-kafka-python | confluent-kafka requires librdkafka native lib; kafka-python is pure-Python. Pure-Python preferred for optional dep |
| urllib.request | requests | D-09 prohibits requests dep for RABBIT-03 |
| raw ssl.SSLContext for Redis | sslyze for Redis | sslyze sends a TLS ClientHello and then expects application data; Redis does not send a recognizable app-layer response before the TLS handshake so sslyze connectivity testing fails. Raw ssl is correct |

---

## Architecture Patterns

### System Architecture Diagram

```
run_scan.py
   │
   ├─ cfg.connectors.enable_broker? (gated by profiles.py apply_profile)
   │
   ├─ scan_kafka_targets(hosts, session_start, ...)
   │     ├─ 9092: TCP connect → recv → kafka-plaintext-listener finding if open
   │     ├─ 9093: sslyze ServerScanRequest → cert+ciphers → CryptoEndpoint
   │     ├─ 9094: sslyze ServerScanRequest → cert+ciphers → CryptoEndpoint
   │     └─ [optional] KafkaAdminClient.describe_configs() → enrichment dict
   │
   ├─ scan_rabbitmq_targets(hosts, azure_namespaces, sqs_regions, session_start, ...)
   │     ├─ 5672: TCP + b'AMQP\x00\x00\x09\x01' → amqp-plaintext-listener finding
   │     ├─ 5671: sslyze → cert+ciphers → CryptoEndpoint (protocol=AMQPS)
   │     ├─ 15672: urllib.request GET /api/overview → enrichment (rabbitmq_version, listeners)
   │     ├─ azure: sslyze {ns}.servicebus.windows.net:5671 → CryptoEndpoint (protocol=AMQPS/Azure-ServiceBus)
   │     └─ sqs: sslyze sqs.{region}.amazonaws.com:443 → CryptoEndpoint (protocol=HTTPS/AWS-SQS)
   │
   ├─ scan_redis_targets(hosts, session_start, ...)
   │     ├─ 6379: TCP connect → read → redis-plaintext-no-auth finding if open
   │     ├─ 6380: ssl.SSLContext.wrap_socket() → TLS version, cipher, cert → CryptoEndpoint
   │     └─ [optional] redis.Redis(ssl=True).config_get("tls-*") → enrichment dict
   │
   └─ broker_scan_json aggregation (mirrors email_scanner.py:550-599)
         ├─ Group all endpoints by scan run
         ├─ Build nested dict: {kafka:[...], rabbitmq:[...], redis:[...], azure_servicebus:[...], aws_sqs:[...]}
         └─ Attach JSON to first endpoint; others get NULL
```

### Recommended Project Structure

```
quirk/scanner/
├── broker_scanner.py        # NEW — BROKER-ARCH single file
│
labs/broker/
├── docker-compose.yml       # profile: broker; 3 services
├── Makefile                 # cert generation target
├── certs/                   # generated; gitignored
└── expected_results.md      # BROKER-LAB-02
```

### Pattern 1: Optional Import Guard (D-07)

**What:** Module-level None assignment for import-guarded optional deps. Ensures test patching works via `unittest.mock.patch`.

**When to use:** Every optional library (kafka-python, redis-py)

```python
# Source: db_connector.py lines 20-34 (VERIFIED: file read)
try:
    import kafka  # type: ignore[import]
    from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType
    KAFKA_AVAILABLE = True
except ImportError:
    KafkaAdminClient = None   # type: ignore[assignment,misc]
    ConfigResource = None     # type: ignore[assignment]
    ConfigResourceType = None # type: ignore[assignment]
    KAFKA_AVAILABLE = False

try:
    import redis as redis_lib  # type: ignore[import]
    REDIS_AVAILABLE = True
except ImportError:
    redis_lib = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False
```

### Pattern 2: sslyze Probe for Any Direct-TLS Port (KAFKA-01, RABBIT-01, RABBIT-04, RABBIT-05)

**What:** sslyze treats every TLS endpoint identically — Kafka 9093, AMQPS 5671, and HTTPS 443 all use the same `ServerScanRequest` shape. The `tls_server_name_indication` MUST be set explicitly in `ServerNetworkConfiguration`; it is a required field with no default.

**When to use:** All direct-TLS broker ports (not Redis — see Pattern 4)

```python
# Source: email_scanner.py lines 134-156 (VERIFIED: file read) + sslyze dataclass inspection (VERIFIED)
# tls_server_name_indication is REQUIRED in ServerNetworkConfiguration — no auto-derive from hostname.
def _scan_one_sslyze_broker(
    host: str,
    port: int,
    timeout: int,
    logger=None,
) -> Optional[CryptoEndpoint]:
    if SslyzeScanner is None:
        return None
    try:
        net_cfg = ServerNetworkConfiguration(
            tls_server_name_indication=host,   # REQUIRED — explicit SNI
            network_timeout=timeout,
        )
        scan_request = ServerScanRequest(
            server_location=ServerNetworkLocation(hostname=host, port=port),
            network_configuration=net_cfg,
            scan_commands={
                ScanCommand.CERTIFICATE_INFO,
                ScanCommand.TLS_1_2_CIPHER_SUITES,
                ScanCommand.TLS_1_3_CIPHER_SUITES,
            },
        )
        scanner = SslyzeScanner(per_server_concurrent_connections_limit=2)
        scanner.queue_scans([scan_request])
        results = list(scanner.get_results())
        if not results:
            return None
        server_result = results[0]
        if server_result.scan_status != ServerScanStatusEnum.COMPLETED:
            return None
        # ... parse cert_info + cipher suites (mirror email_scanner.py pattern) ...
        return ep
    except ConnectionRefusedError:
        return None   # D-03 carry-forward: silent at DEBUG
    except Exception as e:
        if logger:
            logger.debug(f"sslyze error for {host}:{port}: {e}")
        return None
```

**SNI for cloud endpoints:**
- Azure Service Bus: `host = f"{namespace}.servicebus.windows.net"` → `tls_server_name_indication=host` — correct SNI automatically.
- AWS SQS: `host = f"sqs.{region}.amazonaws.com"` → `tls_server_name_indication=host` — correct SNI automatically.
- Neither requires special handling; the hostname IS the SNI.

### Pattern 3: AMQP Plaintext Detection (RABBIT-02)

**What:** Send AMQP 0-9-1 protocol header over bare TCP; check for `b'AMQP'` prefix in response. The server returns `Connection.Start` frame which begins with a frame type byte (0x01), channel (0x00 0x00), and eventually the literal string "AMQP" is NOT in the response body — what we get is a binary frame. The conservative detection is: connection succeeds AND server sends data back (any data = broker is speaking AMQP).

**Conservative approach (Claude's Discretion):** TCP connect success + server responds to header = AMQP positive. If connection refused or timeout = not a plaintext AMQP broker.

```python
# Source: AMQP 0-9-1 spec (CITED: rabbitmq.com/resources/specs/amqp0-9-1.pdf)
# The AMQP 0-9-1 protocol header is b'AMQP\x00\x00\x09\x01'
# Server response is a Connection.Start frame — binary, NOT prefixed with b'AMQP'.
# CONSERVATIVE detection: connected + got any bytes back = AMQP speaker.
AMQP_HEADER = b'AMQP\x00\x00\x09\x01'
AMQP_DETECT_TIMEOUT = 2  # seconds (per CONTEXT.md Claude's Discretion guidance)

def _detect_amqp_plaintext(host: str, port: int) -> bool:
    """Return True if host:port responds to AMQP 0-9-1 header (plaintext AMQP listener)."""
    try:
        with socket.create_connection((host, port), timeout=AMQP_DETECT_TIMEOUT) as sock:
            sock.sendall(AMQP_HEADER)
            sock.settimeout(AMQP_DETECT_TIMEOUT)
            data = sock.recv(256)
            return len(data) > 0  # any response = AMQP speaker
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False
```

**False-positive risk:** Any TCP service that responds to arbitrary bytes will trigger this. Port specificity (5672 is Kafka's convention) reduces false positives. The HIGH finding message should note the port-based assumption.

**Important note:** The Context.md says "accept any `b'AMQP'` prefix in response" — but the AMQP 0-9-1 Connection.Start frame is binary and does NOT contain the literal bytes `b'AMQP'`. The conservative `len(data) > 0` approach is more reliable. Both are acceptable per D-Claude's-Discretion.

### Pattern 4: Redis Raw TLS Probe (REDIS-01)

**What:** Redis TLS on port 6380 is direct TLS from the first byte. No banner before TLS. Use `ssl.SSLContext.wrap_socket()` as in `tls_capabilities.py:_try_handshake()`.

```python
# Source: tls_capabilities.py lines 39-79 (VERIFIED: file read)
# Redis 6380: TLS is direct from first byte — no pre-TLS banner.
def _probe_redis_tls(host: str, port: int, timeout: int = 5) -> Optional[CryptoEndpoint]:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    server_hostname = host if not _is_ip(host) else None  # SNI only for non-IP
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=server_hostname) as ssock:
                ver = ssock.version()
                cip = ssock.cipher()        # tuple: (name, protocol, bits)
                der = ssock.getpeercert(binary_form=True)
                ep = CryptoEndpoint(host=host, port=port, protocol="REDIS-TLS")
                ep.tls_version = ver
                ep.cipher_suite = cip[0] if cip else None
                if der:
                    from cryptography import x509
                    from cryptography.hazmat.backends import default_backend
                    cert = x509.load_der_x509_certificate(der, default_backend())
                    alg, size = _pubkey_info(cert.public_key())
                    ep.cert_pubkey_alg = alg
                    ep.cert_pubkey_size = size
                    ep.cert_subject = cert.subject.rfc4514_string()
                    ep.cert_issuer = cert.issuer.rfc4514_string()
                return ep
    except ConnectionRefusedError:
        return None   # silent at DEBUG
    except Exception as e:
        ep = CryptoEndpoint(host=host, port=port, protocol="REDIS-TLS")
        ep.scan_error = str(e)
        return ep
```

### Pattern 5: Redis Plaintext Detection (REDIS-02)

**What:** Attempt bare TCP connection to port 6379. If connection succeeds and Redis sends an inline reply or error, emit HIGH finding. No AUTH needed.

```python
REDIS_INLINE_TIMEOUT = 2

def _detect_redis_plaintext(host: str, port: int) -> bool:
    """Return True if host:port responds like a Redis server (plaintext)."""
    try:
        with socket.create_connection((host, port), timeout=REDIS_INLINE_TIMEOUT) as sock:
            # Redis sends nothing on connect; send PING to provoke response.
            sock.sendall(b"PING\r\n")
            sock.settimeout(REDIS_INLINE_TIMEOUT)
            data = sock.recv(64)
            # Redis responds with +PONG\r\n or -NOAUTH\r\n (both valid — server is Redis)
            return data.startswith(b'+') or data.startswith(b'-') or data.startswith(b'*')
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False
```

**Redis inline reply format:** `+PONG\r\n` (no auth required) or `-NOAUTH Authentication required\r\n` (auth required but server is Redis and is in plaintext). Both indicate plaintext Redis → HIGH finding.

### Pattern 6: kafka-python AdminClient Enrichment (KAFKA-04)

**What:** When kafka-python is installed, `KafkaAdminClient.describe_configs()` retrieves broker SSL configuration. Opens a fresh connection to the TLS port (not reusing sslyze probe).

```python
# Source: Context7 /dpkp/kafka-python docs (VERIFIED: fetched)
# Import: from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType
# Note: kafka.protocol.admin.ConfigResource is an older import path; prefer kafka.admin

def _enrich_kafka_admin(host: str, port: int, logger=None) -> dict:
    """Attempt kafka-python AdminClient broker config enrichment. Returns {} on any failure."""
    if not KAFKA_AVAILABLE:
        return {}
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=[f"{host}:{port}"],
            security_protocol="SSL",
            ssl_check_hostname=False,
            ssl_cafile=None,     # accepts self-signed (no CA verification)
            request_timeout_ms=5000,
        )
        # Describe broker 0 (convention for single-broker / first broker)
        result = admin.describe_configs(
            [ConfigResource(ConfigResourceType.BROKER, "0")]
        )
        # result is dict: {ConfigResource(...) -> [ConfigEntry(...)]}
        interesting = {
            "ssl.enabled.protocols", "ssl.cipher.suites", "ssl.client.auth",
            "listeners", "advertised.listeners",
        }
        enrichment = {}
        for config_resource, config_entries in result.items():
            for entry in config_entries:
                if entry.name in interesting:
                    enrichment[entry.name] = entry.value
        admin.close()
        return enrichment
    except Exception as e:
        if logger:
            logger.debug(f"kafka-python enrichment failed for {host}:{port}: {e}")
        return {}
```

**Auth failure handling (D-08):** Any exception (including `NoBrokersAvailable`, `KafkaError`, connection timeout) is caught, logged at DEBUG, and returns `{}`. No finding emitted.

**Multi-broker clusters:** The planner may add a preliminary `admin.describe_cluster()` to enumerate broker IDs, then describe the first N (or just broker 0 as the convention). Depth is Claude's discretion.

### Pattern 7: redis-py CONFIG GET Enrichment (REDIS-03)

**What:** When redis-py is installed, attempt `CONFIG GET tls-*` using glob pattern.

```python
# Source: Context7 /redis/redis-py docs (VERIFIED: fetched)
# Exception hierarchy (VERIFIED: redis/exceptions.py read):
#   AuthenticationError (subclass of ConnectionError) — NOAUTH
#   NoPermissionError (subclass of ResponseError) — NOPERM

def _enrich_redis_config(host: str, port: int, logger=None) -> dict:
    """Attempt redis-py CONFIG GET tls-* enrichment. Returns {} on any failure."""
    if not REDIS_AVAILABLE:
        return {}
    try:
        r = redis_lib.Redis(
            host=host,
            port=port,
            ssl=True,
            ssl_cert_reqs="none",   # accepts self-signed
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        tls_config = r.config_get("tls-*")   # returns dict; Redis supports glob
        r.close()
        return tls_config
    except redis_lib.exceptions.AuthenticationError as e:
        if logger:
            logger.debug(f"redis enrichment NOAUTH for {host}:{port}: {e}")
        return {}
    except redis_lib.exceptions.NoPermissionError as e:
        if logger:
            logger.debug(f"redis enrichment NOPERM for {host}:{port}: {e}")
        return {}
    except Exception as e:
        if logger:
            logger.debug(f"redis enrichment failed for {host}:{port}: {e}")
        return {}
```

**Exception classes (VERIFIED: redis/exceptions.py read):**
- `redis.exceptions.AuthenticationError` — raised for NOAUTH (auth required but not provided); is a subclass of `ConnectionError`
- `redis.exceptions.NoPermissionError` — raised for NOPERM (user lacks permission); is a subclass of `ResponseError`
- Catch both explicitly per D-08 to avoid logging at levels above DEBUG.

### Pattern 8: RabbitMQ Management API (RABBIT-03)

**What:** stdlib urllib.request with Basic auth. `guest:guest` is the default RabbitMQ credential. 401 is informational.

```python
# Source: rabbitmq.com/docs/http-api-reference (VERIFIED: fetched)
# /api/overview returns: rabbitmq_version, erlang_version, node, listeners (list)
# listeners element: {"node": str, "protocol": str, "ip_address": str, "port": int}

import base64
import json
import urllib.request

def _enrich_rabbitmq_mgmt(host: str, port: int = 15672, logger=None) -> dict:
    """GET /api/overview with guest:guest. Returns partial dict on 401 (informational)."""
    url = f"http://{host}:{port}/api/overview"
    credentials = base64.b64encode(b"guest:guest").decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {credentials}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return {
                "rabbitmq_version": data.get("rabbitmq_version"),
                "erlang_version": data.get("erlang_version"),
                "listeners": data.get("listeners", []),
                "node": data.get("node"),
            }
    except urllib.error.HTTPError as e:
        if e.code == 401:
            if logger:
                logger.debug(f"RabbitMQ mgmt API guest:guest rejected on {host}:{port} (401 — informational)")
            return {"mgmt_auth": "rejected_401"}
        if logger:
            logger.debug(f"RabbitMQ mgmt API HTTP error {e.code} on {host}:{port}")
        return {}
    except Exception as e:
        if logger:
            logger.debug(f"RabbitMQ mgmt API failed on {host}:{port}: {e}")
        return {}
```

### Pattern 9: broker_scan_json Aggregation (D-12, D-14)

**What:** Mirrors `email_scanner.py:550-599`. After all three `scan_*_targets()` calls return endpoints, `run_scan.py` aggregates them into the nested `broker_scan_json` dict and attaches it to the first endpoint.

```python
# Source: email_scanner.py lines 550-599 (VERIFIED: file read)
# broker_scan_json shape (D-12):
# {
#   "kafka": [{"host": ..., "port": ..., "tls_version": ..., ...}, ...],
#   "rabbitmq": [...],
#   "redis": [...],
#   "azure_servicebus": [...],
#   "aws_sqs": [...],
#   "session_start": "ISO8601"
# }

# In run_scan.py after all broker scan_*_targets() calls:
def _build_broker_scan_json(
    kafka_endpoints, rabbitmq_endpoints, redis_endpoints,
    azure_endpoints, sqs_endpoints, session_start
) -> str:
    def _ep_dict(ep):
        return {
            "host": getattr(ep, "host", None),
            "port": getattr(ep, "port", None),
            "protocol": getattr(ep, "protocol", None),
            "tls_version": getattr(ep, "tls_version", None),
            "cipher_suite": getattr(ep, "cipher_suite", None),
            "cert_pubkey_alg": getattr(ep, "cert_pubkey_alg", None),
            "cert_subject": getattr(ep, "cert_subject", None),
            "scan_error": getattr(ep, "scan_error", None),
        }
    payload = {
        "kafka": [_ep_dict(ep) for ep in kafka_endpoints],
        "rabbitmq": [_ep_dict(ep) for ep in rabbitmq_endpoints],
        "redis": [_ep_dict(ep) for ep in redis_endpoints],
        "azure_servicebus": [_ep_dict(ep) for ep in azure_endpoints],
        "aws_sqs": [_ep_dict(ep) for ep in sqs_endpoints],
        "session_start": session_start.isoformat() if session_start else None,
    }
    return json.dumps(payload, default=str)

# Attach to first endpoint across all broker endpoints:
all_broker_eps = kafka_endpoints + rabbitmq_endpoints + redis_endpoints + azure_endpoints + sqs_endpoints
if all_broker_eps:
    all_broker_eps[0].broker_scan_json = _build_broker_scan_json(...)
```

**Note:** Unlike email_scanner's per-host aggregation (one JSON per host), broker_scan_json is one JSON per scan run (across all broker types). This matches D-12's "nested per protocol family" shape and D-14's "first endpoint carries full payload."

### Pattern 10: Profile Gating (D-10)

**What:** Mirrors `enable_email` pattern in `profiles.py:apply_profile()` lines 107-129.

```python
# Source: profiles.py lines 107-129 (VERIFIED: file read)
# In apply_profile(), at the end of each profile branch:

if p == "quick":
    # Broker scanner stays disabled for quick profile (D-10)
    pass   # cfg.connectors.enable_broker remains False (default)

elif p == "deep":
    if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_broker"):
        if not cfg.connectors.enable_broker:
            cfg.connectors.enable_broker = True

else:  # standard
    if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_broker"):
        if not cfg.connectors.enable_broker:
            cfg.connectors.enable_broker = True
```

**Config attribute is `cfg.connectors.enable_broker` (NOT `cfg.scanners.broker_enabled`)** — follow the email precedent exactly. The CONTEXT.md says "cfg.scanners.broker_enabled" but the implementation pattern from Phase 32 uses `cfg.connectors.*`. The planner must resolve this against the actual config.py pattern; recommend `cfg.connectors.enable_broker` to stay consistent with `enable_email`.

### Anti-Patterns to Avoid

- **Relying on sslyze for Redis 6380:** sslyze performs a TLS handshake and then attempts to speak the application protocol (or at minimum reads a banner). Redis sends no banner after the TLS handshake until the client sends a command. This causes sslyze's connectivity check to hang or fail. Use raw `ssl.SSLContext.wrap_socket()` instead.
- **Omitting `tls_server_name_indication` from `ServerNetworkConfiguration`:** It is a REQUIRED field with no default (verified via dataclass inspection). Omitting it causes a TypeError at construction time.
- **Passing `network_configuration=None` to `ServerScanRequest` for broker probes:** While the dataclass default is `None`, the email scanner always constructs it explicitly. Follow that pattern.
- **Using `requests` library for RabbitMQ management API:** D-09 prohibits it. Use `urllib.request`.
- **Emitting a finding for enrichment failure:** D-08 requires silent DEBUG on all enrichment failures.
- **Calling `datetime.now()` inside broker_scanner.py:** STRUCT-01 requires `session_start` parameter; no bare `datetime.now()` calls inside the scanner module.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TLS handshake for Kafka/RabbitMQ TLS ports | Custom TLS client | sslyze (already installed) | cert chain, cipher enumeration, TLS version detection — all handled |
| TLS handshake for Redis 6380 | Custom SSL negotiation | `ssl.SSLContext.wrap_socket()` (stdlib `_try_handshake()` pattern) | Already proven in tls_capabilities.py |
| Kafka SSL config metadata | Custom Kafka protocol client | kafka-python AdminClient (import-guarded) | describe_configs() handles protocol framing |
| Redis TLS config metadata | Custom Redis RESP parser | redis-py (import-guarded) | CONFIG GET glob pattern returns dict directly |
| RabbitMQ management API auth | Custom HTTP auth | `urllib.request` + `base64.b64encode` | Standard pattern; no dep needed |
| Per-host JSON aggregation | New aggregation logic | Mirror email_scanner.py:550-599 verbatim | Tested pattern; handles MagicMock edge cases |

**Key insight:** The only genuinely new code in broker_scanner.py is the plaintext detection probes (TCP connect + response check). Everything else is composition of already-proven patterns from email_scanner.py and tls_capabilities.py.

---

## Common Pitfalls

### Pitfall 1: sslyze SNI Not Auto-Derived from Hostname

**What goes wrong:** Developer passes `ServerNetworkLocation(hostname=host, port=port)` without a `ServerNetworkConfiguration`, assuming sslyze uses the hostname as SNI automatically. sslyze's `ServerScanRequest.network_configuration` defaults to `None` in the dataclass, but the connectivity tester still requires a `ServerNetworkConfiguration` with `tls_server_name_indication` set.

**Why it happens:** The `network_configuration=None` default in `ServerScanRequest` is misleading — it suggests the field is optional. In practice, passing `None` causes sslyze to create a default `ServerNetworkConfiguration` but the SNI behavior depends on the sslyze version.

**How to avoid:** Always construct `ServerNetworkConfiguration(tls_server_name_indication=host, ...)` explicitly. The email_scanner.py already does this correctly (lines 134-153). Mirror it verbatim.

**Warning signs:** sslyze returns `ERROR_NO_CONNECTIVITY` for hostnames that should be reachable; TLS handshake succeeds with curl but fails with sslyze.

### Pitfall 2: AMQP Response Frame Is Not ASCII-Prefixed with b'AMQP'

**What goes wrong:** Detection code checks `data.startswith(b'AMQP')` in the server response. This never matches because the AMQP 0-9-1 Connection.Start response is a binary frame starting with `\x01\x00\x00` (frame type, channel bytes).

**Why it happens:** The AMQP header the CLIENT sends is `b'AMQP\x00\x00\x09\x01'`. The SERVER responds with a binary Connection.Start method frame, not with the literal ASCII "AMQP".

**How to avoid:** Use `len(data) > 0` (any response = AMQP speaker on this port) as the detection signal. The port specificity (5672) provides enough false-positive suppression. The CONTEXT.md Claude's Discretion says "accept any `b'AMQP'` prefix in response" — interpret this as "any response that begins with bytes indicating AMQP communication" — `len(data) > 0` satisfies this conservatively.

**Warning signs:** Zero positive detections on a running AMQP broker.

### Pitfall 3: Bitnami Image Env Var Gaps for Cipher/TLS-Version Control

**What goes wrong:** Plan assumes `KAFKA_CFG_SSL_CIPHER_SUITES` and `KAFKA_CFG_SSL_ENABLED_PROTOCOLS` are sufficient to configure weak TLS + cipher suites on bitnami/kafka without bind-mounted config. For bitnami/rabbitmq and bitnami/redis, there are no env vars for cipher suites or TLS versions at all.

**Why it happens:** bitnami/kafka passes `KAFKA_CFG_*` vars to server.properties (this works — [VERIFIED: WebSearch + MEDIUM confidence from multiple bitnami issues]), but bitnami/rabbitmq only supports `RABBITMQ_SSL_CERT_FILE`, `RABBITMQ_SSL_KEY_FILE`, `RABBITMQ_SSL_CA_FILE` — no cipher/version env vars [VERIFIED: bitnami/rabbitmq README fetched]. bitnami/redis similarly has no cipher env vars [VERIFIED: bitnami/redis README fetched].

**How to avoid:**
- For Kafka: Use `bitnami/kafka:3.7` with `KAFKA_CFG_SSL_CIPHER_SUITES` and `KAFKA_CFG_SSL_ENABLED_PROTOCOLS=TLSv1.1,TLSv1.2`. Works via the `KAFKA_CFG_` passthrough mechanism.
- For RabbitMQ: **Use official `rabbitmq:3.12-management`** (as in REQUIREMENTS.md BROKER-LAB-01), not bitnami/rabbitmq. The official image's `rabbitmq.conf` can be bind-mounted for cipher/TLS-version control. Alternative: use bitnami/rabbitmq with a bind-mounted `rabbitmq.conf` (contradicts D-15 but is the only viable path for cipher control).
- For Redis: **Use official `redis:7-alpine`** (as in REQUIREMENTS.md BROKER-LAB-01) with bind-mounted `redis.conf`. bitnami/redis has no cipher env vars.

**Warning signs:** Lab RabbitMQ and Redis accept strong TLS 1.3 connections instead of weak TLS, so no weak-cipher findings fire.

### Pitfall 4: kafka-python Import Path Instability

**What goes wrong:** `from kafka.protocol.admin import ConfigResource` (older path shown in some Context7 examples) works in some versions of kafka-python but not others.

**Why it happens:** kafka-python reorganized its admin API between versions.

**How to avoid:** Use `from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType` — this is the stable public API path. Guard with the module-level `KAFKA_AVAILABLE` flag pattern (see Pattern 1).

### Pitfall 5: redis-py CONFIG GET Returns Empty Dict for Non-TLS Redis

**What goes wrong:** `r.config_get("tls-*")` returns `{}` even on a running Redis because the instance has no TLS configured. This is correct behavior but can be confused with an error.

**Why it happens:** Redis CONFIG GET returns only keys that are set. If TLS is not configured, no `tls-*` keys exist, so the result is `{}`.

**How to avoid:** Treat `{}` as "no TLS configured" (informational, not an error). Only emit enrichment data if the dict is non-empty. The detection of plaintext Redis (REDIS-02) is separate from the enrichment.

### Pitfall 6: CONTEXT.md vs. REQUIREMENTS.md Image Conflict

**What goes wrong:** D-15 says bitnami images for all three brokers with env-var-only config. REQUIREMENTS.md BROKER-LAB-01 says `rabbitmq:3.12-management` and `redis:7-alpine` (official images, which DO require redis.conf for weak cipher config). Using bitnami/rabbitmq and bitnami/redis without config file overlays produces a lab that accepts strong TLS only — no weak-cipher findings.

**How to avoid:** The planner must choose and document: (a) use official images as REQUIREMENTS.md specifies (allows bind-mounted configs for weak TLS), or (b) use bitnami images but accept bind-mounted config files (contradicts D-15 "no bind-mounted config files"). Recommendation: use official images per REQUIREMENTS.md; update D-15 in plan comments.

---

## Chaos Lab: Bitnami/Official Image Configuration Details

### Kafka (bitnami/kafka:3.7, KRaft mode)

**TLS env vars that work via `KAFKA_CFG_` passthrough [MEDIUM confidence — VERIFIED via WebSearch]:**

```yaml
environment:
  - KAFKA_CFG_PROCESS_ROLES=broker,controller
  - KAFKA_CFG_NODE_ID=1
  - KAFKA_CFG_CONTROLLER_QUORUM_VOTERS=1@kafka:9094
  - KAFKA_CFG_LISTENERS=PLAINTEXT://:29092,SSL://:29093,CONTROLLER://:9094
  - KAFKA_CFG_ADVERTISED_LISTENERS=PLAINTEXT://localhost:29092,SSL://localhost:29093
  - KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,SSL:SSL,CONTROLLER:CONTROLLER
  - KAFKA_CFG_INTER_BROKER_LISTENER_NAME=SSL
  - ALLOW_PLAINTEXT_LISTENER=yes
  # Weak TLS config:
  - KAFKA_CFG_SSL_ENABLED_PROTOCOLS=TLSv1.1,TLSv1.2
  - KAFKA_CFG_SSL_CIPHER_SUITES=TLS_RSA_WITH_AES_128_CBC_SHA,TLS_RSA_WITH_AES_256_CBC_SHA
  - KAFKA_TLS_TYPE=PEM
  - KAFKA_TLS_CLIENT_AUTH=none
  - KAFKA_CFG_SSL_KEYSTORE_LOCATION=/opt/bitnami/kafka/config/certs/kafka.keystore.pem
  - KAFKA_CFG_SSL_TRUSTSTORE_LOCATION=/opt/bitnami/kafka/config/certs/kafka.truststore.pem
```

**Cert generation (Makefile):**
```makefile
kafka-certs:
    openssl req -x509 -newkey rsa:2048 -keyout certs/kafka.key \
        -out certs/kafka.crt -days 3650 -nodes \
        -subj "/CN=kafka.chaos.local"
    # PEM format keystore = key + cert concatenated (bitnami PEM mode)
    cat certs/kafka.key certs/kafka.crt > certs/kafka.keystore.pem
    cp certs/kafka.crt certs/kafka.truststore.pem
```

**Volume mounts:** Certs only (key+cert PEMs). No server.properties mount needed.

### RabbitMQ (rabbitmq:3.12-management — official image, per REQUIREMENTS.md)

**Weak TLS requires `rabbitmq.conf` overlay [VERIFIED: bitnami/rabbitmq README — no cipher env vars exist]:**

```
# labs/broker/rabbitmq/rabbitmq.conf
listeners.tcp.default = 5672
listeners.ssl.default = 5671

ssl_options.cacertfile = /etc/rabbitmq/certs/ca.crt
ssl_options.certfile   = /etc/rabbitmq/certs/server.crt
ssl_options.keyfile    = /etc/rabbitmq/certs/server.key
ssl_options.verify     = verify_none
ssl_options.fail_if_no_peer_cert = false

# Weak TLS config:
ssl_options.versions.1 = tlsv1
ssl_options.versions.2 = tlsv1.1
ssl_options.versions.3 = tlsv1.2
ssl_options.ciphers.1 = DES-CBC3-SHA
ssl_options.ciphers.2 = AES128-SHA
ssl_options.ciphers.3 = AES256-SHA

management.listener.port = 15672
```

```yaml
environment:
  - RABBITMQ_CONFIG_FILE=/etc/rabbitmq/rabbitmq.conf
volumes:
  - ./rabbitmq/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro
  - ./certs/rabbitmq.crt:/etc/rabbitmq/certs/server.crt:ro
  - ./certs/rabbitmq.key:/etc/rabbitmq/certs/server.key:ro
  - ./certs/rabbitmq.crt:/etc/rabbitmq/certs/ca.crt:ro  # self-signed = CA
```

### Redis (redis:7-alpine — official image, per REQUIREMENTS.md)

**Weak TLS requires `redis.conf` overlay [VERIFIED: bitnami/redis README — no cipher env vars]:**

```
# labs/broker/redis/redis.conf
port 6379          # plaintext port
tls-port 6380      # TLS port
tls-cert-file /etc/redis/certs/redis.crt
tls-key-file  /etc/redis/certs/redis.key
tls-ca-cert-file /etc/redis/certs/redis.crt   # self-signed = CA
tls-auth-clients no
tls-protocols "TLSv1.2"
tls-ciphers "DES-CBC3-SHA:AES128-SHA:AES256-SHA"
tls-prefer-server-ciphers yes
```

```yaml
command: redis-server /etc/redis/redis.conf
volumes:
  - ./redis/redis.conf:/etc/redis/redis.conf:ro
  - ./certs/redis.crt:/etc/redis/certs/redis.crt:ro
  - ./certs/redis.key:/etc/redis/certs/redis.key:ro
```

**Note:** This requires a bind-mounted `redis.conf` — acceptable for the official `redis:7-alpine` image; this is the standard Redis TLS configuration method. The bitnami/redis alternative would need the same overlay and is NOT preferred (use official image per REQUIREMENTS.md).

---

## Code Examples

### sslyze Scan for Any Direct-TLS Broker Port

```python
# Source: email_scanner.py lines 134-156 (VERIFIED), sslyze dataclass inspection (VERIFIED)
from sslyze import (
    Scanner as SslyzeScanner,
    ServerScanRequest,
    ServerNetworkLocation,
    ServerNetworkConfiguration,
    ScanCommand,
    ScanCommandAttemptStatusEnum,
    ServerScanStatusEnum,
)

net_cfg = ServerNetworkConfiguration(
    tls_server_name_indication=host,   # REQUIRED — must be explicit
    network_timeout=timeout,
)
scan_request = ServerScanRequest(
    server_location=ServerNetworkLocation(hostname=host, port=port),
    network_configuration=net_cfg,
    scan_commands={
        ScanCommand.CERTIFICATE_INFO,
        ScanCommand.TLS_1_2_CIPHER_SUITES,
        ScanCommand.TLS_1_3_CIPHER_SUITES,
    },
)
```

### kafka-python AdminClient with SSL

```python
# Source: Context7 /dpkp/kafka-python (VERIFIED: fetched)
from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType

admin = KafkaAdminClient(
    bootstrap_servers=[f"{host}:{port}"],
    security_protocol="SSL",
    ssl_check_hostname=False,
    ssl_cafile=None,
    request_timeout_ms=5000,
)
result = admin.describe_configs(
    [ConfigResource(ConfigResourceType.BROKER, "0")]
)
admin.close()
```

### redis-py SSL Connection + CONFIG GET

```python
# Source: Context7 /redis/redis-py (VERIFIED: fetched)
import redis

r = redis.Redis(
    host=host,
    port=6380,
    ssl=True,
    ssl_cert_reqs="none",
    socket_timeout=5,
)
tls_config = r.config_get("tls-*")   # returns dict; {} if no TLS keys configured
```

### RabbitMQ Management API

```python
# Source: rabbitmq.com/docs/http-api-reference (VERIFIED: fetched)
import base64, json, urllib.request

url = f"http://{host}:15672/api/overview"
credentials = base64.b64encode(b"guest:guest").decode()
req = urllib.request.Request(url, headers={"Authorization": f"Basic {credentials}"})
# Response fields: rabbitmq_version, erlang_version, node, listeners (list of dicts)
```

---

## Integration Points Checklist

All file changes required for Phase 33:

| File | Change | Pattern Source |
|------|--------|----------------|
| `quirk/scanner/broker_scanner.py` | NEW — BROKER-ARCH single file | db_connector.py structure + email_scanner.py function shape |
| `quirk/db.py` | Add `_ensure_broker_columns()` + call in `init_db()` | `_ensure_email_columns()` lines 109-126 (VERIFIED) |
| `quirk/models.py` | Add `broker_scan_json = Column(Text, nullable=True)` | Line 85 email_scan_json pattern (VERIFIED) |
| `quirk/config.py` | Add `enable_broker: bool = False` to `ConnectorsCfg` + `broker_azure_namespaces: list = field(...)` + `broker_sqs_regions: list = field(...)` | `enable_email: bool = False` line 101 (VERIFIED) |
| `quirk/engine/profiles.py` | Add `enable_broker` gating in `apply_profile()` | Lines 107-129 email pattern (VERIFIED) |
| `quirk/engine/risk_engine.py` | Add `evaluate_broker_endpoints()` for finding IDs: `kafka-plaintext-listener`, `amqp-plaintext-listener`, `redis-plaintext-no-auth`, `weak-cipher` | `evaluate_email_endpoints()` pattern (VERIFIED from 32-PATTERNS.md) |
| `run_scan.py` | Add broker scan block after email block; add `broker_scan_json` aggregation call; extend endpoint list | Lines 691-713 email pattern (VERIFIED) |
| `quirk/scanner/__init__.py` | Register broker_scanner (currently empty — 1 line file) | N/A — currently `pass` only |
| `pyproject.toml` | Add `[kafka]` and `[redis]` sub-extras; clean up `[motion]` comment | Existing structure (VERIFIED) |
| `quirk/config_template.yaml` | Add `scanners.broker` defaults block | Existing email defaults pattern |
| `labs/broker/docker-compose.yml` | New compose file with profile `broker` | labs/email/docker-compose.yml (if it exists) or quantum-chaos-enterprise-lab structure |
| `labs/broker/Makefile` | Cert generation for kafka, rabbitmq, redis | labs/email/Makefile pattern (VERIFIED) |
| `labs/broker/expected_results.md` | BROKER-LAB-02 expected findings | labs/email/expected_results.md (VERIFIED exists) |
| CLI module | Add `--azure-servicebus-namespace` + `--aws-sqs-region` flags | Existing flag patterns |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Zookeeper-dependent Kafka | KRaft mode (no Zookeeper) | Kafka 3.x+ | bitnami/kafka:3.7 uses KRaft by default; no Zookeeper container needed in lab |
| JKS keystores for Kafka TLS | PEM format supported (`KAFKA_TLS_TYPE=PEM`) | bitnami/kafka recent | Simplifies cert generation; no keytool needed |
| kafka-python legacy admin | `from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType` | kafka-python 2.x | Stable public API; `kafka.protocol.admin.ConfigResource` is older path |
| redis-py v3 | redis-py v5+ | redis-py 5.0 | `ssl_cert_reqs="none"` still works; `ssl_min_version` added for TLS floor control |
| sslyze custom SNI | Always explicit `tls_server_name_indication` | sslyze 5+ | `tls_server_name_indication` is REQUIRED in ServerNetworkConfiguration |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `KAFKA_CFG_SSL_CIPHER_SUITES` and `KAFKA_CFG_SSL_ENABLED_PROTOCOLS` are passed through to server.properties by bitnami/kafka:3.7 | Chaos Lab — Kafka | Lab produces strong TLS only; no weak-cipher findings; lab is non-functional for BROKER-LAB-02 |
| A2 | `kafka.admin.ConfigResourceType.BROKER` is the correct enum value for broker-level describe_configs | Pattern 6 | AdminClient enrichment returns empty or raises; KAFKA-04 silently non-functional |
| A3 | sslyze 6.2.0 will successfully complete a TLS scan against port 9093 (Kafka) and 5671 (AMQPS) treating them like any other TLS port | Patterns 2, sslyze section | sslyze fails on these ports if it expects application-layer data after handshake; fallback would be raw ssl probe |
| A4 | RabbitMQ Connection.Start frame does NOT start with literal bytes `b'AMQP'` | Pattern 3 | AMQP detection never fires; RABBIT-02 silently broken |
| A5 | `cfg.connectors.enable_broker` is the correct config path (vs `cfg.scanners.broker_enabled` mentioned in CONTEXT.md D-10) | Pattern 10, config.py | If wrong namespace, profile gating fails silently; broker scanner never runs |

**Note on A5:** CONTEXT.md D-10 says "`cfg.scanners.broker_enabled` flag" but no `cfg.scanners` namespace exists in `quirk/config.py` (VERIFIED: file read). The correct namespace based on Phase 32 precedent is `cfg.connectors.enable_broker`. The planner should use `cfg.connectors.enable_broker` and note the correction.

---

## Open Questions

1. **Kafka plaintext detection depth (KAFKA-02)**
   - What we know: TCP connect to 9092 suffices; Kafka sends no banner. Port convention is strong.
   - What's unclear: Should the scanner send an ApiVersions request (API key 18, 10-byte minimal frame) to confirm the service is truly Kafka vs. any TCP listener? Or is TCP connect + port 9092 assumption sufficient?
   - Recommendation: Conservative approach — TCP connect success on port 9092 = HIGH finding `kafka-plaintext-listener`. The finding message should state "TCP port 9092 open and accepting connections (Kafka plaintext convention)". This matches REQUIREMENTS.md KAFKA-02: "emits a HIGH finding if port is open" — no protocol confirmation required.

2. **broker_scan_json attachment point**
   - What we know: D-14 says "first endpoint of the first host carries full nested payload; other endpoints carry NULL." But the nested shape aggregates ALL broker types in one JSON — not per-host.
   - What's unclear: Which endpoint is "first" when kafka/rabbitmq/redis endpoints are all in the same list?
   - Recommendation: Sort all broker endpoints by (protocol_family_index, host, port); attach the full nested JSON to `all_broker_endpoints[0]` (the single first endpoint across all families). All other broker endpoints have `broker_scan_json = NULL`. This gives run_scan.py a clean single-row attachment point.

3. **Azure Service Bus + AWS SQS port allocation in scan_rabbitmq_targets() signature**
   - What we know: D-03 folds Azure SB into scan_rabbitmq_targets(); D-04 folds AWS SQS similarly.
   - What's unclear: The function signature currently implied by BROKER-ARCH is `scan_rabbitmq_targets(targets, session_start, ...)`. Azure SB namespaces and SQS regions are NOT part of `targets` (which is the self-hosted host list).
   - Recommendation: `scan_rabbitmq_targets(targets, azure_namespaces=None, sqs_regions=None, session_start=None, ...)`. The planner may also split into a separate `scan_cloud_broker_targets()` helper per CONTEXT.md Claude's Discretion.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| sslyze | KAFKA-01, RABBIT-01, RABBIT-04, RABBIT-05 | ✓ | 6.2.0 | Raw ssl.SSLContext fallback (already proven) |
| kafka-python | KAFKA-04 (optional) | ✗ | — | Module absent path — return basic TLS probe only |
| redis-py | REDIS-03 (optional) | ✗ | — | Module absent path — return basic TLS probe only |
| Docker (for lab) | BROKER-LAB-01 | ✓ | (project has existing labs) | — |
| openssl CLI | Makefile cert gen | ✓ | (system openssl) | — |

**Missing dependencies with no fallback:** None — all core probes use stdlib or already-installed sslyze.

**Missing dependencies with fallback:** kafka-python and redis-py are optional sub-extras with graceful degradation paths documented in D-07.

---

## Validation Architecture

`workflow.nyquist_validation` is enabled (absent key = enabled per config.json).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing project test suite) |
| Config file | pytest.ini or pyproject.toml [tool.pytest] — check project root |
| Quick run command | `python -m pytest tests/test_broker_scanner.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STRUCT-01 | broker_scanner functions accept `session_start`; ep.scanned_at matches it | unit | `pytest tests/test_broker_scanner.py::test_session_start_propagation -x` | ❌ Wave 0 |
| STRUCT-02 | `[kafka]` and `[redis]` extras present in pyproject.toml | unit/smoke | `pytest tests/test_broker_scanner.py::test_pyproject_extras -x` or manual inspect | ❌ Wave 0 |
| BROKER-00 | `broker_scan_json` column added idempotently | unit | `pytest tests/test_broker_scanner.py::test_broker_scan_json_migration -x` | ❌ Wave 0 |
| BROKER-ARCH | `broker_scanner.py` exposes 3 functions with correct signatures | unit | `pytest tests/test_broker_scanner.py::test_module_api -x` | ❌ Wave 0 |
| KAFKA-01 | sslyze TLS probe on port 9093 returns CryptoEndpoint with tls_version | unit (mock sslyze) | `pytest tests/test_broker_scanner.py::test_kafka_tls_probe -x` | ❌ Wave 0 |
| KAFKA-02 | Plaintext Kafka on 9092: TCP connect → kafka-plaintext-listener HIGH finding | unit (mock socket) | `pytest tests/test_broker_scanner.py::test_kafka_plaintext_detection -x` | ❌ Wave 0 |
| KAFKA-02 | Connection refused on 9092: no finding, no crash | unit (mock socket) | `pytest tests/test_broker_scanner.py::test_kafka_plaintext_refused -x` | ❌ Wave 0 |
| KAFKA-04 | kafka-python absent: enrichment silently skipped | unit | `pytest tests/test_broker_scanner.py::test_kafka_enrich_absent -x` | ❌ Wave 0 |
| KAFKA-04 | kafka-python auth failure: DEBUG log, no finding, no crash | unit (mock kafka) | `pytest tests/test_broker_scanner.py::test_kafka_enrich_auth_failure -x` | ❌ Wave 0 |
| RABBIT-01 | sslyze TLS probe on port 5671 returns CryptoEndpoint | unit (mock sslyze) | `pytest tests/test_broker_scanner.py::test_rabbitmq_tls_probe -x` | ❌ Wave 0 |
| RABBIT-02 | Plaintext AMQP on 5672: AMQP header → response → amqp-plaintext-listener finding | unit (mock socket) | `pytest tests/test_broker_scanner.py::test_amqp_plaintext_detection -x` | ❌ Wave 0 |
| RABBIT-03 | Management API 200 → rabbitmq_version + listeners in enrichment | unit (mock urllib) | `pytest tests/test_broker_scanner.py::test_rabbitmq_mgmt_success -x` | ❌ Wave 0 |
| RABBIT-03 | Management API 401 → informational, no crash | unit (mock urllib) | `pytest tests/test_broker_scanner.py::test_rabbitmq_mgmt_401 -x` | ❌ Wave 0 |
| RABBIT-04 | Azure SB sslyze probe with correct SNI | unit (mock sslyze) | `pytest tests/test_broker_scanner.py::test_azure_sb_probe -x` | ❌ Wave 0 |
| RABBIT-05 | AWS SQS sslyze probe with correct SNI | unit (mock sslyze) | `pytest tests/test_broker_scanner.py::test_aws_sqs_probe -x` | ❌ Wave 0 |
| REDIS-01 | Raw ssl.SSLContext probe on 6380 returns TLS version + cipher | unit (mock ssl) | `pytest tests/test_broker_scanner.py::test_redis_tls_probe -x` | ❌ Wave 0 |
| REDIS-02 | Plaintext Redis on 6379: PING → PONG/-NOAUTH → redis-plaintext-no-auth finding | unit (mock socket) | `pytest tests/test_broker_scanner.py::test_redis_plaintext_detection -x` | ❌ Wave 0 |
| REDIS-03 | redis-py absent: enrichment silently skipped | unit | `pytest tests/test_broker_scanner.py::test_redis_enrich_absent -x` | ❌ Wave 0 |
| REDIS-03 | redis-py NOAUTH: DEBUG log, no finding | unit (mock redis) | `pytest tests/test_broker_scanner.py::test_redis_enrich_noauth -x` | ❌ Wave 0 |
| D-12 | broker_scan_json is nested per protocol family | unit | `pytest tests/test_broker_scanner.py::test_broker_scan_json_shape -x` | ❌ Wave 0 |
| D-14 | First broker endpoint carries JSON, others are NULL | unit | `pytest tests/test_broker_scanner.py::test_broker_json_attachment -x` | ❌ Wave 0 |
| BROKER-LAB-01 | All 3 lab containers up; plaintext ports accessible; TLS ports negotiate weak ciphers | integration (lab) | `docker compose --profile broker up -d && python -m quirk scan ...` | ❌ Wave 0 |
| BROKER-LAB-02 | expected_results.md matches actual scan output from broker lab | manual | Manual comparison after lab run | N/A (manual) |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_broker_scanner.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_broker_scanner.py` — covers all BROKER-ARCH, KAFKA, RABBIT, REDIS requirements (unit, mocked)
- [ ] `labs/broker/docker-compose.yml` — integration test target
- [ ] `labs/broker/Makefile` — cert generation
- [ ] `labs/broker/expected_results.md` — BROKER-LAB-02 document
- [ ] pyproject.toml update — `[kafka]` and `[redis]` sub-extras

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Scanner uses no auth (probes are agentless TLS checks) |
| V3 Session Management | No | No sessions created by scanner |
| V4 Access Control | No | Scanner reads only; no write operations |
| V5 Input Validation | Yes | Hostname/namespace/region inputs from CLI/config must be validated; no SQL injection (column names follow _SAFE_COL_RE pattern) |
| V6 Cryptography | Yes | ssl.CERT_NONE used for probing (intentional — probing untrusted/self-signed certs); never hand-roll TLS |

### Known Threat Patterns for Broker Scanner Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hostname injection via `--azure-servicebus-namespace` | Tampering | Validate namespace matches `[a-zA-Z0-9-]+` before constructing hostname |
| SSRF via constructed cloud hostnames | Tampering | Only allow well-formed namespace/region inputs; construct hostnames server-side |
| Logging sensitive enrichment data | Information Disclosure | Log at DEBUG only; don't log cert private key material |
| Port 15672 probes logged in RabbitMQ management audit | Repudiation | D-11 acknowledged; covered by engagement letter assumption |

---

## Sources

### Primary (HIGH confidence)

- `quirk/scanner/email_scanner.py` — 4-function-per-protocol shape; per-host JSON aggregation (lines 550-599); sslyze probe pattern (lines 112-280) [VERIFIED: file read]
- `quirk/scanner/db_connector.py` — BROKER-ARCH architectural precedent; optional import guard pattern; multi-protocol single-file shape [VERIFIED: file read]
- `quirk/scanner/tls_capabilities.py` — `_try_handshake()` raw ssl.SSLContext pattern for Redis 6380 probe [VERIFIED: file read]
- `quirk/engine/profiles.py` — `apply_profile()` email_enabled pattern (lines 107-129) [VERIFIED: file read]
- `quirk/config.py` — `ConnectorsCfg` field pattern; `enable_email: bool = False` [VERIFIED: file read]
- `quirk/db.py` — `_ensure_email_columns()` migration pattern (lines 109-126) [VERIFIED: file read]
- `quirk/models.py` — `email_scan_json` column addition at line 85 [VERIFIED: file read]
- sslyze 6.2.0 dataclass inspection — `ServerNetworkConfiguration.tls_server_name_indication` is REQUIRED with no default; `ServerScanRequest.network_configuration` defaults to None [VERIFIED: `.venv/bin/python3 -c "import dataclasses; from sslyze import ..."` executed]
- `.planning/phases/32-email-scanner/32-PATTERNS.md` — complete pattern map for all 9 Phase 32 files [VERIFIED: file read]
- Context7 `/redis/redis-py` — ssl connection, config_get, exception hierarchy [VERIFIED: fetched]
- Context7 `/dpkp/kafka-python` — KafkaAdminClient, describe_configs, ConfigResource, SSL parameters [VERIFIED: fetched]
- `redis/exceptions.py` (GitHub) — AuthenticationError subclasses ConnectionError; NoPermissionError subclasses ResponseError [VERIFIED: fetched]
- `rabbitmq.com/docs/http-api-reference` — /api/overview response fields [VERIFIED: fetched]

### Secondary (MEDIUM confidence)

- bitnami/kafka README (GitHub) — `KAFKA_CFG_SSL_ENABLED_PROTOCOLS` and `KAFKA_CFG_SSL_CIPHER_SUITES` work via `KAFKA_CFG_` passthrough; `KAFKA_TLS_TYPE=PEM` supported [VERIFIED: WebSearch + bitnami README fetch, corroborated by multiple bitnami GitHub issues]
- bitnami/rabbitmq README (GitHub) — No cipher or TLS-version env vars; only cert file paths [VERIFIED: fetched]
- bitnami/redis README (GitHub) — `REDIS_TLS_ENABLED`, `REDIS_TLS_PORT_NUMBER`, `REDIS_TLS_CERT_FILE`, `REDIS_TLS_KEY_FILE`, `REDIS_TLS_CA_FILE` — no cipher or TLS-version control env vars [VERIFIED: fetched]
- AMQP 0-9-1 spec — protocol header `b'AMQP\x00\x00\x09\x01'`; Connection.Start response is binary frame, not ASCII-prefixed [CITED: rabbitmq.com/resources/specs/amqp0-9-1.pdf; CITED: WebSearch result from rabbitmq AMQP spec GitHub]

### Tertiary (LOW confidence)

- `bitnami/kafka:3.7 KRaft mode` — exact env var names for KRaft listeners configuration require validation against current bitnami docs or the container itself [ASSUMED: based on bitnami/kafka issue threads and KAFKA_CFG_ passthrough mechanism]

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — sslyze version confirmed installed; stdlib patterns verified in codebase; kafka-python/redis-py API confirmed via Context7
- Architecture: HIGH — db_connector.py and email_scanner.py patterns fully read and documented; sslyze dataclass fields verified via Python introspection in project venv
- Pitfalls: HIGH for sslyze SNI (verified via code), HIGH for AMQP frame format (verified via spec), MEDIUM for bitnami cipher env vars (verified via README fetch but not live-tested)
- Chaos lab: MEDIUM — bitnami/kafka env vars confirmed via multiple corroborating sources; RabbitMQ and Redis require config file overlays (not bitnami, official images)

**Research date:** 2026-04-27
**Valid until:** 2026-05-27 (sslyze API stable; bitnami image env vars may change with new releases)
