"""S/MIME signing certificate discovery via LDAP userCertificate /
userSMIMECertificate attributes. Read-only. No mailbox content
accessed. No IMAP imports — enforced by tests/test_smime_ast_gate.py
(SMIME-08).

Phase 79 — SMIME-01, SMIME-02, SMIME-05. The scanner enumerates AD
`userCertificate` and `userSMIMECertificate` LDAP attributes via an
anonymous bind + paged search and classifies each certificate using
shared weak-crypto predicates.

Privacy invariant (SMIME-04): NEVER read or emit envelope-style
metadata (To / From / Subject / Message-ID). NEVER import any IMAP /
SMTP / POP / email.* module.
"""
from __future__ import annotations

try:
    import ldap3
    LDAP3_AVAILABLE = True
except ImportError:  # pragma: no cover - import guard
    LDAP3_AVAILABLE = False

import json
import logging
from datetime import datetime, timezone

from cryptography.x509 import (
    load_der_x509_certificate,
    load_pem_x509_certificate,
)
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from quirk.models import CryptoEndpoint
from quirk.util.weak_crypto import is_weak_cipher
from quirk.util.safe_exc import safe_str

# Module-level logger (mirror saml_scanner / kerberos_scanner pattern)
logger = logging.getLogger(__name__)

# Attributes queried — both forms per SMIME-01 (CONTEXT D-Area-1)
_SMIME_ATTRS = ("userCertificate", "userSMIMECertificate")


def _realm_to_base_dn(realm: str) -> str:
    """Convert a Kerberos realm (e.g. ``QUIRK.LAB``) to an LDAP base DN
    (``DC=quirk,DC=lab``). Empty input returns empty string.

    Mirrors CONTEXT D-Area-1 default for ``smime_search_base``.
    """
    if not realm:
        return ""
    parts = [p for p in realm.split(".") if p]
    if not parts:
        return ""
    return ",".join(f"DC={p.lower()}" for p in parts)


def _parse_smime_cert(cert_bytes: bytes) -> "dict | None":
    """Parse a certificate as DER first, fallback to PEM on failure
    (CONTEXT D-Area-2). Returns a dict with parsed fields or ``None``
    on parse failure.
    """
    cert = None
    try:
        cert = load_der_x509_certificate(cert_bytes)
    except Exception as exc_der:
        logger.debug("SMIME DER parse failed, attempting PEM: %s", safe_str(exc_der))
        try:
            cert = load_pem_x509_certificate(cert_bytes)
        except Exception as exc_pem:
            logger.debug("SMIME PEM parse also failed: %s", safe_str(exc_pem))
            return None

    pub = cert.public_key()
    if isinstance(pub, rsa.RSAPublicKey):
        key_alg = "RSA"
        key_bits = pub.key_size
    elif isinstance(pub, ec.EllipticCurvePublicKey):
        key_alg = "ECDSA"
        key_bits = pub.key_size
    else:
        key_alg = "UNKNOWN"
        key_bits = None

    try:
        sig_hash = cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else ""
    except Exception:
        sig_hash = ""

    not_after = cert.not_valid_after_utc
    expired = not_after < datetime.now(timezone.utc)

    return {
        "key_alg": key_alg,
        "key_bits": key_bits,
        "sig_hash": sig_hash,
        "serial": format(cert.serial_number, "x"),
        "not_after": not_after.isoformat(),
        "expired": expired,
    }


def _classify_severity(parsed: dict) -> "tuple[str | None, list[str]]":
    """Classify a parsed cert dict into (severity, reasons). Per CONTEXT
    D-Area-2: expired alone = MEDIUM; expired + weak = HIGH; weak-signing
    or weak-key = HIGH; SAFE returns (None, []).
    """
    reasons: list[str] = []
    if is_weak_cipher(parsed.get("sig_hash") or ""):
        reasons.append("weak-signing-alg")
    key_alg = (parsed.get("key_alg") or "").upper()
    key_bits = parsed.get("key_bits")
    if key_alg == "RSA" and isinstance(key_bits, int) and key_bits < 2048:
        reasons.append("weak-rsa-key")
    if parsed.get("expired"):
        reasons.append("expired")

    has_weak = any(r in reasons for r in ("weak-signing-alg", "weak-rsa-key"))
    if has_weak:
        return "HIGH", reasons
    if "expired" in reasons:
        return "MEDIUM", reasons
    return None, reasons


def _bind_and_search(host: str, port: int, base_dn: str, timeout: int):
    """Anonymous LDAP bind + paged search. Returns a generator of entry
    dicts or an empty list on failure. All ldap3 exceptions are caught
    at the caller; this helper raises so the caller can attach
    ``scan_error`` if needed.
    """
    server = ldap3.Server(host, port=port, get_info=ldap3.ALL, connect_timeout=timeout)
    conn = ldap3.Connection(
        server,
        authentication=ldap3.ANONYMOUS,
        receive_timeout=timeout,
    )
    if not conn.bind():
        logger.warning("SMIME: anonymous bind rejected on %s:%d", host, port)
        return []
    return conn.extend.standard.paged_search(
        search_base=base_dn,
        search_filter="(|(userCertificate=*)(userSMIMECertificate=*))",
        search_scope=ldap3.SUBTREE,
        attributes=["userCertificate", "userSMIMECertificate", "cn", "uid"],
        paged_size=500,
        generator=True,
    )


