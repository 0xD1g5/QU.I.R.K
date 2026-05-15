"""Email TLS scanner — Phase 32 (v4.4 Data in Motion).

Covers all 7 standard email protocol ports via sslyze (primary) with
stdlib smtplib/imaplib/poplib fallback when sslyze fails or is absent.

Requirements: STRUCT-01, EMAIL-01..07, EMAIL-10
Reference: .planning/phases/32-email-scanner/32-RESEARCH.md (Pattern 1)

Reuses _pubkey_info() and _extract_sans() from quirk.scanner.tls_scanner —
does NOT duplicate them (D-10).
"""
import json
import ssl
import socket
import smtplib
import imaplib
import poplib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from quirk.models import CryptoEndpoint
from quirk.logging_util import Logger
from quirk.scanner.tls_scanner import _pubkey_info, _extract_sans  # D-10: reuse, do NOT duplicate
from quirk.util.safe_exc import safe_str

# ---------------------------------------------------------------------------
# sslyze optional import (mirrors tls_scanner.py guard, plus
# ProtocolWithOpportunisticTlsEnum for STARTTLS port negotiation)
# ---------------------------------------------------------------------------
try:
    from sslyze import (
        Scanner as SslyzeScanner,
        ServerScanRequest,
        ServerNetworkLocation,
        ScanCommand,
        ServerNetworkConfiguration,
        ScanCommandAttemptStatusEnum,
        ServerScanStatusEnum,
        ProtocolWithOpportunisticTlsEnum,
    )
    SSLYZE_AVAILABLE = True
except ImportError:
    SSLYZE_AVAILABLE = False
    # Provide module-level names so tests can `patch("...email_scanner.SslyzeScanner")`
    # and so the EMAIL_PORTS table can reference ProtocolWithOpportunisticTlsEnum
    # without raising NameError when sslyze is absent.
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

    class ProtocolWithOpportunisticTlsEnum:  # noqa: N801
        SMTP = "SMTP"
        IMAP = "IMAP"
        POP3 = "POP3"

_sslyze_warned = False


# ---------------------------------------------------------------------------
# EMAIL_PORTS table — exact 7 rows
# (port, protocol_label, service_detail_prefix, starttls_enum_or_None)
# ---------------------------------------------------------------------------
EMAIL_PORTS = [
    (25,  "SMTP-STARTTLS", "SMTP-STARTTLS",
        ProtocolWithOpportunisticTlsEnum.SMTP if SSLYZE_AVAILABLE else None),
    (465, "SMTPS",         "SMTPS",          None),   # implicit TLS
    (587, "SMTP-STARTTLS", "SMTP-STARTTLS",
        ProtocolWithOpportunisticTlsEnum.SMTP if SSLYZE_AVAILABLE else None),
    (143, "IMAP-STARTTLS", "IMAP-STARTTLS",
        ProtocolWithOpportunisticTlsEnum.IMAP if SSLYZE_AVAILABLE else None),
    (993, "IMAPS",         "IMAPS",          None),   # implicit TLS
    (110, "POP3-STARTTLS", "POP3-STARTTLS",
        ProtocolWithOpportunisticTlsEnum.POP3 if SSLYZE_AVAILABLE else None),
    (995, "POP3S",         "POP3S",          None),   # implicit TLS
]


# ---------------------------------------------------------------------------
# sslyze primary scanner
# ---------------------------------------------------------------------------

# Protocol attribute → (display_name, priority); higher priority wins for ep.tls_version
_EMAIL_PROTO_MAP = [
    ("tls_1_3_cipher_suites", "TLSv1.3", 4),
    ("tls_1_2_cipher_suites", "TLSv1.2", 3),
]


def _is_pfs(name: str) -> bool:
    upper = name.upper()
    return "ECDHE" in upper or "DHE" in upper


def _is_weak(name: str) -> bool:
    upper = name.upper()
    return any(m in upper for m in ("RC4", "3DES", "CBC3", "NULL", "EXPORT", "MD5"))


