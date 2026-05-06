import json
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Callable

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, ed448
from cryptography.hazmat.backends import default_backend

from quirk.models import CryptoEndpoint
from quirk.logging_util import Logger
from quirk.scanner.tls_capabilities import enumerate_tls_capabilities

# ---------------------------------------------------------------------------
# sslyze optional import
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
    )
    import sslyze as _sslyze_module
    SSLYZE_AVAILABLE = True
except ImportError:
    SSLYZE_AVAILABLE = False

# Warn once per process when sslyze is absent
_sslyze_warned = False


def _pubkey_info(pubkey):
    if isinstance(pubkey, rsa.RSAPublicKey):
        return ("RSA", pubkey.key_size)
    if isinstance(pubkey, ec.EllipticCurvePublicKey):
        return ("ECDSA", pubkey.key_size)
    if isinstance(pubkey, ed25519.Ed25519PublicKey):
        return ("Ed25519", 256)
    if isinstance(pubkey, ed448.Ed448PublicKey):
        return ("Ed448", 456)
    return ("Unknown", None)


def _extract_sans(cert: x509.Certificate) -> str:
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        names = ext.value.get_values_for_type(x509.DNSName)
        ips = [str(i) for i in ext.value.get_values_for_type(x509.IPAddress)]
        return ",".join(names + ips)
    except Exception:
        return ""


def _categorize_tls_error(e: Exception) -> str:
    msg = str(e)
    if isinstance(e, ConnectionRefusedError):
        return "CONNECTION_REFUSED"
    if isinstance(e, TimeoutError):
        return "TIMEOUT"
    if "WRONG_VERSION_NUMBER" in msg or "wrong version number" in msg:
        return "NOT_TLS_ON_PORT"
    if "UNKNOWN_PROTOCOL" in msg or "unknown protocol" in msg:
        return "NOT_TLS_ON_PORT"
    if "certificate required" in msg.lower():
        return "MTLS_REQUIRED"
    if "handshake failure" in msg.lower():
        if "certificate" in msg.lower():
            return "MTLS_REQUIRED"
        return "TLS_HANDSHAKE_FAILED"
    if "certificate verify failed" in msg.lower():
        return "CERT_VERIFY_FAILED"
    if "reset by peer" in msg.lower():
        return "RESET_BY_PEER"
    return "TLS_ERROR"


def _as_csv(items: List[str]) -> str:
    return ",".join([x for x in items if x])


# ---------------------------------------------------------------------------
# sslyze primary scanner
# ---------------------------------------------------------------------------

# Protocol label map: scan_result attribute → (display_name, version_priority)
# Higher priority = more preferred; used to pick ep.tls_version
_PROTO_MAP = [
    ("tls_1_3_cipher_suites", "TLSv1.3", 4),
    ("tls_1_2_cipher_suites", "TLSv1.2", 3),
    ("tls_1_1_cipher_suites", "TLSv1.1", 2),
    ("tls_1_0_cipher_suites", "TLSv1", 1),
    ("ssl_3_0_cipher_suites", "SSLv3", 0),
    ("ssl_2_0_cipher_suites", "SSLv2", -1),
]


