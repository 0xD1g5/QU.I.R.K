"""Kerberos scanner module -- sends unauthenticated AS-REQ to enumerate KDC encryption types."""

try:
    from impacket.krb5.asn1 import AS_REQ, AS_REP, KRB_ERROR, ETYPE_INFO2, ETYPE_INFO
    from impacket.krb5.asn1 import seq_set, seq_set_iter
    try:
        # impacket>=0.13.0 (current pin) renamed MethodData -> METHOD_DATA.
        # Phase 149-11 reconciliation: the un-guarded name broke the whole
        # try/except import block, silently disabling IMPACKET_AVAILABLE and
        # every Kerberos scan even with a correctly-pinned impacket installed.
        from impacket.krb5.asn1 import METHOD_DATA as MethodData
    except ImportError:
        from impacket.krb5.asn1 import MethodData  # impacket <0.13.0 fallback
    # 230-REVIEW-R2 CR-01: sendReceive is no longer called (it sets no socket
    # timeout and spins forever on a short read); QUIRK frames TCP itself.
    from impacket.krb5.kerberosv5 import KerberosError
    from impacket.krb5 import constants
    from impacket.krb5.types import KerberosTime, Principal
    from pyasn1.codec.ber import encoder, decoder
    from pyasn1.error import PyAsn1Error
    IMPACKET_AVAILABLE = True
except ImportError:
    IMPACKET_AVAILABLE = False
    PyAsn1Error = Exception  # type: ignore[assignment,misc]  # fallback when impacket/pyasn1 absent

    class KerberosError(Exception):  # type: ignore[no-redef]
        """Stand-in so ``except KerberosError`` resolves without impacket."""

        def __init__(self, error=0, packet=0):
            super().__init__()
            self.error = error
            self.packet = packet

import ipaddress  # Phase 77 D-06 — closes scanners-protocol/IN-06
import json
import logging
import secrets
import socket
import struct
import sys
import time
from datetime import datetime, timezone

from quirk.errors import format_error

from quirk.models import CryptoEndpoint
from quirk.util.safe_exc import safe_str  # IN-01: sanitize tcp_error onto unreachable endpoint

# Module-level logger
logger = logging.getLogger(__name__)

# Phase 230 D-24: client principal named in the probe AS-REQ.  "Administrator"
# exists by default on AD and Samba AD DC, so the KDC answers
# KDC_ERR_PREAUTH_REQUIRED (25) with PA-ETYPE-INFO2 instead of
# KDC_ERR_C_PRINCIPAL_UNKNOWN (6, no etype data).  An AS-REQ carrying no
# pre-auth data is not a failed logon and does not count toward lockout.
# Defined outside the impacket try-block so the module imports without
# impacket; config.py keeps its own literal (drift-guarded by a test).
DEFAULT_PROBE_PRINCIPAL = "Administrator"

# KDC port for both the TCP probe and the UDP fallback.  A module constant so
# the wire tests can point the real transport at a loopback peer.
KDC_PORT = 88

# 230-REVIEW-R2 CR-01: largest framed TCP reply the probe will read.  The
# probe's replies (KRB_ERROR with ETYPE-INFO2, or a bare AS-REP) are a few KiB;
# 64 KiB leaves wide headroom and matches the UDP probe's 65535-byte read.  A
# larger declared length (e.g. "HTTP" read as 1,213,486,160) is rejected on
# the prefix alone, without reading.
MAX_KDC_TCP_REPLY = 64 * 1024

# 230-REVIEW-R4 WR-01: the one TCP retry after a zero-byte drop shares the
# first attempt's reply deadline.  With less than this many seconds of it left,
# the retry is skipped and the probe goes straight to UDP: a retry that short
# could not complete a connect plus a KDC round trip on a real network.
MIN_TCP_RETRY_S = 0.25