def _scan_one_sslyze_email(
    host: str,
    port: int,
    starttls_enum,
    timeout: int,
    logger: Optional[Logger] = None,
) -> Optional[CryptoEndpoint]:
    """Primary TLS probe via sslyze.

    Returns a populated CryptoEndpoint on success, None on any failure
    (so the caller falls back to the stdlib path). Per D-03,
    ConnectionRefusedError is silent at DEBUG.
    """
    global _sslyze_warned

    if SslyzeScanner is None:
        if not _sslyze_warned:
            if logger:
                logger.v("sslyze not installed — email scanner using stdlib fallback")
            _sslyze_warned = True
        return None

    try:
        net_cfg_kwargs = {
            "tls_server_name_indication": host,
            "network_timeout": timeout,
        }
        if starttls_enum is not None:
            net_cfg_kwargs["tls_opportunistic_encryption"] = starttls_enum

        net_cfg = ServerNetworkConfiguration(**net_cfg_kwargs)

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
                logger.v(f"sslyze ERROR for {host}:{port} — using fallback")
            return None

        scan = server_result.scan_result

        ep = CryptoEndpoint(
            host=host,
            port=port,
            protocol="",  # set by orchestrator
        )

        # ----------------------------------------------------------------
        # Cipher suites per protocol (TLS 1.2 + 1.3 only for email)
        # ----------------------------------------------------------------
        accepted_by_version: dict = {}
        all_accepted_ciphers: List[str] = []
        pfs_supported = False
        weak_present = False
        highest_version: Optional[str] = None
        highest_priority = -999

        for attr, version_label, priority in _EMAIL_PROTO_MAP:
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
                    # MagicMock public_key() may not match _pubkey_info isinstance checks
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
                f"sslyze EMAIL {host}:{port} version={ep.tls_version} "
                f"weak={ep.tls_weak_ciphers_present} pfs={ep.tls_pfs_supported}"
            )

        return ep

    except ConnectionRefusedError:
        # D-03: CONNECTION_REFUSED is non-fatal and silent at DEBUG
        if logger:
            try:
                logger.debug(f"Email port {port} CONNECTION_REFUSED on {host} (sslyze)")
            except AttributeError:
                pass
        return None
    except Exception as e:
        if logger:
            logger.v(f"sslyze exception for {host}:{port}: {e} — using fallback")
        return None


# ---------------------------------------------------------------------------
# Stdlib fallback helpers — each returns (tls_version, cipher_name, der_bytes)
# ---------------------------------------------------------------------------

def _peer_metadata(ssock) -> Tuple[Optional[str], Optional[str], Optional[bytes]]:
    """Pull (version, cipher_name, DER cert) from a wrapped SSLSocket-like object.

    Duck-typed so MagicMock fixtures with .version()/.cipher()/.getpeercert()
    satisfy the contract without strict isinstance(ssl.SSLSocket).
    """
    try:
        version = ssock.version() if callable(ssock.version) else ssock.version
    except Exception:
        version = None
    try:
        cipher = ssock.cipher() if callable(ssock.cipher) else ssock.cipher
        cipher_name = cipher[0] if cipher else None
    except Exception:
        cipher_name = None
    try:
        der = ssock.getpeercert(binary_form=True)
    except Exception:
        der = None
    return version, cipher_name, der


def _fallback_smtp_starttls(host, port, timeout, ctx):
    smtp = smtplib.SMTP(host, port, timeout=timeout)
    try:
        smtp.ehlo()
        smtp.starttls(context=ctx)
        smtp.ehlo()
        ssock = smtp.sock
        if ssock is None:
            ssock = getattr(getattr(smtp, "file", None), "_sock", None)
        if ssock is None:
            raise RuntimeError("smtplib STARTTLS did not yield an SSL socket")
        return _peer_metadata(ssock)
    finally:
        try:
            smtp.quit()
        except Exception:
            try:
                smtp.close()
            except Exception:
                pass


def _fallback_imap_starttls(host, port, timeout, ctx):
    imap = imaplib.IMAP4(host, port, timeout=timeout)
    try:
        imap.starttls(ssl_context=ctx)
        ssock = getattr(imap, "sock", None)
        if ssock is None:
            ssock = getattr(getattr(imap, "file", None), "_sock", None)
        if ssock is None:
            raise RuntimeError("imaplib STARTTLS did not yield an SSL socket")
        return _peer_metadata(ssock)
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def _fallback_pop3_starttls(host, port, timeout, ctx):
    pop = poplib.POP3(host, port=port, timeout=timeout)
    try:
        pop.stls(context=ctx)
        ssock = getattr(pop, "sock", None)
        if ssock is None:
            raise RuntimeError("poplib STARTTLS did not yield an SSL socket")
        return _peer_metadata(ssock)
    finally:
        try:
            pop.quit()
        except Exception:
            pass


