"""SAML/OIDC scanner module — fetches IdP metadata XML and OIDC discovery endpoints,
extracts signing/encryption certificates and algorithm declarations."""

import lxml.etree as ET
from quirk.util.xml_safe import make_safe_parser


def _safe_ET_fromstring(xml_bytes):
    # Phase 52 DEBT-04 / Phase 87 DEP-02: hardened lxml parser via xml_safe chokepoint.
    # resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False,
    # huge_tree=False — all five flags active via make_safe_parser().
    # lxml>=6.0 is a mandatory core dep; missing lxml fails loudly (no silent downgrade).
    return ET.fromstring(xml_bytes, parser=make_safe_parser())


LXML_AVAILABLE = True

import base64
import json
import logging
from typing import Optional

# Module-level logger (Phase 71 WR-10)
logger = logging.getLogger(__name__)

# Phase 71 / WR-10 / D-10: maximum JSON payload accepted by _classify_target.
# 1 MiB is generous for OIDC discovery docs (typical < 10 KiB) and bounds memory
# exposure from a malicious endpoint serving multi-GB JSON.
MAX_SAML_JSON_BYTES = 1_048_576
from datetime import datetime, timezone
from urllib.parse import urlparse
from cryptography.x509 import load_der_x509_certificate
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from quirk.models import CryptoEndpoint
from quirk.scanner.target_outcome import (
    OUTCOME_ANSWERED,
    OUTCOME_UNEXPECTED_RESPONSE,
    OUTCOME_UNREACHABLE,
    TargetOutcomeContractError,
    outcome_for_url_guard,
)
from quirk.util.safe_exc import safe_str
from quirk.util.outbound_fetch import OutboundFetchRejected, fetch_validated
from quirk.util.url_allowlist import _redact_url_preview, validate_external_url
from quirk.assessment.migration_advisor import _matches  # Phase 77 D-03 — word-boundary SHA1 detection

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

# SAML XML namespace map — all lxml XPath calls use explicit namespaces=SAML_NS (D-06)
SAML_NS = {
    "md":   "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds":   "http://www.w3.org/2000/09/xmldsig#",
    "alg":  "urn:oasis:names:tc:SAML:metadata:algsupport",
    "mdui": "urn:oasis:names:tc:SAML:metadata:ui",
}

# Substrings indicating SHA-1 algorithm URIs (D-05); checked case-insensitively
SHA1_INDICATORS = ("sha1", "sha-1")

# Phase 57 / D-09: HIGH advisory service_detail when allow_internal_targets is set.
ADVISORY_SAML_INTERNAL_TARGET = "SAML/internal-target-fetched"

# OIDC algorithm severity map per D-09
# None means informational only (no finding produced)
OIDC_ALG_SEVERITY = {
    "RS256": "HIGH", "RS384": "HIGH", "RS512": "HIGH",
    "PS256": "HIGH", "PS384": "HIGH", "PS512": "HIGH",
    "ES256": None,   "ES384": None,   "ES512": None,
    "HS256": None,   "HS384": None,   "HS512": None,
    "EdDSA": None,
}


def _fetch_metadata(
    url: str,
    timeout: int,
    *,
    allow_internal: bool = False,
    outcomes=None,
) -> "bytes | None":
    """Fetch raw content from a SAML metadata or OIDC discovery URL.

    Phase 57 / CR-04: SSRF-guarded metadata fetch. Calls validate_external_url
    before issuing any outbound HTTP request. Blocked URLs return None with zero
    outbound requests.

    Follows redirects one hop at a time, validating each hop. Uses system CA bundle (verify=True) so a network-positioned
    attacker cannot serve a forged metadata document via a fake TLS connection.
    Returns raw bytes on success, None on any error.

    235.3 D-05: when ``outcomes`` is given, the per-target outcome is recorded
    against ``url`` (guard refusal -> outcome_for_url_guard; other exception
    -> unreachable). Phase 238 D-07: a non-200 records unexpected_response
    with ``HTTP <status>``; a 200 records nothing here, because the caller
    decides from the document whether the target answered.
    """
    try:
        response = fetch_validated(
            url,
            fetch=lambda u, h: httpx.get(
                u, timeout=timeout, follow_redirects=False, verify=True, headers=h
            ),
            allow_internal=allow_internal,
        )
        if response.status_code == 200:
            return response.content
        if outcomes is not None:
            outcomes.record(
                url, OUTCOME_UNEXPECTED_RESPONSE, f"HTTP {response.status_code}"
            )
        logging.getLogger(__name__).warning(
            "SAML fetch %s returned HTTP %d", _redact_url_preview(url), response.status_code
        )
        return None
    except OutboundFetchRejected as exc:
        logging.getLogger(__name__).warning(
            "SAML: blocked fetch to %r (%s)", exc.preview, exc.reason
        )
        if outcomes is not None:
            outcomes.record(url, *outcome_for_url_guard(exc.reason))
        return None
    except TargetOutcomeContractError:
        raise
    except Exception as exc:
        if outcomes is not None:
            outcomes.record(url, OUTCOME_UNREACHABLE, safe_str(exc))
        logging.getLogger(__name__).warning(
            "SAML fetch failed for %r (%s)", _redact_url_preview(url), type(exc).__name__
        )
        return None


