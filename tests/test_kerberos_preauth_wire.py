"""Fake-KDC wire proof for Kerberos etype enumeration (Phase 230 DETECT-02).

Decisions: D-05 (decode the RETURNED reply), D-06 (retired by 230-REVIEW-R2
CR-01: the probe no longer calls impacket's sendReceive, whose old versions
raised for code 25; it frames TCP itself), D-07 (no test patches
``_probe_kdc``; the real socket and decode code is driven), D-07a (class-level skipif plus one ``ci_extras_gap`` registry row),
D-24 (the probe principal reaches the AS-REQ cname), D-25 (code 6 is an honest
"etypes unavailable" row, never ``kerberos-no-preauth``).

LOCAL-ONLY PROOF: CI's Linux Full Suite installs ``.[all]`` which excludes the
``identity`` extra (impacket), so this class skips there. The config / wiring /
row-treatment tests live in test_kerberos_probe_principal_config.py and run in
CI.
"""

import datetime
import json
import socket
import struct
import threading

import pytest

from quirk.scanner.kerberos_scanner import IMPACKET_AVAILABLE
from tests import kerberos_wire_helpers as kwh

ETYPES = [23, 17, 18, 1]


def _krb_error(error_code=25, etypes=None, realm="LAB.TEST", enc_ts_only=False):
    """Build DER KRB_ERROR bytes; PA-ETYPE-INFO2 e-data only when etypes given.

    ``enc_ts_only`` builds e-data whose METHOD-DATA carries only a
    PA-ENC-TIMESTAMP hint and no ETYPE-INFO/ETYPE-INFO2 (230-REVIEW CR-02).
    """
    from pyasn1.codec.der import encoder
    from impacket.krb5 import constants
    from impacket.krb5.asn1 import (
        ETYPE_INFO2, ETYPE_INFO2_ENTRY, KRB_ERROR, METHOD_DATA, PA_DATA,
    )
    from impacket.krb5.types import KerberosTime

    err = KRB_ERROR()
    err["pvno"] = 5
    err["msg-type"] = 30
    err["stime"] = KerberosTime.to_asn1(datetime.datetime.now(datetime.timezone.utc))
    err["susec"] = 0
    err["error-code"] = error_code
    err["realm"] = realm
    err["sname"]["name-type"] = 2
    err["sname"]["name-string"][0] = "krbtgt"
    err["sname"]["name-string"][1] = realm
    if etypes:
        info2 = ETYPE_INFO2()
        for i, et in enumerate(etypes):
            e = ETYPE_INFO2_ENTRY()
            e["etype"] = et
            info2.setComponentByPosition(i, e)
        pa = PA_DATA()
        pa["padata-type"] = int(constants.PreAuthenticationDataTypes.PA_ETYPE_INFO2.value)
        pa["padata-value"] = encoder.encode(info2)
        md = METHOD_DATA()
        md.setComponentByPosition(0, pa)
        err["e-data"] = encoder.encode(md)
    elif enc_ts_only:
        pa = PA_DATA()
        pa["padata-type"] = int(constants.PreAuthenticationDataTypes.PA_ENC_TIMESTAMP.value)
        pa["padata-value"] = b""
        md = METHOD_DATA()
        md.setComponentByPosition(0, pa)
        err["e-data"] = encoder.encode(md)
    return encoder.encode(err)


def _as_rep(realm="LAB.TEST", cname="Administrator"):
    """Build a structurally valid DER AS-REP (WR-01 control: decodes as AS_REP)."""
    from pyasn1.codec.der import encoder
    from impacket.krb5.asn1 import AS_REP

    rep = AS_REP()
    rep["pvno"] = 5
    rep["msg-type"] = 11
    rep["crealm"] = realm
    rep["cname"]["name-type"] = 1
    rep["cname"]["name-string"][0] = cname
    tkt = rep["ticket"]
    tkt["tkt-vno"] = 5
    tkt["realm"] = realm
    tkt["sname"]["name-type"] = 2
    tkt["sname"]["name-string"][0] = "krbtgt"
    tkt["sname"]["name-string"][1] = realm
    tkt["enc-part"]["etype"] = 18
    tkt["enc-part"]["cipher"] = b"\x00" * 16
    rep["enc-part"]["etype"] = 18
    rep["enc-part"]["cipher"] = b"\x00" * 16
    return encoder.encode(rep)