def _fallback_implicit_tls(host, port, timeout, ctx):
    """SMTPS/IMAPS/POP3S — direct TLS handshake on connect."""
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        ssock = ctx.wrap_socket(sock, server_hostname=host)
        try:
            return _peer_metadata(ssock)
        finally:
            try:
                ssock.close()
            except Exception:
                pass
    finally:
        try:
            sock.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Stdlib fallback orchestrator
# ---------------------------------------------------------------------------

def _scan_one_fallback_email(
    host: str,
    port: int,
    protocol_label: str,
    timeout: int,
    logger: Optional[Logger] = None,
) -> CryptoEndpoint:
    """Stdlib fallback path. Always returns a CryptoEndpoint — never raises."""
    ep = CryptoEndpoint(host=host, port=port, protocol=protocol_label)

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        if protocol_label == "SMTP-STARTTLS":
            tls_version, cipher_name, der = _fallback_smtp_starttls(host, port, timeout, ctx)
        elif protocol_label == "IMAP-STARTTLS":
            tls_version, cipher_name, der = _fallback_imap_starttls(host, port, timeout, ctx)
        elif protocol_label == "POP3-STARTTLS":
            tls_version, cipher_name, der = _fallback_pop3_starttls(host, port, timeout, ctx)
        else:
            # Implicit TLS (SMTPS 465 / IMAPS 993 / POP3S 995)
            tls_version, cipher_name, der = _fallback_implicit_tls(host, port, timeout, ctx)

        ep.tls_version = tls_version
        ep.cipher_suite = cipher_name

        if cipher_name:
            ep.tls_pfs_supported = _is_pfs(cipher_name)
            ep.tls_weak_ciphers_present = _is_weak(cipher_name)

        if der and isinstance(der, (bytes, bytearray)):
            try:
                cert = x509.load_der_x509_certificate(bytes(der), default_backend())
                try:
                    ep.cert_subject = cert.subject.rfc4514_string()
                except Exception:
                    pass
                try:
                    ep.cert_issuer = cert.issuer.rfc4514_string()
                except Exception:
                    pass
                try:
                    ep.cert_sans = _extract_sans(cert)
                except Exception:
                    pass
                try:
                    sig = cert.signature_hash_algorithm
                    ep.cert_sig_alg = sig.name if sig else "unknown"
                except Exception:
                    pass
                try:
                    alg, size = _pubkey_info(cert.public_key())
                    ep.cert_pubkey_alg = alg
                    ep.cert_pubkey_size = size
                except Exception:
                    pass
            except Exception as e:
                if logger:
                    logger.v(f"Email cert parse failure {host}:{port}: {e}")

        if logger:
            logger.v(
                f"Email fallback {host}:{port} ({protocol_label}) "
                f"version={ep.tls_version} cipher={ep.cipher_suite}"
            )

    except ConnectionRefusedError:
        # D-03: silent at DEBUG, no exception propagates
        ep.tls_blocker_reason = "CONNECTION_REFUSED"
        if logger:
            try:
                logger.debug(f"Email port {port} CONNECTION_REFUSED on {host}")
            except AttributeError:
                pass
    except (socket.timeout, TimeoutError):
        ep.tls_blocker_reason = "TIMEOUT"
        if logger:
            logger.v(f"Email fallback timeout {host}:{port}")
    except OSError as e:
        # ECONNREFUSED via OSError (errno 111 / 113)
        if getattr(e, "errno", None) in (111, 113):
            ep.tls_blocker_reason = "CONNECTION_REFUSED"
            if logger:
                try:
                    logger.debug(f"Email port {port} CONNECTION_REFUSED on {host} (OSError)")
                except AttributeError:
                    pass
        else:
            ep.scan_error = safe_str(e)
            if logger:
                logger.v(f"Email fallback OSError {host}:{port}: {e}")
    except Exception as e:
        ep.scan_error = safe_str(e)
        if logger:
            logger.v(f"Email fallback error {host}:{port}: {e}")

    return ep


# ---------------------------------------------------------------------------
# Per-target orchestrator
# ---------------------------------------------------------------------------

