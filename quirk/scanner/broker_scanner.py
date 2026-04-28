"""Broker TLS scanner — Kafka, RabbitMQ/AMQP, Redis, Azure Service Bus, AWS SQS.

Phase 33 / BROKER-ARCH: single module, three protocol-family functions
(scan_kafka_targets, scan_rabbitmq_targets, scan_redis_targets), parallel to
quirk/scanner/db_connector.py.

STRUCT-01: scanner accepts session_start; no bare now() calls inside the scanner.
D-07: kafka-python and redis-py are import-guarded optional sub-extras.
"""
import base64
import json
import socket
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from quirk.models import CryptoEndpoint
from quirk.logging_util import Logger
from quirk.scanner.tls_scanner import _pubkey_info, _extract_sans

# ---------------------------------------------------------------------------
# sslyze optional import (same guard as email_scanner.py)
# ---------------------------------------------------------------------------
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
    SslyzeScanner = None  # type: ignore[assignment]
    ServerScanRequest = None  # type: ignore[assignment]
    ServerNetworkLocation = None  # type: ignore[assignment]
    ScanCommand = None  # type: ignore[assignment]
    ServerNetworkConfiguration = None  # type: ignore[assignment]

    class ScanCommandAttemptStatusEnum:  # noqa: N801
        COMPLETED = "COMPLETED"
        ERROR = "ERROR"

    class ServerScanStatusEnum:  # noqa: N801
        COMPLETED = "COMPLETED"
        ERROR_NO_CONNECTIVITY = "ERROR_NO_CONNECTIVITY"

    SSLYZE_AVAILABLE = False

# Optional kafka-python (KAFKA-04, D-06/D-07)
try:
    from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType
    KAFKA_AVAILABLE = True
except ImportError:
    KafkaAdminClient = None  # type: ignore[assignment]
    ConfigResource = None  # type: ignore[assignment]
    ConfigResourceType = None  # type: ignore[assignment]
    KAFKA_AVAILABLE = False

# Optional redis-py (REDIS-03, D-06/D-07)
try:
    import redis as redis_lib
    REDIS_AVAILABLE = True
except ImportError:
    redis_lib = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False

_sslyze_warned = False

# ---------------------------------------------------------------------------
# Plaintext detection helpers
# ---------------------------------------------------------------------------

AMQP_HEADER = b'AMQP\x00\x00\x09\x01'   # AMQP 0-9-1 protocol header (Plan 04 uses this)


