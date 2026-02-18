from __future__ import annotations

import ipaddress
import socket
import ssl
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TLSCapabilities:
    supported_versions: List[str]
    supported_ciphers_sample: List[str]
    weak_ciphers_present: bool
    pfs_supported: bool
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except Exception:
        return False


def _make_server_hostname(host: str, include_sni: bool) -> Optional[str]:
    if not include_sni:
        return None
    if _is_ip(host):
        return None
    return host


def _try_handshake(
    host: str,
    port: int,
    timeout: int,
    include_sni: bool,
    tls_min: Optional[ssl.TLSVersion] = None,
    tls_max: Optional[ssl.TLSVersion] = None,
    ciphers: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[Tuple[str, str, int]]]:
    """
    Attempt a TLS handshake using standard library ssl.
    Returns: (success, negotiated_version, negotiated_cipher_tuple)
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Restrict versions if requested
    if tls_min is not None:
        ctx.minimum_version = tls_min
    if tls_max is not None:
        ctx.maximum_version = tls_max

    # Configure cipher list (affects TLS<=1.2 in Python/OpenSSL).
    if ciphers:
        try:
            ctx.set_ciphers(ciphers)
        except ssl.SSLError:
            # cipher string not supported by underlying OpenSSL build
            return (False, None, None)

    server_hostname = _make_server_hostname(host, include_sni)

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=server_hostname) as ssock:
                ver = ssock.version()
                cip = ssock.cipher()
                return (True, ver, cip)
    except Exception:
        return (False, None, None)


def enumerate_tls_capabilities(
    host: str,
    port: int,
    timeout: int = 3,
    include_sni: bool = True,
    mode: str = "fast",
) -> TLSCapabilities:
    """
    Fast, pragmatic enumeration:
      - Supported TLS versions: try TLS1.0/1.1/1.2/1.3 handshakes
      - Cipher sample probing (TLS<=1.2): try representative cipher families
      - Weak cipher detection: attempt handshakes restricted to legacy/weak families
      - PFS supported: if any ECDHE handshake succeeds in sample
    """
    supported_versions: List[str] = []
    supported_ciphers: List[str] = []
    weak_present = False
    pfs_supported = False
    notes_parts: List[str] = []

    # ---- Version support probing ----
    # Note: some Python/OpenSSL builds disable TLS1.0/1.1 entirely; that's fine.
    version_tests = [
        ("TLSv1", getattr(ssl.TLSVersion, "TLSv1", None)),
        ("TLSv1.1", getattr(ssl.TLSVersion, "TLSv1_1", None)),
        ("TLSv1.2", getattr(ssl.TLSVersion, "TLSv1_2", None)),
        ("TLSv1.3", getattr(ssl.TLSVersion, "TLSv1_3", None)),
    ]

    for name, v in version_tests:
        if v is None:
            continue
        ok, ver, cip = _try_handshake(host, port, timeout, include_sni, tls_min=v, tls_max=v)
        if ok:
            supported_versions.append(name)

    if not supported_versions:
        return TLSCapabilities(
            supported_versions=[],
            supported_ciphers_sample=[],
            weak_ciphers_present=False,
            pfs_supported=False,
            notes="No successful constrained-version TLS handshakes (enumeration incomplete).",
        )

    # ---- Cipher probing (sample) ----
    # We probe only TLS 1.2 where cipher lists are meaningful via ctx.set_ciphers.
    # TLS 1.3 cipher suites are not reliably configurable via Python stdlib; we treat TLS1.3 support as signal.
    sample_modern = [
        "ECDHE-RSA-AES128-GCM-SHA256",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-ECDSA-AES128-GCM-SHA256",
        "ECDHE-ECDSA-AES256-GCM-SHA384",
        "ECDHE-RSA-CHACHA20-POLY1305",
        "ECDHE-ECDSA-CHACHA20-POLY1305",
    ]

    sample_legacy = [
        "AES128-SHA",          # TLS_RSA_WITH_AES_128_CBC_SHA (no PFS)
        "AES256-SHA",          # TLS_RSA_WITH_AES_256_CBC_SHA (no PFS)
        "DES-CBC3-SHA",        # 3DES (weak)
    ]

    # Weakest families (often disabled by OpenSSL, but if they work it's a big signal)
    sample_very_weak = [
        "RC4-SHA",
        "NULL-SHA",
        "EXP-RC4-MD5",
        "EXP-DES-CBC-SHA",
    ]

    # Mode determines how aggressive we probe
    if mode not in ("fast", "deep"):
        mode = "fast"

    # Always probe modern sample
    for c in sample_modern:
        ok, ver, cip = _try_handshake(
            host, port, timeout, include_sni,
            tls_min=getattr(ssl.TLSVersion, "TLSv1_2", None),
            tls_max=getattr(ssl.TLSVersion, "TLSv1_2", None),
            ciphers=c,
        )
        if ok and cip:
            name = cip[0]
            if name not in supported_ciphers:
                supported_ciphers.append(name)
            if name.startswith("ECDHE-"):
                pfs_supported = True

    # Probe legacy sample (fast)
    for c in sample_legacy:
        ok, ver, cip = _try_handshake(
            host, port, timeout, include_sni,
            tls_min=getattr(ssl.TLSVersion, "TLSv1_2", None),
            tls_max=getattr(ssl.TLSVersion, "TLSv1_2", None),
            ciphers=c,
        )
        if ok and cip:
            name = cip[0]
            if name not in supported_ciphers:
                supported_ciphers.append(name)
            # mark weak if 3DES or static RSA key exchange
            if "3DES" in name or name.startswith("AES") or name.startswith("DES-") or "-SHA" in name and "GCM" not in name:
                weak_present = True

            # PFS signal: static RSA ciphers are typically no-PFS
            if not name.startswith("ECDHE-"):
                # doesn't negate pfs_supported; just indicates no-PFS is enabled
                pass

    # Deep mode: probe very weak families (if OpenSSL allows)
    if mode == "deep":
        for c in sample_very_weak:
            ok, ver, cip = _try_handshake(
                host, port, timeout, include_sni,
                tls_min=getattr(ssl.TLSVersion, "TLSv1_2", None),
                tls_max=getattr(ssl.TLSVersion, "TLSv1_2", None),
                ciphers=c,
            )
            if ok:
                weak_present = True
                notes_parts.append(f"Very weak cipher accepted ({c})")

    # Notes
    if "TLSv1" in supported_versions or "TLSv1.1" in supported_versions:
        notes_parts.append("Legacy TLS versions supported (1.0/1.1)")

    if "TLSv1.3" in supported_versions:
        notes_parts.append("TLS 1.3 supported")

    if not supported_ciphers:
        notes_parts.append("Cipher enumeration limited (no sampled ciphers succeeded under TLS 1.2 constraints)")

    return TLSCapabilities(
        supported_versions=supported_versions,
        supported_ciphers_sample=supported_ciphers,
        weak_ciphers_present=bool(weak_present),
        pfs_supported=bool(pfs_supported),
        notes="; ".join(notes_parts) if notes_parts else "OK",
    )