def _parse_target(target) -> "tuple[str, int, str | None]":
    """Normalize a target into (host, port, realm).

    Accepts:
      - ``ldap://host:port`` / ``ldaps://host:port`` URL strings
      - bare ``host`` / ``host:port`` strings
      - SimpleNamespace-style objects with attributes
        ``host``, optional ``port``, optional ``realm``.
    """
    realm = None
    if hasattr(target, "host"):
        host = getattr(target, "host")
        port = int(getattr(target, "port", 389) or 389)
        realm = getattr(target, "realm", None)
        return str(host), port, realm

    s = str(target).strip()
    if "://" in s:
        scheme, _, rest = s.partition("://")
        host_part = rest.split("/", 1)[0]
        default_port = 636 if scheme.lower() == "ldaps" else 389
    else:
        host_part = s
        default_port = 389
    if ":" in host_part:
        host, _, p = host_part.rpartition(":")
        try:
            port = int(p)
        except ValueError:
            port = default_port
    else:
        host = host_part
        port = default_port
    return host, port, realm


def scan_smime_targets(
    targets: list,
    timeout: int = 10,
    logger=None,
    session_start=None,
    *,
    search_base: "str | None" = None,
) -> list:
    """Scan LDAP targets for S/MIME signing certificates.

    For each target, anonymously bind and page through any entries
    containing ``userCertificate`` or ``userSMIMECertificate``. Each
    certificate value is parsed independently (multi-cert-per-user
    policy per CONTEXT D-Area-1). One ``CryptoEndpoint`` with
    ``protocol="SMIME"`` is emitted per *non-SAFE* certificate.

    Privacy invariant (SMIME-04): no IMAP / mailbox / envelope content
    is ever read or emitted.
    """
    log = logger or logging.getLogger(__name__)
    if not LDAP3_AVAILABLE:
        log.warning("ldap3 not installed — SMIME scanning disabled")
        return []

    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results: list = []

    for target in targets:
        host, port, realm = _parse_target(target)
        base_dn = search_base or _realm_to_base_dn(realm or "")
        if not base_dn:
            log.warning(
                "SMIME: no search base for target %s (no realm; pass --smime-base)",
                host,
            )
            continue

        try:
            entries = _bind_and_search(host, port, base_dn, timeout)
        except Exception as exc:
            log.warning("SMIME: bind/search failed for %s:%d: %s", host, port, safe_str(exc))
            err_ep = CryptoEndpoint(
                host=host,
                port=port,
                protocol="SMIME",
                service_detail=f"smime-unreachable|base={base_dn}",
                scan_error=safe_str(exc),
                scan_error_category="exception",
                scanned_at=now,
            )
            results.append(err_ep)
            continue

        for entry in entries:
            # Filter to searchResEntry only — paged_search may yield refs/controls
            if not isinstance(entry, dict):
                continue
            if entry.get("type") and entry.get("type") != "searchResEntry":
                continue
            raw = entry.get("raw_attributes") or {}
            user_dn = entry.get("dn") or ""

            for attr_name in _SMIME_ATTRS:
                cert_values = raw.get(attr_name) or []
                for cert_bytes in cert_values:
                    if not isinstance(cert_bytes, (bytes, bytearray)):
                        continue
                    parsed = _parse_smime_cert(bytes(cert_bytes))
                    if parsed is None:
                        log.warning(
                            "SMIME: cert parse failed for %s (%s)", user_dn, attr_name
                        )
                        continue

                    severity, reasons = _classify_severity(parsed)
                    if severity is None:
                        # SAFE — no finding emitted (CONTEXT D-Area-2)
                        continue

                    detail = (
                        f"{user_dn}|attr={attr_name}|serial={parsed['serial']}"
                    )
                    if parsed.get("expired"):
                        detail += "|expired=true"

                    scan_dict = dict(parsed)
                    scan_dict["reasons"] = reasons
                    scan_dict["attr"] = attr_name
                    scan_dict["user_dn"] = user_dn

                    ep = CryptoEndpoint(
                        host=host,
                        port=port,
                        protocol="SMIME",
                        cert_pubkey_alg=parsed["key_alg"],
                        cert_pubkey_size=parsed["key_bits"],
                        cert_sig_alg=parsed.get("sig_hash") or None,
                        service_detail=detail,
                        severity=severity,
                        smime_scan_json=json.dumps(scan_dict),
                        scanned_at=now,
                    )
                    results.append(ep)

    return results
