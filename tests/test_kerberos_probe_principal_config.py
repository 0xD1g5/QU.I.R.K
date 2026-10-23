"""CI-visible tests for the Kerberos probe principal (Phase 230 DETECT-02).

D-24: ``connectors.kerberos_probe_principal`` (default ``Administrator``) is
read from YAML and reaches ``scan_kerberos_targets(principal=...)``.
D-25: a KDC_ERR_C_PRINCIPAL_UNKNOWN row derives no finding and adds no weak
etype; its (pre-existing, shared with kerberos-no-preauth) effect on coverage
and identity presence is pinned, not endorsed.
D-28: the template documents the option.

230-REVIEW-R2 CR-01: the QUIRK-owned TCP exchange (``_kdc_tcp_exchange``)
needs no impacket, so its hang/framing tests live here and run in CI, against
raw loopback peers with per-socket timeouts and a watchdog.

This file must not need impacket, so it runs in the Linux Full Suite (`.[all]`
excludes the identity extra). The fake-KDC wire proof is
test_kerberos_preauth_wire.py and is local-only.
"""

import ast
import logging
import time
from pathlib import Path

import pytest
import yaml

from quirk.config import ConnectorsCfg, load_config
from quirk.models import CryptoEndpoint
from quirk.scanner import kerberos_scanner as ks
from quirk.scanner.kerberos_scanner import DEFAULT_PROBE_PRINCIPAL
from tests import kerberos_wire_helpers as kwh

REPO = Path(__file__).resolve().parent.parent


def _write_cfg(tmp_path, connectors):
    p = tmp_path / "cfg.yaml"
    doc = {
        "assessment": {
            "name": "kerberos-principal-test",
            "data_classification": "internal",
            "report_owner": "tester",
            "timezone": "UTC",
        },
        "scan": {"concurrency": 50, "ports_tls": [443]},
        "output": {
            "directory": str(tmp_path / "out"),
            "db_path": str(tmp_path / "out" / "quirk.db"),
        },
        "connectors": connectors,
    }
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return str(p)


def test_default_probe_principal_is_administrator():
    assert ConnectorsCfg().kerberos_probe_principal == "Administrator"
    # Drift guard between the two literals (config.py must not import the scanner).
    assert ConnectorsCfg().kerberos_probe_principal == DEFAULT_PROBE_PRINCIPAL


def test_yaml_probe_principal_is_loaded(tmp_path, caplog):
    path = _write_cfg(tmp_path, {
        "enable_kerberos": True,
        "kerberos_targets": ["kdc.example.com"],
        "kerberos_probe_principal": "svc-quirk-probe",
    })
    with caplog.at_level(logging.WARNING):
        cfg = load_config(path)
    assert cfg.connectors.kerberos_probe_principal == "svc-quirk-probe"
    assert not [r for r in caplog.records if "kerberos_probe_principal" in r.getMessage()]


@pytest.mark.parametrize("bad", ["", "   ", 5, ["a"]])
def test_empty_probe_principal_rejected(tmp_path, bad):
    path = _write_cfg(tmp_path, {"kerberos_probe_principal": bad})
    with pytest.raises(ValueError, match="kerberos_probe_principal"):
        load_config(path)


def test_run_scan_passes_configured_principal():
    """Structural wiring check: no harness drives run_scan's Kerberos phase."""
    tree = ast.parse((REPO / "run_scan.py").read_text(encoding="utf-8"))
    calls = [
        n for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and getattr(n.func, "id", getattr(n.func, "attr", "")) == "scan_kerberos_targets"
    ]
    assert calls, "scan_kerberos_targets call not found in run_scan.py"
    found = False
    for call in calls:
        for kw in call.keywords:
            if kw.arg == "principal":
                assert ast.unparse(kw.value) == "cfg.connectors.kerberos_probe_principal"
                found = True
    assert found, "run_scan.py does not pass principal= to scan_kerberos_targets"


def test_template_lists_the_option():
    text = (REPO / "quirk" / "config_template.yaml").read_text(encoding="utf-8")
    assert "# kerberos_probe_principal:" in text


def _unknown_principal_row():
    return CryptoEndpoint(
        host="kdc.example.com",
        port=88,
        protocol="KERBEROS",
        cert_pubkey_alg=None,
        service_detail="kerberos-etypes-unavailable-principal-unknown",
    )


def test_principal_unknown_row_derives_no_finding_and_no_weak_count():
    from quirk.dashboard.api.routes.scan import _derive_identity_findings
    from quirk.intelligence.evidence import build_evidence_summary

    ep = _unknown_principal_row()
    assert _derive_identity_findings([ep]) == []
    assert build_evidence_summary([ep])["identity_weak_etype_count"] == 0