_UTF8_BOM = b"\xef\xbb\xbf"


def _strip_bom(content):
    """Drop a leading UTF-8 byte-order mark (common in ADFS metadata) so the
    JSON/XML sniff sees the document's first real character (WR-05)."""
    if isinstance(content, (bytes, bytearray)) and bytes(content[:3]) == _UTF8_BOM:
        return bytes(content[3:])
    if isinstance(content, str) and content.startswith("\ufeff"):
        return content[1:]
    return content


def _looks_like_xml(content) -> bool:
    if isinstance(content, str):
        return content.lstrip().startswith("<")
    if isinstance(content, (bytes, bytearray)):
        return bytes(content).lstrip().startswith(b"<")
    return False


def _classify_target(url: str, content: bytes) -> str:
    """Determine whether a URL/content is a SAML metadata document or OIDC discovery doc.

    Returns "saml", "oidc", or "unknown" (D-01).
    Checks URL path for '.well-known' first; falls back to content sniffing.
    Binary or non-XML content returns "unknown" so the caller can log a distinct warning.
    """
    if ".well-known" in url:
        return "oidc"
    # Phase 71 WR-10 (D-10): cap JSON payload size BEFORE json.loads to bound
    # memory exposure from a malicious endpoint. Oversized payloads log WARNING
    # and fall through to the XML sniff / "unknown" fallback (same shape as a
    # JSONDecodeError would yield).
    if isinstance(content, (bytes, bytearray)):
        payload_len = len(content)
    elif content is None:
        payload_len = 0
    else:
        payload_len = len(content.encode("utf-8"))
    if payload_len > MAX_SAML_JSON_BYTES:
        logger.warning(
            "SAML _classify_target payload from %r is %d bytes; exceeds "
            "MAX_SAML_JSON_BYTES (%d) — skipping JSON parse",
            url, payload_len, MAX_SAML_JSON_BYTES,
        )
    else:
        try:
            json.loads(content)
            return "oidc"
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError, TypeError) as e:
            # WR-10 (Phase 71): narrowed from bare except; log at debug level
            # because JSON-vs-XML sniffing routinely fails for legitimate SAML XML.
            logger.debug("SAML _classify_target JSON parse failed for %r: %s", url, e)
    stripped = content.lstrip()
    if stripped.startswith(b"<") or stripped.startswith(b"<?xml"):
        return "saml"
    return "unknown"


# Phase 238 D-07: root elements that make a document SAML 2.0 metadata.
_SAML_METADATA_ROOTS = frozenset({"EntityDescriptor", "EntitiesDescriptor"})
# Phase 238 D-07: an attacker-chosen root name is cut to this length in details.
_ROOT_NAME_MAX = 40


def _saml_root_detail(content) -> Optional[str]:
    """Return None when *content* is SAML 2.0 metadata, else the outcome detail.

    Phase 238 D-07: the root must be EntityDescriptor or EntitiesDescriptor in
    the SAML 2.0 metadata namespace. Parsing goes through the hardened parser.
    """
    head = bytes(content).lstrip()[:32].lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        return "not SAML metadata (HTML page)"
    try:
        root = _safe_ET_fromstring(content)
        qname = ET.QName(root)
    except Exception:
        return "unparseable XML"
    localname = qname.localname or ""
    if localname.lower() == "html":
        return "not SAML metadata (HTML page)"
    if localname in _SAML_METADATA_ROOTS and qname.namespace == SAML_NS["md"]:
        return None
    return f"not SAML metadata (root element {localname[:_ROOT_NAME_MAX]})"


