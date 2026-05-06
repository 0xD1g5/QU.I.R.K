# Redis TLS Scanning and Message Broker Architecture Research

**Project:** QU.I.R.K. v4.4 Data in Motion milestone
**Researched:** 2026-04-27
**Scope:** Redis TLS probe mechanics, broker scanner architecture, SQLite schema, evidence counter naming

---

## Q1: Redis TLS Probe — Best Python Approach

**Recommendation: Raw `ssl` socket probe (same pattern as `tls_capabilities.py`) for TLS enumeration, with optional `redis-py` for CONFIG GET.**

### Option Comparison

| Approach | What you get | Auth barrier | Verdict |
|---|---|---|---|
| Raw `ssl` socket wrap on port 6380 | TLS version, cipher tuple, peer cert (DER) | None — handshake completes before any Redis command | **Primary path** |
| `sslyze` ServerScanRequest on port 6380 | Full sslyze cipher suite enumeration | None — sslyze works at TLS level | Good for deep mode, but adds latency overhead |
| `redis-py` with `ssl=True` | TLS version + cipher via `.connection_pool` internals; CONFIG GET for config | Blocked by `requirepass` / ACL NOPERM before CONFIG GET | Secondary path; config read only |

### Recommended Primary Probe — Raw SSL Socket

The existing `tls_capabilities.py` `_try_handshake()` pattern is directly reusable. A raw TLS handshake to port 6380 gives:

```python
import socket
import ssl
from cryptography import x509
from cryptography.hazmat.backends import default_backend

def probe_redis_tls(host: str, port: int = 6380, timeout: int = 5):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # fingerprint without validation for scanning

    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            tls_version = ssock.version()          # e.g. "TLSv1.2", "TLSv1.3"
            cipher = ssock.cipher()                # ("ECDHE-RSA-AES256-GCM-SHA384", "TLSv1.2", 256)
            der_cert = ssock.getpeercert(binary_form=True)

    cert = x509.load_der_x509_certificate(der_cert, default_backend())
    # Now extract: cert.subject, cert.issuer, cert.not_valid_after_utc,
    # cert.signature_hash_algorithm, cert.public_key() for key type/size
    return tls_version, cipher, cert
```

This is identical in structure to `_try_handshake()` in `tls_capabilities.py`. No new library dependency.

**After the raw socket probe you know:**
- TLS version negotiated (what the server accepted)
- Cipher suite name, protocol string, bit strength
- Full peer certificate: subject, issuer, SANs, not-after, sig alg, pubkey type+size
- Whether the port is TLS at all (ConnectionRefused / "WRONG_VERSION_NUMBER" if not)

### sslyze Handoff (Deep Mode)

sslyze's `ServerScanRequest` works on any TCP port — it does direct TLS, not STARTTLS. Point it at port 6380 identically to how the existing `tls_scanner.py` points it at port 443:

```python
from sslyze import ServerNetworkLocation, ServerScanRequest, ScanCommand

location = ServerNetworkLocation(hostname="redis.internal", port=6380)
request = ServerScanRequest(server_location=location, scan_commands={
    ScanCommand.CERTIFICATE_INFO,
    ScanCommand.TLS_1_2_CIPHER_SUITES,
    ScanCommand.TLS_1_3_CIPHER_SUITES,
})
```

sslyze does **not** have a Redis-specific STARTTLS handler (it handles SMTP, IMAP, XMPP, LDAP, POP3, FTP, RDP, Postgres only). Direct TLS (as Redis uses on port 6380) needs no STARTTLS negotiation — sslyze will connect and run cipher enumeration normally.

**Recommendation:** use raw `ssl` probe as fast path (always runs), optionally hand off to sslyze when `scan_mode == "deep"` — matching the existing tls_scanner pattern.

### Auth Barrier Reality

The TLS handshake completes before Redis sends its greeting or requires AUTH. The scanner gets full cert+cipher data with zero authentication. The barrier only appears if you then try to issue Redis commands over that TLS socket (PING, CONFIG GET). That second step is optional — TLS metadata is already extracted.

**Confidence:** HIGH — based on Python `ssl` stdlib docs and Redis TLS architecture (TLS layer is transport, not application-level auth).

---

## Q2: Redis TLS Config Surface — Security-Relevant Settings

Based on `redis.conf` (Redis 7 unstable, verified via raw GitHub source):

