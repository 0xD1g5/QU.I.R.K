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
    from impacket.krb5.types import KerberosException, KerberosTime, Principal
    from pyasn1.codec.ber import encoder, decoder
    from pyasn1.error import PyAsn1Error
    IMPACKET_AVAILABLE = True
except ImportError:
    IMPACKET_AVAILABLE = False

    # 230-REVIEW-R11 IN-02: sentinels that nothing raises, never ``Exception``,
    # so an ``except (PyAsn1Error, KerberosException)`` stays narrow without
    # impacket, the configuration CI runs.
    class PyAsn1Error(Exception):  # type: ignore[no-redef]
        """Stand-in so ``except PyAsn1Error`` resolves without pyasn1."""

    class KerberosException(Exception):  # type: ignore[no-redef]
        """Stand-in so ``except KerberosException`` resolves without impacket."""

    class KerberosError(Exception):  # type: ignore[no-redef]
        """Stand-in so ``except KerberosError`` resolves without impacket."""

        def __init__(self, error=0, packet=0):
            super().__init__()
            self.error = error
            self.packet = packet

import ipaddress  # Phase 77 D-06 — closes scanners-protocol/IN-06
import unicodedata
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


class KerberosRequestBuildError(Exception):
    """The AS-REQ for this target could not be encoded, so nothing was sent.

    230-REVIEW-R10 WR-02/WR-03: deliberately NOT an OSError.  An OSError reads
    as "no KDC answered" and triggers the UDP fallback and the LDAP probe; a
    request that cannot be built would fail the same way on UDP, and no network
    leg ran, so the target is reported as not probed.
    """


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
    # 230-REVIEW-R10 WR-05 / R11 IN-05: a trailing dot marks an absolute name,
    # and goes before the IP-literal check so "10.0.0.1." is an IP literal.
    stripped = _normalise_target(host)
    try:
        ipaddress.ip_address(stripped)
        return stripped.upper()
    except ValueError:
        pass
    # 230-REVIEW-R9 WR-01: RFC 4120 §5.2.1 KerberosString should hold IA5
    # characters only, so an internationalised name's realm is its IDNA
    # A-label; the U-label could not be encoded into the AS-REQ.
    try:
        stripped = stripped.encode("idna").decode("ascii")
    except UnicodeError:
        # Keep the name.  scan_kerberos_targets never gets here: such a
        # target is rejected by _invalid_target_reason (R11 IN-03).
        pass
    parts = stripped.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:]).upper()
    return stripped.upper()


# 230-REVIEW-R12 IN-01: IDNA treats these as label separators like ".".
_IDNA_DOTS = str.maketrans({"\u3002": ".", "\uff0e": ".", "\uff61": "."})


def _normalise_target(target: str) -> str:
    """The name that is validated, probed and reported: surrounding whitespace
    and a trailing dot removed (230-REVIEW-R10 WR-01/WR-05, R11 IN-05), with
    IDNA's other full stops read as dots (R12 IN-01)."""
    # 230-REVIEW-R13 WR-01/WR-02: NFKC first, as IDNA does, so full-width
    # look-alikes (":" "/" "[" and dot leaders) are checked as what they become.
    return unicodedata.normalize("NFKC", target).strip().translate(_IDNA_DOTS).rstrip(".")


def _invalid_target_reason(target):
    """Why ``target`` is not a usable KDC host name, or None if it is.

    230-REVIEW-R9 WR-02/WR-03/IN-03: a non-str target used to abort the whole
    Kerberos loop; a NUL truncates the name inside ``getaddrinfo``, so a
    different host would be probed under this target's name; and "" resolves
    to the local host.  None of these is probed.
    """
    if not isinstance(target, str):
        return f"KDC target is not a host name string ({type(target).__name__})"
    stripped = _normalise_target(target)
    if not stripped:
        return "KDC target is empty"
    if "\x00" in stripped:
        return "KDC target contains a NUL character"
    # 230-REVIEW-R11 CR-01/IN-04: a lone surrogate (YAML can load one) breaks
    # the AS-REQ build and the SQLite insert; control characters are never
    # part of a host name.
    if any(unicodedata.category(c) in ("Cc", "Cs") for c in stripped):
        return "KDC target contains a control or surrogate character"
    if any(c.isspace() for c in stripped):
        return "KDC target contains whitespace"
    try:
        ipaddress.ip_address(stripped)
        return None
    except ValueError:
        pass
    # 230-REVIEW-R12 WR-05: the KDC port is always 88, so a host:port,
    # bracketed or path-like target names no host that resolves.
    if any(c in stripped for c in ":[]/"):
        return "KDC target must be a bare host name or IP address (the port is always 88)"
    # 230-REVIEW-R11 IN-03: a name IDNA cannot encode can neither resolve nor
    # yield an ASCII realm, so it is rejected here, before any probe.
    try:
        stripped.encode("idna")
    except UnicodeError as exc:
        return f"KDC target is not a valid host name ({exc})"
    return None