class _FakeKdc:
    """Principal-aware loopback KDC: replies per cname, code 6 for unknown."""

    def __init__(self, replies, fixed_blob=None):
        self.replies = replies
        self.fixed_blob = fixed_blob
        self.cnames = []
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.sock.settimeout(5)
        self.port = self.sock.getsockname()[1]
        self._t = threading.Thread(target=self._serve, daemon=True)
        self._t.start()

    def _recv_exact(self, c, n):
        data = b""
        while len(data) < n:
            chunk = c.recv(n - len(data))
            if not chunk:
                break
            data += chunk
        return data

    def _serve(self):
        from pyasn1.codec.ber import decoder
        from impacket.krb5.asn1 import AS_REQ

        while True:
            try:
                c, _ = self.sock.accept()
            except (OSError, socket.timeout):
                return
            try:
                c.settimeout(5)
                n = struct.unpack(">I", self._recv_exact(c, 4))[0]
                req = self._recv_exact(c, n)
                msg = decoder.decode(req, asn1Spec=AS_REQ())[0]
                cname = str(msg["req-body"]["cname"]["name-string"][0])
                self.cnames.append(cname)
                if self.fixed_blob is not None:
                    r = self.fixed_blob
                else:
                    r = self.replies.get(cname) or _krb_error(6)
                c.sendall(struct.pack(">I", len(r)) + r)
            except Exception:  # noqa: BLE001 - test server must never kill the thread
                pass
            finally:
                c.close()

    def close(self):
        self.sock.close()


class _FakeUdpKdc:
    """Principal-aware loopback UDP KDC (230-08 D-29): replies per cname.

    Runs on a port with no TCP listener, so the scanner's real TCP connect is
    refused and its real UDP fallback talks to this server.  Unframed datagrams,
    real ASN.1 bytes, per-socket timeouts.
    """

    def __init__(self, replies, fixed_blob=None):
        self.replies = replies
        self.fixed_blob = fixed_blob
        self.cnames = []
        self.stop = threading.Event()
        for _ in range(50):
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(("127.0.0.1", 0))
            self.port = self.sock.getsockname()[1]
            if kwh.tcp_port_is_closed(self.port):
                break
            self.sock.close()
        self.sock.settimeout(0.2)
        self._t = threading.Thread(target=self._serve, daemon=True)
        self._t.start()

    def _serve(self):
        from pyasn1.codec.ber import decoder
        from impacket.krb5.asn1 import AS_REQ

        while not self.stop.is_set():
            try:
                req, addr = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                msg = decoder.decode(req, asn1Spec=AS_REQ())[0]
                cname = str(msg["req-body"]["cname"]["name-string"][0])
                self.cnames.append(cname)
                if self.fixed_blob is not None:
                    r = self.fixed_blob
                else:
                    r = self.replies.get(cname) or _krb_error(6)
                self.sock.sendto(r, addr)
            except Exception:  # noqa: BLE001 - test server must never kill the thread
                pass

    def close(self):
        self.stop.set()
        self._t.join(2)
        self.sock.close()


@pytest.fixture
def fake_udp_kdc_factory():
    made = []

    def make(replies=None, fixed_blob=None):
        k = _FakeUdpKdc(replies or {}, fixed_blob)
        made.append(k)
        return k

    yield make
    for k in made:
        k.close()


@pytest.fixture
def fake_kdc_factory():
    # 230-REVIEW-R2 CR-01: no process-wide socket.setdefaulttimeout here.  It
    # masked a production hang (the scanner set no timeout of its own).  The
    # fake KDC's own sockets carry per-socket timeouts instead.
    made = []

    def make(replies=None, fixed_blob=None):
        k = _FakeKdc(replies or {}, fixed_blob)
        made.append(k)
        return k

    yield make
    for k in made:
        k.close()


def _redirect_kdc(monkeypatch, port):
    """Point the scanner's real TCP (and UDP) transport at a loopback port."""
    import quirk.scanner.kerberos_scanner as ks

    monkeypatch.setattr(ks, "KDC_PORT", port)


def _row_etypes(rows):
    out = []
    for r in rows:
        if r.service_detail.startswith("etype:"):
            out.append(int(r.service_detail.split(":")[1]))
    return out