| Directive | Security Relevance | Scanner Behavior |
|---|---|---|
| `tls-port` | Non-zero = TLS is active | Port probe confirms TLS presence |
| `tls-protocols` | e.g. "TLSv1.2 TLSv1.3" — TLS 1.0/1.1 enabled is HIGH | Detectable via constrained-version handshake probes |
| `tls-ciphers` | TLS ≤1.2 cipher list; includes RC4/DES = CRITICAL | Detectable via cipher-restricted handshake probes |
| `tls-ciphersuites` | TLS 1.3 suite list | Only three standard suites exist; safe by default |
| `tls-auth-clients` | "no" means no mTLS requirement; "yes" requires client cert | Client cert rejection during probe = mTLS required |
| `tls-prefer-server-ciphers` | "yes" = server controls cipher order (good) | Not directly externally detectable |
| `tls-key-file` / `tls-cert-file` | Cert quality (RSA key size, sig alg) | Extracted from handshake cert |
| `tls-replication` / `tls-cluster` | Internal-use; not externally detectable without config read | Out of scope for agentless scanner |

**Key insight:** The most security-relevant directives (`tls-protocols`, `tls-ciphers`) are **detectable externally** by attempting handshakes constrained to specific versions/ciphers — exactly what `tls_capabilities.py` `enumerate_tls_capabilities()` already does. No CONFIG GET needed.

The difference between a server with `tls-protocols TLSv1` and one with `tls-protocols TLSv1.3` is fully observable via external probe:

```python
# Try constrained handshake at TLS 1.0
ok, ver, _ = _try_handshake(host, 6380, timeout=5, include_sni=True,
                             tls_min=ssl.TLSVersion.TLSv1,
                             tls_max=ssl.TLSVersion.TLSv1)
if ok:
    # Server accepted TLS 1.0 -> CRITICAL/HIGH finding
```