def _detect_kafka_plaintext(host: str, port: int, timeout: int = 2) -> bool:
    """KAFKA-02: bare TCP connect succeeds = plaintext Kafka listener present."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


# ---------------------------------------------------------------------------
# sslyze cipher helpers
# ---------------------------------------------------------------------------

_BROKER_PROTO_MAP = [
    ("tls_1_3_cipher_suites", "TLSv1.3", 4),
    ("tls_1_2_cipher_suites", "TLSv1.2", 3),
    ("tls_1_1_cipher_suites", "TLSv1.1", 2),
    ("tls_1_0_cipher_suites", "TLSv1.0", 1),
]


def _is_pfs(name: str) -> bool:
    upper = name.upper()
    return "ECDHE" in upper or "DHE" in upper


def _is_weak(name: str) -> bool:
    upper = name.upper()
    return any(m in upper for m in ("RC4", "3DES", "CBC3", "NULL", "EXPORT", "MD5"))


# ---------------------------------------------------------------------------
# sslyze probe for Kafka TLS ports (9093, 9094)
# ---------------------------------------------------------------------------

def _scan_one_sslyze_broker(
    host: str,
    port: int,
    timeout: int,
    logger: Optional[Logger] = None,
) -> Optional[CryptoEndpoint]:
    """Protocol-agnostic sslyze TLS probe (used by Kafka + RabbitMQ/AMQPS + cloud broker probes).

    Returns a populated CryptoEndpoint on success, None on any failure.
    The caller is responsible for setting ep.protocol to the correct label.
    ConnectionRefusedError is silent at DEBUG (D-03 carry-forward).
    No tls_opportunistic_encryption — broker TLS is always direct.
    """
    global _sslyze_warned

    if not SSLYZE_AVAILABLE:
        if not _sslyze_warned:
            if logger:
                logger.v("sslyze not installed — broker scanner TLS probe skipped")
            _sslyze_warned = True
        return None

    try:
        net_cfg = ServerNetworkConfiguration(
            tls_server_name_indication=host,
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
            if logger:
                logger.v(f"sslyze ERROR for broker {host}:{port}")
            return None

        scan = server_result.scan_result

        # Placeholder — callers (scan_one_kafka, scan_one_rabbitmq) set the final ep.protocol
        ep = CryptoEndpoint(host=host, port=port, protocol="KAFKA-TLS")

        # ----------------------------------------------------------------
        # Cipher suites per protocol
        # ----------------------------------------------------------------
        accepted_by_version: dict = {}
        all_accepted_ciphers: List[str] = []
        pfs_supported = False
        weak_present = False
        highest_version: Optional[str] = None
        highest_priority = -999

        for attr, version_label, priority in _BROKER_PROTO_MAP:
            attempt = getattr(scan, attr, None)
            if attempt is None:
                continue
            try:
                if attempt.status != ScanCommandAttemptStatusEnum.COMPLETED:
                    continue
                names = [s.cipher_suite.name for s in attempt.result.accepted_cipher_suites]
            except Exception:
                continue
            if names:
                accepted_by_version[version_label] = names
                all_accepted_ciphers.extend(names)
                if priority > highest_priority:
                    highest_priority = priority
                    highest_version = version_label
                for cipher_name in names:
                    if _is_pfs(cipher_name):
                        pfs_supported = True
                    if _is_weak(cipher_name):
                        weak_present = True

        ep.tls_version = highest_version
        ep.cipher_suite = (
            accepted_by_version[highest_version][0] if highest_version else None
        )
        ep.tls_pfs_supported = pfs_supported
        ep.tls_weak_ciphers_present = weak_present

        # ----------------------------------------------------------------
        # Certificate info
        # ----------------------------------------------------------------
        try:
            cert_attempt = scan.certificate_info
            if cert_attempt.status == ScanCommandAttemptStatusEnum.COMPLETED:
                deployment = cert_attempt.result.certificate_deployments[0]
                leaf = deployment.received_certificate_chain[0]

                try:
                    ep.cert_subject = leaf.subject.rfc4514_string()
                except Exception:
                    pass
                try:
                    ep.cert_issuer = leaf.issuer.rfc4514_string()
                except Exception:
                    pass
                try:
                    ep.cert_sans = _extract_sans(leaf)
                except Exception:
                    pass
                try:
                    sig = leaf.signature_hash_algorithm
                    ep.cert_sig_alg = sig.name if sig else "unknown"
                except Exception:
                    pass
                try:
                    pubkey = leaf.public_key()
                    alg, size = _pubkey_info(pubkey)
                    ep.cert_pubkey_alg = alg
                    ep.cert_pubkey_size = size
                except Exception:
                    try:
                        size = leaf.public_key().key_size
                        if isinstance(size, int):
                            ep.cert_pubkey_size = size
                    except Exception:
                        pass
        except Exception:
            pass

        if logger:
            logger.v(
                f"sslyze BROKER {host}:{port} version={ep.tls_version} "
                f"weak={ep.tls_weak_ciphers_present} pfs={ep.tls_pfs_supported}"
            )

        return ep

    except ConnectionRefusedError:
        # D-03: CONNECTION_REFUSED is non-fatal and silent at DEBUG
        if logger:
            try:
                logger.debug(f"Broker port {port} CONNECTION_REFUSED on {host} (sslyze)")
            except AttributeError:
                pass
        return None
    except Exception as e:
        if logger:
            logger.v(f"sslyze exception for broker {host}:{port}: {e}")
        return None


# Backward-compat alias — Plan 03 tests import _scan_one_sslyze_kafka by name
_scan_one_sslyze_kafka = _scan_one_sslyze_broker


# ---------------------------------------------------------------------------
# RabbitMQ: AMQP plaintext detection (RABBIT-02)
# ---------------------------------------------------------------------------

def _detect_amqp_plaintext(host: str, port: int, timeout: int = 2) -> bool:
    """RABBIT-02. Send AMQP 0-9-1 header; len(data) > 0 = AMQP speaker (CONTEXT.md 2026-04-27).

    NOTE: original spec said b'AMQP' prefix match — that yields false negatives because
    the AMQP 0-9-1 Connection.Start response is a binary METHOD frame, not ASCII-prefixed.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(AMQP_HEADER)
            sock.settimeout(timeout)
            data = sock.recv(256)
            return len(data) > 0
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