def test_principal_unknown_row_counts_as_assessed_pinned():
    from quirk.intelligence.evidence import build_evidence_summary
    from quirk.intelligence.scoring import _identity_assessed

    ep = _unknown_principal_row()
    ev = build_evidence_summary([ep])
    # PINNED, not endorsed: a placeholder row the KDC answered without etypes
    # counts as assessed crypto and as identity presence. Pre-existing, shared
    # with kerberos-no-preauth. Owned by todo
    # 261023-detect-kerberos-placeholder-rows-count-as-assessed (resolve before
    # or in Phase 233). Change this assertion only together with that todo.
    assert ev["assessed_crypto_count"] == 1
    assert ev["assessable_endpoint_count"] == 1
    assert _identity_assessed(
        ev.get("certificate_observations", {}) or ev.get("cert_observations", {}) or {},
        ev["protocol_counts"],
    ) is True


# --- 230-REVIEW-R2 CR-01: QUIRK-owned TCP framing (CI-visible) ---------------

_REQ = b"\x6a\x03\x02\x01\x05"  # bytes only; the transport does not decode


def _exchange(handler, timeout, budget):
    peer = kwh.RawPeer(handler)
    try:
        return kwh.run_with_watchdog(
            lambda: ks._kdc_tcp_exchange("127.0.0.1", peer.port, _REQ, timeout),
            budget=budget,
        )
    finally:
        peer.close()


def test_tcp_exchange_returns_framed_reply():
    result, exc, _ = _exchange(kwh.framed(b"reply-body"), timeout=2, budget=5)
    assert exc is None
    assert result == b"reply-body"


@pytest.mark.parametrize(
    "handler",
    [kwh.http_unframed, kwh.short_then_close],
    ids=["http-unframed", "short-then-close"],
)
def test_tcp_exchange_broken_framing_raises_answered(handler):
    result, exc, elapsed = _exchange(handler, timeout=2, budget=6)
    assert result is None
    assert isinstance(exc, ks.KerberosTransportError)
    assert exc.answered is True
    assert elapsed < 3


def test_tcp_exchange_rejects_huge_length_without_reading():
    result, exc, elapsed = _exchange(kwh.huge_declared, timeout=5, budget=8)
    assert isinstance(exc, ks.KerberosTransportError)
    assert exc.answered is True
    assert "implausible KDC reply length 1073741824" in str(exc)
    assert elapsed < 2  # a read would block to the 5 s timeout


def test_tcp_exchange_length_cap_boundary():
    at_cap = b"\x00" * ks.MAX_KDC_TCP_REPLY
    result, exc, _ = _exchange(kwh.framed(at_cap), timeout=3, budget=6)
    assert exc is None and result == at_cap

    over = b"\x00" * (ks.MAX_KDC_TCP_REPLY + 1)
    result, exc, _ = _exchange(kwh.framed(over), timeout=3, budget=6)
    assert isinstance(exc, ks.KerberosTransportError) and exc.answered is True


@pytest.mark.parametrize(
    "handler", [kwh.silent, kwh.close_immediately], ids=["silent", "close-immediately"],
)
def test_tcp_exchange_no_reply_byte_is_not_answered(handler):
    result, exc, elapsed = _exchange(handler, timeout=1, budget=5)
    assert isinstance(exc, ks.KerberosTransportError)
    assert exc.answered is False
    assert elapsed < 2


def test_tcp_exchange_deadline_bounds_a_slow_drip():
    # 100 bytes at one per 0.3 s would take 30 s under a per-recv timeout.
    result, exc, elapsed = _exchange(kwh.slow_drip, timeout=1, budget=5)
    assert isinstance(exc, ks.KerberosTransportError)
    assert exc.answered is True
    assert elapsed < 2


def test_tcp_exchange_connect_refused_is_plain_oserror():
    s = __import__("socket").socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()  # nothing listens here now
    result, exc, _ = kwh.run_with_watchdog(
        lambda: ks._kdc_tcp_exchange("127.0.0.1", port, _REQ, 1), budget=5,
    )
    assert isinstance(exc, OSError)
    assert not isinstance(exc, ks.KerberosTransportError)


# --- 230-REVIEW-R2 WR-01: which TCP failures fall back to UDP (CI-visible) ---
# _probe_kdc is replaced here only to choose the exception; the real wire path
# is proven in test_kerberos_preauth_wire.py (local-only, needs impacket).


def _scan_with_tcp_raising(monkeypatch, exc):
    monkeypatch.setattr(ks, "IMPACKET_AVAILABLE", True)

    def tcp(*a, **k):
        raise exc

    udp_calls = []
    monkeypatch.setattr(ks, "_probe_kdc", tcp)
    monkeypatch.setattr(ks, "_probe_kdc_udp", lambda *a, **k: udp_calls.append(1) or [])
    monkeypatch.setattr(ks, "_probe_ldap_anon", lambda *a, **k: {"ldap_status": "skipped"})
    return ks.scan_kerberos_targets(["kdc.example.com"], timeout=1), udp_calls


