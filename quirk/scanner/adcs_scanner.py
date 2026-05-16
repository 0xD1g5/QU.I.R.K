"""Active Directory Certificate Services (AD CS) enumeration via
authenticated LDAP. This scanner performs read-only LDAP enumeration
of AD CS configuration. No certificate enrollment, no template
creation, no CSR generation, no write operations under any code path.
Enforced by tests/test_adcs_ast_gate.py (ADCS-09) and
tests/test_adcs_no_writes.py.

Phase 80 — ADCS-01 ... ADCS-08. Enumerates CA configurations under
CN=Public Key Services,CN=Services,CN=Configuration,<root-DN> and
certificate templates under CN=Certificate Templates,...; classifies
msPKI-* attributes for ESC1-ESC8 observable misconfigurations.
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

from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.primitives.asymmetric import rsa, ec

from quirk.models import CryptoEndpoint
from quirk.util.weak_crypto import is_weak_cipher
from quirk.util.safe_exc import safe_str

# Module-level logger (mirror smime_scanner / saml_scanner / kerberos_scanner pattern)
logger = logging.getLogger(__name__)

# ============================================================================
# ESC bitmask constants (RESEARCH Pattern 2 — verified against [MS-CRTD] §2.4.*)
# ============================================================================

# msPKI-Certificate-Name-Flag (DWORD)
CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT          = 0x00000001  # ESC1
CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT_ALT_NAME = 0x00010000  # ESC1 variant

# msPKI-Enrollment-Flag
CT_FLAG_NO_SECURITY_EXTENSION              = 0x00080000  # ESC2 / ESC9 territory
CT_FLAG_AUTO_ENROLLMENT                    = 0x00000020
CT_FLAG_PEND_ALL_REQUESTS                  = 0x00000002  # mitigating bit

# Application Policy / EKU OIDs
EKU_CLIENT_AUTH        = "1.3.6.1.5.5.7.3.2"
EKU_PKINIT_CLIENT_AUTH = "1.3.6.1.5.2.3.4"
EKU_SMART_CARD_LOGON   = "1.3.6.1.4.1.311.20.2.2"
EKU_CERT_REQUEST_AGENT = "1.3.6.1.4.1.311.20.2.1"
EKU_ANY_PURPOSE        = "2.5.29.37.0"
EKU_SUBORDINATE_CA     = "1.3.6.1.5.5.7.3.9"

# ESC classes that are not observable from LDAP attributes alone (D-80-R8)
_COVERAGE_GAP_ESCS = ("ESC4", "ESC5", "ESC7", "ESC8")


def _realm_to_base_dn(realm: str) -> str:
    """Convert a realm (``QUIRK.LAB``) to an LDAP base DN
    (``DC=quirk,DC=lab``). Empty input returns empty string. Mirrors
    ``smime_scanner._realm_to_base_dn``.
    """
    if not realm:
        return ""
    parts = [p for p in realm.split(".") if p]
    if not parts:
        return ""
    return ",".join(f"DC={p.lower()}" for p in parts)


def _parse_target(target) -> "tuple[str, int, str | None]":
    """Normalize a target into (host, port, realm). Mirrors
    ``smime_scanner._parse_target``.
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


def _parse_ca_cert(der_bytes: bytes) -> "dict | None":
    """Parse a ``cACertificate`` value (always DER per [MS-CRTD] §2.21).
    Returns ``{key_alg, key_bits, sig_hash, serial, not_after, expired}``
    or ``None`` on parse failure. No PEM fallback (RESEARCH Pattern 3).
    """
    try:
        cert = load_der_x509_certificate(der_bytes)
    except Exception as exc:
        logger.debug("ADCS CA cert parse failed: %s", safe_str(exc))
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


def _decode_attr_list(raw_value) -> list:
    """Decode an LDAP multi-valued attribute that may contain bytes,
    handling Pitfall 7 (bytes→str decode for OID list attrs).
    """
    if not raw_value:
        return []
    out = []
    for v in raw_value:
        if isinstance(v, (bytes, bytearray)):
            try:
                out.append(v.decode("utf-8"))
            except UnicodeDecodeError:
                out.append(v.decode("latin-1", errors="replace"))
        else:
            out.append(str(v))
    return out