# ---------------------------------------------------------------------------
# RabbitMQ: management API enrichment (RABBIT-03 / D-09)
# ---------------------------------------------------------------------------

def _enrich_rabbitmq_mgmt(host: str, port: int = 15672, logger=None) -> dict:
    """RABBIT-03 / D-09. urllib.request GET /api/overview with Basic guest:guest.

    Returns {} on connection failure or non-401 HTTP error.
    Returns {"mgmt_auth": "rejected_401"} on 401 (informational data point, NOT an error).
    No `requests` dependency (D-09).
    """
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
                logger.debug(
                    f"RabbitMQ mgmt API guest:guest rejected on {host}:{port} (401 — informational)"
                )
            return {"mgmt_auth": "rejected_401"}
        if logger:
            logger.debug(f"RabbitMQ mgmt API HTTP error {e.code} on {host}:{port}")
        return {}
    except Exception as e:
        if logger:
            logger.debug(f"RabbitMQ mgmt API failed on {host}:{port}: {e}")
        return {}


# ---------------------------------------------------------------------------
# KAFKA-04 enrichment helper (kafka-python AdminClient)
# ---------------------------------------------------------------------------

def _enrich_kafka_admin(host: str, port: int, logger=None) -> dict:
    """KAFKA-04: best-effort kafka-python AdminClient enrichment. Returns {} on any failure (D-08)."""
    if not KAFKA_AVAILABLE:
        return {}
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=[f"{host}:{port}"],
            security_protocol="SSL",
            ssl_check_hostname=False,
            ssl_cafile=None,
            request_timeout_ms=5000,
        )
        result = admin.describe_configs([ConfigResource(ConfigResourceType.BROKER, "0")])
        interesting = {"ssl.enabled.protocols", "ssl.cipher.suites", "ssl.client.auth",
                       "listeners", "advertised.listeners"}
        enrichment = {}
        for _resource, entries in result.items():
            for entry in entries:
                if entry.name in interesting:
                    enrichment[entry.name] = entry.value
        admin.close()
        return enrichment
    except Exception as e:
        if logger:
            logger.debug(f"kafka-python enrichment failed for {host}:{port}: {e}")
        return {}


# ---------------------------------------------------------------------------
# Per-host orchestrator
# ---------------------------------------------------------------------------

def scan_one_kafka(
    host: str,
    port: int,
    timeout: int,
    logger: Optional[Logger] = None,
    session_start: Optional[datetime] = None,
) -> Optional[CryptoEndpoint]:
    """Probe a single Kafka host:port. Returns endpoint or None.

    Port 9092 -> plaintext detection (KAFKA-02). Port 9093/9094 -> sslyze (KAFKA-01/KAFKA-03).
    Optionally enriches with kafka-python AdminClient (KAFKA-04).
    """
    if port == 9092:
        if _detect_kafka_plaintext(host, port):
            ep = CryptoEndpoint(host=host, port=port, protocol="KAFKA-PLAIN")
            ep.service_detail = f"KAFKA-PLAIN:{port}"
            ep.scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
            return ep
        return None

    # TLS ports 9093 / 9094
    ep = _scan_one_sslyze_kafka(host, port, timeout, logger)
    if ep is None:
        return None
    ep.protocol = "KAFKA-TLS"
    ep.service_detail = f"KAFKA-TLS:{port}"
    ep.scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)

    # KAFKA-04 optional enrichment — never fails the scan
    enrichment = _enrich_kafka_admin(host, port, logger)
    if enrichment:
        # Stash enrichment dict on a discoverable attribute for Plan 06 aggregation
        setattr(ep, "_kafka_admin_enrichment", enrichment)
    return ep


# ---------------------------------------------------------------------------
# Top-level driver — Kafka
# ---------------------------------------------------------------------------

