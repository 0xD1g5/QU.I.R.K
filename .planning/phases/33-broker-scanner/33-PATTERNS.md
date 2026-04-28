# Phase 33: Broker Scanner — Pattern Map

**Mapped:** 2026-04-27
**Files analyzed:** 12 new/modified files
**Analogs found:** 12 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `quirk/scanner/broker_scanner.py` | scanner module (multi-protocol) | request-response | `quirk/scanner/db_connector.py` (PG+MySQL+RDS in one file) + `quirk/scanner/email_scanner.py` (4-function shape) | exact composite |
| `quirk/db.py` | migration helper | CRUD | `quirk/db.py:_ensure_email_columns()` (Phase 32) | exact (same file) |
| `quirk/models.py` | model column add | CRUD | `quirk/models.py` `email_scan_json` line | exact (same file) |
| `quirk/config.py` | config flags | config | `ConnectorsCfg.enable_email` line 101 | exact (same file) |
| `quirk/engine/profiles.py` | profile gating | config | `apply_profile()` email block (Phase 32) | role-match |
| `quirk/engine/risk_engine.py` | finding emitter | request-response | `evaluate_email_endpoints()` (Phase 32) | role-match |
| `run_scan.py` | integration call site + CLI flags + aggregation | request-response | `run_scan.py` lines 691–724 (email block) | exact |
| `quirk/scanner/__init__.py` | scanner registration | wiring | existing `pass` (no-op) | trivial |
| `tests/test_broker_scanner.py` | scanner unit tests | test | `tests/test_email_scanner.py` | exact |
| `pyproject.toml` | optional sub-extras | config | existing `[motion]` block | exact (same file) |
| `quirk/config_template.yaml` | config defaults | config | existing email defaults | exact (same file) |
| `labs/broker/` (whole directory) | chaos lab | event-driven | `labs/email/` + `quantum-chaos-enterprise-lab/docker-compose.yml` profile blocks | role-match |

---

## Pattern Assignments

### `quirk/scanner/broker_scanner.py` (multi-protocol scanner module)

**Architectural analog:** `quirk/scanner/db_connector.py` — single file, multiple `scan_*_targets()` (PG + MySQL + RDS).
**Per-protocol shape analog:** `quirk/scanner/email_scanner.py` — 4-function-per-protocol shape (`_scan_one_sslyze_email`, `_scan_one_fallback_email`, `scan_one_email`, `scan_email_targets`) plus per-host JSON aggregation lines 550–599.

**Mirror exactly for each broker family (Kafka / RabbitMQ / Redis):**

```
_scan_one_sslyze_<family>(host, port, timeout, logger=None) -> Optional[CryptoEndpoint]
_scan_one_fallback_<family>(host, port, timeout, logger=None) -> CryptoEndpoint   # Redis-only (raw ssl); Kafka/RabbitMQ have no fallback below sslyze
scan_one_<family>(host, port, ..., timeout, logger=None, session_start=None) -> CryptoEndpoint
scan_<family>_targets(hosts, ..., timeout, logger=None, session_start=None) -> List[CryptoEndpoint]
```

**Imports** (combined Kafka + Redis optional guards from RESEARCH.md Pattern 1):

```python
import base64, json, socket, ssl, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from quirk.models import CryptoEndpoint
from quirk.logging_util import Logger
from quirk.scanner.tls_scanner import _pubkey_info, _extract_sans

# sslyze (already a project dep; same guard as email_scanner.py)
try:
    from sslyze import (
        Scanner as SslyzeScanner,
        ServerScanRequest,
        ServerNetworkLocation,
        ServerNetworkConfiguration,
        ScanCommand,
        ScanCommandAttemptStatusEnum,
        ServerScanStatusEnum,
    )
    SSLYZE_AVAILABLE = True
except ImportError:
    SSLYZE_AVAILABLE = False

# Optional kafka-python (KAFKA-04, D-06/D-07)
try:
    from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType
    KAFKA_AVAILABLE = True
except ImportError:
    KafkaAdminClient = None
    ConfigResource = None
    ConfigResourceType = None
    KAFKA_AVAILABLE = False

# Optional redis-py (REDIS-03, D-06/D-07)
try:
    import redis as redis_lib
    REDIS_AVAILABLE = True
except ImportError:
    redis_lib = None
    REDIS_AVAILABLE = False
```

**Plaintext detection helpers (RESEARCH.md Patterns 3 + 5):**