def _build_request(principal: str, realm: str):
    """``(client_name, encoded AS-REQ)`` for one probe (230-REVIEW-R9 WR-01).

    230-REVIEW-R11 CR-01: every build step is covered, not only the encode.
    ``Principal()`` raises KerberosException for a principal impacket rejects
    (config accepts any non-blank string), and the realm can fail inside
    ``_build_as_req``.  Only those library failures are caught (R10 WR-03); a
    programming error still surfaces.  The message names the exception class
    only: pyasn1's text is a dump of the whole request, about 32 KB (R10 WR-02).
    """
    try:
        client_name = Principal(
            principal, type=constants.PrincipalNameType.NT_PRINCIPAL.value)
        server_name = Principal(
            f"krbtgt/{realm}", type=constants.PrincipalNameType.NT_SRV_INST.value
        )
        return client_name, encoder.encode(
            _build_as_req(client_name, server_name, realm))
    except (PyAsn1Error, UnicodeError, KerberosException) as exc:
        raise KerberosRequestBuildError(
            f"cannot build AS-REQ for principal {principal[:80]!r} in realm "
            f"{realm[:80]!r}: {type(exc).__name__}"
        ) from exc


def _resolve_udp(host: str, port: int):
    """``(family, sockaddr)`` for the UDP probe; an A record is preferred over
    an AAAA record, as the AF_INET-only probe did (230-08 D-30).

    Raises OSError for a name that does not resolve or cannot be IDNA-encoded
    (230-REVIEW-R8 WR-03).  Split out so it is testable without impacket
    (230-REVIEW-R9 IN-01).
    """
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_DGRAM)
    except UnicodeError as exc:
        raise OSError(f"KDC host name cannot be encoded: {exc}") from exc
    if not infos:
        raise OSError(f"no UDP address for {host!r}")
    # Stable sort: IPv4 records first.
    infos = sorted(infos, key=lambda i: i[0] != socket.AF_INET)
    return infos[0][0], infos[0][4]


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
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
        except UnicodeError as exc:
            # 230-REVIEW-R8 WR-03: a name IDNA cannot encode never resolved;
            # that is a connect failure, not a reply that failed to decode.
            raise OSError(f"KDC host name cannot be encoded: {exc}") from exc
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
    client_name, message = _build_request(principal, realm)

    r = _kdc_tcp_exchange(host, port, message, timeout, deadline=deadline,
                          peer=peer)
    return _classify_kdc_reply(r, realm, client_name, principal)


