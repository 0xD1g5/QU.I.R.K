"""Kerberos scanner module -- sends unauthenticated AS-REQ to enumerate KDC encryption types."""

try:
    from impacket.krb5.asn1 import AS_REQ, KRB_ERROR, ETYPE_INFO2, ETYPE_INFO
    from impacket.krb5.asn1 import seq_set, seq_set_iter, MethodData
    from impacket.krb5.kerberosv5 import sendReceive, KerberosError
    from impacket.krb5 import constants
    from impacket.krb5.types import KerberosTime, Principal
    from pyasn1.codec.ber import encoder, decoder
    from pyasn1.error import PyAsn1Error
    IMPACKET_AVAILABLE = True
except ImportError:
    IMPACKET_AVAILABLE = False
    PyAsn1Error = Exception  # type: ignore[assignment,misc]  # fallback when impacket/pyasn1 absent

import ipaddress  # Phase 77 D-06 — closes scanners-protocol/IN-06
import json
import logging
import secrets
import socket
import struct
import sys
from datetime import datetime, timezone

from quirk.errors import format_error

from quirk.models import CryptoEndpoint

# Module-level logger
logger = logging.getLogger(__name__)

# KERBEROS etype severity map (D-08 through D-12)
# Maps etype int -> (name, severity)
# CRITICAL: DES-based etypes (RFC 6649 deprecated)
# HIGH:     RC4-HMAC (classical weak) and AES-128 (Grover reduces to ~64-bit)
# SAFE:     AES-256 etypes
KERBEROS_ETYPE_MAP: dict = {
    1:  ("des-cbc-crc",                "CRITICAL"),   # D-08: DES deprecated
    2:  ("des-cbc-md4",                "CRITICAL"),   # D-08: DES deprecated
    3:  ("des-cbc-md5",                "CRITICAL"),   # D-08: DES deprecated
    17: ("aes128-cts-hmac-sha1-96",    "HIGH"),       # D-11: Grover -> ~64-bit
    18: ("aes256-cts-hmac-sha1-96",    "SAFE"),       # D-10: quantum-safe
    20: ("aes256-cts-hmac-sha384-192", "SAFE"),       # D-10: RFC 8009
    23: ("rc4-hmac",                   "HIGH"),       # D-09: RC4 weak
}

# Advertise all known etypes in AS-REQ to maximize KDC response completeness (D-03)
ALL_ETYPES = [17, 18, 20, 23, 1, 3]


def _derive_realm(host: str) -> str:
    """Derive Kerberos realm from FQDN by uppercasing domain portion (per D-06).

    For IP addresses (IPv4 or IPv6), returns the address uppercased as-is.
    For single-label hostnames, returns uppercased hostname.
    For FQDNs with >= 2 labels, returns the last two labels uppercased.

    Phase 77 D-06 — closes scanners-protocol/IN-06: the previous
    ``parts.isdigit()`` quad-form heuristic mis-classified IPv6 literals
    like ``"::1"`` and any host whose label happened to be all-numeric.
    Replaced with the stdlib ``ipaddress.ip_address`` strict parser
    (RESEARCH Pattern 4).
    """
    stripped = host.strip()
    try:
        ipaddress.ip_address(stripped)
        return stripped.upper()
    except ValueError:
        pass
    parts = stripped.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:]).upper()
    return stripped.upper()


def _build_as_req(client_name, server_name, realm: str):
    """Build an unauthenticated AS-REQ advertising all known etypes.

    Returns an AS_REQ ASN.1 object ready for encoding and transmission.
    Per D-01, D-03: advertises ALL_ETYPES so the KDC returns its full support list.
    """
    as_req = AS_REQ()
    as_req['pvno'] = 5
    as_req['msg-type'] = int(constants.ApplicationTagNumbers.AS_REQ.value)

    req_body = as_req['req-body']
    req_body['kdc-options'] = constants.KDCOptions(
        constants.KDCOptions.forwardable
    )
    seq_set(req_body, 'sname', server_name.components_to_asn1)
    seq_set(req_body, 'cname', client_name.components_to_asn1)
    req_body['realm'] = realm
    req_body['till'] = KerberosTime.to_asn1(
        datetime(2037, 12, 31, 0, 0, tzinfo=timezone.utc)
    )
    # Cryptographic RNG per audit WR-09 (Phase 71) and CONTEXT D-09: full
    # 32-bit unsigned nonce per RFC 4120 §5.4.1. pyasn1 handles DER signed-int
    # encoding (leading-zero byte expansion when the high bit is set) on its
    # own — the caller does not need to mask.
    req_body['nonce'] = secrets.randbits(32)
    seq_set_iter(req_body, 'etype', ALL_ETYPES)
    return as_req