def _scan_one_sslyze(
    host: str,
    port: int,
    timeout: int,
    include_sni: bool,
    logger: Optional[Logger] = None,
) -> Optional[CryptoEndpoint]:
    """
    Attempt TLS scan using sslyze.  Returns a populated CryptoEndpoint on success,
    or None if sslyze fails/is unavailable (triggers fallback to _scan_one_fallback).
    """
    global _sslyze_warned

    if not SSLYZE_AVAILABLE:
        if not _sslyze_warned:
            if logger:
                logger.v("sslyze not installed — falling back to ssl+cryptography scanner")
            _sslyze_warned = True
        return None

    try:
        # Determine SNI hostname
        is_ip = False
        try:
            import ipaddress
            ipaddress.ip_address(host)
            is_ip = True
        except ValueError:
            pass

        sni_hostname = host if (include_sni and not is_ip) else None

        scan_request = ServerScanRequest(
            server_location=ServerNetworkLocation(hostname=host, port=port),
            network_configuration=ServerNetworkConfiguration(
                tls_server_name_indication=sni_hostname,
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

        server_result = results[0]
        if server_result.scan_status != ServerScanStatusEnum.COMPLETED:
            if logger:
                logger.v(f"sslyze ERROR_NO_CONNECTIVITY for {host}:{port} — using fallback")
            return None

        scan = server_result.scan_result

        ep = CryptoEndpoint(
            host=host,
            port=port,
            protocol="TLS",
            scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
            sni_used=bool(include_sni and not is_ip),
        )

        # ----------------------------------------------------------------
        # Certificate info
        # ----------------------------------------------------------------
        cert_attempt = scan.certificate_info
        if cert_attempt.status == ScanCommandAttemptStatusEnum.COMPLETED:
            deployment = cert_attempt.result.certificate_deployments[0]
            leaf = deployment.received_certificate_chain[0]

            ep.cert_subject = leaf.subject.rfc4514_string()
            ep.cert_issuer = leaf.issuer.rfc4514_string()
            ep.cert_sans = _extract_sans(leaf)
            ep.cert_sig_alg = (
                leaf.signature_hash_algorithm.name
                if leaf.signature_hash_algorithm
                else "unknown"
            )

            pubkey = leaf.public_key()
            alg, size = _pubkey_info(pubkey)
            ep.cert_pubkey_alg = alg
            ep.cert_pubkey_size = size

            # Date handling — use _utc variant when available
            if hasattr(leaf, "not_valid_before_utc") and hasattr(leaf, "not_valid_after_utc"):
                nb = leaf.not_valid_before_utc
                na = leaf.not_valid_after_utc
            else:
                nb = leaf.not_valid_before
                na = leaf.not_valid_after
            ep.cert_not_before = nb.replace(tzinfo=None)
            ep.cert_not_after = na.replace(tzinfo=None)

            chain_depth = len(deployment.received_certificate_chain)
            chain_verified = deployment.verified_certificate_chain is not None
        else:
            chain_depth = 0
            chain_verified = False

        # Phase 46 TLS-FIND-06: persist chain verification result to column
        ep.chain_verified = chain_verified

        # ----------------------------------------------------------------
        # Cipher suites per protocol
        # ----------------------------------------------------------------
        accepted_by_version: dict = {}
        ssl_versions_with_suites = set()
        legacy_versions_with_suites = set()  # TLS 1.0/1.1

        highest_version: Optional[str] = None
        highest_priority = -999

        all_accepted_ciphers: List[str] = []
        pfs_supported = False
        weak_present = False
        legacy_suites = False

        def _is_pfs(name: str) -> bool:
            upper = name.upper()
            return "ECDHE" in upper or "DHE" in upper

        weak_markers = ("RC4", "3DES", "CBC3", "NULL", "EXPORT", "MD5")

        def _is_weak(name: str) -> bool:
            upper = name.upper()
            return any(m in upper for m in weak_markers)

        def _is_legacy_suite(name: str) -> bool:
            upper = name.upper()
            if upper in {"AES128-SHA", "AES256-SHA"}:
                return True
            if "CBC" in upper and not _is_pfs(upper):
                return True
            return False

        for attr, version_label, priority in _PROTO_MAP:
            attempt = getattr(scan, attr, None)
            if attempt is None:
                continue
            if attempt.status != ScanCommandAttemptStatusEnum.COMPLETED:
                continue
            names = [s.cipher_suite.name for s in attempt.result.accepted_cipher_suites]
            if names:
                accepted_by_version[version_label] = names
                all_accepted_ciphers.extend(names)

                if version_label in ("SSLv2", "SSLv3"):
                    ssl_versions_with_suites.add(version_label)
                elif version_label in ("TLSv1", "TLSv1.1"):
                    legacy_versions_with_suites.add(version_label)

                if priority > highest_priority:
                    highest_priority = priority
                    highest_version = version_label

                for cipher_name in names:
                    if _is_pfs(cipher_name):
                        pfs_supported = True
                    if _is_weak(cipher_name):
                        weak_present = True
                    if _is_legacy_suite(cipher_name):
                        legacy_suites = True

        ep.tls_version = highest_version
        ep.cipher_suite = (
            accepted_by_version[highest_version][0] if highest_version else None
        )
        ep.tls_supported_versions = ",".join(
            label for _, label, _ in sorted(_PROTO_MAP, key=lambda x: -x[2])
            if label in accepted_by_version
        )
        ep.tls_supported_ciphers_sample = ",".join(all_accepted_ciphers[:10])
        ep.tls_weak_ciphers_present = bool(ssl_versions_with_suites) or weak_present
        ep.tls_legacy_suites_present = bool(legacy_versions_with_suites) or legacy_suites
        ep.tls_pfs_supported = pfs_supported
        ep.tls_enum_mode = "sslyze"

        # ----------------------------------------------------------------
        # Elliptic curves
        # ----------------------------------------------------------------
        curve_names: List[str] = []
        ec_attempt = getattr(scan, "elliptic_curves", None)
        if ec_attempt is not None and ec_attempt.status == ScanCommandAttemptStatusEnum.COMPLETED:
            curve_names = [c.name for c in ec_attempt.result.supported_curves]

        # ----------------------------------------------------------------
        # tls_capabilities_json
        # ----------------------------------------------------------------
        sslyze_version = getattr(_sslyze_module, "__version__", "unknown")
        caps = {
            "source": "sslyze",
            "sslyze_version": sslyze_version,
            "accepted_by_version": accepted_by_version,
            "chain_depth": chain_depth,
            "chain_verified": chain_verified,
            "elliptic_curves": curve_names,
        }
        ep.tls_capabilities_json = json.dumps(caps)

        if logger:
            logger.v(
                f"sslyze TLS {host}:{port} version={ep.tls_version} "
                f"versions=[{ep.tls_supported_versions}] weak={ep.tls_weak_ciphers_present} "
                f"pfs={ep.tls_pfs_supported}"
            )

        return ep

    except Exception as e:
        if logger:
            logger.v(f"sslyze exception for {host}:{port}: {e} — using fallback")
        return None


# ---------------------------------------------------------------------------
# Fallback scanner (original scan_one, renamed)
# ---------------------------------------------------------------------------

def _scan_one_fallback(
    host: str,
    port: int,
    timeout: int,
    include_sni: bool,
    logger: Optional[Logger] = None,
    tls_enum_mode: str = "fast",
) -> CryptoEndpoint:
    ep = CryptoEndpoint(
        host=host,
        port=port,
        protocol="TLS",
        scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
        sni_used=bool(include_sni),
    )

    # Phase 46 D-01: chain verification pre-pass.
    # CERT_REQUIRED against system trust store. SSLCertVerificationError → False.
    # Any other exception (timeout, connection refused) → None (indeterminate).
    # Per Pitfall 1: network errors must NOT produce false untrusted-CA findings.
    try:
        verify_ctx = ssl.create_default_context()
        verify_ctx.verify_mode = ssl.CERT_REQUIRED
        is_ip_for_verify = False
        try:
            import ipaddress
            ipaddress.ip_address(host)
            is_ip_for_verify = True
        except Exception:
            pass
        verify_hostname = host if (include_sni and not is_ip_for_verify) else None
        # Phase 46 fix: ssl requires server_hostname when check_hostname=True. When
        # we have no hostname to use (SNI off, or host is a literal IP), disable
        # the hostname check so the chain-verification pre-pass can still run —
        # chain validation against the system trust store is independent of the
        # hostname check, and a hostname mismatch is a separate concern from
        # untrusted-CA. Without this, verify_ctx.wrap_socket raises ValueError,
        # which the broad except below would swallow as chain_verified=None,
        # leaving the untrusted-CA branch structurally dead.
        if verify_hostname is None:
            verify_ctx.check_hostname = False
        else:
            verify_ctx.check_hostname = True
        with socket.create_connection((host, port), timeout=timeout) as vsock:
            with verify_ctx.wrap_socket(vsock, server_hostname=verify_hostname) as vssock:
                ep.chain_verified = True
    except ssl.SSLCertVerificationError:
        ep.chain_verified = False
    except Exception:
        ep.chain_verified = None

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, port), timeout=timeout) as sock:
            # If host is an IP, server_hostname should be None for SNI
            is_ip = False
            try:
                import ipaddress
                ipaddress.ip_address(host)
                is_ip = True
            except Exception:
                is_ip = False

            server_hostname = host if (include_sni and not is_ip) else None

            with ctx.wrap_socket(sock, server_hostname=server_hostname) as ssock:
                ep.tls_version = ssock.version()
                cipher = ssock.cipher()
                ep.cipher_suite = cipher[0] if cipher else None

                der = ssock.getpeercert(binary_form=True)
                cert = x509.load_der_x509_certificate(der, default_backend())

                ep.cert_subject = cert.subject.rfc4514_string()
                ep.cert_issuer = cert.issuer.rfc4514_string()
                ep.cert_sans = _extract_sans(cert)
                ep.cert_sig_alg = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else "unknown"

                pubkey = cert.public_key()
                alg, size = _pubkey_info(pubkey)
                ep.cert_pubkey_alg = alg
                ep.cert_pubkey_size = size

                # avoid cryptography warnings if possible
                if hasattr(cert, "not_valid_before_utc") and hasattr(cert, "not_valid_after_utc"):
                    nb = cert.not_valid_before_utc
                    na = cert.not_valid_after_utc
                else:
                    nb = cert.not_valid_before
                    na = cert.not_valid_after

                ep.cert_not_before = nb.replace(tzinfo=None)
                ep.cert_not_after = na.replace(tzinfo=None)

        # ==========================
        # v3.6 TLS capability enum
        # ==========================
        # Only run after a successful TLS handshake
        mode = tls_enum_mode if tls_enum_mode in ("fast", "deep") else "fast"
        caps = enumerate_tls_capabilities(host, port, timeout=max(2, min(timeout, 5)), include_sni=include_sni, mode=mode)

        ep.tls_supported_versions = _as_csv(caps.supported_versions)
        ep.tls_supported_ciphers_sample = _as_csv(caps.supported_ciphers_sample)
        ep.tls_weak_ciphers_present = bool(caps.weak_ciphers_present)
        ep.tls_legacy_suites_present = bool(caps.legacy_suites_present)
        ep.tls_pfs_supported = bool(caps.pfs_supported)
        ep.tls_enum_mode = mode
        ep.tls_enum_notes = caps.notes

        if logger:
            logger.v(
                f"TLS {host}:{port} {ep.tls_version} "
                f"versions=[{ep.tls_supported_versions}] weak={ep.tls_weak_ciphers_present} "
                f"legacy={ep.tls_legacy_suites_present} pfs={ep.tls_pfs_supported}"
            )

    except Exception as e:
        cat = _categorize_tls_error(e)
        ep.tls_blocker_reason = cat
        ep.scan_error = f"{cat}: {e}"
        if logger:
            logger.v(f"TLS {host}:{port} {cat} ({e})")

    return ep


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scan_one(
    host: str,
    port: int,
    timeout: int,
    include_sni: bool,
    logger: Optional[Logger] = None,
    tls_enum_mode: str = "fast",
) -> CryptoEndpoint:
    """
    Primary TLS scan entry point.

    Tries sslyze first (if installed).  If sslyze is unavailable or fails for
    this target, falls back to the ssl+cryptography scanner (_scan_one_fallback).
    """
    if SSLYZE_AVAILABLE:
        try:
            ep = _scan_one_sslyze(host, port, timeout, include_sni, logger)
            if ep is not None:
                # Phase 46 D-01: validation gate — half-populated ep => merge with fallback.
                # If sslyze omitted critical certificate metadata, run the fallback and
                # merge any missing fields (chain_verified included) so the row that
                # reaches the DB is never half-populated.
                if ep.cert_not_after is None or not (ep.cert_subject or "").strip():
                    fb = _scan_one_fallback(host, port, timeout, include_sni, logger, tls_enum_mode)
                    if ep.cert_not_after is None:
                        ep.cert_not_after = fb.cert_not_after
                    if not (ep.cert_subject or "").strip():
                        ep.cert_subject = fb.cert_subject
                    if not (ep.cert_issuer or "").strip():
                        ep.cert_issuer = fb.cert_issuer
                    if ep.cert_pubkey_size is None:
                        ep.cert_pubkey_size = fb.cert_pubkey_size
                        ep.cert_pubkey_alg = fb.cert_pubkey_alg
                    if ep.chain_verified is None:
                        ep.chain_verified = fb.chain_verified
                return ep
        except Exception as e:
            if logger:
                logger.v(f"sslyze failed for {host}:{port}, falling back: {e}")
    return _scan_one_fallback(host, port, timeout, include_sni, logger, tls_enum_mode)


