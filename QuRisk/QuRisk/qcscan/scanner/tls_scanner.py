import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Callable

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, ed448
from cryptography.hazmat.backends import default_backend

from qcscan.models import CryptoEndpoint
from qcscan.logging_util import Logger
from qcscan.scanner.tls_capabilities import enumerate_tls_capabilities


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
    if "handshake failure" in msg.lower():
        return "TLS_HANDSHAKE_FAILURE"
    if "certificate verify failed" in msg.lower():
        return "CERT_VERIFY_FAILED"
    if "reset by peer" in msg.lower():
        return "RESET_BY_PEER"
    return "TLS_ERROR"


def _as_csv(items: List[str]) -> str:
    return ",".join([x for x in items if x])


def scan_one(
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
        ep.tls_pfs_supported = bool(caps.pfs_supported)
        ep.tls_enum_mode = mode
        ep.tls_enum_notes = caps.notes

        if logger:
            logger.v(
                f"✅ TLS {host}:{port} {ep.tls_version} "
                f"versions=[{ep.tls_supported_versions}] weak={ep.tls_weak_ciphers_present} pfs={ep.tls_pfs_supported}"
            )

    except Exception as e:
        cat = _categorize_tls_error(e)
        ep.scan_error = f"{cat}: {e}"
        if logger:
            logger.v(f"⚠️ TLS {host}:{port} {cat} ({e})")

    return ep


def scan_tls_targets(
    cfg,
    targets: List[Tuple[str, int]],
    logger: Optional[Logger] = None,
    progress_cb: Optional[Callable[[int], None]] = None
) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []

    # default enum mode
    tls_enum_mode = getattr(getattr(cfg, "scan", cfg), "tls_enum_mode", "fast")
    if logger:
        logger.stamp(f"Starting TLS scans: {len(targets)} targets (workers={cfg.scan.concurrency}, enum={tls_enum_mode})")

    with ThreadPoolExecutor(max_workers=cfg.scan.concurrency) as ex:
        futures = [
            ex.submit(scan_one, host, port, cfg.scan.timeout_seconds, cfg.scan.include_sni, logger, tls_enum_mode)
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
