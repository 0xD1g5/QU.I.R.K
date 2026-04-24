"""SAML/OIDC scanner module — fetches IdP metadata XML and OIDC discovery endpoints,
extracts signing/encryption certificates and algorithm declarations."""

try:
    import lxml.etree as ET
    import defusedxml.lxml as _defused_lxml_ET
    def _safe_ET_fromstring(xml_bytes):  # noqa: E306
        return _defused_lxml_ET.fromstring(xml_bytes)
    LXML_AVAILABLE = True
except ImportError:
    ET = None  # type: ignore[assignment]
    try:
        import defusedxml.ElementTree as _defused_stdlib_ET
        def _safe_ET_fromstring(xml_bytes):  # noqa: E306
            return _defused_stdlib_ET.fromstring(xml_bytes)
        LXML_AVAILABLE = True
    except ImportError:
        def _safe_ET_fromstring(xml_bytes):  # noqa: E306
            raise RuntimeError("defusedxml is not installed — SAML parsing unavailable")
        LXML_AVAILABLE = False

import base64
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from quirk.models import CryptoEndpoint

# SAML XML namespace map — all lxml XPath calls use explicit namespaces=SAML_NS (D-06)
SAML_NS = {
    "md":   "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds":   "http://www.w3.org/2000/09/xmldsig#",
    "alg":  "urn:oasis:names:tc:SAML:metadata:algsupport",
    "mdui": "urn:oasis:names:tc:SAML:metadata:ui",
}

# Substrings indicating SHA-1 algorithm URIs (D-05); checked case-insensitively
SHA1_INDICATORS = ("sha1", "sha-1")

# OIDC algorithm severity map per D-09
# None means informational only (no finding produced)
OIDC_ALG_SEVERITY = {
    "RS256": "HIGH", "RS384": "HIGH", "RS512": "HIGH",
    "PS256": "HIGH", "PS384": "HIGH", "PS512": "HIGH",
    "ES256": None,   "ES384": None,   "ES512": None,
    "HS256": None,   "HS384": None,   "HS512": None,
    "EdDSA": None,
}


def _fetch_metadata(url: str, timeout: int) -> "bytes | None":
    """Fetch raw content from a SAML metadata or OIDC discovery URL.

    Follows redirects and disables SSL verification for enterprise CAs (D-13, D-14).
    Returns raw bytes on success, None on any error.
    """
    try:
        import httpx
        response = httpx.get(url, timeout=timeout, follow_redirects=True, verify=False)
        if response.status_code == 200:
            return response.content
        logging.getLogger(__name__).warning(
            "SAML fetch %s returned HTTP %d", url, response.status_code
        )
        return None
    except Exception as exc:
        logging.getLogger(__name__).warning("SAML fetch failed for %s: %s", url, exc)
        return None


def _classify_target(url: str, content: bytes) -> str:
    """Determine whether a URL/content is a SAML metadata document or OIDC discovery doc.

    Returns "saml" or "oidc" (D-01).
    Checks URL path for '.well-known' first; falls back to content sniffing.
    """
    if ".well-known" in url:
        return "oidc"
    try:
        json.loads(content)
        return "oidc"
    except Exception:
        return "saml"


def _parse_cert_element(cert_b64_text: str) -> "dict | None":
    """Parse a base64-encoded DER X.509 certificate from a SAML KeyDescriptor.

    Decodes base64 DER, loads via cryptography.x509, extracts key_alg, key_bits,
    serial (hex), not_after (ISO string). Returns dict or None on parse error.
    Follows Research Pattern 3 — strips whitespace before decoding.
    """
    try:
        # Strip ALL whitespace per Pitfall 7
        cleaned = cert_b64_text.replace(" ", "").replace("\n", "").replace("\r", "").strip()
        der = base64.b64decode(cleaned)
        cert = load_der_x509_certificate(der)
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

        return {
            "key_alg": key_alg,
            "key_bits": key_bits,
            "serial": format(cert.serial_number, 'x'),
            "not_after": cert.not_valid_after_utc.isoformat(),
        }
    except Exception:
        return None


def _is_sha1_uri(uri: str) -> bool:
    """Return True if uri contains a SHA-1 algorithm indicator (D-05).

    Checks for 'sha1' or 'sha-1' (case-insensitive) anywhere in the URI string.
    """
    lower = uri.lower()
    return any(ind in lower for ind in SHA1_INDICATORS)