def _classify_kdc_reply(reply: bytes, realm: str, client_name, principal: str) -> list:
    """Classify one KDC reply; the single rule set for the TCP and UDP legs.

    230-08 D-29: ``_probe_kdc`` (TCP) and ``_probe_kdc_udp`` both hand the
    reply bytes here, so no transport can read a reply differently.

    Returns the etype list of a KDC_ERR_PREAUTH_REQUIRED (25) reply.  Returns
    ``[]`` ONLY when the reply decodes as an AS-REP whose crealm and cname
    match the probe (no pre-auth required): ``[]`` is the one value the caller
    turns into ``kerberos-no-preauth``.  Raises KerberosUnrecognisedReply for
    anything else that is not a KRB_ERROR (garbage, an empty datagram, a
    mismatched AS-REP), KerberosPreauthNoEtypes for a code-25 reply with no
    usable etype info, KerberosPrincipalUnknown for code 6, and KerberosError
    for any other KRB_ERROR code.
    """
    preauth_required = constants.ErrorCodes.KDC_ERR_PREAUTH_REQUIRED.value
    principal_unknown = constants.ErrorCodes.KDC_ERR_C_PRINCIPAL_UNKNOWN.value
    r = reply

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
    """UDP fallback for KDC probing; follows the same rule as the TCP probe.

    Sends the raw AS-REQ (no length prefix, per Pitfall 1: only TCP frames) to
    the KDC port and hands the one reply to ``_classify_kdc_reply``, the same
    classifier ``_probe_kdc`` uses (230-08 D-29).  Returns the etype list of a
    code-25 reply, or ``[]`` only for an AS-REP that answers the probe.

    Every other outcome raises, because a swallowed UDP failure used to come
    back as ``[]``, which the caller reads as "no pre-auth": a timeout, a
    refusal, a send failure or a name that does not resolve (or cannot be
    IDNA-encoded) raises OSError;
    an empty datagram, garbage or a mismatched AS-REP raises
    KerberosUnrecognisedReply; code 6 raises KerberosPrincipalUnknown; code 25
    without etypes raises KerberosPreauthNoEtypes; any other KRB_ERROR code
    raises KerberosError.

    The address family and sockaddr come from ``getaddrinfo`` (230-08 D-30), so
    an IPv6 KDC is reachable; an A record is preferred over an AAAA record, as
    the AF_INET-only probe did.  The socket is ``connect()``ed to that sockaddr,
    so the kernel discards a reply from any other source and an ICMP
    port-unreachable surfaces as ConnectionRefusedError.  Bounded by
    ``settimeout(timeout)``: one send and one recv.
    """
    if port is None:
        port = KDC_PORT
    client_name, message = _build_request(principal, realm)

    try:
        family, sockaddr = _resolve_udp(host, port)
        sock = socket.socket(family, socket.SOCK_DGRAM)
    except OSError as e:
        logger.warning("KDC UDP probe transport failed for %r: %s", host, e)
        raise
    try:
        sock.settimeout(timeout)
        sock.connect(sockaddr)
        sock.send(message)
        data = sock.recv(65535)
    except OSError as e:
        # socket.timeout, ConnectionRefusedError (ICMP unreachable), send errors.
        logger.warning("KDC UDP probe transport failed for %r: %s", host, e)
        raise
    finally:
        sock.close()

    try:
        return _classify_kdc_reply(data, realm, client_name, principal)
    except KerberosUnrecognisedReply as e:
        logger.warning("KDC UDP probe decode failed for %r: %s", host, e)
        raise
    except KerberosPrincipalUnknown:
        logger.warning(
            "KDC UDP probe: principal %r unknown to the KDC at %r "
            "(KDC_ERR_C_PRINCIPAL_UNKNOWN 6)", principal, host)
        raise