def scan_one_email(
    host: str,
    port: int,
    protocol_label: str,
    starttls_enum,
    timeout: int,
    logger: Optional[Logger] = None,
    session_start=None,
) -> CryptoEndpoint:
    """Try sslyze → stdlib fallback. Sets protocol, service_detail, scanned_at."""
    ep = _scan_one_sslyze_email(host, port, starttls_enum, timeout, logger)
    if ep is None:
        ep = _scan_one_fallback_email(host, port, protocol_label, timeout, logger)
    ep.protocol = protocol_label
    ep.service_detail = f"{protocol_label}:{port}"
    # STRUCT-01: shared session_start, no bare datetime.now() inside scanner
    ep.scanned_at = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    return ep


# ---------------------------------------------------------------------------
# Top-level driver — expand hosts × EMAIL_PORTS, scan in parallel
# ---------------------------------------------------------------------------

def scan_email_targets(
    hosts: List[str],
    timeout: int,
    logger: Optional[Logger] = None,
    session_start=None,
    motion_concurrency: int = 50,
) -> List[CryptoEndpoint]:
    """Scan each host across all 7 EMAIL_PORTS via ThreadPoolExecutor."""
    results: List[CryptoEndpoint] = []
    tasks = [
        (host, port, label, starttls_enum)
        for host in hosts
        for (port, label, _, starttls_enum) in EMAIL_PORTS
    ]
    if not tasks:
        return results

    if logger:
        logger.stamp(
            f"Starting email TLS scans: {len(tasks)} tasks "
            f"({len(hosts)} hosts × {len(EMAIL_PORTS)} ports)"
        )

    with ThreadPoolExecutor(max_workers=min(len(tasks), motion_concurrency)) as ex:
        futures = {
            ex.submit(
                scan_one_email, host, port, label, starttls_enum,
                timeout, logger, session_start,
            ): (host, port)
            for host, port, label, starttls_enum in tasks
        }
        for f in as_completed(futures):
            try:
                ep = f.result()
            except Exception as e:
                if logger:
                    logger.v(f"Email scan task crashed: {e}")
                continue
            if ep is not None:
                results.append(ep)

    # ------------------------------------------------------------------
    # Phase 32 SC-1 / EMAIL-11: per-host email_scan_json aggregation.
    # Mirrors the kerberos_scan_json attachment pattern at
    # quirk/scanner/kerberos_scanner.py:294,329,340 — group endpoints by
    # host, build a structured summary of every port scan, and attach the
    # JSON to the first endpoint (lowest port) per host for determinism.
    # ------------------------------------------------------------------
    def _port_key(ep) -> int:
        """Sort key that tolerates MagicMock-backed endpoints in unit tests
        (their .port is a MagicMock that can't be compared to int)."""
        try:
            return int(getattr(ep, "port", 0))
        except (TypeError, ValueError):
            return 0

    by_host: dict = {}
    for ep in results:
        host_key = getattr(ep, "host", None)
        # Skip aggregation for MagicMock-backed endpoints (unit-test stubs):
        # their host attribute is a MagicMock, not a hashable string. The real
        # scanner always sets ep.host to a str via CryptoEndpoint(host=...).
        if not isinstance(host_key, str):
            continue
        by_host.setdefault(host_key, []).append(ep)

    session_start_iso = (
        session_start.isoformat() if session_start is not None else None
    )

    for host, host_endpoints in by_host.items():
        host_endpoints_sorted = sorted(host_endpoints, key=_port_key)
        payload = {
            "host": host,
            "session_start": session_start_iso,
            "ports": [
                {
                    "port": ep.port,
                    "service_detail": getattr(ep, "service_detail", None),
                    "tls_version": getattr(ep, "tls_version", None),
                    "cipher_suite": getattr(ep, "cipher_suite", None),
                    "cert_pubkey_alg": getattr(ep, "cert_pubkey_alg", None),
                    "cert_subject": getattr(ep, "cert_subject", None),
                    "cert_issuer": getattr(ep, "cert_issuer", None),
                    "cert_not_after": getattr(ep, "cert_not_after", None),
                    "scan_error": getattr(ep, "scan_error", None),
                    "tls_blocker_reason": getattr(ep, "tls_blocker_reason", None),
                }
                for ep in host_endpoints_sorted
            ],
        }
        host_endpoints_sorted[0].email_scan_json = json.dumps(payload, default=str)

    if logger:
        ok = len([
            e for e in results
            if not getattr(e, "scan_error", None)
            and not getattr(e, "tls_blocker_reason", None)
        ])
        logger.stamp(f"Email scans complete: {ok}/{len(results)} successful")
    return results