@pytest.mark.parametrize(
    "exc",
    [
        ks.KerberosUnrecognisedReply("neither KRB_ERROR nor AS-REP"),
        ks.KerberosTransportError("implausible KDC reply length", answered=True),
    ],
    ids=["unrecognised-reply", "answered-transport-error"],
)
def test_answered_tcp_failure_is_honest_row_without_udp(monkeypatch, exc):
    rows, udp_calls = _scan_with_tcp_raising(monkeypatch, exc)
    assert udp_calls == []
    assert [r.service_detail for r in rows] == [
        "kerberos-etypes-unavailable-unrecognised-reply"
    ]
    assert rows[0].scan_error and rows[0].cert_pubkey_alg is None


@pytest.mark.parametrize(
    "exc",
    [
        ConnectionRefusedError("refused"),
        TimeoutError("connect timed out"),
        ks.KerberosTransportError("KDC reply timed out", answered=False),
        # 230-REVIEW-R4 WR-02/IN-02: every trigger the guide and oracle list.
        OSError(65, "No route to host"),
        __import__("socket").gaierror(8, "nodename nor servname provided"),
        ks.KerberosTransportError("KDC reply timed out", False, "timeout"),
        ks.KerberosTransportError("KDC send failed", False, "send"),
        ks.KerberosTransportError("failed before any reply byte", False, "error"),
    ],
    ids=["refused", "connect-timeout", "no-reply-byte", "unreachable",
         "name-does-not-resolve", "silent-peer", "send-failed",
         "other-socket-error-before-first-byte"],
)
def test_unanswered_tcp_failure_still_falls_back_to_udp(monkeypatch, exc):
    rows, udp_calls = _scan_with_tcp_raising(monkeypatch, exc)
    assert udp_calls == [1]


@pytest.mark.parametrize(
    "exc",
    [
        IndexError("list assignment index out of range"),
        RuntimeError("arbitrary decoder failure"),
    ],
    ids=["indexerror", "arbitrary"],
)
def test_unexpected_tcp_probe_exception_is_honest_row_without_udp(monkeypatch, exc):
    """230-REVIEW-R3 WR-01: only OSError, KerberosError and an unanswered
    KerberosTransportError reach UDP.  Anything else the TCP probe raises (a
    decoder failure on untrusted reply bytes) is the honest row, never UDP's
    ``[]`` (= ``kerberos-no-preauth``, D-08a)."""
    rows, udp_calls = _scan_with_tcp_raising(monkeypatch, exc)
    assert udp_calls == []
    assert [r.service_detail for r in rows] == [
        "kerberos-etypes-unavailable-unrecognised-reply"
    ]
    assert rows[0].scan_error and rows[0].cert_pubkey_alg is None


def test_kerberos_error_still_falls_back_to_udp(monkeypatch):
    """A KRB_ERROR code other than 25/6 keeps the known D-08a UDP path."""
    rows, udp_calls = _scan_with_tcp_raising(monkeypatch, ks.KerberosError())
    assert udp_calls == [1]


def test_unexpected_udp_probe_exception_is_unreachable_row(monkeypatch):
    """230-REVIEW-R4 IN-02: only UDP's swallowed network/decode errors read as
    ``kerberos-no-preauth``; any other UDP exception gives kerberos-unreachable."""
    monkeypatch.setattr(ks, "IMPACKET_AVAILABLE", True)

    def tcp(*a, **k):
        raise ConnectionRefusedError("refused")

    def udp(*a, **k):
        raise AttributeError("unexpected")

    monkeypatch.setattr(ks, "_probe_kdc", tcp)
    monkeypatch.setattr(ks, "_probe_kdc_udp", udp)
    monkeypatch.setattr(ks, "_probe_ldap_anon", lambda *a, **k: {"ldap_status": "skipped"})
    rows = ks.scan_kerberos_targets(["kdc.example.com"], timeout=1)
    assert [r.service_detail for r in rows] == ["kerberos-unreachable"]


# --- 230-REVIEW-R3 IN-01: one TCP retry, only after a zero-byte close/reset ---
# Retry rule: retry the TCP probe exactly once, and only when it raised
# KerberosTransportError(answered=False) because the peer closed (EOF) or
# reset the connection before sending any reply byte.  Connect refused,
# connect timeout and a silent-peer reply timeout are NOT retried: each would
# add up to another full timeout to the scan's worst case.


def test_tcp_exchange_zero_byte_close_kind_is_eof():
    result, exc, _ = _exchange(kwh.close_immediately, timeout=1, budget=5)
    assert isinstance(exc, ks.KerberosTransportError)
    assert exc.answered is False and exc.kind == "eof"


