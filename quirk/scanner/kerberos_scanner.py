"""Kerberos scanner module -- sends unauthenticated AS-REQ to enumerate KDC encryption types."""

try:
    from impacket.krb5.asn1 import AS_REQ, KRB_ERROR, ETYPE_INFO2, ETYPE_INFO
    from impacket.krb5.asn1 import seq_set, seq_set_iter, MethodData
    from impacket.krb5.kerberosv5 import sendReceive, KerberosError
    from impacket.krb5 import constants
    from impacket.krb5.types import KerberosTime, Principal
    from pyasn1.codec.ber import encoder, decoder
    IMPACKET_AVAILABLE = True
except ImportError:
    IMPACKET_AVAILABLE = False

import json
import logging
import random
import socket
import struct
from datetime import datetime, timezone

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

    For IP addresses (all-numeric octets), returns the address uppercased as-is.
    For single-label hostnames, returns uppercased hostname.
    For FQDNs with >= 2 labels, returns the last two labels uppercased.
    """
    stripped = host.strip()
    parts = stripped.split(".")
    # Detect IPv4 address: all parts are numeric
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        return stripped.upper()
    if len(parts) >= 2:
        return ".".join(parts[-2:]).upper()
    return stripped.upper()


def _build_as_req(client_name, server_name, realm: str):
    """Build an unauthenticated AS-REQ advertising all known etypes.

    Returns an AS_REQ ASN.1 object ready for encoding and transmission.
    Raises NotImplementedError until Plan 02 implements this function.
    """
    raise NotImplementedError("stub")


def _probe_kdc(host: str, realm: str, timeout: int) -> list:
    """Probe a KDC over TCP and parse etypes from PA-ETYPE-INFO2 in KDC_ERR_PREAUTH_REQUIRED.

    Returns list of etype integers advertised by the KDC.
    Raises NotImplementedError until Plan 02 implements this function.
    """
    raise NotImplementedError("stub")


def _probe_kdc_udp(host: str, realm: str, timeout: int) -> list:
    """UDP fallback for KDC probing.

    Returns list of etype integers advertised by the KDC via UDP transport.
    Raises NotImplementedError until Plan 02 implements this function.
    """
    raise NotImplementedError("stub")


def _probe_ldap_anon(host: str, timeout: int, logger=None) -> dict:
    """Attempt anonymous LDAP bind on port 389 to read msDS-SupportedEncryptionTypes.

    Returns dict with ldap_status and optional enc_types fields.
    Raises NotImplementedError until Plan 02 implements this function.
    """
    raise NotImplementedError("stub")


def scan_kerberos_targets(targets: list, timeout: int = 10, logger=None) -> list:
    """Scan Kerberos KDCs for supported encryption types via unauthenticated AS-REQ probe.

    Entry point for the Kerberos scanner. Returns list[CryptoEndpoint] -- one endpoint
    per etype discovered per host.

    Degrades gracefully if impacket is not installed (returns empty list).
    """
    if not IMPACKET_AVAILABLE:
        if logger:
            logger.warning("impacket not installed -- Kerberos scanning disabled")
        return []
    raise NotImplementedError("stub")