**What you cannot determine externally:** `tls-auth-clients` value (unless you actually attempt a connection without a client cert and observe whether it's required — but the probe already does this and maps it to `MTLS_REQUIRED`).

**Confidence:** HIGH — based on Redis docs and Python ssl stdlib behavior.

---

## Q3: Redis CONFIG GET Approach

### What CONFIG GET Returns

`CONFIG GET tls-*` returns key-value pairs for all TLS parameters. For example:
```
redis-cli --tls --cacert ca.crt CONFIG GET tls-protocols
# -> ["tls-protocols", "TLSv1.2 TLSv1.3"]
```

**CONFIG GET is categorized `@admin @slow @dangerous` in Redis ACL.** This means:

1. **No auth configured:** CONFIG GET succeeds over a plain socket or a TLS socket.
2. **`requirepass` set:** Every command before AUTH returns `NOAUTH Authentication required`. CONFIG GET fails.
3. **ACL configured (Redis 6+):** Default user may have CONFIG GET blocked. Returns `NOPERM this user has no permissions to run the 'config|get' command`.
4. **ACL disabled (default Redis 6 fresh install):** Default user has all permissions — CONFIG GET works.

### Python Implementation with redis-py

```python
import redis

def get_redis_tls_config(host: str, port: int, password: str | None = None,
                          use_tls: bool = True, ca_certs: str | None = None):
    try:
        r = redis.Redis(
            host=host,
            port=port,
            password=password,
            ssl=use_tls,
            ssl_cert_reqs="none",       # scanner has no client cert
            ssl_ca_certs=ca_certs,      # optional CA bundle
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        raw = r.config_get("tls-*")
        # raw = {"tls-protocols": "TLSv1.2 TLSv1.3", "tls-ciphers": "DEFAULT:!MEDIUM", ...}
        return raw
    except redis.exceptions.AuthenticationError:
        # NOAUTH or WRONGPASS — auth required
        return None
    except redis.exceptions.NoPermissionError:
        # NOPERM — ACL blocks CONFIG GET
        return None
    except Exception:
        return None
```

**Fallback strategy:** If CONFIG GET fails (auth/NOPERM), rely entirely on external probe results. The scanner should not require CONFIG GET access — it's a "bonus enrichment" path.

**Severity implications of CONFIG GET data:**
- `tls-protocols` contains "TLSv1" or "TLSv1.1" → HIGH (add to existing weak-version finding)
- `tls-ciphers` contains "RC4" or "DES" → CRITICAL
- `tls-protocols` absent/empty → treat as unknown (probe data is authoritative)

**Confidence:** MEDIUM — behavior on secured servers is well-documented (NOAUTH response), but exact ACL defaults vary by Redis version. Test confirms: probe-based detection is authoritative; CONFIG GET is optional enrichment.

---

## Q4: Port Conventions

| Port | Protocol | Notes |
|---|---|---|
| 6379 | Redis plaintext | Default; no TLS |
| 6380 | Redis TLS | Convention; not universal |
| 6381–6389 | Redis Cluster | Node ports; less relevant for v4.4 |
| 26379 | Redis Sentinel | Monitoring port; no TLS typically |

**Default scan targets for broker scanner:**

```python
REDIS_DEFAULT_PORTS = [6379, 6380]   # plaintext + TLS
KAFKA_DEFAULT_PORTS = [9092, 9093]    # plaintext + SSL/SASL_SSL
RABBITMQ_DEFAULT_PORTS = [5672, 5671] # AMQP plaintext + AMQPS/TLS
```

**Plaintext port (6379) is a distinct finding:** If Redis is reachable on 6379 without auth, this is a HIGH finding ("Redis/plaintext-no-auth"). Even if TLS is also configured on 6380, plaintext availability is the finding. Match the MySQL `ssl_disabled=True` probe pattern — connect intentionally without TLS to detect availability.

**Port 6380 not universal:** AWS ElastiCache uses 6379 for TLS with `--tls-url`. Redis Cloud uses 6380. Standalone Redis 6/7 configured for TLS commonly uses 6380 but this is convention, not standard. Scanner should allow port override in config.

**Confidence:** HIGH — port conventions are stable and well-documented.

---

## Q5: Chaos Lab Docker Configuration

**Recommended image:** `redis:7-alpine` with a mounted `redis.conf`. Do NOT use Bitnami (adds abstraction layers that complicate TLS cert mounting). The official `redis:7-alpine` accepts `redis-server /etc/redis/redis.conf` as its entrypoint command.

### Weak TLS Lab Profile — `redis-tls-weak`

Scenario: Redis with TLS enabled but TLS 1.1 permitted and weak cipher present.

Note: Modern OpenSSL builds (≥3.0) disable TLS 1.0/1.1 at the library level regardless of app config. This is the same constraint documented in the existing chaos lab for `tls-legacy` nginx. The scanner must handle this gracefully — if the OpenSSL on the scanner host doesn't support TLS 1.1, the weak-version probe returns false (inconclusive), not a false negative. Log a note, don't assert.

**redis.conf for chaos lab:**
```
# TLS port (scanner target)
tls-port 6380
port 0                          # disable plaintext entirely (TLS-only scenario)

# Certificates (mounted from host)
tls-cert-file /tls/redis.crt
tls-key-file  /tls/redis.key
tls-ca-cert-file /tls/ca.crt

# Weak TLS settings (chaos lab: deliberately permissive)
tls-protocols "TLSv1.2"        # Leave out TLSv1.3 to test TLS-only-1.2 scenario
                                # Note: TLSv1.1 often blocked by modern OpenSSL

# tls-ciphers uses OpenSSL cipher string format (TLS <= 1.2)
# Including 3DES gives the scanner a detectable weak cipher
tls-ciphers "HIGH:3DES:!aNULL:!MD5"

tls-auth-clients no            # no client cert required (scanner has none)
```

**docker-compose.yml service definition:**
```yaml
redis-tls-weak:
  image: redis:7-alpine
  profiles: ["broker"]
  command: ["redis-server", "/etc/redis/redis.conf"]
  volumes:
    - ./certs:/tls:ro
    - ./broker/redis/redis-weak.conf:/etc/redis/redis.conf:ro
  ports:
    - "26380:6380"

redis-plain:
  image: redis:7-alpine
  profiles: ["broker"]
  ports:
    - "26379:6379"
  # No custom command — default starts on 6379 with no TLS, no auth
  # Scanner finding: Redis/plaintext-no-auth HIGH
```

**Certificate reuse:** Reuse the existing `./certs` CA and cert bundle already present in the chaos lab. The `modern.crt` / `modern.key` pair works for Redis. Weak-TLS behavior comes from the `tls-protocols` and `tls-ciphers` directives, not from the cert itself.

**Plaintext port scenario:** The `redis-plain` service (no config file) starts with default settings: port 6379, no auth, no TLS. This gives the scanner a HIGH finding for "unauthenticated Redis reachable on plaintext port." This is the most common real-world misconfiguration.

**Confidence:** MEDIUM — Redis 7 TLS config directives verified via `redis.conf` source. The OpenSSL TLS 1.1 caveat is documented in existing chaos lab notes and applies equally here.

---

## Q6: Architecture Decision — One File vs Multiple

**Recommendation: One `broker_scanner.py` covering Kafka, RabbitMQ, and Redis.**

### Analysis

**Argument for single file:**
1. The broker surface is coherent — all three answer the same question ("is this message broker's transport encrypted and how strongly?"). This is a single v4.4 feature, not three independent features.
2. The existing `db_connector.py` precedent: PostgreSQL and MySQL are different databases but share one file. That file is ~260 lines and manages two distinct protocols without architectural problems.
3. Kafka and RabbitMQ TLS probe logic is nearly identical — both use raw `ssl` socket wrapping. Sharing `_try_handshake()` via a local helper or import from `tls_capabilities` avoids duplication across three files.
4. Config block in `quirk.toml` would be `[brokers]` — a single section for all three brokers. Splitting into three scanners implies three config sections, three optional import guards, three `PROTOCOL_KEYS` additions to `evidence.py`, and three sets of tests. This is overhead without benefit.
5. The feature is purely additive and not complex enough to warrant the maintenance cost of three separate modules.

**Argument for separate files (rejected):**
- "Each surface gets its own file" is a pattern in QUIRK, but this applies to distinct cryptographic surfaces (identity vs. data-at-rest vs. cloud), not to sub-protocols within the same surface (SMTP vs. IMAP vs. POP3 are all in the same email scanner; PostgreSQL and MySQL are in `db_connector.py`).
- Separate files would force test scaffolding to import three modules where the test fixtures (mock TLS probe, mock CONFIG GET) are nearly identical.

**Verdict:**

```
quirk/scanner/broker_scanner.py   # Kafka + RabbitMQ + Redis in one file
```

Internal structure:
```python
# broker_scanner.py
def scan_kafka_targets(targets, ...) -> List[CryptoEndpoint]: ...
def scan_rabbitmq_targets(targets, ...) -> List[CryptoEndpoint]: ...
def scan_redis_targets(targets, ...) -> List[CryptoEndpoint]: ...
```

Each function follows the same signature pattern as `scan_pg_targets()` and `scan_mysql_targets()` in `db_connector.py`: `targets: list, logger=None, session_start=None`.

**Protocol strings for `CryptoEndpoint.protocol`:**
- `"KAFKA"` — Kafka TLS endpoint
- `"RABBITMQ"` — RabbitMQ AMQPS endpoint
- `"REDIS"` — Redis TLS/plaintext endpoint

These must be added to `_PROTOCOL_KEYS` in `evidence.py`.

**Confidence:** HIGH — based on existing codebase patterns and the coherence argument.

---

## Q7: SQLite Schema Column Names

**Recommendation: `broker_scan_json` — a single column for all three brokers.**

### Analysis

**Pattern review:**
- `kerberos_scan_json` — Kerberos-specific
- `saml_scan_json` — SAML-specific
- `dnssec_scan_json` — DNSSEC-specific
- `dat_scan_json` — Universal DAR scan result (covers PostgreSQL, MySQL, RDS, S3, Azure Blob, K8s, Vault)
- `gcs_scan_json` — GCS-specific (hand-off from Phase 26 to Phase 28)

The `dat_scan_json` column serves as the universal DAR column for all data-at-rest protocols. The broker scanner should follow this same pattern: **one column, all brokers.**

**`broker_scan_json`** stores a JSON object per endpoint containing:
```json
{
  "broker_type": "REDIS",
  "plaintext_reachable": true,
  "tls_reachable": true,
  "tls_version": "TLSv1.2",
  "cipher_suite": "ECDHE-RSA-AES256-GCM-SHA384",
  "cert_subject": "...",
  "config_get_result": {"tls-protocols": "TLSv1.2"},
  "weak_ciphers_present": false,
  "tls_1_1_enabled": false
}
```

**Against per-broker columns (`kafka_scan_json`, `rabbitmq_scan_json`, `redis_scan_json`):**

| Factor | `broker_scan_json` | Per-broker columns |
|---|---|---|
| Schema migration | One `ALTER TABLE` | Three `ALTER TABLE` statements |
| Query pattern | `WHERE protocol='KAFKA'` on existing `protocol` column | No benefit — protocol is already in the endpoint row |
| SaaS migration | Migrating to Postgres: one JSON column | Three JSON columns; no architectural advantage |
| Consistency | Matches `dat_scan_json` universal pattern | Matches identity-scanner pattern but those are distinct protocols across different surfaces |

**Similarly for email scanner:**

```
email_scan_json   # SMTP/STARTTLS, IMAP, POP3 scan result JSON
```

This follows the same `broker_scan_json` rationale — one column, all email protocols, discriminated by `protocol` field in the endpoint row and within the JSON payload.

**Schema additions for v4.4:**
```python
# models.py
# ==========================
# v4.4 Data in Motion fields
# ==========================
email_scan_json  = Column(Text, nullable=True)  # SMTP/STARTTLS, IMAP, POP3 scan result JSON
broker_scan_json = Column(Text, nullable=True)  # Kafka/RabbitMQ/Redis scan result JSON
```

**Confidence:** HIGH — directly derived from existing `dat_scan_json` precedent in v4.3.

---

## Q8: motion_ Evidence Counter Naming

**Recommended naming scheme following `dar_` and `identity_` patterns:**

### Proposed Counters

**Email surface:**
```python
motion_email_starttls_missing_count   # SMTP without STARTTLS (HIGH)
motion_email_plaintext_count          # IMAP/POP3 without TLS (HIGH)
motion_email_weak_cipher_count        # Weak cipher on SMTP/IMAP/POP3 TLS (MEDIUM)
```

**Broker surface:**
```python
motion_broker_plaintext_count         # Kafka/RabbitMQ/Redis reachable without TLS (HIGH)
motion_broker_weak_tls_count          # Weak TLS version (TLS 1.1 or earlier) on broker port (HIGH)
motion_broker_weak_cipher_count       # RC4/3DES/etc on broker TLS port (MEDIUM)
```

**Rationale for this naming:**

- `motion_` prefix: matches `dar_` (data-at-rest) and `identity_` — subscore domain prefix
- `email_` / `broker_` sub-prefix: matches `dar_db_` / `dar_storage_` / `dar_k8s_` — surface prefix within the domain
- `_count` suffix: all evidence counters use `_count`, paired with `_ratio` derived at aggregation time
- Terms chosen to be self-explaining in dashboard tooltips without abbreviation

**Counters that do NOT need to be split per-protocol:**
`motion_broker_plaintext_count` counts across Kafka + RabbitMQ + Redis together. The `protocol` field on the endpoint row already discriminates by broker type for detail views. This mirrors `dar_db_plaintext_count` which covers PostgreSQL + MySQL + RDS in one counter.

**Ratios (derived in `build_evidence_summary()`, not stored separately):**
```python
motion_broker_plaintext_ratio = round(motion_broker_plaintext_count / total_endpoints, 4)
motion_email_plaintext_ratio  = round(motion_email_plaintext_count / total_endpoints, 4)
# etc.
```

**SCORE_WEIGHTS additions (parallel to dar_ weights):**
```python
"motion_broker_plaintext_ratio":   14.0,  # same weight as dar_db_plaintext_ratio
"motion_broker_weak_tls_ratio":     8.0,  # same as dar_vault_weak_ratio
"motion_broker_weak_cipher_ratio":  6.0,  # same as dar_db_weak_ssl_ratio
"motion_email_plaintext_ratio":    12.0,  # same weight as dar_storage_unencrypted_ratio
"motion_email_weak_cipher_ratio":   6.0,
```

**PROFILE_MULTIPLIERS addition:**
```python
PROFILE_MULTIPLIERS = {
    "strict":   {"agility_": 1.4, "identity_": 1.4, "dar_": 1.4, "motion_": 1.4},
    "balanced": {"agility_": 1.0, "identity_": 1.0, "dar_": 1.0, "motion_": 1.0},
    "lenient":  {"agility_": 0.7, "identity_": 0.7, "dar_": 0.7, "motion_": 0.7},
}
```

**Confidence:** HIGH — directly derived from the existing `dar_` counter naming convention in `evidence.py` and `scoring.py`.

---

## Recommended Architecture Summary

### Scanner Module Structure

```
quirk/scanner/broker_scanner.py     # New: Kafka + RabbitMQ + Redis
quirk/scanner/email_scanner.py      # New: SMTP/STARTTLS + IMAP + POP3
```

`broker_scanner.py` internal structure:
- `REDIS_AVAILABLE = True` (no optional dep — uses stdlib `ssl` + optional `redis-py`)
- `KAFKA_AVAILABLE = True/False` (optional dep: `kafka-python` or `confluent-kafka`)
- `RABBITMQ_AVAILABLE = True/False` (optional dep: `pika`)
- `def scan_redis_targets(targets, password=None, ca_certs=None, logger=None, session_start=None)`
- `def scan_kafka_targets(targets, logger=None, session_start=None)`
- `def scan_rabbitmq_targets(targets, logger=None, session_start=None)`

### Redis Scanner Logic Flow

```
For each target (host:port):

1. Probe plaintext port (6379 or configured):
   - TCP connect → Redis PING (no auth)
   - PONG response → HIGH: Redis/plaintext-no-auth
   - NOAUTH response → MEDIUM: Redis/plaintext-auth-required (plaintext still active)
   - ConnectionRefused → INFO: plaintext port closed (good)

2. Probe TLS port (6380 or configured):
   - raw ssl.wrap_socket → success → extract TLS version, cipher, cert
   - TLS 1.1 or older → HIGH: Redis/weak-tls-version
   - RC4/3DES cipher → CRITICAL: Redis/weak-cipher
   - No TLS (ConnectionRefused) → not a finding if plaintext finding already emitted

3. Optional enrichment (if password provided):
   - redis-py CONFIG GET tls-* → store in broker_scan_json
   - NOAUTH/NOPERM → log, skip config enrichment, not a scan_error
```

### CryptoEndpoint.protocol Values to Add

`evidence.py` `_PROTOCOL_KEYS` additions:
```python
_PROTOCOL_KEYS = (...existing...,
    "REDIS", "KAFKA", "RABBITMQ",      # broker surface
    "SMTP", "IMAP", "POP3",            # email surface
)
```

### Severity Ladder for Redis

| Condition | Severity | service_detail format |
|---|---|---|
| Plaintext port reachable, no auth | HIGH | `Redis/plaintext-no-auth` |
| Plaintext port reachable, auth required | MEDIUM | `Redis/plaintext-auth-required` |
| TLS 1.1 or older negotiated | HIGH | `Redis/weak-tls-TLSv1.1` |
| RC4/DES/NULL cipher | CRITICAL | `Redis/weak-cipher-RC4` |
| TLS 1.2/1.3, strong cipher | None (informational) | `Redis/tls-ok-TLSv1.3` |
| Connection refused both ports | INFO | `Redis/no-service` |

### Chaos Lab Profile Name

Recommend profile `"broker"` (matches `"identity"`, `"cloud"`, `"database"` existing profiles). Services:
- `redis-plain` — port 26379 — plaintext, no auth
- `redis-tls-weak` — port 26380 — TLS 1.2 + 3DES cipher
- `kafka-plain` — port 29092 — Kafka without SSL
- `kafka-tls` — port 29093 — Kafka with TLS
- `rabbitmq-plain` — port 25672 — AMQP without TLS
- `rabbitmq-tls` — port 25671 — AMQPS with TLS

---

## Sources

- [Redis TLS documentation — redis.io](https://redis.io/docs/latest/operate/oss_and_stack/management/security/encryption/)
- [redis-py SSL connection examples](https://redis.readthedocs.io/en/stable/examples/ssl_connection_examples.html)
- [Redis CONFIG GET docs — redis.io](https://redis.io/docs/latest/commands/config-get/)
- [Redis ACL documentation — redis.io](https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/)
- [Python ssl module — docs.python.org](https://docs.python.org/3/library/ssl.html)
- [sslyze Python API — blog.adqt.fr](https://blog.adqt.fr/sslyze/documentation/running-a-scan-in-python.html)
- [Redis port 6379 security — hackviser.com](https://hackviser.com/tactics/pentesting/services/redis)
- [RabbitMQ networking docs — rabbitmq.com](https://www.rabbitmq.com/docs/networking)
- [Amazon MSK port info — AWS docs](https://docs.aws.amazon.com/msk/latest/developerguide/port-info.html)
- [redis.conf TLS directives — GitHub redis/redis unstable](https://raw.githubusercontent.com/redis/redis/unstable/redis.conf)