def test_tcp_exchange_zero_byte_reset_kind_is_reset():
    """230-REVIEW-R4 WR-03: a real RST before any reply byte maps to
    kind "reset" (retryable), not "error" (straight to UDP)."""
    result, exc, _ = _exchange(kwh.reset_immediately, timeout=1, budget=5)
    assert isinstance(exc, ks.KerberosTransportError), repr(exc)
    assert isinstance(exc.__cause__, (ConnectionResetError, ConnectionAbortedError))
    assert exc.answered is False and exc.kind == "reset"
    # 230-REVIEW-R4 IN-05: zero bytes arrived, so it is not "mid-reply".
    assert "before any reply byte" in str(exc)
    assert "mid-reply" not in str(exc)


def test_tcp_exchange_silent_peer_kind_is_timeout():
    result, exc, _ = _exchange(kwh.silent, timeout=1, budget=5)
    assert isinstance(exc, ks.KerberosTransportError)
    assert exc.answered is False and exc.kind == "timeout"


_PEER = ("192.0.2.88", 88)


def _scan_with_tcp_sequence(monkeypatch, outcomes):
    """``_probe_kdc`` raises/returns each of ``outcomes`` in turn."""
    monkeypatch.setattr(ks, "IMPACKET_AVAILABLE", True)
    tcp_calls = []

    def tcp(*a, **k):
        out = outcomes[len(tcp_calls)]
        tcp_calls.append(1)
        if isinstance(out, BaseException):
            raise out
        return out

    udp_calls = []
    monkeypatch.setattr(ks, "_probe_kdc", tcp)
    monkeypatch.setattr(ks, "_probe_kdc_udp", lambda *a, **k: udp_calls.append(1) or [])
    monkeypatch.setattr(ks, "_probe_ldap_anon", lambda *a, **k: {"ldap_status": "skipped"})
    rows = ks.scan_kerberos_targets(["kdc.example.com"], timeout=1)
    return rows, tcp_calls, udp_calls


@pytest.mark.parametrize("kind", ["eof", "reset"])
def test_zero_byte_drop_is_retried_once_over_tcp(monkeypatch, kind):
    # R4 WR-01: the retry needs time left on the failed attempt's deadline,
    # and (R5 WR-02) the address the failed attempt was connected to.
    drop = ks.KerberosTransportError("dropped", answered=False, kind=kind,
                                     deadline=time.monotonic() + 5, peer=_PEER)
    rows, tcp_calls, udp_calls = _scan_with_tcp_sequence(monkeypatch, [drop, [18]])
    assert tcp_calls == [1, 1]
    assert udp_calls == []
    assert [r.service_detail for r in rows] == ["etype:18:aes256-cts-hmac-sha1-96:SAFE"]


def test_two_zero_byte_drops_fall_back_to_udp(monkeypatch):
    drop = ks.KerberosTransportError("dropped", answered=False, kind="eof",
                                     deadline=time.monotonic() + 5, peer=_PEER)
    rows, tcp_calls, udp_calls = _scan_with_tcp_sequence(monkeypatch, [drop, drop, [18]])
    assert tcp_calls == [1, 1]
    assert udp_calls == [1]


@pytest.mark.parametrize("deadline_left, peer",
                         [(None, _PEER), (-1.0, _PEER), (0.1, _PEER), (5.0, None)],
                         ids=["unknown", "passed", "below-minimum", "peer-unknown"])
def test_zero_byte_drop_without_time_left_is_not_retried(monkeypatch, deadline_left,
                                                          peer):
    """R4 WR-01: no retry when the failed attempt's deadline is unknown,
    passed, or less than MIN_TCP_RETRY_S away; R5 WR-02: none when the
    address it was connected to is unknown.  Straight to UDP."""
    assert ks.MIN_TCP_RETRY_S == 0.25
    deadline = None if deadline_left is None else time.monotonic() + deadline_left
    drop = ks.KerberosTransportError("dropped", answered=False, kind="eof",
                                     deadline=deadline, peer=peer)
    rows, tcp_calls, udp_calls = _scan_with_tcp_sequence(monkeypatch, [drop, [18]])
    assert tcp_calls == [1]
    assert udp_calls == [1]


@pytest.mark.parametrize(
    "exc",
    [
        ConnectionRefusedError("refused"),
        TimeoutError("connect timed out"),
        ks.KerberosTransportError("KDC reply timed out", answered=False, kind="timeout"),
    ],
    ids=["refused", "connect-timeout", "silent-peer"],
)
def test_slow_or_refused_tcp_failure_is_not_retried(monkeypatch, exc):
    rows, tcp_calls, udp_calls = _scan_with_tcp_sequence(monkeypatch, [exc, [18]])
    assert tcp_calls == [1]
    assert udp_calls == [1]


