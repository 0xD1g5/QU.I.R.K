"""In-process loopback LDAP responder for the referral-hardening tests.

Phase 239 TRUST-02 D-10/D-23: serves just enough LDAP to answer a bind and a
search with a result-code-10 referral, and records every accepted connection,
bind and byte received. Every socket has its own timeout; nothing touches the
process-wide default. Binds 127.0.0.1 only. Requests are hand-parsed: decoding
them with the ldap3 ASN.1 spec fails on present-filters.
"""

import socket
import threading

from pyasn1.codec.ber import encoder

from ldap3.protocol.rfc4511 import (
    BindResponse, LDAPDN, LDAPMessage, LDAPString, MessageID, ProtocolOp,
    Referral, ResultCode, SearchResultDone, URI,
)


def _read_pdu(sock, recv):
    """Read one BER-framed LDAPMessage; None on EOF."""
    hdr = b""
    while len(hdr) < 2:
        chunk = recv(sock, 2 - len(hdr))
        if not chunk:
            return None
        hdr += chunk
    first_len = hdr[1]
    if first_len & 0x80:
        n = first_len & 0x7F
        ext = b""
        while len(ext) < n:
            chunk = recv(sock, n - len(ext))
            if not chunk:
                return None
            ext += chunk
        length = int.from_bytes(ext, "big")
        hdr += ext
    else:
        length = first_len
    body = b""
    while len(body) < length:
        chunk = recv(sock, length - len(body))
        if not chunk:
            return None
        body += chunk
    return _parse_message(hdr + body)


def _tlv(buf, i):
    """(tag, value_bytes, next_index) of the BER TLV at buf[i]."""
    tag = buf[i]
    ln = buf[i + 1]
    j = i + 2
    if ln & 0x80:
        n = ln & 0x7F
        ln = int.from_bytes(buf[j:j + n], "big")
        j += n
    return tag, buf[j:j + ln], j + ln


def _parse_message(pdu):
    """Hand-parse just what the responder needs: (message_id, op, info)."""
    _, seq, _ = _tlv(pdu, 0)
    _, mid, k = _tlv(seq, 0)
    op_tag, op_body, _ = _tlv(seq, k)
    message_id = int.from_bytes(mid, "big")
    if op_tag == 0x60:  # bindRequest
        _, _ver, a = _tlv(op_body, 0)
        _, name, b = _tlv(op_body, a)
        auth_tag, auth, _ = _tlv(op_body, b)
        pw = auth if auth_tag == 0x80 else None
        return message_id, "bindRequest", (name.decode(), pw)
    if op_tag == 0x63:  # searchRequest
        _, base, _ = _tlv(op_body, 0)
        return message_id, "searchRequest", base.decode()
    if op_tag == 0x42:
        return message_id, "unbindRequest", None
    return message_id, hex(op_tag), None


def _result(cls, code, referral_uri=None):
    op = cls()
    op["resultCode"] = ResultCode(code)
    op["matchedDN"] = LDAPDN("")
    op["diagnosticMessage"] = LDAPString("")
    if referral_uri:
        ref = Referral()
        ref.setComponentByPosition(0, URI(referral_uri))
        op["referral"] = ref
    return op


def _send(sock, message_id, op_name, op):
    msg = LDAPMessage()
    msg["messageID"] = MessageID(message_id)
    po = ProtocolOp()
    po[op_name] = op
    msg["protocolOp"] = po
    sock.sendall(encoder.encode(msg))


class Responder:
    """Bind -> success; search -> referral (code 10) when ``referral_uri`` is set."""

    def __init__(self, referral_uri=None):
        self.referral_uri = referral_uri
        # ldap3 rejects port 65535 ("must in range from 0 to 65535" is checked
        # as < 65535), so never serve there: hold a port-65535 socket open
        # while drawing another, then release it.
        spare = []
        while True:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("127.0.0.1", 0))
            if self.sock.getsockname()[1] != 65535:
                break
            spare.append(self.sock)
        for extra in spare:
            extra.close()
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        self.accepts = 0
        self.binds = []  # (dn, simple-password bytes or None)
        self.ops = []
        self.referrals_sent = 0
        self.received_bytes = bytearray()
        self.errors = []
        self._stop = False
        self._closed = False
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        self.sock.settimeout(0.2)
        while not self._stop:
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.accepts += 1
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _recv(self, conn, n):
        chunk = conn.recv(n)
        self.received_bytes.extend(chunk)
        return chunk

    def _handle(self, conn):
        conn.settimeout(5)
        try:
            while True:
                msg = _read_pdu(conn, self._recv)
                if msg is None:
                    return
                mid, name, info = msg
                self.ops.append(name)
                if name == "bindRequest":
                    self.binds.append(info)
                    _send(conn, mid, "bindResponse", _result(BindResponse, 0))
                elif name == "searchRequest":
                    if info == "" or self.referral_uri is None:
                        _send(conn, mid, "searchResDone",
                              _result(SearchResultDone, 0))
                    else:
                        self.referrals_sent += 1
                        _send(conn, mid, "searchResDone",
                              _result(SearchResultDone, 10, self.referral_uri))
                else:
                    return
        except Exception as exc:  # noqa: BLE001 - surfaced via .errors
            self.errors.append(repr(exc))
        finally:
            conn.close()

    def drain_backlog(self):
        """Stop accepting, then count connections still queued in the backlog."""
        self._stop = True
        self.thread.join(2)
        drained = 0
        try:
            self.sock.setblocking(False)
            while True:
                conn, _ = self.sock.accept()
                drained += 1
                conn.close()
        except (BlockingIOError, OSError):
            pass
        return drained

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._stop = True
        self.sock.close()
