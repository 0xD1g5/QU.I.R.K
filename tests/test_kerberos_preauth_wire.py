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
        kdc = fake_kdc_factory(fixed_blob=_as_rep())
        _redirect_kdc(monkeypatch, kdc.port)
        rows = ks.scan_kerberos_targets(["127.0.0.1"], timeout=3)
        assert [r.service_detail for r in rows] == ["kerberos-no-preauth"]

    @pytest.mark.parametrize(
        "blob",
        [
            b"\x00garbage",
            bytes([0x6B, 0x03, 0x30, 0x01, 0x00]),  # AS-REP tag, not an AS-REP
            b"HTTP/1.1 400 Bad Request\r\n\r\n",
        ],
        ids=["garbage", "as-rep-shell", "http"],
    )
    def test_unrecognised_reply_is_not_no_preauth(self, blob, fake_kdc_factory, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        kdc = fake_kdc_factory(fixed_blob=blob)
        _redirect_kdc(monkeypatch, kdc.port)

        def udp_fails(*a, **k):
            # Host port 88 is held by the macOS KDC; simulate the UDP leg
            # failing so the existing error handling is what the row shows.
            raise OSError("udp probe stubbed out")

        monkeypatch.setattr(ks, "_probe_kdc_udp", udp_fails)
        rows = ks.scan_kerberos_targets(["127.0.0.1"], timeout=3)
        assert not any(r.service_detail == "kerberos-no-preauth" for r in rows)
        assert [r.service_detail for r in rows] == ["kerberos-unreachable"]
        assert rows[0].scan_error

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

    def test_scan_returns_on_unframed_http_peer(self, monkeypatch):
        import quirk.scanner.kerberos_scanner as ks

        peer = kwh.RawPeer(kwh.http_unframed)
        monkeypatch.setattr(ks, "KDC_PORT", peer.port)
        try:
            rows, exc, _ = kwh.run_with_watchdog(
                lambda: ks.scan_kerberos_targets(["127.0.0.1"], timeout=1), budget=10,
            )
        finally:
            peer.close()
        assert exc is None
        assert len(rows) == 1