@pytest.mark.skipif(
    not IMPACKET_AVAILABLE,
    reason="identity extra absent from .[all]; impacket not installed",
)
class TestKerberosPreauthWire:
    def test_preauth_required_reply_yields_etypes(self, fake_kdc_factory, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory({"Administrator": _krb_error(25, ETYPES)})
        _redirect_kdc(monkeypatch, kdc.port)
        rows = ks.scan_kerberos_targets(["127.0.0.1"], timeout=3)
        assert _row_etypes(rows) == ETYPES
        assert json.loads(rows[0].kerberos_scan_json)["etypes"] == ETYPES
        assert not any(r.service_detail == "kerberos-no-preauth" for r in rows)
        assert kdc.cnames == ["Administrator"]

    def test_configured_principal_is_sent_on_the_wire(self, fake_kdc_factory, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory({"svc-quirk-probe": _krb_error(25, ETYPES)})
        _redirect_kdc(monkeypatch, kdc.port)
        rows = ks.scan_kerberos_targets(
            ["127.0.0.1"], timeout=3, principal="svc-quirk-probe"
        )
        assert kdc.cnames == ["svc-quirk-probe"]
        assert _row_etypes(rows) == ETYPES

    def test_principal_unknown_reply_yields_honest_row(self, fake_kdc_factory, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory({})  # every cname -> code 6
        _redirect_kdc(monkeypatch, kdc.port)
        udp_calls = []
        # Replaces only the UDP fallback (host port 88 is held by the macOS KDC),
        # never _probe_kdc.
        monkeypatch.setattr(
            ks, "_probe_kdc_udp",
            lambda *a, **k: udp_calls.append(1) or [],
        )
        rows = ks.scan_kerberos_targets(["127.0.0.1"], timeout=3)
        assert len(rows) == 1
        row = rows[0]
        assert row.service_detail == "kerberos-etypes-unavailable-principal-unknown"
        assert row.cert_pubkey_alg is None
        assert row.scan_error is None
        assert not any(r.service_detail == "kerberos-no-preauth" for r in rows)
        sj = json.loads(row.kerberos_scan_json)
        assert sj["probe_principal"] == "Administrator"
        assert "(6)" in sj["etypes_unavailable_reason"]
        assert udp_calls == []

    def test_probe_kdc_direct_port(self, fake_kdc_factory):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory({"Administrator": _krb_error(25, ETYPES)})
        assert ks._probe_kdc("127.0.0.1", "LAB.TEST", 3, port=kdc.port) == ETYPES

    def test_as_rep_control_still_no_preauth(self, fake_kdc_factory, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        # A real encoded AS-REP (WR-01): only a reply that decodes as AS_REP
        # may be read as "no pre-auth required".
        # The AS-REP must name the probed realm and principal (230-REVIEW-R2
        # IN-04); an IP-literal target's realm is the address itself.
        kdc = fake_kdc_factory(fixed_blob=_as_rep(realm="127.0.0.1"))
        _redirect_kdc(monkeypatch, kdc.port)
        rows = ks.scan_kerberos_targets(["127.0.0.1"], timeout=3)
        assert [r.service_detail for r in rows] == ["kerberos-no-preauth"]

    # 230-REVIEW-R2 WR-01: a TCP peer that answered with non-Kerberos bytes is
    # a positive answer, not a transport failure.  It must yield the honest
    # unrecognised-reply row with NO UDP fallback: something answered on the
    # port, so it is not a transport failure (230-08: the UDP leg no longer
    # returns [] on failure either, but a TCP answer still ends the probe).  The
    # UDP leg here is the REAL _probe_kdc_udp behind a delegating spy, aimed at
    # the same loopback port number, where nothing listens on UDP.

    def _real_udp_spy(self, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        calls = []
        real = ks._probe_kdc_udp

        def spy(*a, **k):
            calls.append(1)
            return real(*a, **k)

        monkeypatch.setattr(ks, "_probe_kdc_udp", spy)
        return calls

    def _assert_unrecognised_row(self, rows, udp_calls):
        assert not any(r.service_detail == "kerberos-no-preauth" for r in rows)
        assert [r.service_detail for r in rows] == [
            "kerberos-etypes-unavailable-unrecognised-reply"
        ]
        row = rows[0]
        assert row.cert_pubkey_alg is None
        assert row.scan_error
        assert udp_calls == []
        sj = json.loads(row.kerberos_scan_json)
        assert sj["etypes"] == []
        assert sj["probe_principal"] == "Administrator"
        assert sj["etypes_unavailable_reason"]

    @pytest.mark.parametrize(
        "blob",
        [
            b"\x00garbage",
            bytes([0x6B, 0x03, 0x30, 0x01, 0x00]),  # AS-REP tag, not an AS-REP
            b"HTTP/1.1 400 Bad Request\r\n\r\n",
        ],
        ids=["garbage", "as-rep-shell", "http-framed"],
    )
    def test_unrecognised_reply_is_not_no_preauth(self, blob, fake_kdc_factory, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory(fixed_blob=blob)
        _redirect_kdc(monkeypatch, kdc.port)
        udp_calls = self._real_udp_spy(monkeypatch)
        rows = ks.scan_kerberos_targets(["127.0.0.1"], timeout=1)
        self._assert_unrecognised_row(rows, udp_calls)

    @pytest.mark.parametrize(
        "handler",
        [kwh.http_unframed, kwh.short_then_close, kwh.huge_declared],
        ids=["http-unframed", "short-then-close", "huge-declared"],
    )
    def test_broken_framing_is_not_no_preauth(self, handler, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        peer = kwh.RawPeer(handler)
        _redirect_kdc(monkeypatch, peer.port)
        udp_calls = self._real_udp_spy(monkeypatch)
        try:
            rows, exc, _ = kwh.run_with_watchdog(
                lambda: ks.scan_kerberos_targets(["127.0.0.1"], timeout=1), budget=10,
            )
        finally:
            peer.close()
        assert exc is None
        self._assert_unrecognised_row(rows, udp_calls)

    @pytest.mark.parametrize(
        "handler", [None, kwh.silent], ids=["tcp-refused", "silent-peer"],
    )
    def test_no_tcp_reply_still_falls_back_to_udp(self, handler, monkeypatch):
        """A TCP leg that got no reply byte is a transport failure: UDP is
        still tried (RFC 4120 §7.2.1).  Nothing listens on UDP either, so
        the row is kerberos-unreachable, never kerberos-no-preauth (230-08
        D-29: UDP failure is no longer read as "no pre-auth")."""
        import quirk.scanner.kerberos_scanner as ks

        if handler is None:
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            s.close()
            peer = None
        else:
            peer = kwh.RawPeer(handler)
            port = peer.port
        _redirect_kdc(monkeypatch, port)
        udp_calls = self._real_udp_spy(monkeypatch)
        try:
            rows, exc, _ = kwh.run_with_watchdog(
                lambda: ks.scan_kerberos_targets(["127.0.0.1"], timeout=1), budget=10,
            )
        finally:
            if peer:
                peer.close()
        assert exc is None
        assert udp_calls == [1]
        assert [r.service_detail for r in rows] == ["kerberos-unreachable"]

    def test_unencodable_host_is_unreachable_not_unrecognised(self, monkeypatch):
        """230-REVIEW-R8 WR-03: a target name IDNA cannot encode (a 64-character
        label) never resolved on either leg, so nothing answered: the row is
        kerberos-unreachable carrying the UDP error, not unrecognised-reply."""
        import quirk.scanner.kerberos_scanner as ks

        host = "a" * 64 + ".example.com"
        rows, exc, _ = kwh.run_with_watchdog(
            lambda: ks.scan_kerberos_targets([host], timeout=1), budget=10,
        )
        assert exc is None
        assert [r.service_detail for r in rows] == ["kerberos-unreachable"]
        assert "cannot be encoded" in json.loads(rows[0].kerberos_scan_json)["udp_error"]

    def test_idn_target_is_probed_with_its_a_label_realm(self, monkeypatch):
        """230-REVIEW-R9 WR-01: a non-Latin-1 IDN target used to fail while the
        AS-REQ was encoded, before any packet, and was labelled
        unrecognised-reply ("a peer answered").  Its realm is now the A-label,
        the request encodes, and with the name unresolvable the row is
        kerberos-unreachable."""
        import quirk.scanner.kerberos_scanner as ks

        def no_such_name(*a, **k):
            raise socket.gaierror(socket.EAI_NONAME, "stubbed NXDOMAIN")

        monkeypatch.setattr(ks.socket, "getaddrinfo", no_such_name)
        monkeypatch.setattr(ks.socket, "create_connection", no_such_name)
        rows, exc, _ = kwh.run_with_watchdog(
            lambda: ks.scan_kerberos_targets(["kdc.пример"], timeout=1), budget=10,
        )
        assert exc is None
        assert [r.service_detail for r in rows] == ["kerberos-unreachable"]
        assert json.loads(rows[0].kerberos_scan_json)["realm"] == "KDC.XN--E1AFMKFD"

    def test_request_build_failure_is_its_own_short_error(self):
        """230-REVIEW-R10 WR-02/WR-03: an AS-REQ that cannot be encoded raises
        KerberosRequestBuildError on both legs, not OSError (so it is never read
        as a network failure) and with a short message, not pyasn1's ~32 KB
        dump of the request."""
        import quirk.scanner.kerberos_scanner as ks

        for probe in (ks._probe_kdc, ks._probe_kdc_udp):
            with pytest.raises(ks.KerberosRequestBuildError) as info:
                probe("127.0.0.1", "X.\u0436", 1)
            assert not isinstance(info.value, OSError)
            assert "cannot build AS-REQ" in str(info.value)
            assert len(str(info.value)) < 300

    def test_unbuildable_realm_target_is_not_probed(self, monkeypatch):
        """230-REVIEW-R10 WR-02/WR-03: a realm that stays unencodable (its label
        is too long for IDNA, so the U-label is kept) is reported as not probed:
        invalid_input, a short scan_error, and no TCP, UDP or LDAP traffic."""
        import quirk.scanner.kerberos_scanner as ks

        touched = []

        def record(host, *a, **k):
            touched.append(host)
            raise socket.gaierror(socket.EAI_NONAME, "stubbed NXDOMAIN")

        monkeypatch.setattr(ks.socket, "getaddrinfo", record)
        monkeypatch.setattr(ks.socket, "create_connection", record)
        monkeypatch.setattr(ks, "_probe_ldap_anon",
                            lambda host, *a, **k: touched.append(("ldap", host)) or {})
        host = "kdc." + "\u043f" * 70 + ".ru"
        rows, exc, _ = kwh.run_with_watchdog(
            lambda: ks.scan_kerberos_targets([host], timeout=1), budget=10,
        )
        assert exc is None
        assert [r.service_detail for r in rows] == ["kerberos-unreachable"]
        assert rows[0].scan_error_category == "invalid_input"
        assert "cannot build AS-REQ" in rows[0].scan_error
        assert len(rows[0].scan_error) < 300
        assert touched == []

    # 230-REVIEW-R3 WR-01: a framed KRB_ERROR-shaped reply whose malformed
    # indefinite-length inner SEQUENCE makes pyasn1 0.6.3 raise IndexError
    # (found by fuzzing).  Any exception while decoding untrusted reply bytes
    # is an unrecognised reply: never UDP, never kerberos-no-preauth.
    DECODER_INDEXERROR_BLOB = bytes.fromhex(
        "7e753073a003020105a10302011ea411180f323032363130323331371f3133315aa5"
        "03020100a603020119a90a1b084c41422e544553a6aa1d3080a003020102a1143012"
        "1b066b72627467741b084c41420d54455354ac1f041d301b3019a103020113a21204"
        "10300e3005a0030201173005a003020112"
    )

    @classmethod
    def _assert_blob_still_trips_a_non_pyasn1_error(cls):
        """230-REVIEW-R4 IN-03: precondition.  These tests prove the broad
        ``except`` only while the pinned decoder raises something OTHER than
        PyAsn1Error on the blob (IndexError on pyasn1 0.6.3).  If an upgrade
        changes that, fail loudly (find a new blob by fuzzing) rather than
        pass while exercising only the narrow path."""
        from impacket.krb5.asn1 import KRB_ERROR
        from pyasn1.codec.ber import decoder
        from pyasn1.error import PyAsn1Error

        try:
            decoder.decode(cls.DECODER_INDEXERROR_BLOB, asn1Spec=KRB_ERROR())
        except PyAsn1Error as exc:
            pytest.fail("precondition lost: DECODER_INDEXERROR_BLOB now raises "
                        f"PyAsn1Error ({exc!r}), so this test no longer covers a "
                        "non-pyasn1 decoder exception; re-fuzz a new blob")
        except Exception:  # noqa: BLE001 - the precondition holds
            return
        pytest.fail("precondition lost: DECODER_INDEXERROR_BLOB now decodes "
                    "without error; re-fuzz a new blob")

    def test_probe_kdc_decoder_indexerror_is_unrecognised_reply(self):
        import quirk.scanner.kerberos_scanner as ks

        self._assert_blob_still_trips_a_non_pyasn1_error()
        peer = kwh.RawPeer(kwh.framed(self.DECODER_INDEXERROR_BLOB))
        try:
            result, exc, _ = kwh.run_with_watchdog(
                lambda: ks._probe_kdc("127.0.0.1", "LAB.TEST", 2, port=peer.port),
                budget=6,
            )
        finally:
            peer.close()
        assert result is None
        assert isinstance(exc, ks.KerberosUnrecognisedReply), repr(exc)

    def test_scan_decoder_indexerror_is_unrecognised_row_without_udp(self, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        self._assert_blob_still_trips_a_non_pyasn1_error()
        peer = kwh.RawPeer(kwh.framed(self.DECODER_INDEXERROR_BLOB))
        _redirect_kdc(monkeypatch, peer.port)
        udp_calls = self._real_udp_spy(monkeypatch)
        try:
            rows, exc, _ = kwh.run_with_watchdog(
                lambda: ks.scan_kerberos_targets(["127.0.0.1"], timeout=1), budget=10,
            )
        finally:
            peer.close()
        assert exc is None
        self._assert_unrecognised_row(rows, udp_calls)

    def test_first_connection_dropped_second_answered_no_udp(self, monkeypatch):
        """230-REVIEW-R3 IN-01: the live Samba drop shape (zero bytes, then
        FIN) is retried once over TCP before any UDP fallback."""
        import quirk.scanner.kerberos_scanner as ks

        conns = []
        reply = _krb_error(25, ETYPES)

        def drop_first(c, stop):
            conns.append(1)
            if len(conns) > 1:
                c.sendall(struct.pack(">I", len(reply)) + reply)

        peer = kwh.RawPeer(drop_first)
        _redirect_kdc(monkeypatch, peer.port)
        udp_calls = self._real_udp_spy(monkeypatch)
        try:
            rows, exc, _ = kwh.run_with_watchdog(
                lambda: ks.scan_kerberos_targets(["127.0.0.1"], timeout=1), budget=10,
            )
        finally:
            peer.close()
        assert exc is None
        assert conns == [1, 1]
        assert udp_calls == []
        assert _row_etypes(rows) == ETYPES

    def test_late_close_retry_through_real_probe_stays_within_one_deadline(
            self, monkeypatch):
        """230-REVIEW-R5 WR-03: the real AS-REQ, the real ``_probe_kdc`` and
        the real retry.  The peer closes with zero bytes 2.5 s into a 4 s
        deadline, twice.  The retry makes exactly one connect, to the address
        the first attempt reached, and the TCP leg ends by the original
        deadline (~5 s if the retry got a fresh budget)."""
        import quirk.scanner.kerberos_scanner as ks

        conns = []

        def late(c, stop):
            conns.append(1)
            stop.wait(2.5)

        peer = kwh.RawPeer(late)
        _redirect_kdc(monkeypatch, peer.port)
        udp_calls = []
        monkeypatch.setattr(ks, "_probe_kdc_udp",
                            lambda *a, **k: udp_calls.append(1) or [])
        monkeypatch.setattr(ks, "_probe_ldap_anon",
                            lambda *a, **k: {"ldap_status": "skipped"})
        connects = []
        real_cc = socket.create_connection

        def cc(address, *a, **k):
            connects.append(tuple(address))
            return real_cc(address, *a, **k)

        monkeypatch.setattr(socket, "create_connection", cc)
        try:
            rows, exc, elapsed = kwh.run_with_watchdog(
                lambda: ks.scan_kerberos_targets(["127.0.0.1"], timeout=4),
                budget=15,
            )
        finally:
            peer.close()
        assert exc is None, repr(exc)
        # Only the first attempt resolves via create_connection; the retry
        # reconnects to the recorded sockaddr directly (230-REVIEW-R6 WR-01).
        # The peer seeing two connections is the behavioural proof.
        assert connects == [("127.0.0.1", peer.port)]
        assert conns == [1, 1]
        assert udp_calls == [1]
        assert elapsed <= 4 + 0.5, f"TCP leg took {elapsed:.2f}s; one deadline is 4s"

    def test_probe_kdc_unrecognised_reply_raises(self, fake_kdc_factory):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory(fixed_blob=b"\x00garbage")
        with pytest.raises(ks.KerberosUnrecognisedReply):
            ks._probe_kdc("127.0.0.1", "LAB.TEST", 3, port=kdc.port)

    # D-06's raise shape came from older impacket's sendReceive raising for
    # code 25.  230-REVIEW-R2 CR-01 replaced sendReceive with QUIRK's own TCP
    # framing, so every reply now arrives as bytes on the D-05 path.  These
    # pin that impacket's sendReceive is never on the probe path and that the
    # returned-reply path covers what the raise shape used to.

    def test_probe_kdc_never_calls_impacket_sendreceive(self, fake_kdc_factory, monkeypatch):
        import impacket.krb5.kerberosv5 as kv5
        import quirk.scanner.kerberos_scanner as ks

        def boom(*a, **k):
            raise AssertionError("impacket sendReceive must not be called")

        monkeypatch.setattr(kv5, "sendReceive", boom)
        assert not hasattr(ks, "sendReceive")
        kdc = fake_kdc_factory({"Administrator": _krb_error(25, ETYPES)})
        assert ks._probe_kdc("127.0.0.1", "LAB.TEST", 3, port=kdc.port) == ETYPES

    def test_probe_kdc_principal_unknown_raises(self, fake_kdc_factory):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory({})  # every cname -> code 6
        with pytest.raises(ks.KerberosPrincipalUnknown):
            ks._probe_kdc("127.0.0.1", "LAB.TEST", 3, port=kdc.port)

    def test_other_error_code_raises(self, fake_kdc_factory):
        import quirk.scanner.kerberos_scanner as ks
        from impacket.krb5.kerberosv5 import KerberosError

        kdc = fake_kdc_factory({"Administrator": _krb_error(68)})  # WRONG_REALM
        with pytest.raises(KerberosError) as ei:
            ks._probe_kdc("127.0.0.1", "LAB.TEST", 3, port=kdc.port)
        assert not isinstance(ei.value, ks.KerberosPrincipalUnknown)

    # 230-REVIEW CR-02: a KRB_ERROR 25 reply is proof that pre-auth IS required,
    # so it must never yield kerberos-no-preauth, even when it carries no usable
    # etype info.  Honest row, no UDP fallback, no weak-etype count.

    def _assert_preauth_no_etype_info_row(self, rows, udp_calls):
        assert [r.service_detail for r in rows] == [
            "kerberos-etypes-unavailable-preauth-no-etype-info"
        ]
        row = rows[0]
        assert row.cert_pubkey_alg is None
        assert row.scan_error is None
        assert udp_calls == []
        sj = json.loads(row.kerberos_scan_json)
        assert sj["etypes"] == []
        assert sj["probe_principal"] == "Administrator"
        assert "(25)" in sj["etypes_unavailable_reason"]

    @pytest.mark.parametrize(
        "reply_kwargs",
        [{}, {"enc_ts_only": True}],
        ids=["no-e-data", "enc-timestamp-only"],
    )
    def test_preauth_required_without_etype_info_is_not_no_preauth(
        self, reply_kwargs, fake_kdc_factory, monkeypatch
    ):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory({"Administrator": _krb_error(25, **reply_kwargs)})
        _redirect_kdc(monkeypatch, kdc.port)
        udp_calls = []
        monkeypatch.setattr(
            ks, "_probe_kdc_udp",
            lambda *a, **k: udp_calls.append(1) or [],
        )
        rows = ks.scan_kerberos_targets(["127.0.0.1"], timeout=3)
        self._assert_preauth_no_etype_info_row(rows, udp_calls)

    @pytest.mark.parametrize(
        "reply_kwargs",
        [{}, {"enc_ts_only": True}],
        ids=["no-e-data", "enc-timestamp-only"],
    )
    def test_probe_kdc_preauth_without_etype_info_raises(self, reply_kwargs, fake_kdc_factory):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory({"Administrator": _krb_error(25, **reply_kwargs)})
        with pytest.raises(ks.KerberosPreauthNoEtypes):
            ks._probe_kdc("127.0.0.1", "LAB.TEST", 3, port=kdc.port)

    # 230-REVIEW-R2 CR-01: a peer on port 88 that breaks the length-prefix
    # framing must not hang the probe.  Raw peers (not _FakeKdc, which always
    # frames correctly), no process-wide default timeout, and a watchdog so a
    # regression fails instead of stalling the suite.

    @pytest.mark.parametrize(
        "handler",
        [kwh.http_unframed, kwh.short_then_close],
        ids=["http-unframed", "short-then-close"],
    )
    def test_probe_kdc_returns_on_broken_framing(self, handler):
        import quirk.scanner.kerberos_scanner as ks

        peer = kwh.RawPeer(handler)
        try:
            result, exc, elapsed = kwh.run_with_watchdog(
                lambda: ks._probe_kdc("127.0.0.1", "LAB.TEST", 2, port=peer.port),
                budget=6,
            )
        finally:
            peer.close()
        assert result is None, "a broken reply must never return [] (= no pre-auth)"
        assert type(exc).__name__ == "KerberosTransportError"
        assert exc.answered is True
        assert elapsed < 3

    def test_probe_kdc_rejects_huge_declared_length_without_reading(self):
        import quirk.scanner.kerberos_scanner as ks

        peer = kwh.RawPeer(kwh.huge_declared)  # declares 1 GiB, then sends nothing
        try:
            result, exc, elapsed = kwh.run_with_watchdog(
                lambda: ks._probe_kdc("127.0.0.1", "LAB.TEST", 5, port=peer.port),
                budget=8,
            )
        finally:
            peer.close()
        assert type(exc).__name__ == "KerberosTransportError"
        assert exc.answered is True
        # Rejected on the prefix alone: a read attempt would block to the 5 s timeout.
        assert elapsed < 2

    def test_probe_kdc_silent_peer_times_out(self):
        import quirk.scanner.kerberos_scanner as ks

        peer = kwh.RawPeer(kwh.silent)
        try:
            result, exc, elapsed = kwh.run_with_watchdog(
                lambda: ks._probe_kdc("127.0.0.1", "LAB.TEST", 1, port=peer.port),
                budget=5,
            )
        finally:
            peer.close()
        assert type(exc).__name__ == "KerberosTransportError"
        assert exc.answered is False
        assert elapsed < 2

    # 230-REVIEW-R2 IN-04: an AS-REP is "no pre-auth required" only when it
    # answers THIS probe: crealm (case-insensitive) is the probed realm and
    # cname (case-insensitive) is the probe principal.  A mis-routed or
    # replayed AS-REP for someone else is an unrecognised reply.

    @pytest.mark.parametrize(
        "rep_kwargs",
        [{"realm": "OTHER.TEST"}, {"cname": "someone-else"}],
        ids=["other-realm", "other-principal"],
    )
    def test_probe_kdc_rejects_as_rep_for_another_probe(self, rep_kwargs, fake_kdc_factory):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory(fixed_blob=_as_rep(**rep_kwargs))
        with pytest.raises(ks.KerberosUnrecognisedReply):
            ks._probe_kdc("127.0.0.1", "LAB.TEST", 3, port=kdc.port)

    def test_probe_kdc_as_rep_match_is_case_insensitive(self, fake_kdc_factory):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory(fixed_blob=_as_rep(realm="lab.test", cname="administrator"))
        assert ks._probe_kdc("127.0.0.1", "LAB.TEST", 3, port=kdc.port) == []

    def test_scan_as_rep_for_another_realm_is_unrecognised_row(
        self, fake_kdc_factory, monkeypatch
    ):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory(fixed_blob=_as_rep(realm="OTHER.TEST"))
        _redirect_kdc(monkeypatch, kdc.port)
        udp_calls = self._real_udp_spy(monkeypatch)
        rows = ks.scan_kerberos_targets(["127.0.0.1"], timeout=1)
        self._assert_unrecognised_row(rows, udp_calls)

    # --- 230-08 D-29: the UDP leg, real ASN.1 bytes both ways --------------------
    # Real UDP socket, real decode, real caller routing.  Nothing listens on TCP
    # at the fake KDC's port, so the real TCP connect is refused and the UDP
    # leg runs.

    @staticmethod
    def _shapes():
        """name -> (blob builder, expected service_detail list).  The probe
        target is the IP literal 127.0.0.1, whose realm is the address itself."""
        from quirk.scanner.kerberos_scanner import KERBEROS_ETYPE_MAP

        realm = "127.0.0.1"
        etype_rows = [
            f"etype:{e}:{KERBEROS_ETYPE_MAP[e][0]}:{KERBEROS_ETYPE_MAP[e][1]}"
            for e in ETYPES
        ]
        unrec = "kerberos-etypes-unavailable-unrecognised-reply"
        return {
            "err25-etypes": (lambda: _krb_error(25, ETYPES, realm=realm), etype_rows),
            "err25-enc-ts-only": (
                lambda: _krb_error(25, realm=realm, enc_ts_only=True),
                ["kerberos-etypes-unavailable-preauth-no-etype-info"]),
            "err25-no-edata": (
                lambda: _krb_error(25, realm=realm),
                ["kerberos-etypes-unavailable-preauth-no-etype-info"]),
            "err6": (lambda: _krb_error(6, realm=realm),
                     ["kerberos-etypes-unavailable-principal-unknown"]),
            "err68": (lambda: _krb_error(68, realm=realm),
                      ["kerberos-etypes-unavailable-krb-error"]),
            "garbage": (lambda: b"\x00garbage", [unrec]),
            "asrep-other-realm": (lambda: _as_rep(realm="OTHER.TEST"), [unrec]),
            "asrep-other-cname": (
                lambda: _as_rep(realm=realm, cname="someone-else"), [unrec]),
            "asrep-match": (lambda: _as_rep(realm=realm), ["kerberos-no-preauth"]),
            "asrep-match-case": (
                lambda: _as_rep(realm=realm, cname="administrator"),
                ["kerberos-no-preauth"]),
        }

    @pytest.mark.parametrize("shape", sorted([
        "err25-etypes", "err25-enc-ts-only", "err25-no-edata", "err6", "err68",
        "garbage", "asrep-other-realm", "asrep-other-cname", "asrep-match",
        "asrep-match-case",
    ]))
    def test_udp_leg_real_decode_rows(self, shape, fake_udp_kdc_factory, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        build, expected = self._shapes()[shape]
        kdc = fake_udp_kdc_factory(fixed_blob=build())
        _redirect_kdc(monkeypatch, kdc.port)
        rows, exc, _ = kwh.run_with_watchdog(
            lambda: ks.scan_kerberos_targets(["127.0.0.1"], timeout=2), budget=15,
        )
        assert exc is None, repr(exc)
        assert [r.service_detail for r in rows] == expected
        assert kdc.cnames == ["Administrator"]
        assert (("kerberos-no-preauth" in expected)
                == any(r.service_detail == "kerberos-no-preauth" for r in rows))

    def test_udp_leg_sends_the_configured_principal(self, fake_udp_kdc_factory, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_udp_kdc_factory({"svc-quirk-probe": _krb_error(25, ETYPES)})
        _redirect_kdc(monkeypatch, kdc.port)
        rows = ks.scan_kerberos_targets(["127.0.0.1"], timeout=2, principal="svc-quirk-probe")
        assert kdc.cnames == ["svc-quirk-probe"]
        assert _row_etypes(rows) == ETYPES

    @pytest.mark.parametrize("leg", ["tcp", "udp"])
    @pytest.mark.parametrize("shape", sorted([
        "err25-etypes", "err25-enc-ts-only", "err25-no-edata", "err6", "err68",
        "garbage", "asrep-other-realm", "asrep-other-cname", "asrep-match",
        "asrep-match-case",
    ]))
    def test_no_preauth_iff_matching_as_rep_real_decode(
        self, leg, shape, fake_kdc_factory, fake_udp_kdc_factory, monkeypatch
    ):
        """Real-decode mirror of the CI invariant: over real ASN.1 bytes on both
        transports, kerberos-no-preauth appears iff the reply is an AS-REP that
        answers the probe (case-insensitive realm and cname)."""
        import quirk.scanner.kerberos_scanner as ks

        build, expected = self._shapes()[shape]
        blob = build()
        kdc = (fake_kdc_factory if leg == "tcp" else fake_udp_kdc_factory)(fixed_blob=blob)
        _redirect_kdc(monkeypatch, kdc.port)
        rows, exc, _ = kwh.run_with_watchdog(
            lambda: ks.scan_kerberos_targets(["127.0.0.1"], timeout=2), budget=15,
        )
        assert exc is None, repr(exc)
        details = [r.service_detail for r in rows]
        # A TCP code 68 falls back to a UDP leg with no listener: the KDC
        # answered, so the row is the krb-error row from the TCP code.
        assert details == expected
        is_match = shape.startswith("asrep-match")
        assert ("kerberos-no-preauth" in details) == is_match