def _probe_kdc(host: str, realm: str, timeout: int) -> list:
    """Probe a KDC over TCP and parse etypes from PA-ETYPE-INFO2 in KDC_ERR_PREAUTH_REQUIRED.

    Returns list of etype integers advertised by the KDC.
    Returns [] if KDC returns AS-REP (no preauth required -- unexpected).
    Raises on non-preauth errors or connection failures.
    Per Pitfall 3: handles both PA_ETYPE_INFO2 (type 19) and PA_ETYPE_INFO (type 11).
    """
    client_name = Principal("nobody", type=constants.PrincipalNameType.NT_PRINCIPAL.value)
    server_name = Principal(
        f"krbtgt/{realm}", type=constants.PrincipalNameType.NT_SRV_INST.value
    )
    as_req = _build_as_req(client_name, server_name, realm)
    message = encoder.encode(as_req)

    try:
        _r = sendReceive(message, realm, host)
        return []  # Unexpected AS-REP without preauth
    except KerberosError as e:
        code = e.getErrorCode()
        if code != constants.ErrorCodes.KDC_ERR_PREAUTH_REQUIRED.value:
            raise
        error_pkt = e.getErrorPacket()
        method_data_raw = bytes(error_pkt['e-data'])
        method_data = decoder.decode(method_data_raw, asn1Spec=MethodData())[0]
        etypes = []
        for method in method_data:
            ptype = int(method['padata-type'])
            # Handle both PA_ETYPE_INFO2 (type 19) and PA_ETYPE_INFO (type 11)
            if ptype == int(constants.PreAuthenticationDataTypes.PA_ETYPE_INFO2.value):
                info2 = decoder.decode(
                    bytes(method['padata-value']),
                    asn1Spec=ETYPE_INFO2()
                )[0]
                for entry in info2:
                    etypes.append(int(entry['etype']))
            elif ptype == int(constants.PreAuthenticationDataTypes.PA_ETYPE_INFO.value):
                info1 = decoder.decode(
                    bytes(method['padata-value']),
                    asn1Spec=ETYPE_INFO()
                )[0]
                for entry in info1:
                    etypes.append(int(entry['etype']))
        return etypes


def _probe_kdc_udp(host: str, realm: str, timeout: int) -> list:
    """UDP fallback for KDC probing.

    Sends raw AS-REQ bytes (no length prefix) to port 88 via UDP.
    Returns list of etype integers advertised by the KDC via UDP transport.
    Returns empty list on any failure (errors are swallowed -- UDP is best-effort fallback).
    Per Pitfall 1: UDP does NOT use the 4-byte length prefix (only TCP does).
    """
    client_name = Principal("nobody", type=constants.PrincipalNameType.NT_PRINCIPAL.value)
    server_name = Principal(
        f"krbtgt/{realm}", type=constants.PrincipalNameType.NT_SRV_INST.value
    )
    as_req = _build_as_req(client_name, server_name, realm)
    message = encoder.encode(as_req)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(message, (host, 88))
        data, _ = sock.recvfrom(65535)
        # Try to decode as KRB_ERROR
        krb_error = decoder.decode(data, asn1Spec=KRB_ERROR())[0]
        error_code = int(krb_error['error-code'])
        if error_code != constants.ErrorCodes.KDC_ERR_PREAUTH_REQUIRED.value:
            return []
        method_data_raw = bytes(krb_error['e-data'])
        method_data = decoder.decode(method_data_raw, asn1Spec=MethodData())[0]
        etypes = []
        for method in method_data:
            ptype = int(method['padata-type'])
            if ptype == int(constants.PreAuthenticationDataTypes.PA_ETYPE_INFO2.value):
                info2 = decoder.decode(
                    bytes(method['padata-value']),
                    asn1Spec=ETYPE_INFO2()
                )[0]
                for entry in info2:
                    etypes.append(int(entry['etype']))
            elif ptype == int(constants.PreAuthenticationDataTypes.PA_ETYPE_INFO.value):
                info1 = decoder.decode(
                    bytes(method['padata-value']),
                    asn1Spec=ETYPE_INFO()
                )[0]
                for entry in info1:
                    etypes.append(int(entry['etype']))
        return etypes
    except (socket.timeout, socket.error, OSError) as e:
        # WR-08 (Phase 71): UDP transport failure — log+continue (best-effort fallback)
        logger.warning("KDC UDP probe transport failed for %r: %s", host, e)
        return []
    except (ValueError, TypeError, struct.error, IndexError, KeyError, PyAsn1Error) as e:
        # WR-08 (Phase 71): malformed KDC response — log+continue. Covers pyasn1
        # decode errors (PyAsn1Error) and any shape/type mismatches downstream.
        logger.warning("KDC UDP probe decode failed for %r: %s", host, e)
        return []
    finally:
        sock.close()