```python
AMQP_HEADER = b'AMQP\x00\x00\x09\x01'   # AMQP 0-9-1

def _detect_amqp_plaintext(host, port, timeout=2) -> bool:
    """RABBIT-02. Send AMQP 0-9-1 header; len(data)>0 = plaintext AMQP listener."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(AMQP_HEADER)
            sock.settimeout(timeout)
            data = sock.recv(256)
            return len(data) > 0   # CONTEXT.md 2026-04-27 revision (NOT b'AMQP' prefix)
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False

def _detect_kafka_plaintext(host, port, timeout=2) -> bool:
    """KAFKA-02. Plain TCP connect — Kafka 9092 accepts unauthenticated connection."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False

def _detect_redis_plaintext(host, port, timeout=2) -> bool:
    """REDIS-02. PING; +PONG | -NOAUTH | other RESP prefix all = plaintext Redis."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(b"PING\r\n")
            sock.settimeout(timeout)
            data = sock.recv(64)
            return data.startswith((b'+', b'-', b'*'))
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False
```

**Redis raw TLS probe (RESEARCH.md Pattern 4):**
Mirror `quirk/scanner/tls_capabilities.py:_try_handshake()` exactly. Use `_pubkey_info()` from `tls_scanner` on `getpeercert(binary_form=True)`.

**sslyze probe** (RESEARCH.md Pattern 2): identical to `email_scanner.py:_scan_one_sslyze_email()` minus the `tls_opportunistic_encryption` field. Always set `tls_server_name_indication=host` explicitly.

**RabbitMQ mgmt enrichment** (Pattern 8): stdlib `urllib.request` + `base64.b64encode(b"guest:guest")`. 401 returns `{"mgmt_auth": "rejected_401"}`. Any other error returns `{}`.

**Cloud broker probes (D-03/D-04):** Inside `scan_rabbitmq_targets()`, after the self-hosted host loop, iterate `azure_namespaces` constructing `f"{ns}.servicebus.windows.net"` and probe port 5671 via `_scan_one_sslyze_rabbitmq()` with `protocol="AMQPS/Azure-ServiceBus"`. Likewise iterate `sqs_regions` constructing `f"sqs.{region}.amazonaws.com"` probe port 443 with `protocol="HTTPS/AWS-SQS"`.

---

### `quirk/db.py` — `_ensure_broker_columns()`

**Analog:** `_ensure_email_columns()` (Phase 32 PATTERNS.md §db.py).

```python
_BROKER_COLUMNS = ["broker_scan_json"]

def _ensure_broker_columns(engine) -> None:
    existing = {c["name"] for c in sa_inspect(engine).get_columns("crypto_endpoints")}
    with engine.connect() as conn:
        for col in _BROKER_COLUMNS:
            if not _SAFE_COL_RE.match(col):
                raise ValueError(f"Unsafe column name in migration: {col!r}")
            if col not in existing:
                conn.execute(text(f"ALTER TABLE crypto_endpoints ADD COLUMN {col} TEXT"))
        conn.commit()
```

Call site append after `_ensure_email_columns(engine)` in `init_db()`.

---

### `quirk/models.py` — `broker_scan_json` column

**Analog:** `email_scan_json = Column(Text, nullable=True)` line.

```python
    broker_scan_json = Column(Text, nullable=True)  # Per-scan broker probe summary JSON (Phase 33)
```

---

### `quirk/config.py` — `ConnectorsCfg` additions

**Analog:** `enable_email: bool = False` (line 101).

```python
    # Broker scanner enable flag (v4.4, Phase 33) — D-10
    enable_broker: bool = False
    # Cloud broker targets (D-01) — supplied via CLI/config only; no SDK enumeration (D-02)
    broker_azure_namespaces: List[str] = field(default_factory=list)
    broker_sqs_regions: List[str] = field(default_factory=list)
```

`config_from_dict()` must hydrate both list fields via `_as_str_list()`.

**CRITICAL:** Attribute namespace is `cfg.connectors.enable_broker` (matches `enable_email` precedent — see CONTEXT.md D-10 revision 2026-04-27, NOT `cfg.scanners.broker_enabled`).

---

### `quirk/engine/profiles.py` — broker profile gating

**Analog:** Phase 32 email block in `apply_profile()`.

```python
# Quick: broker stays disabled (D-10)
if p == "quick":
    pass

elif p == "deep":
    if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_broker"):
        if not cfg.connectors.enable_broker:
            cfg.connectors.enable_broker = True

else:  # standard
    if hasattr(cfg, "connectors") and hasattr(cfg.connectors, "enable_broker"):
        if not cfg.connectors.enable_broker:
            cfg.connectors.enable_broker = True
```

---

### `quirk/engine/risk_engine.py` — `evaluate_broker_endpoints()`

**Analog:** `evaluate_email_endpoints()` (Phase 32 PATTERNS.md §risk_engine.py).