def _scalar(raw_value, default=0):
    """Decode a single-valued attribute that may arrive as ``[b"1"]``
    or ``[1]`` or ``1`` or ``None``. Handles Pitfall 3 (``int(... or 0)``).
    """
    if raw_value is None:
        return default
    if isinstance(raw_value, list):
        if not raw_value:
            return default
        raw_value = raw_value[0]
    if isinstance(raw_value, (bytes, bytearray)):
        try:
            raw_value = raw_value.decode("utf-8")
        except UnicodeDecodeError:
            raw_value = raw_value.decode("latin-1", errors="replace")
    return raw_value


def _classify_template_escs(entry: dict) -> "list[tuple[str, str, list[str]]]":
    """Return list of (esc_id, severity, reasons) for one template entry.
    LDAP-observable subset only — emits ESC1/ESC2/ESC3/ESC6. The caller
    emits ADCS-COVERAGE-GAP for ESC4/ESC5/ESC7/ESC8 (D-80-R8).
    """
    findings: list = []
    try:
        name_flag = int(_scalar(entry.get("msPKI-Certificate-Name-Flag"), 0) or 0)
    except (TypeError, ValueError):
        name_flag = 0
    try:
        enroll_flag = int(_scalar(entry.get("msPKI-Enrollment-Flag"), 0) or 0)
    except (TypeError, ValueError):
        enroll_flag = 0
    try:
        ra_sig = int(_scalar(entry.get("msPKI-RA-Signature"), 0) or 0)
    except (TypeError, ValueError):
        ra_sig = 0

    app_policies = _decode_attr_list(entry.get("msPKI-Certificate-Application-Policy"))
    ekus = _decode_attr_list(entry.get("pKIExtendedKeyUsage"))

    pending = bool(enroll_flag & CT_FLAG_PEND_ALL_REQUESTS)
    client_auth_eku = any(
        o in ekus for o in (EKU_CLIENT_AUTH, EKU_PKINIT_CLIENT_AUTH, EKU_SMART_CARD_LOGON)
    )

    # ESC1: ENROLLEE_SUPPLIES_SUBJECT + client-auth EKU + no RA signature.
    if (name_flag & CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT) and client_auth_eku \
            and ra_sig == 0 and not pending:
        findings.append((
            "ESC1", "HIGH",
            ["enrollee-supplies-subject", "client-auth-eku", "no-ra-signature"],
        ))

    # ESC2: NO_SECURITY_EXTENSION enrollment bit OR any-purpose EKU.
    if (enroll_flag & CT_FLAG_NO_SECURITY_EXTENSION):
        findings.append(("ESC2", "HIGH", ["no-security-extension"]))
    elif EKU_ANY_PURPOSE in app_policies or EKU_ANY_PURPOSE in ekus:
        findings.append(("ESC2", "HIGH", ["any-purpose-eku"]))

    # ESC3: cert-request-agent EKU + missing manager approval (ra_sig == 0).
    if (EKU_CERT_REQUEST_AGENT in ekus or EKU_CERT_REQUEST_AGENT in app_policies) \
            and ra_sig == 0:
        findings.append(("ESC3", "HIGH",
                         ["cert-request-agent-eku", "no-manager-approval"]))

    # ESC6: subordinate-CA EKU (LDAP-observable partial signal for EDITF flag).
    if EKU_SUBORDINATE_CA in app_policies or EKU_SUBORDINATE_CA in ekus:
        findings.append(("ESC6", "HIGH", ["subordinate-ca-eku"]))

    return findings


def _bind_and_query(
    host: str,
    port: int,
    timeout: int,
    *,
    user: "str | None" = None,
    password: "str | None" = None,
):
    """SIMPLE-or-ANONYMOUS LDAP bind. Returns (Connection, config_base_dn).
    Raises ``ldap3.core.exceptions.LDAPBindError`` on bind failure so the
    caller converts to an ADCS-UNREACH coverage gap.
    """
    server = ldap3.Server(host, port=port, get_info=ldap3.ALL, connect_timeout=timeout)
    if user and password:
        conn = ldap3.Connection(
            server, user=user, password=password,
            authentication=ldap3.SIMPLE, receive_timeout=timeout,
        )
    else:
        conn = ldap3.Connection(
            server, authentication=ldap3.ANONYMOUS, receive_timeout=timeout,
        )
    if not conn.bind():
        raise ldap3.core.exceptions.LDAPBindError(
            conn.last_error or "bind-rejected"
        )
    config_base = None
    info = getattr(server, "info", None)
    if info is not None:
        other = getattr(info, "other", None) or {}
        nc = other.get("configurationNamingContext")
        if nc:
            config_base = nc[0] if isinstance(nc, (list, tuple)) else nc
    return conn, config_base