def scan_tls_targets(
    cfg,
    targets: List[Tuple[str, int]],
    logger: Optional[Logger] = None,
    progress_cb: Optional[Callable[[int], None]] = None
) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []

    # default enum mode
    tls_enum_mode = getattr(getattr(cfg, "scan", cfg), "tls_enum_mode", "fast")
    # Phase 41 / D-08: read per-scanner timeout + concurrency from canonical sub-table /
    # dedicated flat field. No more cfg.scan.timeout_seconds / cfg.scan.concurrency mutation.
    if hasattr(cfg.scan, "timeouts"):
        tls_timeout = cfg.scan.timeouts.tls_seconds
    else:
        tls_timeout = cfg.scan.timeout_seconds
    tls_workers = getattr(cfg.scan, "tls_concurrency", cfg.scan.concurrency)
    if logger:
        logger.stamp(f"Starting TLS scans: {len(targets)} targets (workers={tls_workers}, enum={tls_enum_mode})")

    with ThreadPoolExecutor(max_workers=tls_workers) as ex:
        futures = [
            ex.submit(scan_one, host, port, tls_timeout, cfg.scan.include_sni, logger, tls_enum_mode)
            for (host, port) in targets
        ]
        for f in as_completed(futures):
            results.append(f.result())
            if progress_cb:
                progress_cb(1)

    if logger:
        ok = len([e for e in results if not e.scan_error])
        logger.stamp(f"TLS scans complete: {ok}/{len(results)} successful")
    return results