class KerberosTransportError(Exception):
    """The framed TCP exchange with the KDC port failed (230-REVIEW-R2 CR-01).

    ``answered`` is True when the peer sent at least one reply byte (a short
    read, an implausible length prefix, or a stall mid-reply).  Something
    answered on the port but not as a KDC, so the caller must not treat it as a
    plain transport failure.  ``answered`` is False when no reply byte arrived
    (silent peer, or closed or reset before replying).

    ``kind`` says how it failed (230-REVIEW-R3 IN-01/IN-02): ``"eof"`` (peer
    closed), ``"reset"`` (connection reset or aborted), ``"error"`` (another
    socket error mid-read), ``"timeout"`` (deadline passed), ``"framing"``
    (implausible length prefix) or ``"send"`` (the request could not be sent).

    ``deadline`` is the ``time.monotonic()`` reply deadline of the attempt that
    failed, or None when unknown.  The one TCP retry may use only the time left
    before it (230-REVIEW-R4 WR-01).

    ``peer`` is the socket address the failed attempt was connected to (its
    ``getpeername()``), or None when unknown.  The one TCP retry connects to
    exactly that address and no other (230-REVIEW-R5 WR-01/WR-02).
    """

    def __init__(self, message: str, answered: bool, kind=None, deadline=None,
                 peer=None):
        super().__init__(message)
        self.answered = answered
        self.kind = kind
        self.deadline = deadline
        self.peer = peer


class KerberosPrincipalUnknown(Exception):
    """The KDC answered KDC_ERR_C_PRINCIPAL_UNKNOWN (6): reachable, but it
    returned no etype information for the probe principal (Phase 230 D-25)."""

    def __init__(self, principal: str, error_code: int = 6):
        super().__init__(
            f"KDC does not know principal {principal!r} (error {error_code})"
        )
        self.principal = principal
        self.error_code = error_code


class KerberosUnrecognisedReply(Exception):
    """The KDC port answered with bytes that decode as neither KRB_ERROR nor
    AS-REP (garbage, a truncated reply, or a non-Kerberos service).

    Only a reply that positively decodes as an AS-REP may be read as "no
    pre-auth required" (230-REVIEW WR-01); anything else takes the existing
    probe-failure path.
    """