def scan_kafka_targets(
    hosts: List[str],
    timeout: int,
    profile: str = "standard",
    logger: Optional[Logger] = None,
    session_start: Optional[datetime] = None,
) -> List[CryptoEndpoint]:
    """Probe Kafka hosts on 9092 (plaintext), 9093 (TLS), and 9094 (TLS, standard/deep only).

    KAFKA-01: sslyze probe on 9093.
    KAFKA-02: TCP detection on 9092.
    KAFKA-03: 9094 included for standard/deep profiles.
    STRUCT-01: session_start propagated to every ep.scanned_at; no bare now() calls in this module.
    """
    results: List[CryptoEndpoint] = []
    ports = [9092, 9093]
    if profile in ("standard", "deep"):
        ports.append(9094)
    tasks = [(h, p) for h in hosts for p in ports]
    if not tasks:
        return results
    if logger:
        logger.stamp(f"Starting Kafka scans: {len(tasks)} probes ({len(hosts)} hosts x {len(ports)} ports)")
    with ThreadPoolExecutor(max_workers=min(len(tasks), 50)) as ex:
        futs = {ex.submit(scan_one_kafka, h, p, timeout, logger, session_start): (h, p) for h, p in tasks}
        for f in as_completed(futs):
            ep = f.result()
            if ep is not None:
                results.append(ep)
    if logger:
        logger.stamp(f"Kafka scans complete: {len(results)} endpoints")
    return results


# ---------------------------------------------------------------------------
# RabbitMQ: per-host orchestrator
# ---------------------------------------------------------------------------

def scan_one_rabbitmq(
    host: str,
    port: int,
    timeout: int,
    *,
    protocol_label: str = "AMQPS",
    logger: Optional[Logger] = None,
    session_start: Optional[datetime] = None,
) -> Optional[CryptoEndpoint]:
    """Probe a single RabbitMQ-family endpoint.

    Port 5672 -> AMQP plaintext detection (RABBIT-02).
    Other ports -> sslyze direct-TLS probe with caller-supplied protocol_label.
    protocol_label values: "AMQPS" (5671 self-hosted), "AMQPS/Azure-ServiceBus" (5671 cloud),
    "HTTPS/AWS-SQS" (443 cloud).
    """
    if port == 5672:
        if _detect_amqp_plaintext(host, port):
            ep = CryptoEndpoint(host=host, port=port, protocol="AMQP-PLAIN")
            ep.service_detail = f"AMQP-PLAIN:{port}"
            ep.scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
            return ep
        return None

    ep = _scan_one_sslyze_broker(host, port, timeout, logger)
    if ep is None:
        return None
    ep.protocol = protocol_label
    ep.service_detail = f"{protocol_label}:{port}"
    ep.scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    return ep


# ---------------------------------------------------------------------------
# RabbitMQ: top-level driver (RABBIT-01..05 + Azure SB + AWS SQS)
# ---------------------------------------------------------------------------

def scan_rabbitmq_targets(
    hosts: List[str],
    azure_namespaces: Optional[List[str]] = None,
    sqs_regions: Optional[List[str]] = None,
    timeout: int = 5,
    logger: Optional[Logger] = None,
    session_start: Optional[datetime] = None,
) -> List[CryptoEndpoint]:
    """RABBIT-01..05. Probe self-hosted RabbitMQ + Azure SB + AWS SQS in parallel.

    Self-hosted: ports 5672 (AMQP plaintext detection) and 5671 (AMQPS via sslyze).
    Azure Service Bus: {namespace}.servicebus.windows.net:5671 (D-03, RABBIT-04).
    AWS SQS: sqs.{region}.amazonaws.com:443 (D-04, RABBIT-05).
    RABBIT-03: Management API enrichment (best-effort, attaches to 5671 ep for that host).
    STRUCT-01: session_start propagated; no bare now() calls in this module.
    """
    results: List[CryptoEndpoint] = []
    azure_namespaces = azure_namespaces or []
    sqs_regions = sqs_regions or []

    # Self-hosted: 5672 (AMQP plaintext), 5671 (AMQPS)
    self_tasks = [(h, 5672, "AMQPS") for h in hosts] + [(h, 5671, "AMQPS") for h in hosts]
    # Azure SB: {ns}.servicebus.windows.net:5671 (D-03)
    azure_tasks = [
        (f"{ns}.servicebus.windows.net", 5671, "AMQPS/Azure-ServiceBus")
        for ns in azure_namespaces
    ]
    # AWS SQS: sqs.{region}.amazonaws.com:443 (D-04)
    sqs_tasks = [
        (f"sqs.{r}.amazonaws.com", 443, "HTTPS/AWS-SQS")
        for r in sqs_regions
    ]
    all_tasks = self_tasks + azure_tasks + sqs_tasks
    if not all_tasks:
        return results
    if logger:
        logger.stamp(
            f"Starting RabbitMQ scans: {len(all_tasks)} probes "
            f"(self={len(self_tasks)} azure={len(azure_tasks)} sqs={len(sqs_tasks)})"
        )
    with ThreadPoolExecutor(max_workers=min(len(all_tasks), 50)) as ex:
        futs = {
            ex.submit(
                scan_one_rabbitmq, host, port, timeout,
                protocol_label=label, logger=logger, session_start=session_start,
            ): (host, port)
            for host, port, label in all_tasks
        }
        for f in as_completed(futs):
            ep = f.result()
            if ep is not None:
                results.append(ep)

    # RABBIT-03: management API enrichment per self-hosted host
    # (best-effort, attaches to first AMQPS endpoint for that host)
    for host in hosts:
        mgmt = _enrich_rabbitmq_mgmt(host, port=15672, logger=logger)
        if mgmt:
            for ep in results:
                if ep.host == host and ep.protocol == "AMQPS":
                    setattr(ep, "_rabbit_mgmt_enrichment", mgmt)
                    break
    if logger:
        logger.stamp(f"RabbitMQ scans complete: {len(results)} endpoints")
    return results


