"""Code-signing certificate inventory via LDAP ``userCertificate`` (filtered
to the CodeSigning EKU) and in-process EKU check on already-captured TLS
endpoints. Read-only; no network I/O beyond LDAP bind. No impacket.

Phase 95 — CSIGN-01, CSIGN-02.

CSIGN-01: Discovers code-signing certificates from two passive sources:
  1. LDAP ``userCertificate`` attributes on configured targets, filtered
     to entries that carry the CodeSigning EKU (OID 1.3.6.1.5.5.7.3.3).
  2. Already-captured TLS ``CryptoEndpoint`` objects checked in-process
     for the CodeSigning EKU (reads ``tls_capabilities_json["eku_oids"]``);
     no new network fetch is performed.

CSIGN-02: Certificates with weak algorithms (RSA<2048, EC<256, SHA-1 sig
hash) are classified HIGH.

Protocol label: ``CODE_SIGNING`` (UPPERCASE; all downstream consumers —
CBOM builder, evidence, scoring, resume logic — key on exact string match).
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

from cryptography import x509
from cryptography.x509 import (
    load_der_x509_certificate,
    load_pem_x509_certificate,
    ExtendedKeyUsage,
)
from cryptography.x509.oid import ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from quirk.models import CryptoEndpoint
from quirk.util.weak_crypto import is_weak_cipher
from quirk.util.safe_exc import safe_str

# Module-level logger (mirror smime_scanner / adcs_scanner pattern)
logger = logging.getLogger(__name__)

# Protocol label — UPPERCASE.  ALL downstream consumers key on exact match.
CODE_SIGNING = "CODE_SIGNING"

# EKU OID for code signing: 1.3.6.1.5.5.7.3.3
EKU_CODE_SIGNING = ExtendedKeyUsageOID.CODE_SIGNING

# LDAP attribute — only the standard RFC 4523 attribute (NOT userSMIMECertificate)
_CODESIGN_ATTRS = ("userCertificate",)

# CodeSigning EKU OID as a dotted string (for tls_capabilities_json lookup)
_CODE_SIGNING_OID = EKU_CODE_SIGNING.dotted_string  # "1.3.6.1.5.5.7.3.3"


# ---------------------------------------------------------------------------
# EKU detection helper
# ---------------------------------------------------------------------------

def _has_codesigning_eku(cert_obj: "x509.Certificate") -> bool:
    """Return True if the certificate carries the CodeSigning EKU
    (OID 1.3.6.1.5.5.7.3.3). Returns False on missing extension or error.
    """
    try:
        eku_ext = cert_obj.extensions.get_extension_for_class(ExtendedKeyUsage)
        return EKU_CODE_SIGNING in eku_ext.value
    except x509.ExtensionNotFound:
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Certificate parsing
# ---------------------------------------------------------------------------

def _parse_codesign_cert(cert_bytes: bytes) -> "dict | None":
    """Parse a certificate as DER first, fallback to PEM on failure.

    Returns a dict with parsed fields or ``None`` on parse failure.
    Mirrors ``_parse_smime_cert()`` from smime_scanner.py.
    """
    cert = None
    try:
        cert = load_der_x509_certificate(cert_bytes)
    except Exception as exc_der:
        logger.debug("CODESIGN DER parse failed, attempting PEM: %s", safe_str(exc_der))
        try:
            cert = load_pem_x509_certificate(cert_bytes)
        except Exception as exc_pem:
            logger.debug("CODESIGN PEM parse also failed: %s", safe_str(exc_pem))
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

    # SHA-256 fingerprint for CBOM dedup — embedded in service_detail
    fingerprint = cert.fingerprint(hashes.SHA256()).hex()

    try:
        subject = cert.subject.rfc4514_string()
    except Exception:
        subject = ""

    return {
        "key_alg": key_alg,
        "key_bits": key_bits,
        "sig_hash": sig_hash,
        "serial": format(cert.serial_number, "x"),
        "subject": subject,
        "not_after": not_after.isoformat(),
        "not_after_dt": not_after,  # datetime for the cert_not_after ORM column (CR-01)
        "expired": expired,
        "fingerprint": fingerprint,
        "_cert_obj": cert,  # kept in-memory only; not serialised into JSON
    }


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

def _classify_codesign_severity(parsed: dict) -> "tuple[str | None, list[str]]":
    """Classify a parsed cert dict into (severity, reasons).

    HIGH for: SHA-1 sig hash (via is_weak_cipher), RSA<2048, EC<256.
    SAFE (None) when no weak indicators present.

    NOTE: EC<256 is handled inline (NOT via is_weak_cipher — adding an
    "ECDSA-256" token to _WEAK_CIPHER_TOKENS would incorrectly match
    "AES-256" via substring). This matches the pattern in adcs_scanner.py.
    """
    reasons: list[str] = []

    # SHA-1 and other weak sig hashes via centralised predicate
    if is_weak_cipher(parsed.get("sig_hash") or ""):
        reasons.append("weak-signing-alg")

    key_alg = (parsed.get("key_alg") or "").upper()
    key_bits = parsed.get("key_bits")

    # RSA key-size check (threshold: <2048 bits)
    if key_alg == "RSA" and isinstance(key_bits, int) and key_bits < 2048:
        reasons.append("weak-rsa-key")

    # EC key-size check (threshold: <256 bits) — inline, NOT via is_weak_cipher
    if key_alg == "ECDSA" and isinstance(key_bits, int) and key_bits < 256:
        reasons.append("weak-ec-key")

    if reasons:
        return "HIGH", reasons
    return None, reasons


# ---------------------------------------------------------------------------
# LDAP helpers (copied verbatim from smime_scanner.py)
# ---------------------------------------------------------------------------

def _realm_to_base_dn(realm: str) -> str:
    """Convert a Kerberos realm (e.g. ``QUIRK.LAB``) to an LDAP base DN
    (``DC=quirk,DC=lab``). Empty input returns empty string.
    """
    if not realm:
        return ""
    parts = [p for p in realm.split(".") if p]
    if not parts:
        return ""
    return ",".join(f"DC={p.lower()}" for p in parts)


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


def _bind_and_search_codesign(host: str, port: int, base_dn: str, timeout: int):
    """Anonymous LDAP bind + paged search for userCertificate entries.

    Search filter is the hardcoded literal ``(userCertificate=*)`` — no
    user-controlled DN or filter interpolation (T-95-01 / LDAP injection
    mitigation).

    Returns a generator of entry dicts or raises on bind/search failure
    (caller handles exceptions and emits an error CryptoEndpoint).

    paged_size=500 bounds entries per page (T-95-02 / DoS mitigation).
    """
    server = ldap3.Server(host, port=port, get_info=ldap3.ALL, connect_timeout=timeout)
    conn = ldap3.Connection(
        server,
        authentication=ldap3.ANONYMOUS,
        receive_timeout=timeout,
    )
    if not conn.bind():
        logger.warning("CODESIGN: anonymous bind rejected on %s:%d", host, port)
        return []
    return conn.extend.standard.paged_search(
        search_base=base_dn,
        search_filter="(userCertificate=*)",
        search_scope=ldap3.SUBTREE,
        attributes=list(_CODESIGN_ATTRS) + ["cn", "uid"],
        paged_size=500,
        generator=True,
    )


# ---------------------------------------------------------------------------
# Public scanner functions
# ---------------------------------------------------------------------------

def scan_codesign_from_ldap(
    targets: list,
    timeout: int = 10,
    logger=None,
    session_start=None,
    *,
    search_base: "str | None" = None,
) -> list:
    """Scan LDAP targets for code-signing certificates (CSIGN-01).

    For each target, anonymously bind and page through entries containing
    ``userCertificate``. Each certificate value is parsed independently
    and checked for the CodeSigning EKU. Entries without the EKU are
    silently skipped. One ``CryptoEndpoint`` with ``protocol="CODE_SIGNING"``
    is emitted per *non-SAFE* certificate (CSIGN-02: HIGH for weak algorithms).

    On bind/search failure, an error CryptoEndpoint with ``scan_error`` is
    appended and scanning continues to the next target.

    All logging of LDAP-derived strings and exceptions routes through
    ``safe_str()`` (T-95-03 / information-disclosure mitigation).
    """
    log = logger or logging.getLogger(__name__)
    if not LDAP3_AVAILABLE:
        log.warning("ldap3 not installed — CODESIGN scanning disabled")
        return []

    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results: list = []

    for target in targets:
        host, port, realm = _parse_target(target)
        base_dn = search_base or _realm_to_base_dn(realm or "")
        if not base_dn:
            log.warning(
                "CODESIGN: no search base for target %s (no realm; pass search_base=)",
                safe_str(host),
            )
            continue

        try:
            entries = _bind_and_search_codesign(host, port, base_dn, timeout)
        except Exception as exc:
            log.warning(
                "CODESIGN: bind/search failed for %s:%d: %s",
                safe_str(host),
                port,
                safe_str(exc),
            )
            err_ep = CryptoEndpoint(
                host=host,
                port=port,
                protocol=CODE_SIGNING,
                service_detail=f"codesign-unreachable|base={safe_str(base_dn)}",
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

            for attr_name in _CODESIGN_ATTRS:
                cert_values = raw.get(attr_name) or []
                for cert_bytes in cert_values:
                    if not isinstance(cert_bytes, (bytes, bytearray)):
                        continue

                    parsed = _parse_codesign_cert(bytes(cert_bytes))
                    if parsed is None:
                        log.warning(
                            "CODESIGN: cert parse failed for %s (%s)",
                            safe_str(user_dn),
                            attr_name,
                        )
                        continue

                    # CSIGN-01: filter — skip certs without CodeSigning EKU
                    cert_obj = parsed.pop("_cert_obj", None)
                    if cert_obj is None or not _has_codesigning_eku(cert_obj):
                        continue

                    # CSIGN-02: weak-algorithm classification
                    severity, reasons = _classify_codesign_severity(parsed)
                    if severity is None:
                        # SAFE cert — no finding emitted
                        continue

                    fp = parsed["fingerprint"]
                    detail = (
                        f"{safe_str(user_dn)}"
                        f"|attr={attr_name}"
                        f"|serial={parsed['serial']}"
                        f"|fingerprint={fp}"
                        f"|weak"
                    )

                    # Exclude non-JSON-serializable keys (cert object + datetime) from the blob.
                    _skip = {"fingerprint", "_cert_obj", "not_after_dt"}
                    scan_dict = {k: v for k, v in parsed.items() if k not in _skip}
                    scan_dict["fingerprint"] = fp
                    scan_dict["reasons"] = reasons
                    scan_dict["attr"] = attr_name
                    scan_dict["user_dn"] = safe_str(user_dn)

                    ep = CryptoEndpoint(
                        host=host,
                        port=port,
                        protocol=CODE_SIGNING,
                        cert_pubkey_alg=parsed["key_alg"],
                        cert_pubkey_size=parsed["key_bits"],
                        cert_sig_alg=parsed.get("sig_hash") or None,
                        # CR-01: populate the ORM columns the CBOM surrogate-key dedup reads.
                        cert_subject=parsed.get("subject") or None,
                        cert_not_after=parsed.get("not_after_dt"),
                        service_detail=detail,
                        severity=severity,
                        smime_scan_json=json.dumps(scan_dict),
                        scanned_at=now,
                    )
                    results.append(ep)

    return results


def scan_codesign_from_tls_endpoints(
    tls_endpoints: list,
    session_start=None,
    logger=None,
) -> list:
    """Check already-captured TLS endpoints in-process for the CodeSigning EKU.

    No new network I/O is performed (CSIGN-01 in-process path). Reads EKU OIDs
    from ``ep.tls_capabilities_json["eku_oids"]`` if present, else skips.

    When the CodeSigning EKU OID (1.3.6.1.5.5.7.3.3) is found, emits a
    CODE_SIGNING CryptoEndpoint. Since raw DER is not stored in TLS endpoints,
    the surrogate compound key (cert_subject + cert_pubkey_alg + cert_not_after)
    is embedded in service_detail instead of a SHA-256 fingerprint (RESEARCH
    OQ1 resolution — TLS path uses surrogate-key dedup).

    For weak-algorithm classification: uses cert_pubkey_alg/cert_pubkey_size and
    cert_sig_alg from the TLS CryptoEndpoint directly.
    """
    log = logger or logging.getLogger(__name__)
    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results: list = []

    for ep in tls_endpoints:
        # Read EKU OIDs from tls_capabilities_json
        eku_oids: list[str] = []
        try:
            caps_json = getattr(ep, "tls_capabilities_json", None)
            if caps_json:
                caps = json.loads(caps_json)
                eku_oids = caps.get("eku_oids") or []
        except Exception:
            pass

        if _CODE_SIGNING_OID not in eku_oids:
            continue

        # Perform severity classification on TLS endpoint metadata
        # Build a pseudo-parsed dict matching _classify_codesign_severity's interface
        pseudo_parsed = {
            "sig_hash": getattr(ep, "cert_sig_alg", None) or "",
            "key_alg": (getattr(ep, "cert_pubkey_alg", None) or "").upper(),
            "key_bits": getattr(ep, "cert_pubkey_size", None),
        }
        severity, reasons = _classify_codesign_severity(pseudo_parsed)

        # Build surrogate service_detail (no fingerprint available from TLS metadata)
        cert_subject = getattr(ep, "cert_subject", None) or ""
        key_alg = getattr(ep, "cert_pubkey_alg", None) or ""
        not_after = getattr(ep, "cert_not_after", None)
        not_after_str = not_after.isoformat() if not_after else "unknown"
        surrogate_key = f"{cert_subject}|{key_alg}|{not_after_str}"

        detail = f"tls-eku-check|{ep.host}:{ep.port}|surrogate={surrogate_key}"
        if severity == "HIGH":
            detail += "|weak"

        scan_dict = {
            **pseudo_parsed,
            "reasons": reasons,
            "source": "tls-eku-check",
            "host": ep.host,
            "port": ep.port,
        }

        code_ep = CryptoEndpoint(
            host=ep.host,
            port=ep.port,
            protocol=CODE_SIGNING,
            cert_pubkey_alg=getattr(ep, "cert_pubkey_alg", None),
            cert_pubkey_size=getattr(ep, "cert_pubkey_size", None),
            cert_sig_alg=getattr(ep, "cert_sig_alg", None),
            # CR-01: carry the subject + not_after ORM columns through so the CBOM
            # surrogate-key dedup (cert_subject, cert_pubkey_alg, cert_not_after) matches
            # the TLS-derived component built from this same endpoint (TLS wins, we annotate).
            cert_subject=getattr(ep, "cert_subject", None),
            cert_not_after=getattr(ep, "cert_not_after", None),
            service_detail=detail,
            severity=severity,
            smime_scan_json=json.dumps(scan_dict),
            scanned_at=now,
        )
        results.append(code_ep)

    return results