def _probe_ldap_anon(host: str, timeout: int, logger=None) -> dict:
    """Attempt anonymous LDAP bind on port 389 to read msDS-SupportedEncryptionTypes.

    Returns dict with 'ldap_status' key. Always succeeds (never raises).
    Per KERB-03: gracefully degrades if unreachable or auth required.
    """
    try:
        import ldap3
        server = ldap3.Server(host, port=389, connect_timeout=timeout)
        conn = ldap3.Connection(
            server, authentication=ldap3.ANONYMOUS, receive_timeout=timeout
        )
        if not conn.bind():
            return {
                "ldap_status": "anonymous-bind-rejected",
                "ldap_error": str(conn.last_error),
            }

        # Try to read defaultNamingContext
        conn.search('', '(objectClass=*)', attributes=['defaultNamingContext'])
        base_dn = ""
        if conn.entries:
            entry = conn.entries[0]
            if hasattr(entry, 'defaultNamingContext'):
                base_dn = str(entry.defaultNamingContext.value)

        if base_dn:
            conn.search(
                base_dn,
                '(objectClass=domain)',
                attributes=['msDS-SupportedEncryptionTypes'],
            )
            if conn.entries:
                enc_types_val = None
                if 'msDS-SupportedEncryptionTypes' in conn.entries[0]:
                    enc_types_val = conn.entries[0]['msDS-SupportedEncryptionTypes'].value
                return {
                    "ldap_status": "ok",
                    "msDS-SupportedEncryptionTypes": enc_types_val,
                }

        return {"ldap_status": "ok", "msDS-SupportedEncryptionTypes": None}
    except ImportError:
        if logger:
            logger.warning("ldap3 not available; skipping LDAP probe for %s", host)
        return {"ldap_status": "skipped", "ldap_error": "ldap3 not installed"}
    except Exception as exc:
        if logger:
            logger.warning(
                "Kerberos LDAP probe failed for %s: %s (skipped)", host, exc
            )
        return {"ldap_status": "skipped", "ldap_error": str(exc)}


def scan_kerberos_targets(targets: list, timeout: int = 10, logger=None, session_start=None) -> list:
    """Scan Kerberos KDCs for supported encryption types via unauthenticated AS-REQ probe.

    Entry point for the Kerberos scanner. Returns list[CryptoEndpoint] -- one endpoint
    per etype discovered per host.

    Degrades gracefully if impacket is not installed (returns empty list).
    """
    if not IMPACKET_AVAILABLE:
        print(format_error("INSTALL-001"), file=sys.stderr)
        if logger:
            logger.warning("impacket not installed -- Kerberos scanning disabled")
        return []

    now = (session_start or datetime.now(timezone.utc)).replace(tzinfo=None)
    results = []
    for target in targets:
        realm = _derive_realm(target)
        etypes = []
        tcp_error = None

        # TCP primary (per D-01, sendReceive uses TCP).
        # AUDIT-03: If the TCP probe raises (connection refused, timeout, or any
        # transport failure), control falls through to _probe_kdc_udp below.  This
        # silent TCP→UDP downgrade is intentional standard Kerberos behaviour per
        # RFC 4120 §7.2.1 ("Kerberos clients SHOULD support both UDP and TCP; a
        # client MAY retry over TCP/UDP on failure") — it is NOT a defect.
        try:
            etypes = _probe_kdc(target, realm, timeout)
        except Exception as exc:
            tcp_error = exc
            # UDP fallback on any TCP failure (RFC 4120 §7.2.1)
            try:
                etypes = _probe_kdc_udp(target, realm, timeout)
            except Exception:
                etypes = None  # Both paths failed

        # Graceful failure: both TCP and UDP failed
        if etypes is None:
            unreachable_ep = CryptoEndpoint(
                host=target,
                port=88,
                protocol="KERBEROS",
                cert_pubkey_alg="kerberos-unreachable",
                service_detail="kerberos-unreachable",
                scanned_at=now,
            )
            ldap_result = _probe_ldap_anon(target, timeout, logger)
            scan_json = json.dumps({
                "realm": realm,
                "etypes": [],
                "etype_details": [],
                "ldap": ldap_result,
                "ldap_status": ldap_result.get("ldap_status", "skipped"),
            })
            unreachable_ep.kerberos_scan_json = scan_json
            results.append(unreachable_ep)
            continue

        # Build per-etype CryptoEndpoints
        target_endpoints = []
        etype_details = []
        for etype in etypes:
            name, severity = KERBEROS_ETYPE_MAP.get(
                etype, (f"unknown-etype-{etype}", "MEDIUM")
            )
            etype_details.append({"etype": etype, "name": name, "severity": severity})
            ep = CryptoEndpoint(
                host=target,
                port=88,
                protocol="KERBEROS",
                cert_pubkey_alg=name,
                service_detail=f"etype:{etype}:{name}:{severity}",
                scanned_at=now,
            )
            target_endpoints.append(ep)

        # LDAP probe (KERB-03: always runs, never aborts scan on failure)
        ldap_result = _probe_ldap_anon(target, timeout, logger)

        # Build kerberos_scan_json and attach to the first endpoint for this target
        scan_json = json.dumps({
            "realm": realm,
            "etypes": etypes,
            "etype_details": etype_details,
            "ldap": ldap_result,
            "ldap_status": ldap_result.get("ldap_status", "skipped"),
        })

        if target_endpoints:
            target_endpoints[0].kerberos_scan_json = scan_json
        else:
            # No etypes discovered (AS-REP without preauth) -- create a placeholder
            placeholder = CryptoEndpoint(
                host=target,
                port=88,
                protocol="KERBEROS",
                cert_pubkey_alg=None,
                service_detail="kerberos-no-preauth",
                scanned_at=now,
            )
            placeholder.kerberos_scan_json = scan_json
            target_endpoints.append(placeholder)

        results.extend(target_endpoints)

    return results