Finding IDs (severities):
- `kafka-plaintext-listener` — HIGH on plaintext probe success at port 9092.
- `amqp-plaintext-listener` — HIGH on plaintext AMQP detection at port 5672.
- `redis-plaintext-no-auth` — HIGH on plaintext Redis detection at port 6379.
- `weak-cipher` — HIGH for `TLS_RSA_WITH_*`, `3DES`, `RC4`, `*-SHA` non-AEAD on any broker TLS port (re-use email logic).

Finding dict shape identical to Phase 32 — `{severity, host, port, title, recommendation}`.

`_dedupe_findings()` key `(host, port, title, recommendation)` ensures layered findings (plaintext + weak-cipher on same host/port) survive, mirroring Phase 32 D-11/D-12 carry-forward.

---

### `run_scan.py` — broker integration block

**Analog:** Phase 32 email block at `run_scan.py:691–724`.

**CLI flags (D-01):** Add to argparse — `--azure-servicebus-namespace` and `--aws-sqs-region`, both `action="append"`, default `[]`. Wire into `cfg.connectors.broker_azure_namespaces` / `broker_sqs_regions` after config load.

**Top-of-file import:**

```python
from quirk.scanner.broker_scanner import (
    scan_kafka_targets, scan_rabbitmq_targets, scan_redis_targets,
)
from quirk.engine.risk_engine import evaluate_broker_endpoints
```

**Block (insert AFTER email block, BEFORE `endpoints = (...)` aggregation):**

```python
    # ── Broker TLS scanning (Phase 33) ────────────────────────
    kafka_endpoints = []
    rabbit_endpoints = []
    redis_endpoints = []
    with _phase_timer(run_stats, "broker_scanning"):
        if cfg.connectors.enable_broker:
            broker_hosts = list(dict.fromkeys(h for h, _ in tls_targets))
            if broker_hosts:
                kafka_endpoints = scan_kafka_targets(
                    hosts=broker_hosts, timeout=cfg.scan.timeout_seconds,
                    profile=cfg.scan.profile, logger=logger, session_start=session_start,
                )
                rabbit_endpoints = scan_rabbitmq_targets(
                    hosts=broker_hosts,
                    azure_namespaces=cfg.connectors.broker_azure_namespaces,
                    sqs_regions=cfg.connectors.broker_sqs_regions,
                    timeout=cfg.scan.timeout_seconds,
                    logger=logger, session_start=session_start,
                )
                redis_endpoints = scan_redis_targets(
                    hosts=broker_hosts, timeout=cfg.scan.timeout_seconds,
                    logger=logger, session_start=session_start,
                )
                logger.info(f"Broker scan: kafka={len(kafka_endpoints)} rabbit={len(rabbit_endpoints)} redis={len(redis_endpoints)}")
```

**Aggregation (D-12/D-14, mirrors `email_scanner.py:550–599`):**

```python
    # broker_scan_json — nested per protocol family on first endpoint
    all_broker_eps = kafka_endpoints + rabbit_endpoints + redis_endpoints
    if all_broker_eps:
        # Split rabbit_endpoints into self-hosted vs azure vs sqs by ep.protocol
        azure_eps = [e for e in rabbit_endpoints if getattr(e, "protocol", "") == "AMQPS/Azure-ServiceBus"]
        sqs_eps   = [e for e in rabbit_endpoints if getattr(e, "protocol", "") == "HTTPS/AWS-SQS"]
        rabbit_self = [e for e in rabbit_endpoints if e not in azure_eps and e not in sqs_eps]
        payload = {
            "kafka":             [_ep_dict(e) for e in kafka_endpoints],
            "rabbitmq":          [_ep_dict(e) for e in rabbit_self],
            "redis":             [_ep_dict(e) for e in redis_endpoints],
            "azure_servicebus":  [_ep_dict(e) for e in azure_eps],
            "aws_sqs":           [_ep_dict(e) for e in sqs_eps],
            "session_start":     session_start.isoformat() if session_start else None,
        }
        all_broker_eps[0].broker_scan_json = json.dumps(payload, default=str)

    endpoints = (... + email_endpoints + kafka_endpoints + rabbit_endpoints + redis_endpoints)

    broker_findings = evaluate_broker_endpoints(all_broker_eps)
```

---

### `quirk/scanner/__init__.py`

Currently `pass`. Add no imports — keep file at `pass` (consistent with current state); broker_scanner imported directly by `run_scan.py`.

---

### `tests/test_broker_scanner.py`

**Analog:** `tests/test_email_scanner.py` (Phase 32).

Same RED-state convention: `pytest.importorskip("quirk.scanner.broker_scanner", reason="Phase 33 Plan 03–05 implements")`.

Mock helpers:
- `_make_mock_sslyze_result(...)` — copy from Phase 32 verbatim (same sslyze API).
- `_mock_socket_amqp_response(data=b'\x01\x00\x00...')` — patches `socket.create_connection` for AMQP detection tests.
- `_mock_redis_lib(config_get_return)` — sets module-level `redis_lib` to a `MagicMock` for REDIS-03 tests.
- `_mock_kafka_admin(describe_return)` — sets module-level `KafkaAdminClient` to a `MagicMock` for KAFKA-04 tests.