# --- 230-REVIEW-R4 IN-04: _parse_preauth_etypes catches ANY decode failure ---
# The e-data is untrusted bytes; a non-pyasn1 exception while reading it must
# become KerberosPreauthNoEtypes (the honest code-25 row), never escape.
# ks.PyAsn1Error is replaced with a narrow class so that narrowing the
# ``except Exception`` back to ``except PyAsn1Error`` fails here even in CI,
# where impacket/pyasn1 are absent and PyAsn1Error is aliased to Exception.


class _NarrowPyAsn1Error(Exception):
    pass


class _EDataRaises:
    def __init__(self, exc):
        self.exc = exc

    def __getitem__(self, key):
        raise self.exc


class _DecoderRaises:
    def __init__(self, exc):
        self.exc = exc

    def decode(self, *a, **k):
        raise self.exc


@pytest.mark.parametrize("exc", [IndexError("list index out of range"),
                                 KeyError("e-data")], ids=["indexerror", "keyerror"])
@pytest.mark.parametrize("where", ["e-data-access", "decoder"])
def test_parse_preauth_etypes_non_pyasn1_error_is_no_etypes(monkeypatch, exc, where):
    monkeypatch.setattr(ks, "PyAsn1Error", _NarrowPyAsn1Error, raising=False)
    if where == "e-data-access":
        error_pkt = _EDataRaises(exc)
    else:
        monkeypatch.setattr(ks, "decoder", _DecoderRaises(exc), raising=False)
        monkeypatch.setattr(ks, "MethodData", lambda: None, raising=False)
        error_pkt = {"e-data": b"\x30\x00"}
    with pytest.raises(ks.KerberosPreauthNoEtypes) as ei:
        ks._parse_preauth_etypes(error_pkt)
    assert ei.value.__cause__ is exc


# --- 230-REVIEW-R4 WR-01: the retry shares the first attempt's deadline ------
# A zero-byte close that arrives LATE (an idle-closing listener, or a proxy
# whose backend connect timed out) must not buy a second full connect+reply
# budget.  The retry gets only what is left of the first attempt's reply
# deadline, and none at all below MIN_TCP_RETRY_S.  ``_probe_kdc`` is replaced
# by a stand-in that forwards to the REAL transport, so this runs without
# impacket against a real loopback peer.


def _scan_over_loopback(monkeypatch, handler, timeout, budget):
    monkeypatch.setattr(ks, "IMPACKET_AVAILABLE", True)
    listener = kwh.RawPeer(handler)
    tcp_calls = []

    def tcp(host, realm, t, principal=None, port=None, deadline=None, peer=None):
        tcp_calls.append(time.monotonic())
        kw = ({"deadline": deadline, "peer": peer}
              if deadline is not None else {})
        ks._kdc_tcp_exchange("127.0.0.1", listener.port, _REQ, t, **kw)
        return [18]

    udp_calls = []
    monkeypatch.setattr(ks, "_probe_kdc", tcp)
    monkeypatch.setattr(ks, "_probe_kdc_udp", lambda *a, **k: udp_calls.append(1) or [])
    monkeypatch.setattr(ks, "_probe_ldap_anon", lambda *a, **k: {"ldap_status": "skipped"})
    try:
        rows, exc, elapsed = kwh.run_with_watchdog(
            lambda: ks.scan_kerberos_targets(["127.0.0.1"], timeout=timeout),
            budget=budget,
        )
    finally:
        listener.close()
    assert exc is None, repr(exc)
    return rows, tcp_calls, udp_calls, elapsed


def test_late_zero_byte_close_retry_stays_within_one_deadline(monkeypatch):
    # Peer closes 2.5 s into a 4 s deadline.  The retry gets the remaining
    # ~1.5 s, so the TCP leg ends by the ORIGINAL deadline (was ~5.0 s).
    # 230-REVIEW-R5 IN-03: 1.25 s of margin on the retry-happens side
    # (1.5 s left vs MIN_TCP_RETRY_S) and 0.5 s on each side of the bound
    # (~4.0 s now, ~5.0 s with a fresh retry budget, bound 4.5 s); at 2 s /
    # 1.5 s a peer thread waking 0.25 s late skipped the retry.
    rows, tcp_calls, udp_calls, elapsed = _scan_over_loopback(
        monkeypatch, kwh.late_close(2.5), timeout=4, budget=15,
    )
    assert len(tcp_calls) == 2
    assert udp_calls == [1]
    assert elapsed <= 4 + 0.5, f"TCP leg took {elapsed:.2f}s; one deadline is 4s"


def test_zero_byte_close_too_close_to_deadline_is_not_retried(monkeypatch):
    # Peer closes 1.9 s into a 2 s deadline: < MIN_TCP_RETRY_S left, so no
    # retry; straight to UDP (was a second full attempt, ~3.8 s).
    rows, tcp_calls, udp_calls, elapsed = _scan_over_loopback(
        monkeypatch, kwh.late_close(1.9), timeout=2, budget=10,
    )
    assert len(tcp_calls) == 1
    assert udp_calls == [1]
    assert elapsed <= 2 + 0.5