def _oidc_discovery_detail(content) -> Optional[str]:
    """Return None when *content* is an OIDC discovery document, else the detail.

    Phase 238 D-07: a JSON object with ``issuer`` plus ``jwks_uri`` or a
    ``*_signing_alg_values_supported`` key.
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError, UnicodeDecodeError, TypeError):
        return "not an OIDC discovery document"
    if (
        isinstance(data, dict)
        and data.get("issuer")
        and (
            data.get("jwks_uri")
            or any(
                isinstance(k, str) and k.endswith("_signing_alg_values_supported")
                for k in data
            )
        )
    ):
        return None
    return "not an OIDC discovery document"


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

    Phase 77 D-03 — closes scanners-protocol/IN-03: replaces the previous
    substring scan (which mis-matched ``SHA1024`` as a SHA-1 indicator) with
    the Phase 74 ``_matches`` word-boundary helper. The helper consults
    ``CANONICAL_ALG_SYNONYMS["SHA1"]`` which covers both ``SHA1`` and
    ``SHA-1`` variants.
    """
    return _matches("SHA1", uri)


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
    Uses _safe_ET_fromstring() (lxml.etree with resolve_entities=False) for XXE-safe parsing.
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
            severity=_classify_key_severity(cert_info["key_alg"], cert_info["key_bits"]),
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
            severity=_classify_key_severity(cert_info["key_alg"], cert_info["key_bits"]),
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
                severity=severity,
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
                severity=severity,
                saml_scan_json=json.dumps(scan_dict),
                scanned_at=now,
            )
            endpoints.append(ep)

    # Update saml_scan_json on all endpoints with final scan_dict
    final_json = json.dumps(scan_dict)
    for ep in endpoints:
        ep.saml_scan_json = final_json

    return endpoints, scan_dict


def scan_saml_targets(
    targets: list,
    timeout: int = 10,
    logger=None,
    session_start=None,
    *,
    allow_internal_targets: bool = False,
    outcomes=None,
) -> list:
    """Scan SAML IdP metadata and OIDC discovery endpoints.

    Phase 57 / CR-04: supports allow_internal_targets kwarg. When True, fetches to
    RFC1918/loopback/link-local IPs proceed and emit a HIGH advisory CryptoEndpoint
    per affected target. Metadata-service IPs (169.254.169.254, fd00:ec2::254) are
    always blocked regardless of allow_internal_targets.

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
        content = _fetch_metadata(
            target_url, timeout, allow_internal=allow_internal_targets, outcomes=outcomes
        )
        if content is None:
            log.warning("SAML: no content fetched from %s, skipping", target_url)
            continue

        # Phase 57 / CR-04: if allow_internal_targets is set and the target was an
        # internal (non-metadata) IP, emit a HIGH advisory so the consulting deliverable
        # surfaces exactly which internal hosts were probed.
        if allow_internal_targets:
            strict = validate_external_url(target_url, allow_internal=False)
            if not strict.ok and strict.reason in {"internal_ip", "loopback", "link_local"}:
                all_endpoints.append(CryptoEndpoint(
                    host=target_url,
                    port=443,
                    protocol="ADVISORY",
                    service_detail=ADVISORY_SAML_INTERNAL_TARGET,
                    severity="HIGH",
                    scan_error_category="config",
                    scanned_at=datetime.now(timezone.utc).replace(tzinfo=None),
                ))

        content = _strip_bom(content)
        target_type = _classify_target(target_url, content)

        # Phase 238 D-07: the target is answered only when its document
        # qualifies; anything else records unexpected_response with a detail.
        if target_type == "oidc":
            detail = _oidc_discovery_detail(content)
            # WR-05: content decides before the URL. A .well-known URL that
            # serves SAML 2.0 metadata is SAML, not a failed OIDC document.
            if detail is not None and _looks_like_xml(content):
                if _saml_root_detail(content) is None:
                    target_type, detail = "saml", None
        elif target_type == "saml":
            detail = _saml_root_detail(content)
        else:
            detail = "not JSON or XML"
        if detail is not None:
            if outcomes is not None:
                outcomes.record(target_url, OUTCOME_UNEXPECTED_RESPONSE, detail)
            log.warning("SAML: %s at %s, skipping", detail, target_url)
            continue
        if outcomes is not None:
            outcomes.record(target_url, OUTCOME_ANSWERED)

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