# ---------------------------------------------------------------------------
# Redis: plaintext detection constant
# ---------------------------------------------------------------------------

REDIS_INLINE_TIMEOUT = 2


# ---------------------------------------------------------------------------
# Redis: plaintext PING detection (REDIS-02)
# ---------------------------------------------------------------------------

def _detect_redis_plaintext(host: str, port: int, timeout: int = REDIS_INLINE_TIMEOUT) -> bool:
    """REDIS-02. Send PING; +PONG / -NOAUTH / *<reply> all indicate plaintext Redis."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(b"PING\r\n")
            sock.settimeout(timeout)
            data = sock.recv(64)
            return data.startswith((b'+', b'-', b'*'))
    except (ConnectionRefusedError, OSError, socket.timeout):
        return False


# ---------------------------------------------------------------------------
# Redis: IP address detection helper for SNI suppression (REDIS-01)
# ---------------------------------------------------------------------------

def _is_ip_redis(host: str) -> bool:
    """Crude IPv4/IPv6 detection — SNI is suppressed for raw IP addresses (REDIS-01)."""
    import ipaddress
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Redis: raw ssl.SSLContext TLS probe (REDIS-01)
# ---------------------------------------------------------------------------

def _probe_redis_tls(host: str, port: int, timeout: int = 5) -> Optional[CryptoEndpoint]:
    """REDIS-01. Raw ssl.SSLContext probe — sslyze CANNOT speak Redis (no app-layer banner)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    server_hostname = host if not _is_ip_redis(host) else None
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=server_hostname) as ssock:
                ver = ssock.version()
                cip = ssock.cipher()                  # tuple (name, protocol, bits)
                der = ssock.getpeercert(binary_form=True)
                ep = CryptoEndpoint(host=host, port=port, protocol="REDIS-TLS")
                ep.tls_version = ver
                ep.cipher_suite = cip[0] if cip else None
                if der:
                    cert = x509.load_der_x509_certificate(der, default_backend())
                    alg, size = _pubkey_info(cert.public_key())
                    ep.cert_pubkey_alg = alg
                    ep.cert_pubkey_size = size
                    ep.cert_subject = cert.subject.rfc4514_string()
                    ep.cert_issuer = cert.issuer.rfc4514_string()
                return ep
    except ConnectionRefusedError:
        return None
    except Exception as e:
        ep = CryptoEndpoint(host=host, port=port, protocol="REDIS-TLS")
        ep.scan_error = str(e)
        return ep


# ---------------------------------------------------------------------------
# Redis: redis-py CONFIG GET enrichment (REDIS-03 / D-08)
# ---------------------------------------------------------------------------

def _enrich_redis_config(host: str, port: int, logger=None) -> dict:
    """REDIS-03 / D-08. redis-py CONFIG GET tls-*. NOAUTH/NOPERM degrade silently to {}."""
    if not REDIS_AVAILABLE:
        return {}
    try:
        r = redis_lib.Redis(
            host=host, port=port, ssl=True, ssl_cert_reqs="none",
            socket_timeout=5, socket_connect_timeout=5,
        )
        tls_config = r.config_get("tls-*")
        r.close()
        return tls_config or {}
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