def test_fast_zero_byte_close_is_still_retried_over_real_tcp(monkeypatch):
    rows, tcp_calls, udp_calls, elapsed = _scan_over_loopback(
        monkeypatch, kwh.close_immediately, timeout=2, budget=10,
    )
    assert len(tcp_calls) == 2
    assert udp_calls == [1]
    assert elapsed < 1.5


def test_real_zero_byte_reset_is_retried_once_over_tcp(monkeypatch):
    """230-REVIEW-R4 WR-03: the reset half of the retry rule, over a real
    loopback RST: two TCP attempts, then UDP."""
    rows, tcp_calls, udp_calls, elapsed = _scan_over_loopback(
        monkeypatch, kwh.reset_immediately, timeout=2, budget=10,
    )
    assert len(tcp_calls) == 2
    assert udp_calls == [1]


@pytest.mark.parametrize(
    "exc, expected",
    [
        (ks.KerberosUnrecognisedReply("neither KRB_ERROR nor AS-REP"),
         "complete reply that does not parse"),
        (ks.KerberosTransportError("KDC reply timed out", True, "timeout"),
         "did not finish it before the Kerberos timeout"),
        (ks.KerberosTransportError("closed after 9 of 40", True, "eof"),
         "closed or failed partway through"),
        (ks.KerberosTransportError("reset mid-reply", True, "reset"),
         "closed or failed partway through"),
        (ks.KerberosTransportError("implausible KDC reply length", True, "framing"),
         "length prefix that is not Kerberos TCP framing"),
        (RuntimeError("arbitrary"), "unexpected error"),
    ],
    ids=["unparseable", "mid-reply-timeout", "truncated-eof", "truncated-reset",
         "framing", "unexpected"],
)
def test_unrecognised_row_reason_names_the_cause(monkeypatch, exc, expected):
    """230-REVIEW-R3 IN-02: the reason must not claim "not a Kerberos reply"
    for a reply that was cut off or stalled partway through."""
    import json

    rows, udp_calls = _scan_with_tcp_raising(monkeypatch, exc)
    assert udp_calls == []
    reason = json.loads(rows[0].kerberos_scan_json)["etypes_unavailable_reason"]
    assert expected in reason


def test_unrecognised_reply_row_derives_no_finding_and_no_weak_count():
    from quirk.dashboard.api.routes.scan import _derive_identity_findings
    from quirk.intelligence.evidence import build_evidence_summary

    ep = CryptoEndpoint(
        host="kdc.example.com",
        port=88,
        protocol="KERBEROS",
        cert_pubkey_alg=None,
        service_detail="kerberos-etypes-unavailable-unrecognised-reply",
        scan_error="implausible KDC reply length 1213486160",
        scan_error_category="exception",
    )
    assert _derive_identity_findings([ep]) == []
    assert build_evidence_summary([ep])["identity_weak_etype_count"] == 0


# --- 230-REVIEW-R5 WR-01/WR-02/WR-03: the REAL _probe_kdc -> retry path ------
# The tests above replace ``_probe_kdc`` with a stand-in, so the production
# line that forwards the retry's deadline and peer was never run (R5 WR-03).
# Here only the impacket AS-REQ builders are stubbed (the transport never
# decodes, and every peer below drops before replying), so the real
# ``_probe_kdc`` and ``_kdc_tcp_exchange`` run in CI without impacket.

_BLACKHOLE = "192.0.2.1"  # TEST-NET-1; connects to it are simulated, never sent


def _stub_as_req_builders(monkeypatch):
    import types

    nt = types.SimpleNamespace(value=1)
    consts = types.SimpleNamespace(
        PrincipalNameType=types.SimpleNamespace(NT_PRINCIPAL=nt, NT_SRV_INST=nt),
        ErrorCodes=types.SimpleNamespace(
            KDC_ERR_PREAUTH_REQUIRED=types.SimpleNamespace(value=25),
            KDC_ERR_C_PRINCIPAL_UNKNOWN=types.SimpleNamespace(value=6),
        ),
    )
    monkeypatch.setattr(ks, "constants", consts, raising=False)
    monkeypatch.setattr(ks, "Principal", lambda *a, **k: object(), raising=False)
    monkeypatch.setattr(ks, "_build_as_req", lambda *a, **k: object())
    monkeypatch.setattr(ks, "encoder", types.SimpleNamespace(encode=lambda _: _REQ),
                        raising=False)