Tests grouped by REQ-ID, one assertion per test, ≥25 tests covering KAFKA-01..04, RABBIT-01..05, REDIS-01..03, BROKER-00, STRUCT-01.

---

### `pyproject.toml`

**Analog:** existing `[project.optional-dependencies]` block with `[motion]` stub.

```toml
[project.optional-dependencies]
# ...existing entries unchanged...
motion = []
kafka  = ["kafka-python>=2.0"]
redis  = ["redis>=5.0"]
```

---

### `quirk/config_template.yaml`

**Analog:** existing `connectors:` block with email defaults.

```yaml
connectors:
  # ...existing entries...
  enable_broker: false
  broker_azure_namespaces: []
  broker_sqs_regions: []
```

---

### `labs/broker/` (chaos lab — D-15 revision 2026-04-27)

**Analog:** `labs/email/` directory + `quantum-chaos-enterprise-lab/docker-compose.yml` profile blocks.

**Layout:**

```
labs/broker/
├── README.md
├── Makefile                  # cert-gen target (mirrors labs/email/Makefile)
├── certs/                    # generated, gitignored
├── kafka/server.properties   # bind-mounted weak TLS config (apache/kafka image)
├── rabbitmq/rabbitmq.conf    # bind-mounted weak TLS config (official rabbitmq:3.12-management)
├── redis/redis.conf          # bind-mounted weak TLS config (official redis:7-alpine)
└── expected_results.md       # BROKER-LAB-02
```

**Compose blocks** added to `quantum-chaos-enterprise-lab/docker-compose.yml` under `profiles: ["broker"]`:

| Service | Image | Plaintext port | TLS port | Mounts |
|---------|-------|----------------|----------|--------|
| `kafka-broker` | `apache/kafka:3.6` (or `confluentinc/cp-kafka:7.5` — planner picks) | 29092 | 29093 | certs + server.properties |
| `rabbitmq-broker` | `rabbitmq:3.12-management` | 25672 | 25671 | certs + rabbitmq.conf |
| `redis-broker` | `redis:7-alpine` | 26379 | 26380 | certs + redis.conf |

Cert generation Makefile target identical pattern to `labs/email/Makefile` — `openssl req -x509 -newkey rsa:2048 -nodes -days 3650` per service.

**Weak-TLS config snippets** copied verbatim from RESEARCH.md §"Chaos Lab" (rabbitmq.conf lines 740–761, redis.conf lines 778–788).

**`labs/broker/expected_results.md`** structure identical to `labs/email/expected_results.md` — table of (port, protocol, tls_version, cipher_suite, finding, severity).

---

## Shared Patterns

### sslyze Optional Import Guard
**Source:** `quirk/scanner/tls_scanner.py` lines 19–35
**Apply to:** `broker_scanner.py` (same block as `email_scanner.py`)

### session_start Plumbing (STRUCT-01)
**Source:** `quirk/scanner/email_scanner.py:scan_one_email` line 207
**Apply to:** every `scan_one_<family>` and `scan_<family>_targets` in `broker_scanner.py`

```python
ep.scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
```

### ConnectionRefusedError Silent Handling
**Source:** Phase 32 D-03 carry-forward; `tls_scanner.py` lines 413–418
**Apply to:** every probe helper in `broker_scanner.py`

```python
except ConnectionRefusedError:
    return None   # silent at DEBUG
```

### Inspector-First Migration
**Source:** `quirk/db.py` lines 49–63
**Apply to:** `_ensure_broker_columns()`

### Finding Dict Shape
**Source:** `quirk/engine/risk_engine.py` lines 263–282
**Apply to:** `evaluate_broker_endpoints()`

### Optional Library Import Guard with Module-Level None
**Source:** Phase 32 sslyze guard pattern
**Apply to:** `kafka` (KAFKA-04) and `redis_lib` (REDIS-03) — module-level `None` assignment so `unittest.mock.patch` can replace them in tests.

---

## No Analog Found

None. All 12 files have direct precedents.

---

## Metadata

**Analog search scope:** `quirk/scanner/`, `quirk/engine/`, `quirk/`, `tests/`, `labs/`, `quantum-chaos-enterprise-lab/`
**Files scanned:** 13 source files (db_connector.py, email_scanner.py, tls_scanner.py, tls_capabilities.py, db.py, models.py, config.py, profiles.py, risk_engine.py, run_scan.py, test_email_scanner.py, labs/email/Makefile, quantum-chaos-enterprise-lab/docker-compose.yml)
**Pattern extraction date:** 2026-04-27