def _classify_key_severity(key_alg: str, key_bits: "int | None") -> "str | None":
    """Classify a public key's quantum-readiness severity per D-07.

    RSA key_bits < 2048  -> "CRITICAL"
    RSA key_bits == 2048 -> "HIGH"
    RSA key_bits > 2048  -> "HIGH" (still quantum-vulnerable)
    ECDSA / EdDSA        -> None (SAFE, no finding)
    Unknown alg          -> None

    Returns severity string or None (no finding).
    """
    alg_upper = key_alg.upper() if key_alg else ""
    if alg_upper == "RSA":
        if key_bits is None:
            return "HIGH"
        if key_bits < 2048:
            return "CRITICAL"
        return "HIGH"
    # ECDSA, EdDSA, EC — quantum-safe or out of scope for key-size findings
    return None


def _parse_saml_metadata(xml_bytes: bytes, target_url: str, now=None) -> "tuple[list, dict]":
    """Parse a SAML EntityDescriptor XML document.

    Returns (endpoints, scan_dict) where endpoints is a list of CryptoEndpoint objects
    and scan_dict is the D-17 JSON structure dict for saml_scan_json (D-02, D-05).
    Uses defusedxml.lxml.fromstring() for XXE-safe parsing.
    """
    root = _safe_ET_fromstring(xml_bytes)

    # Extract entityID — handle both EntityDescriptor root and EntitiesDescriptor wrapper
    entity_id = root.get("entityID", "")
    if not entity_id:
        ed = root.find("md:EntityDescriptor", namespaces=SAML_NS)
        if ed is not None:
            entity_id = ed.get("entityID", "")

    # Parse port from target_url
    parsed = urlparse(target_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    host = parsed.hostname or target_url

    scan_dict = {
        "url": target_url,
        "type": "saml",
        "entity_id": entity_id,
        "signing_certs": [],
        "encryption_certs": [],
        "sha1_uris": [],
        "errors": [],
    }
    endpoints = []
    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

    # ── Signing certs (SAML-01) ──────────────────────────────
    # Find explicit signing certs
    signing_elems = root.findall(
        ".//md:KeyDescriptor[@use='signing']/ds:KeyInfo/ds:X509Data/ds:X509Certificate",
        namespaces=SAML_NS,
    )
    # Also handle KeyDescriptor WITHOUT use attribute (default = both signing and encryption)
    # Note: lxml ElementPath does not support not(@use) predicate — filter in Python
    md_ns = SAML_NS["md"]
    for kd in root.findall(f".//{{{md_ns}}}KeyDescriptor"):
        if kd.get("use") is None:
            for cert_elem in kd.findall(
                "ds:KeyInfo/ds:X509Data/ds:X509Certificate", namespaces=SAML_NS
            ):
                signing_elems.append(cert_elem)

    for elem in signing_elems:
        if elem.text is None:
            continue
        cert_info = _parse_cert_element(elem.text)
        if cert_info is None:
            continue
        scan_dict["signing_certs"].append({
            "serial": cert_info["serial"],
            "key_alg": cert_info["key_alg"],
            "key_bits": cert_info["key_bits"],
            "not_after": cert_info["not_after"],
        })
        ep = CryptoEndpoint(
            host=host,
            port=port,
            protocol="SAML",
            cert_pubkey_alg=cert_info["key_alg"],
            cert_pubkey_size=cert_info["key_bits"],
            service_detail=f"{entity_id}|use=signing|serial={cert_info['serial']}",
            saml_scan_json=json.dumps(scan_dict),
            scanned_at=now,
        )
        endpoints.append(ep)

    # ── Encryption certs (SAML-02) ──────────────────────────
    encryption_elems = root.findall(
        ".//md:KeyDescriptor[@use='encryption']/ds:KeyInfo/ds:X509Data/ds:X509Certificate",
        namespaces=SAML_NS,
    )

    for elem in encryption_elems:
        if elem.text is None:
            continue
        cert_info = _parse_cert_element(elem.text)
        if cert_info is None:
            continue
        scan_dict["encryption_certs"].append({
            "serial": cert_info["serial"],
            "key_alg": cert_info["key_alg"],
            "key_bits": cert_info["key_bits"],
            "not_after": cert_info["not_after"],
        })
        ep = CryptoEndpoint(
            host=host,
            port=port,
            protocol="SAML",
            cert_pubkey_alg=cert_info["key_alg"],
            cert_pubkey_size=cert_info["key_bits"],
            service_detail=f"{entity_id}|use=encryption|serial={cert_info['serial']}",
            saml_scan_json=json.dumps(scan_dict),
            scanned_at=now,
        )
        endpoints.append(ep)

    # ── SHA-1 URI detection (D-05) ──────────────────────────
    # Check ds:SignatureMethod elements
    for elem in root.findall(".//ds:SignatureMethod", namespaces=SAML_NS):
        uri = elem.get("Algorithm", "")
        if uri and _is_sha1_uri(uri):
            scan_dict["sha1_uris"].append({"source": "SignatureMethod", "uri": uri})
            ep = CryptoEndpoint(
                host=host,
                port=port,
                protocol="SAML",
                cert_pubkey_alg="SHA1",
                cert_pubkey_size=None,
                service_detail=f"{entity_id}|algo_uri={uri}|source=SignatureMethod",
                saml_scan_json=json.dumps(scan_dict),
                scanned_at=now,
            )
            endpoints.append(ep)

    # Check alg:SigningMethod elements
    for elem in root.findall(".//alg:SigningMethod", namespaces=SAML_NS):
        uri = elem.get("Algorithm", "")
        if uri and _is_sha1_uri(uri):
            scan_dict["sha1_uris"].append({"source": "alg:SigningMethod", "uri": uri})
            ep = CryptoEndpoint(
                host=host,
                port=port,
                protocol="SAML",
                cert_pubkey_alg="SHA1",
                cert_pubkey_size=None,
                service_detail=f"{entity_id}|algo_uri={uri}|source=alg:SigningMethod",
                saml_scan_json=json.dumps(scan_dict),
                scanned_at=now,
            )
            endpoints.append(ep)

    # Update saml_scan_json on all endpoints with the final scan_dict
    final_json = json.dumps(scan_dict)
    for ep in endpoints:
        ep.saml_scan_json = final_json

    return endpoints, scan_dict


def _parse_oidc_discovery(json_bytes: bytes, target_url: str, now=None) -> "tuple[list, dict]":
    """Parse an OIDC discovery document (RFC 8414 / OpenID Connect Discovery).

    Enumerates id_token_signing_alg_values_supported and
    request_object_signing_alg_values_supported (if present).
    Returns (endpoints, scan_dict) per D-03 and D-17.
    """
    data = json.loads(json_bytes)
    issuer = data.get("issuer", target_url)

    parsed = urlparse(target_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    host = parsed.hostname or target_url

    id_token_algs = data.get("id_token_signing_alg_values_supported", [])
    request_algs = data.get("request_object_signing_alg_values_supported", [])

    scan_dict = {
        "url": target_url,
        "type": "oidc",
        "issuer": issuer,
        "id_token_signing_alg_values_supported": id_token_algs,
        "request_object_signing_alg_values_supported": request_algs,
        "errors": [],
    }
    endpoints = []
    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Enumerate id_token_signing_alg_values_supported per Pitfall 6
    for alg in id_token_algs:
        severity = OIDC_ALG_SEVERITY.get(alg)
        if severity is not None:
            ep = CryptoEndpoint(
                host=host,
                port=port,
                protocol="SAML",
                cert_pubkey_alg=alg,
                cert_pubkey_size=2048 if (alg.startswith("RS") or alg.startswith("PS")) else None,
                service_detail="oidc-discovery|id_token_signing_alg",
                saml_scan_json=json.dumps(scan_dict),
                scanned_at=now,
            )
            endpoints.append(ep)

    # Enumerate request_object_signing_alg_values_supported
    for alg in request_algs:
        severity = OIDC_ALG_SEVERITY.get(alg)
        if severity is not None:
            ep = CryptoEndpoint(
                host=host,
                port=port,
                protocol="SAML",
                cert_pubkey_alg=alg,
                cert_pubkey_size=2048 if (alg.startswith("RS") or alg.startswith("PS")) else None,
                service_detail="oidc-discovery|request_object_signing_alg",
                saml_scan_json=json.dumps(scan_dict),
                scanned_at=now,
            )
            endpoints.append(ep)

    # Update saml_scan_json on all endpoints with final scan_dict
    final_json = json.dumps(scan_dict)
    for ep in endpoints:
        ep.saml_scan_json = final_json

    return endpoints, scan_dict


def scan_saml_targets(targets: list, timeout: int = 10, logger=None, session_start=None) -> list:
    """Scan SAML IdP metadata and OIDC discovery endpoints.

    Returns list of CryptoEndpoint objects.
    Degrades gracefully if lxml is not installed (returns empty list).
    """
    if not LXML_AVAILABLE:
        if logger:
            logger.warning("lxml not installed — SAML scanning disabled")
        return []

    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    log = logger or logging.getLogger(__name__)
    all_endpoints = []

    for target_url in targets:
        content = _fetch_metadata(target_url, timeout)
        if content is None:
            log.warning("SAML: no content fetched from %s, skipping", target_url)
            continue

        target_type = _classify_target(target_url, content)

        if target_type == "oidc":
            try:
                endpoints, _scan_dict = _parse_oidc_discovery(content, target_url, now=now)
                all_endpoints.extend(endpoints)
            except Exception as exc:
                log.warning("SAML: OIDC parse failed for %s: %s", target_url, exc)
        else:
            try:
                endpoints, _scan_dict = _parse_saml_metadata(content, target_url, now=now)
                all_endpoints.extend(endpoints)
            except Exception as exc:
                log.warning("SAML: metadata parse failed for %s: %s", target_url, exc)

    return all_endpoints