class _SocketSpy:
    """Patches ``socket`` so client connects are recorded, sockets created by
    the scanner are checked for ``close()``, ``_BLACKHOLE`` never answers
    (the connect waits out its timeout), and AF_INET6 ``socket()`` can fail
    as on a host with IPv6 disabled."""

    def __init__(self, monkeypatch, gai_for_name, no_ipv6=False, connect_delay=0.0):
        import socket as socket_mod

        real_socket = socket_mod.socket
        real_gai = socket_mod.getaddrinfo
        self.connects = []
        self.client_socks = []
        self.send_timeouts = []
        spy = self

        class Tracked(real_socket):
            def __init__(self, family=-1, type=-1, proto=-1, fileno=None):
                if fileno is None and no_ipv6 and family == socket_mod.AF_INET6:
                    raise OSError(97, "Address family not supported by protocol")
                super().__init__(family, type, proto, fileno)
                self.closed_by_close = False
                if fileno is None:  # accept() passes fileno: server side
                    spy.client_socks.append(self)

            def connect(self, addr):
                spy.connects.append(tuple(addr[:2]))
                if addr[0] == _BLACKHOLE:
                    time.sleep(self.gettimeout() or 0)
                    raise socket_mod.timeout("timed out")
                time.sleep(connect_delay)
                return super().connect(addr)

            def sendall(self, data, *a):
                if is_client(self):
                    spy.send_timeouts.append(self.gettimeout())
                return super().sendall(data, *a)

            def close(self):
                self.closed_by_close = True
                return super().close()

        def is_client(sock):
            return any(sock is c for c in spy.client_socks)

        def gai(host, port, *a, **k):
            if host in gai_for_name:
                return gai_for_name[host](port)
            return real_gai(host, port, *a, **k)

        monkeypatch.setattr(socket_mod, "socket", Tracked)
        monkeypatch.setattr(socket_mod, "getaddrinfo", gai)

    def assert_all_closed(self):
        leaked = [s for s in self.client_socks if not s.closed_by_close]
        assert not leaked, f"{len(leaked)} scanner socket(s) never closed: {leaked}"


def _v4(port, host="127.0.0.1"):
    import socket as socket_mod
    return (socket_mod.AF_INET, socket_mod.SOCK_STREAM, 6, "", (host, port))


def _real_probe_scan(monkeypatch, handler, timeout, budget, gai_for_name=None,
                     no_ipv6=False, target="127.0.0.1"):
    """Scan ``target`` through the REAL ``_probe_kdc`` against a loopback peer."""
    monkeypatch.setattr(ks, "IMPACKET_AVAILABLE", True)
    _stub_as_req_builders(monkeypatch)
    conns = []

    def counting(c, stop):
        conns.append(time.monotonic())
        handler(c, stop)

    peer = kwh.RawPeer(counting)
    monkeypatch.setattr(ks, "KDC_PORT", peer.port)
    udp_calls = []
    monkeypatch.setattr(ks, "_probe_kdc_udp", lambda *a, **k: udp_calls.append(1) or [])
    monkeypatch.setattr(ks, "_probe_ldap_anon", lambda *a, **k: {"ldap_status": "skipped"})
    spy = _SocketSpy(monkeypatch, gai_for_name or {}, no_ipv6=no_ipv6)
    try:
        rows, exc, elapsed = kwh.run_with_watchdog(
            lambda: ks.scan_kerberos_targets([target], timeout=timeout),
            budget=budget,
        )
    finally:
        peer.close()
    assert exc is None, repr(exc)
    return rows, conns, udp_calls, elapsed, spy, peer.port


def test_real_probe_late_close_retry_stays_within_one_deadline(monkeypatch):
    """R5 WR-03: through the real ``_probe_kdc``.  The peer closes 2.5 s into
    a 4 s deadline; the retry gets the remaining ~1.5 s for its connect AND
    reply, so the TCP leg ends by the original deadline.  If ``_probe_kdc``
    stops forwarding the retry's deadline, the retry gets a fresh 4 s and the
    leg takes ~5 s."""
    rows, conns, udp_calls, elapsed, spy, port = _real_probe_scan(
        monkeypatch, kwh.late_close(2.5), timeout=4, budget=15,
    )
    assert len(conns) == 2, conns
    assert spy.connects == [("127.0.0.1", port)] * 2
    assert udp_calls == [1]
    assert elapsed <= 4 + 0.5, f"TCP leg took {elapsed:.2f}s; one deadline is 4s"
    spy.assert_all_closed()


def test_real_probe_retry_targets_the_address_that_answered(monkeypatch):
    """R5 WR-02: the name resolves to an unresponsive address first.  The
    first attempt waits it out, connects to the second, and is dropped.  The
    retry must go straight to the address that answered, not start over at
    the unresponsive one and spend its whole remaining time there."""
    gai = {"kdc.example.com": lambda p: [_v4(p, _BLACKHOLE), _v4(p)]}
    rows, conns, udp_calls, elapsed, spy, port = _real_probe_scan(
        monkeypatch, kwh.close_immediately, timeout=1.5, budget=15,
        gai_for_name=gai, target="kdc.example.com",
    )
    assert spy.connects == [(_BLACKHOLE, port), ("127.0.0.1", port),
                            ("127.0.0.1", port)]
    assert len(conns) == 2, conns
    assert udp_calls == [1]
    spy.assert_all_closed()