class KerberosPreauthNoEtypes(Exception):
    """The KDC answered KDC_ERR_PREAUTH_REQUIRED (25) but its e-data is absent,
    undecodable, or carries no PA-ETYPE-INFO2/PA-ETYPE-INFO entry.

    A code-25 reply proves pre-auth IS required, so this must never be read as
    "no pre-auth" (230-REVIEW CR-02).  Raised instead of returning ``[]``,
    because ``[]`` means "AS-REP, no pre-auth required" to the caller.
    """

    def __init__(self, principal: str = "", error_code: int = 25):
        super().__init__(
            "KDC requires pre-auth (error 25) but advertised no parsable etype info"
        )
        self.principal = principal
        self.error_code = error_code

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
    # Phase 150 D-05: impacket 0.13.0 changed constants.KDCOptions from a
    # bit-flag helper class to a plain enum.Enum, so calling it as a
    # constructor (constants.KDCOptions(constants.KDCOptions.forwardable))
    # now raises pyasn1 KeyError('Bad BitString initializer type'). Detect
    # the new shape via constants.encodeFlags (impacket's own idiom for
    # turning KDCOption enum members into the bit-list a pyasn1 BitString
    # expects) and fall back to the legacy bit-flag constructor call when
    # encodeFlags is absent (impacket <0.13.0).
    if hasattr(constants, "encodeFlags"):
        req_body['kdc-options'] = constants.encodeFlags(
            [constants.KDCOptions.forwardable.value]
        )
    else:
        req_body['kdc-options'] = constants.KDCOptions(  # impacket <0.13.0 fallback
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


def _parse_preauth_etypes(error_pkt) -> list:
    """Parse etypes from the PA-ETYPE-INFO2 / PA-ETYPE-INFO e-data of a KRB_ERROR.

    One parser shared by the returned-reply and raised-error shapes of
    KDC_ERR_PREAUTH_REQUIRED, and the UDP probe (Phase 230 D-05/D-06).
    Per Pitfall 3: handles both PA_ETYPE_INFO2 (type 19) and PA_ETYPE_INFO (type 11).

    Never returns ``[]``: absent/undecodable e-data, or e-data with no
    ETYPE-INFO(2) entry, raises KerberosPreauthNoEtypes (230-REVIEW CR-02).
    """
    try:
        method_data_raw = bytes(error_pkt['e-data'])
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
    except Exception as exc:  # noqa: BLE001 - untrusted bytes (230-REVIEW-R3 WR-01)
        raise KerberosPreauthNoEtypes() from exc
    if not etypes:
        raise KerberosPreauthNoEtypes()
    return etypes


def _recv_exact(sock, n: int, deadline: float, received_before: int) -> bytes:
    """Read exactly ``n`` bytes before ``deadline`` or raise KerberosTransportError.

    An empty ``recv`` (peer closed) is an error, never a retry; that retry is
    the impacket ``sendReceive`` busy-loop this replaces (230-REVIEW-R2 CR-01).
    """
    buf = b""
    while len(buf) < n:
        remaining = deadline - time.monotonic()
        answered = (received_before + len(buf)) > 0
        if remaining <= 0:
            raise KerberosTransportError("KDC reply timed out", answered, "timeout")
        sock.settimeout(remaining)
        try:
            chunk = sock.recv(n - len(buf))
        except socket.timeout as exc:
            raise KerberosTransportError(
                "KDC reply timed out", answered, "timeout"
            ) from exc
        except OSError as exc:
            kind = ("reset" if isinstance(exc, (ConnectionResetError,
                                                ConnectionAbortedError))
                    else "error")
            # 230-REVIEW-R4 IN-05: "mid-reply" only if a reply byte arrived.
            where = "mid-reply" if answered else "before any reply byte"
            raise KerberosTransportError(
                f"KDC connection failed {where}: {exc}", answered, kind
            ) from exc
        if not chunk:
            raise KerberosTransportError(
                f"KDC closed the connection after {received_before + len(buf)} "
                f"of {received_before + n} reply bytes", answered, "eof",
            )
        buf += chunk
    return buf


def _kdc_tcp_exchange(host: str, port: int, message: bytes, timeout: float,
                      deadline=None, peer=None) -> bytes:
    """Send one length-prefixed Kerberos message over TCP; return the reply body.

    RFC 4120 §7.2.2 framing: a 4-byte big-endian length, then the message.
    ``timeout`` bounds the connect, and separately bounds the whole send plus
    reply (a deadline, so a peer dripping one byte at a time cannot stretch
    it).  Connect failures propagate as ``OSError``; failures after connect
    raise KerberosTransportError, which says whether the peer sent anything
    and carries the reply deadline and the connected peer address.

    The one retry (230-REVIEW-R4 WR-01, R5 WR-01/WR-02) passes ``deadline``
    (a ``time.monotonic()`` value) and ``peer`` (the address the failed
    attempt was connected to).  It connects to that single address only, so
    its connect timeout applies once, and its connect, send and reply must
    all finish before ``deadline``: the retry cannot extend the first
    attempt's budget.  ``host`` and ``port`` are then unused.
    """
    if deadline is None:
        sock = socket.create_connection((host, port), timeout=timeout)
        deadline = time.monotonic() + timeout
    else:
        if peer is None:
            raise OSError("no recorded KDC peer address to retry")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise socket.timeout("no time left before the Kerberos deadline to connect")
        # 230-REVIEW-R6 WR-01: connect to the FULL recorded sockaddr in its own
        # family. An IPv6 getpeername() is a 4-tuple whose host string has no
        # "%scope", so re-resolving peer[:2] would drop scope_id and could
        # never reach a link-local KDC.
        family = socket.AF_INET6 if len(peer) == 4 else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.settimeout(remaining)
            sock.connect(tuple(peer))
        except BaseException:
            sock.close()
            raise
    with sock:
        if peer is None:
            try:
                peer = sock.getpeername()
            except OSError:
                peer = None  # already reset; the retry is then skipped
        try:
            # 230-REVIEW-R5 IN-01: the send gets only what is left before the
            # deadline, not the timeout that was set before the connect.
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise KerberosTransportError(
                    "no time left before the Kerberos deadline to send", False,
                    "timeout",
                )
            sock.settimeout(remaining)
            try:
                sock.sendall(struct.pack("!I", len(message)) + message)
            except OSError as exc:
                raise KerberosTransportError(
                    f"KDC send failed: {exc}", False, "send"
                ) from exc
            (length,) = struct.unpack("!I", _recv_exact(sock, 4, deadline, 0))
            if length == 0 or length > MAX_KDC_TCP_REPLY:
                raise KerberosTransportError(
                    f"implausible KDC reply length {length} "
                    f"(limit {MAX_KDC_TCP_REPLY}); not a Kerberos TCP reply", True,
                    "framing",
                )
            return _recv_exact(sock, length, deadline, 4)
        except KerberosTransportError as exc:
            exc.deadline = deadline
            exc.peer = peer
            raise


def _fmt_peer(peer) -> str:
    """Render a recorded sockaddr for logs, keeping an IPv6 scope id
    (230-REVIEW-R7 IN-02): ``fe80::1%3`` rather than a bare ``fe80::1``."""
    if len(peer) == 4 and peer[3]:
        return f"{peer[0]}%{peer[3]}"
    return str(peer[0])


def _probe_kdc(host: str, realm: str, timeout: int, port=None,
               principal: str = DEFAULT_PROBE_PRINCIPAL, deadline=None,
               peer=None) -> list:
    """Probe a KDC over TCP and parse etypes from PA-ETYPE-INFO2 in KDC_ERR_PREAUTH_REQUIRED.

    Returns list of etype integers advertised by the KDC.
    Returns [] only if the reply decodes as an AS-REP whose crealm and cname
    match the probe (no preauth required); any other reply that is not a
    KRB_ERROR raises KerberosUnrecognisedReply.
    Raises KerberosPrincipalUnknown for KDC_ERR_C_PRINCIPAL_UNKNOWN (6),
    KerberosPreauthNoEtypes for a code-25 reply with no usable etype info,
    KerberosError for any other error code, KerberosTransportError for a failed
    or malformed exchange after connect, and OSError for a failed connect.

    The TCP exchange is QUIRK's own (230-REVIEW-R2 CR-01), with a timeout and an
    EOF check; impacket's ``sendReceive`` set neither.  Every reply, including
    KRB_ERROR 25, comes back as bytes and is decoded here (Phase 230 D-05).
    D-06's raise shape existed only because older impacket's ``sendReceive``
    raised KerberosError for code 25; with sendReceive gone, no impacket call
    on this path raises it, so that branch is retired.

    ``deadline`` and ``peer`` are passed to ``_kdc_tcp_exchange`` (the retry,
    230-REVIEW-R4 WR-01 and R5 WR-01/WR-02).
    """
    if port is None:
        port = KDC_PORT
    client_name = Principal(principal, type=constants.PrincipalNameType.NT_PRINCIPAL.value)
    server_name = Principal(
        f"krbtgt/{realm}", type=constants.PrincipalNameType.NT_SRV_INST.value
    )
    as_req = _build_as_req(client_name, server_name, realm)
    message = encoder.encode(as_req)

    preauth_required = constants.ErrorCodes.KDC_ERR_PREAUTH_REQUIRED.value
    principal_unknown = constants.ErrorCodes.KDC_ERR_C_PRINCIPAL_UNKNOWN.value
    r = _kdc_tcp_exchange(host, port, message, timeout, deadline=deadline,
                          peer=peer)

    # 230-REVIEW-R3 WR-01: ``r`` is untrusted bytes.  ANY exception while
    # decoding it (pyasn1 raises IndexError, not only PyAsn1Error, on some
    # malformed indefinite-length input) means "not a KRB_ERROR"; the exception
    # types are deliberately not enumerated.
    try:
        err = decoder.decode(r, asn1Spec=KRB_ERROR())[0]
        code = int(err['error-code'])
    except Exception:  # noqa: BLE001 - untrusted bytes
        # Not a KRB_ERROR.  Conclude "no pre-auth required" only if the reply
        # positively decodes as an AS-REP (230-REVIEW WR-01); garbage, a
        # truncated reply or a non-Kerberos service raises instead.
        try:
            rep = decoder.decode(r, asn1Spec=AS_REP())[0]
            rep_realm = str(rep['crealm'])
            rep_cname = [str(c) for c in rep['cname']['name-string']]
        except Exception as exc:  # noqa: BLE001 - untrusted bytes
            raise KerberosUnrecognisedReply(
                "KDC reply decodes as neither KRB_ERROR nor AS-REP"
            ) from exc
        # 230-REVIEW-R2 IN-04: only an AS-REP that answers THIS probe proves
        # "no pre-auth required".  Case-insensitive on both: realms are
        # conventionally upper-case, and AD matches principal names without
        # regard to case.
        expected_cname = [str(c) for c in client_name.components]
        if (rep_realm.upper() != realm.upper()
                or [c.lower() for c in rep_cname] != [c.lower() for c in expected_cname]):
            raise KerberosUnrecognisedReply(
                "AS-REP does not answer the probe (realm or principal mismatch)"
            )
        return []
    if code == preauth_required:
        return _parse_preauth_etypes(err)
    if code == principal_unknown:
        raise KerberosPrincipalUnknown(principal, code)
    raise KerberosError(packet=err)


def _is_retryable_tcp_drop(exc) -> bool:
    """True for a TCP probe the peer dropped before sending any reply byte.

    230-REVIEW-R3 IN-01 retry rule: retry the TCP probe exactly once, and only
    for KerberosTransportError(answered=False) whose kind is ``"eof"`` (closed
    with zero bytes) or ``"reset"`` (reset with zero bytes); the live Samba lab
    drops about half of TCP connections this way.  Connect refused, connect
    timeout, a silent peer's reply timeout, a send failure and any other
    socket error are NOT retried.

    A drop is NOT always fast: a peer can stay silent for most of the deadline
    and then close (230-REVIEW-R4 WR-01).  So the retry is given only the time
    left before the first attempt's reply deadline (its connect, send and
    reply must all finish by then), and is skipped when less than
    ``MIN_TCP_RETRY_S`` remains.  It connects only to the address the first
    attempt reached (230-REVIEW-R5 WR-01/WR-02), and is skipped when that
    address is unknown.  Retrying therefore never makes the TCP leg longer
    than one attempt's connect-plus-reply budget.  This predicate only
    classifies the failure; the caller checks the time left and the peer.
    """
    return (isinstance(exc, KerberosTransportError) and not exc.answered
            and exc.kind in ("eof", "reset"))


def _probe_kdc_udp(host: str, realm: str, timeout: int,
                   principal: str = DEFAULT_PROBE_PRINCIPAL, port=None) -> list:
    """UDP fallback for KDC probing.

    Sends raw AS-REQ bytes (no length prefix) to port 88 via UDP.
    Returns list of etype integers advertised by the KDC via UDP transport.
    Returns empty list on any failure (errors are swallowed -- UDP is best-effort fallback),
    except a code-25 reply with no usable etype info, which raises
    KerberosPreauthNoEtypes (230-REVIEW CR-02) so it is never read as no-preauth.
    Per Pitfall 1: UDP does NOT use the 4-byte length prefix (only TCP does).
    Bounded by ``sock.settimeout(timeout)``: one ``sendto`` and one ``recvfrom``.
    """
    if port is None:
        port = KDC_PORT
    client_name = Principal(principal, type=constants.PrincipalNameType.NT_PRINCIPAL.value)
    server_name = Principal(
        f"krbtgt/{realm}", type=constants.PrincipalNameType.NT_SRV_INST.value
    )
    as_req = _build_as_req(client_name, server_name, realm)
    message = encoder.encode(as_req)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(message, (host, port))
        data, _ = sock.recvfrom(65535)
        # Try to decode as KRB_ERROR
        krb_error = decoder.decode(data, asn1Spec=KRB_ERROR())[0]
        error_code = int(krb_error['error-code'])
        if error_code != constants.ErrorCodes.KDC_ERR_PREAUTH_REQUIRED.value:
            return []
        return _parse_preauth_etypes(krb_error)
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


def _preauth_no_etypes_row(target: str, realm: str, timeout: int, logger,
                           principal: str, now) -> CryptoEndpoint:
    """Build the honest row for a code-25 reply that named no etypes (CR-02)."""
    row = CryptoEndpoint(
        host=target,
        port=88,
        protocol="KERBEROS",
        cert_pubkey_alg=None,
        service_detail="kerberos-etypes-unavailable-preauth-no-etype-info",
        scanned_at=now,
    )
    ldap_result = _probe_ldap_anon(target, timeout, logger)
    row.kerberos_scan_json = json.dumps({
        "realm": realm,
        "etypes": [],
        "etype_details": [],
        "ldap": ldap_result,
        "ldap_status": ldap_result.get("ldap_status", "skipped"),
        "probe_principal": principal,
        "etypes_unavailable_reason": (
            "KDC_ERR_PREAUTH_REQUIRED (25) with no ETYPE-INFO/ETYPE-INFO2 e-data"
        ),
    })
    return row


def _unrecognised_reply_reason(exc) -> str:
    """Name the actual cause on the honest row (230-REVIEW-R3 IN-02).

    A reply cut off or stalled partway through is not proof that the peer
    "is not a KDC", so it is not described as one.  Carries no reply bytes,
    principal or secret; the exception text stays in ``scan_error``.
    """
    if isinstance(exc, KerberosUnrecognisedReply):
        return ("port 88 sent a complete reply that does not parse as a "
                "Kerberos KRB_ERROR or AS-REP for this probe")
    if isinstance(exc, KerberosTransportError):
        if exc.kind == "timeout":
            return ("port 88 started a TCP reply but did not finish it before "
                    "the Kerberos timeout")
        if exc.kind == "framing":
            return ("port 88 replied with a length prefix that is not Kerberos "
                    "TCP framing")
        return ("port 88 started a TCP reply, then the connection closed or "
                "failed partway through it (truncated reply)")
    return "the TCP probe failed with an unexpected error; etypes not assessed"


def _unrecognised_reply_row(target: str, realm: str, timeout: int, logger,
                            principal: str, now, exc) -> CryptoEndpoint:
    """Honest row for a port-88 peer that answered, but not as a KDC.

    230-REVIEW-R2 WR-01: the reply decoded as neither KRB_ERROR nor AS-REP, or
    broke the TCP framing after sending bytes.  Something answered, so this is
    not a transport failure: no UDP fallback (whose ``[]`` reads as "no
    pre-auth", D-08a), never ``kerberos-no-preauth``.  Carries the error, so it
    is visibly a failed assessment rather than a clean result.
    """
    row = CryptoEndpoint(
        host=target,
        port=88,
        protocol="KERBEROS",
        cert_pubkey_alg=None,
        service_detail="kerberos-etypes-unavailable-unrecognised-reply",
        scanned_at=now,
        scan_error=safe_str(exc),
        scan_error_category="exception",
    )
    ldap_result = _probe_ldap_anon(target, timeout, logger)
    row.kerberos_scan_json = json.dumps({
        "realm": realm,
        "etypes": [],
        "etype_details": [],
        "ldap": ldap_result,
        "ldap_status": ldap_result.get("ldap_status", "skipped"),
        "probe_principal": principal,
        "etypes_unavailable_reason": _unrecognised_reply_reason(exc),
    })
    return row


def scan_kerberos_targets(targets: list, timeout: int = 10, logger=None, session_start=None,
                          principal: str = DEFAULT_PROBE_PRINCIPAL) -> list:
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

        # TCP primary (per D-01; QUIRK-framed TCP since 230-REVIEW-R2 CR-01).
        # AUDIT-03: If the TCP probe raises (connection refused, timeout, or any
        # transport failure), control falls through to _probe_kdc_udp below.  This
        # silent TCP→UDP downgrade is intentional standard Kerberos behaviour per
        # RFC 4120 §7.2.1 ("Kerberos clients SHOULD support both UDP and TCP; a
        # client MAY retry over TCP/UDP on failure") — it is NOT a defect.
        try:
            try:
                etypes = _probe_kdc(target, realm, timeout, principal=principal)
            except KerberosTransportError as exc:
                if not _is_retryable_tcp_drop(exc):
                    raise
                # 230-REVIEW-R3 IN-01: one TCP retry after a zero-byte drop,
                # inside the first attempt's deadline (230-REVIEW-R4 WR-01),
                # to the one address that answered (230-REVIEW-R5 WR-01/WR-02).
                left = (exc.deadline - time.monotonic()
                        if exc.deadline is not None else 0.0)
                if exc.peer is None:
                    if logger:
                        logger.info("Kerberos TCP probe to %s dropped (%s) and "
                                    "the peer address is unknown; not retrying",
                                    target, exc)
                    raise
                if left < MIN_TCP_RETRY_S:
                    if logger:
                        logger.info("Kerberos TCP probe to %s dropped (%s) with "
                                    "%.2fs of its deadline left; not retrying",
                                    target, exc, max(left, 0.0))
                    raise
                if logger:
                    logger.info("Kerberos TCP probe to %s dropped (%s); retrying "
                                "once to %s within the remaining %.2fs",
                                target, exc, _fmt_peer(exc.peer), left)
                etypes = _probe_kdc(target, realm, timeout, principal=principal,
                                    deadline=exc.deadline, peer=exc.peer)
        except KerberosPreauthNoEtypes:
            # 230-REVIEW CR-02: code 25 proves pre-auth IS required, but the
            # KDC named no etypes.  Honest gap row like D-25: no UDP fallback,
            # no scan_error, no finding, never "kerberos-no-preauth".
            results.append(_preauth_no_etypes_row(target, realm, timeout, logger,
                                                  principal, now))
            continue
        except KerberosPrincipalUnknown:
            # Phase 230 D-25: the KDC answered (code 6) but returns no etype data
            # for this principal.  An assessment gap, not a transport failure:
            # no UDP fallback, no scan_error, and never "kerberos-no-preauth".
            gap_ep = CryptoEndpoint(
                host=target,
                port=88,
                protocol="KERBEROS",
                cert_pubkey_alg=None,
                service_detail="kerberos-etypes-unavailable-principal-unknown",
                scanned_at=now,
            )
            ldap_result = _probe_ldap_anon(target, timeout, logger)
            gap_ep.kerberos_scan_json = json.dumps({
                "realm": realm,
                "etypes": [],
                "etype_details": [],
                "ldap": ldap_result,
                "ldap_status": ldap_result.get("ldap_status", "skipped"),
                "probe_principal": principal,
                "etypes_unavailable_reason": "KDC_ERR_C_PRINCIPAL_UNKNOWN (6)",
            })
            results.append(gap_ep)
            continue
        except KerberosUnrecognisedReply as exc:
            # 230-REVIEW-R2 WR-01: the peer answered with non-Kerberos bytes.
            # A positive answer, not a transport failure: no UDP fallback.
            results.append(_unrecognised_reply_row(target, realm, timeout, logger,
                                                   principal, now, exc))
            continue
        except (OSError, KerberosError, KerberosTransportError) as exc:
            if isinstance(exc, KerberosTransportError) and exc.answered:
                # WR-01: bytes arrived but broke the framing (short read,
                # implausible length prefix such as unframed HTTP, a stall or
                # reset mid-reply).  Same honest row, no UDP fallback.
                results.append(_unrecognised_reply_row(target, realm, timeout,
                                                       logger, principal, now, exc))
                continue
            tcp_error = exc
            # 230-REVIEW-R3 WR-01: UDP fallback ONLY for these three: OSError
            # (connect refused, timed out or unreachable, the name does not
            # resolve, or the retry's connect failed or ran out of time),
            # KerberosTransportError with no reply byte (kind "timeout":
            # silent peer, including a retry that ran out of the remaining
            # deadline; "send"; "error": any other socket error before the
            # first reply byte; "eof"/"reset": a zero-byte close/reset after
            # the one retry, or with too little time left or no known peer
            # address to retry), and
            # KerberosError for KRB_ERROR codes other than 25/6.  The guide
            # and the lab oracle list exactly this set (230-REVIEW-R4 WR-02)
            # (RFC 4120 §7.2.1; the known D-08a path, todo
            # 261023-detect-kerberos-udp-failure-reads-as-no-preauth).
            try:
                etypes = _probe_kdc_udp(target, realm, timeout, principal=principal)
            except KerberosPreauthNoEtypes:
                results.append(_preauth_no_etypes_row(target, realm, timeout, logger,
                                                      principal, now))
                continue
            except Exception:
                etypes = None  # Both paths failed
        except Exception as exc:  # noqa: BLE001 - see below
            # 230-REVIEW-R3 WR-01: anything else the TCP probe raises is not a
            # transport failure.  UDP's [] would read as "no pre-auth" (D-08a),
            # so this gets the honest row instead.
            results.append(_unrecognised_reply_row(target, realm, timeout, logger,
                                                   principal, now, exc))
            continue

        # Graceful failure: both TCP and UDP failed
        if etypes is None:
            unreachable_ep = CryptoEndpoint(
                host=target,
                port=88,
                protocol="KERBEROS",
                cert_pubkey_alg="kerberos-unreachable",
                service_detail="kerberos-unreachable",
                scanned_at=now,
                # IN-01: thread the TCP failure into the endpoint for operator
                # diagnostics instead of leaving tcp_error as dead state.
                scan_error=safe_str(tcp_error) if tcp_error is not None else None,
                scan_error_category="exception" if tcp_error is not None else None,
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