def _enc_types_int(value):
    """``msDS-SupportedEncryptionTypes`` as an int, or None.

    230-REVIEW-R12 CR-02: the value is peer-supplied.  ldap3 hands back raw
    bytes for an undecodable value, and the result reaches ``json.dumps``, so
    anything that is not an integer (or a decimal string) becomes None.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _probe_ldap_anon(host: str, timeout: int, logger=None) -> dict:
    """Attempt anonymous LDAP bind on port 389 to read msDS-SupportedEncryptionTypes.

    Returns dict with 'ldap_status' key. Always succeeds (never raises), and
    every value is JSON-serialisable (230-REVIEW-R12 CR-02).
    Per KERB-03: gracefully degrades if unreachable or auth required.
    The connection is unbound on every path (R12 WR-02).
    """
    conn = None
    try:
        import ldap3
        server = ldap3.Server(host, port=389, connect_timeout=timeout)
        conn = ldap3.Connection(
            server, authentication=ldap3.ANONYMOUS, receive_timeout=timeout
        )
        if not conn.bind():
            return {
                "ldap_status": "anonymous-bind-rejected",
                # 230-REVIEW-R12 IN-03: peer-supplied text, bounded.
                "ldap_error": str(conn.last_error)[:200],
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
                    enc_types_val = _enc_types_int(
                        conn.entries[0]['msDS-SupportedEncryptionTypes'].value)
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
                "Kerberos LDAP probe failed for %s: %s (skipped)", host,
                safe_str(exc)[:200],
            )
        return {"ldap_status": "skipped", "ldap_error": safe_str(exc)[:200]}
    finally:
        if conn is not None:
            try:
                conn.unbind()
            except Exception:  # noqa: BLE001 - best-effort close
                pass


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
    not a transport failure: no UDP fallback after a TCP answer, never
    ``kerberos-no-preauth``.  Also the row for a UDP reply that does not parse
    (230-08 D-29).  Carries the error, so it is visibly a failed assessment
    rather than a clean result.
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


def _not_probed_row(host: str, realm, now, reason: str) -> CryptoEndpoint:
    """Row for a target that was never probed: an invalid name
    (230-REVIEW-R9 WR-02/WR-03) or an AS-REQ that cannot be built (R10 WR-02).
    No Kerberos or LDAP traffic was sent for it.
    """
    row = CryptoEndpoint(
        host=host,
        port=88,
        protocol="KERBEROS",
        cert_pubkey_alg="kerberos-unreachable",
        service_detail="kerberos-unreachable",
        scanned_at=now,
        scan_error=reason,
        scan_error_category="invalid_input",
    )
    row.kerberos_scan_json = json.dumps({
        "realm": realm, "etypes": [], "etype_details": [],
        "ldap": {}, "ldap_status": "skipped",
    })
    return row


def _principal_unknown_row(target: str, realm: str, timeout: int, logger,
                           principal: str, now) -> CryptoEndpoint:
    """Honest row for KDC_ERR_C_PRINCIPAL_UNKNOWN (6), on either transport.

    Phase 230 D-25: the KDC answered but returns no etype data for this
    principal.  An assessment gap, not a transport failure: no scan_error, and
    never "kerberos-no-preauth".
    """
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
    return gap_ep


def _krb_error_code(exc):
    """The KRB_ERROR code carried by a KerberosError, or None.  Never raises."""
    try:
        code = int(exc.error)
        packet = getattr(exc, "packet", 0)
        if code == 0 and not isinstance(packet, int):
            code = int(packet["error-code"])
        return code
    except Exception:  # noqa: BLE001 - diagnostics only
        return None


def _krb_error_reason(exc) -> str:
    """Name the KRB_ERROR code on the honest row (no reply bytes, no secrets)."""
    code = _krb_error_code(exc)
    if code is None:
        return "KDC answered a KRB_ERROR (unknown code); etypes not assessed"
    name = ""
    try:
        name = f" {constants.ErrorCodes(code).name}"
    except Exception:  # noqa: BLE001 - name lookup is best-effort
        pass
    return (f"KDC answered KRB_ERROR code {code}{name}; "
            "it advertised no etype information for this probe")


def _krb_error_row(target: str, realm: str, timeout: int, logger,
                   principal: str, now, exc) -> CryptoEndpoint:
    """Honest row for a KRB_ERROR other than 25 and 6 (230-08 D-29).

    The KDC answered, so "kerberos-unreachable" would be false, and an error
    reply is not an AS-REP, so it is never "kerberos-no-preauth".  Derives no
    finding and adds no weak-etype count; ``scan_error`` carries the error.
    """
    row = CryptoEndpoint(
        host=target,
        port=88,
        protocol="KERBEROS",
        cert_pubkey_alg=None,
        service_detail="kerberos-etypes-unavailable-krb-error",
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
        "etypes_unavailable_reason": _krb_error_reason(exc),
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
    # 230-REVIEW-R12 CR-01 / R13 CR-01/CR-02: anything that is not a list is
    # one target (a str is never a sequence of one-character targets, a dict
    # never a set of key targets); a non-str target then gets the not-probed
    # row.
    if not isinstance(targets, (list, tuple, set, frozenset)):
        targets = [targets]
    results = []
    for target in targets:
        invalid = _invalid_target_reason(target)
        if invalid is not None:
            # 230-REVIEW-R9 WR-02/WR-03: never probed (no Kerberos, no LDAP).
            results.append(_not_probed_row(
                target if isinstance(target, str) else repr(target), None, now,
                invalid))
            continue
        # 230-REVIEW-R10 WR-01: probe and report the name that was validated.
        target = _normalise_target(target)
        realm = _derive_realm(target)
        # 230-08 D-29: None, never [].  Every path below assigns it; a path
        # that does not must read as unreachable.  [] means "matching AS-REP"
        # and nothing else.
        etypes = None
        tcp_error = None
        udp_error = None

        # TCP primary (per D-01; QUIRK-framed TCP since 230-REVIEW-R2 CR-01).
        # AUDIT-03: If the TCP probe raises (connection refused, timeout, or any
        # transport failure), control falls through to _probe_kdc_udp below.  This
        # TCP→UDP downgrade is intentional standard Kerberos behaviour per
        # RFC 4120 §7.2.1 ("Kerberos clients SHOULD support both UDP and TCP; a
        # client MAY retry over TCP/UDP on failure") — it is NOT a defect.  The
        # UDP answer goes through the same classifier as TCP (230-08 D-29).
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
        except KerberosRequestBuildError as exc:
            # 230-REVIEW-R10 WR-02/WR-03: nothing was sent; UDP would fail to
            # build the same request.  Not probed: no UDP, no LDAP.
            results.append(_not_probed_row(target, realm, now, safe_str(exc)))
            continue
        except KerberosPrincipalUnknown:
            # Phase 230 D-25: the KDC answered (code 6) but returns no etype data
            # for this principal.  An assessment gap, not a transport failure:
            # no UDP fallback, no scan_error, and never "kerberos-no-preauth".
            results.append(_principal_unknown_row(target, realm, timeout, logger,
                                                  principal, now))
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
            # (RFC 4120 §7.2.1).
            #
            # 230-08 D-29: the UDP reply is classified exactly as a TCP reply
            # is.  No UDP failure reads as "no pre-auth": only a matching AS-REP
            # returns [].
            try:
                etypes = _probe_kdc_udp(target, realm, timeout, principal=principal)
            except KerberosRequestBuildError as udp_exc:
                # 230-REVIEW-R11 IN-01: nothing was sent on this leg either.
                results.append(_not_probed_row(target, realm, now,
                                               safe_str(udp_exc)))
                continue
            except KerberosPreauthNoEtypes:
                results.append(_preauth_no_etypes_row(target, realm, timeout, logger,
                                                      principal, now))
                continue
            except KerberosPrincipalUnknown:
                results.append(_principal_unknown_row(target, realm, timeout, logger,
                                                      principal, now))
                continue
            except KerberosUnrecognisedReply as udp_exc:
                results.append(_unrecognised_reply_row(target, realm, timeout, logger,
                                                       principal, now, udp_exc))
                continue
            except KerberosError as udp_exc:
                results.append(_krb_error_row(target, realm, timeout, logger,
                                              principal, now, udp_exc))
                continue
            except OSError as udp_exc:
                if isinstance(tcp_error, KerberosError):
                    # The KDC answered over TCP with a KRB_ERROR; a dead UDP leg
                    # does not make it unreachable.
                    results.append(_krb_error_row(target, realm, timeout, logger,
                                                  principal, now, tcp_error))
                    continue
                etypes = None  # both paths failed
                udp_error = udp_exc
            except Exception as udp_exc:  # noqa: BLE001 - not a reply we can read
                etypes = None
                udp_error = udp_exc
        except Exception as exc:  # noqa: BLE001 - see below
            # 230-REVIEW-R3 WR-01: anything else the TCP probe raises is not a
            # transport failure (a decoder failure on untrusted reply bytes),
            # so this gets the honest row instead of a UDP retry.
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
            unreachable_doc = {
                "realm": realm,
                "etypes": [],
                "etype_details": [],
                "ldap": ldap_result,
                "ldap_status": ldap_result.get("ldap_status", "skipped"),
            }
            if udp_error is not None:
                unreachable_doc["udp_error"] = safe_str(udp_error)
            unreachable_ep.kerberos_scan_json = json.dumps(unreachable_doc)
            results.append(unreachable_ep)
            continue

        # Build per-etype CryptoEndpoints
        target_endpoints = []
        etype_details = []
        # 230-REVIEW-R12 WR-03: e-data with both PA-ETYPE-INFO2 and PA-ETYPE-INFO
        # names an etype twice; one row each, so the weak count is not doubled.
        etypes = list(dict.fromkeys(etypes))
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