def test_real_probe_retry_survives_a_family_whose_socket_fails(monkeypatch):
    """R5 WR-01: the name resolves to ::1 first on a host where AF_INET6
    ``socket()`` fails.  The first attempt falls through to IPv4; the retry
    must reach the same IPv4 address, not stop at the failing family."""
    import socket as socket_mod

    def v6_then_v4(p):
        return [(socket_mod.AF_INET6, socket_mod.SOCK_STREAM, 6, "", ("::1", p, 0, 0)),
                _v4(p)]

    rows, conns, udp_calls, elapsed, spy, port = _real_probe_scan(
        monkeypatch, kwh.close_immediately, timeout=2, budget=15,
        gai_for_name={"kdc.example.com": v6_then_v4}, no_ipv6=True,
        target="kdc.example.com",
    )
    assert len(conns) == 2, conns
    assert udp_calls == [1]
    spy.assert_all_closed()


# --- 230-REVIEW-R5: the retry exchange itself (CI-visible, no impacket) ------


def test_tcp_exchange_records_the_connected_peer():
    """The failed attempt carries the address it was connected to, which is
    the only address the retry may use (R5 WR-02)."""
    peer = kwh.RawPeer(kwh.close_immediately)
    try:
        _, exc, _ = kwh.run_with_watchdog(
            lambda: ks._kdc_tcp_exchange("127.0.0.1", peer.port, _REQ, 1), budget=5,
        )
    finally:
        peer.close()
    assert isinstance(exc, ks.KerberosTransportError) and exc.kind == "eof"
    assert tuple(exc.peer[:2]) == ("127.0.0.1", peer.port)


def test_retry_exchange_uses_only_the_recorded_peer(monkeypatch):
    """The retry ignores ``host``/``port`` (no re-resolution of the name) and
    makes exactly one connect, to the recorded peer, closing its socket."""
    peer = kwh.RawPeer(kwh.framed(b"reply-body"))
    spy = _SocketSpy(monkeypatch, {})
    try:
        result, exc, _ = kwh.run_with_watchdog(
            lambda: ks._kdc_tcp_exchange(
                "unresolvable.invalid", 1, _REQ, 2,
                deadline=time.monotonic() + 2, peer=("127.0.0.1", peer.port),
            ),
            budget=6,
        )
    finally:
        peer.close()
    assert exc is None, repr(exc)
    assert result == b"reply-body"
    assert spy.connects == [("127.0.0.1", peer.port)]
    spy.assert_all_closed()


def test_retry_exchange_without_peer_is_a_plain_oserror():
    """R5 IN-02: an unknown peer is reported as exactly that (and routes like
    a failed connect), not as a deadline that ran out."""
    with pytest.raises(OSError) as ei:
        ks._kdc_tcp_exchange("127.0.0.1", 1, _REQ, 2,
                             deadline=time.monotonic() + 2, peer=None)
    assert not isinstance(ei.value, ks.KerberosTransportError)
    assert "no recorded KDC peer address" in str(ei.value)


def test_retry_exchange_with_no_time_left_does_not_connect(monkeypatch):
    spy = _SocketSpy(monkeypatch, {})
    with pytest.raises(OSError) as ei:
        ks._kdc_tcp_exchange("127.0.0.1", 1, _REQ, 2,
                             deadline=time.monotonic() - 0.01,
                             peer=("127.0.0.1", 1))
    assert "no time left before the Kerberos deadline to connect" in str(ei.value)
    assert spy.connects == []


def test_retry_send_gets_only_the_time_left_after_connect(monkeypatch):
    """R5 IN-01: the send timeout is what is left after the connect, not the
    timeout set before it, so the send cannot run past the deadline."""
    peer = kwh.RawPeer(kwh.framed(b"reply-body"))
    spy = _SocketSpy(monkeypatch, {}, connect_delay=0.6)
    try:
        result, exc, _ = kwh.run_with_watchdog(
            lambda: ks._kdc_tcp_exchange(
                "127.0.0.1", peer.port, _REQ, 1.5,
                deadline=time.monotonic() + 1.5, peer=("127.0.0.1", peer.port),
            ),
            budget=6,
        )
    finally:
        peer.close()
    assert exc is None, repr(exc)
    assert len(spy.send_timeouts) == 1
    assert spy.send_timeouts[0] <= 1.5 - 0.6 + 0.05, spy.send_timeouts