def scan_adcs_targets(
    targets: list,
    timeout: int = 10,
    logger=None,
    session_start=None,
    *,
    search_base: "str | None" = None,
    user: "str | None" = None,
    password: "str | None" = None,
) -> list:
    """Scan LDAP targets for AD CS configuration. For each target, SIMPLE
    bind (or anonymous fallback) and page through (a) CA enumeration under
    ``CN=Enrollment Services,CN=Public Key Services,...`` then (b) template
    enumeration under ``CN=Certificate Templates,CN=Public Key Services,...``.

    Emits ``CryptoEndpoint(protocol="ADCS")`` per finding:
    - Weak CA signing alg / weak RSA key → HIGH ``weak-signing-alg``.
    - ESC1/ESC2/ESC3/ESC6 template misconfigs → HIGH (per classifier).
    - ESC4/ESC5/ESC7/ESC8 → one LOW ``coverage-gap`` per ESC class per
      target (4 per target — D-80-R8).
    - Bind/search failure → one LOW ``adcs-unreachable`` per target
      (ADCS-04 SC#2 — never raises).
    """
    log = logger or logging.getLogger(__name__)
    if not LDAP3_AVAILABLE:
        log.warning("ldap3 not installed — ADCS scanning disabled")
        return []

    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results: list = []

    for target in targets:
        host, port, realm = _parse_target(target)
        base_dn = search_base or _realm_to_base_dn(realm or "")
        # Per-target user/password override (target object can carry them)
        t_user = getattr(target, "user", None) or user
        t_pass = getattr(target, "password", None) or password

        try:
            conn, config_base = _bind_and_query(
                host, port, timeout, user=t_user, password=t_pass,
            )
        except Exception as exc:
            log.warning("ADCS: bind failed for %s:%d: %s",
                        host, port, safe_str(exc))
            results.append(CryptoEndpoint(
                host=host,
                port=port,
                protocol="ADCS",
                service_detail=f"adcs-unreachable|base={base_dn}",
                severity="LOW",
                scan_error=safe_str(exc),
                scan_error_category="exception",
                scanned_at=now,
            ))
            continue

        if not config_base:
            config_base = f"CN=Configuration,{base_dn}" if base_dn else None
        if not config_base:
            log.warning("ADCS: no configurationNamingContext for %s (no realm; pass search_base)", host)
            results.append(CryptoEndpoint(
                host=host,
                port=port,
                protocol="ADCS",
                service_detail="adcs-unreachable|base=unknown",
                severity="LOW",
                scan_error="no-config-naming-context",
                scan_error_category="config",
                scanned_at=now,
            ))
            continue

        # ----- Phase A — CA enumeration -----
        ca_base = f"CN=Enrollment Services,CN=Public Key Services,CN=Services,{config_base}"
        try:
            ca_entries = conn.extend.standard.paged_search(
                search_base=ca_base,
                search_filter="(objectClass=pKIEnrollmentService)",
                search_scope=ldap3.SUBTREE,
                attributes=["cn", "cACertificate", "certificateTemplates", "dNSHostName"],
                paged_size=500,
                generator=True,
            )
            for entry in ca_entries:
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") and entry.get("type") != "searchResEntry":
                    continue
                raw = entry.get("raw_attributes") or {}
                cn = _scalar(raw.get("cn"), "") or "unknown"
                if isinstance(cn, (bytes, bytearray)):
                    cn = cn.decode("utf-8", errors="replace")
                ca_certs = raw.get("cACertificate") or []
                for cert_bytes in ca_certs:
                    if not isinstance(cert_bytes, (bytes, bytearray)):
                        continue
                    parsed = _parse_ca_cert(bytes(cert_bytes))
                    if parsed is None:
                        log.warning("ADCS: CA cert parse failed for cn=%s", cn)
                        continue
                    reasons = []
                    if is_weak_cipher(parsed.get("sig_hash") or ""):
                        reasons.append("weak-signing-alg")
                    key_alg = (parsed.get("key_alg") or "").upper()
                    key_bits = parsed.get("key_bits")
                    if key_alg == "RSA" and isinstance(key_bits, int) and key_bits < 2048:
                        reasons.append("weak-rsa-key")
                    if not reasons:
                        continue
                    scan_dict = dict(parsed)
                    scan_dict["reasons"] = reasons
                    scan_dict["ca_cn"] = cn
                    results.append(CryptoEndpoint(
                        host=host,
                        port=port,
                        protocol="ADCS",
                        cert_pubkey_alg=parsed["key_alg"],
                        cert_pubkey_size=parsed["key_bits"],
                        cert_sig_alg=parsed.get("sig_hash") or None,
                        service_detail=f"ca|cn={cn}|reason={reasons[0]}",
                        severity="HIGH",
                        adcs_scan_json=json.dumps(scan_dict),
                        scanned_at=now,
                    ))
        except Exception as exc:
            log.warning("ADCS: CA enumeration failed for %s:%d: %s",
                        host, port, safe_str(exc))
            results.append(CryptoEndpoint(
                host=host,
                port=port,
                protocol="ADCS",
                service_detail=f"adcs-unreachable|base={ca_base}",
                severity="LOW",
                scan_error=safe_str(exc),
                scan_error_category="exception",
                scanned_at=now,
            ))

        # ----- Phase B — Template enumeration -----
        tpl_base = f"CN=Certificate Templates,CN=Public Key Services,CN=Services,{config_base}"
        try:
            tpl_entries = conn.extend.standard.paged_search(
                search_base=tpl_base,
                search_filter="(objectClass=pKICertificateTemplate)",
                search_scope=ldap3.SUBTREE,
                attributes=[
                    "cn",
                    "msPKI-Certificate-Name-Flag",
                    "msPKI-Enrollment-Flag",
                    "msPKI-Certificate-Application-Policy",
                    "pKIExtendedKeyUsage",
                    "msPKI-RA-Signature",
                    "msPKI-Minimal-Key-Size",
                    "pKIKeyUsage",
                ],
                paged_size=500,
                generator=True,
            )
            for entry in tpl_entries:
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") and entry.get("type") != "searchResEntry":
                    continue
                raw = entry.get("raw_attributes") or {}
                cn = _scalar(raw.get("cn"), "") or "unknown"
                if isinstance(cn, (bytes, bytearray)):
                    cn = cn.decode("utf-8", errors="replace")
                esc_findings = _classify_template_escs(raw)
                for esc_id, severity, reasons in esc_findings:
                    primary = reasons[0] if reasons else esc_id.lower()
                    scan_dict = {
                        "template_cn": cn,
                        "esc": esc_id,
                        "reasons": reasons,
                    }
                    results.append(CryptoEndpoint(
                        host=host,
                        port=port,
                        protocol="ADCS",
                        service_detail=(
                            f"template|cn={cn}|{esc_id.lower()}-{primary}"
                        ),
                        severity=severity,
                        adcs_scan_json=json.dumps(scan_dict),
                        scanned_at=now,
                    ))
        except Exception as exc:
            log.warning("ADCS: template enumeration failed for %s:%d: %s",
                        host, port, safe_str(exc))
            results.append(CryptoEndpoint(
                host=host,
                port=port,
                protocol="ADCS",
                service_detail=f"adcs-unreachable|base={tpl_base}",
                severity="LOW",
                scan_error=safe_str(exc),
                scan_error_category="exception",
                scanned_at=now,
            ))

        # ----- Phase C — Coverage-gap emissions (D-80-R8) -----
        # One LOW finding per non-LDAP-observable ESC class per target.
        for esc_class in _COVERAGE_GAP_ESCS:
            results.append(CryptoEndpoint(
                host=host,
                port=port,
                protocol="ADCS",
                service_detail=(
                    f"coverage-gap|{esc_class}|reason=not-ldap-observable"
                ),
                severity="LOW",
                adcs_scan_json=json.dumps({
                    "esc": esc_class,
                    "reason": "not-ldap-observable",
                }),
                scanned_at=now,
            ))

        # Defensive unbind — never let cleanup raise.
        try:
            conn.unbind()
        except Exception:
            pass

    return results
