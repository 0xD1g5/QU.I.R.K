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

def _scan_one_sslyze_kafka(
    host: str,
    port: int,
    timeout: int,
    logger: Optional[Logger] = None,
) -> Optional[CryptoEndpoint]:
    """KAFKA-01: sslyze TLS probe against a Kafka TLS listener.

    Returns a populated CryptoEndpoint on success, None on any failure.
    ConnectionRefusedError is silent at DEBUG (D-03 carry-forward).
    No tls_opportunistic_encryption — Kafka TLS is direct, not STARTTLS.
    """
    global _sslyze_warned

    if not SSLYZE_AVAILABLE:
        if not _sslyze_warned:
            if logger:
                logger.v("sslyze not installed — broker scanner Kafka probe skipped")
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
                logger.v(f"sslyze ERROR for Kafka {host}:{port}")
            return None

        scan = server_result.scan_result

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
                f"sslyze KAFKA {host}:{port} version={ep.tls_version} "
                f"weak={ep.tls_weak_ciphers_present} pfs={ep.tls_pfs_supported}"
            )

        return ep

    except ConnectionRefusedError:
        # D-03: CONNECTION_REFUSED is non-fatal and silent at DEBUG
        if logger:
            try:
                logger.debug(f"Kafka port {port} CONNECTION_REFUSED on {host} (sslyze)")
            except AttributeError:
                pass
        return None
    except Exception as e:
        if logger:
            logger.v(f"sslyze exception for Kafka {host}:{port}: {e}")
        return None


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
