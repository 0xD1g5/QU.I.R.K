import socket
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Tuple

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519, ed448
from cryptography.hazmat.backends import default_backend

from quirk.models import CryptoEndpoint
from quirk.util.safe_exc import safe_str


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


def scan_one(host: str, port: int, timeout: int, include_sni: bool) -> CryptoEndpoint:
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

                # ✅ cryptography prefers *_utc (timezone-aware).
                # Avoid eager evaluation of deprecated properties by checking attribute existence first.
                if hasattr(cert, "not_valid_before_utc") and hasattr(cert, "not_valid_after_utc"):
                    nb = cert.not_valid_before_utc
                    na = cert.not_valid_after_utc
                else:
                    nb = cert.not_valid_before
                    na = cert.not_valid_after

                # Store as naive UTC for SQLite simplicity
                ep.cert_not_before = nb.replace(tzinfo=None)
                ep.cert_not_after = na.replace(tzinfo=None)


    except Exception as e:
        ep.scan_error = safe_str(e)

    return ep


def scan_tls_targets(cfg, targets: List[Tuple[str, int]]) -> List[CryptoEndpoint]:
    results: List[CryptoEndpoint] = []

    with ThreadPoolExecutor(max_workers=cfg.scan.concurrency) as ex:
        futures = [
            ex.submit(scan_one, host, port, cfg.scan.timeout_seconds, cfg.scan.include_sni)
            for (host, port) in targets
        ]
        for f in as_completed(futures):
            results.append(f.result())

    return results
