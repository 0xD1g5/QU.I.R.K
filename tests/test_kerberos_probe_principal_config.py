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
    ],
    ids=["refused", "connect-timeout", "no-reply-byte"],
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


def test_tcp_exchange_silent_peer_kind_is_timeout():
    result, exc, _ = _exchange(kwh.silent, timeout=1, budget=5)
    assert isinstance(exc, ks.KerberosTransportError)
    assert exc.answered is False and exc.kind == "timeout"


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
    drop = ks.KerberosTransportError("dropped", answered=False, kind=kind)
    rows, tcp_calls, udp_calls = _scan_with_tcp_sequence(monkeypatch, [drop, [18]])
    assert tcp_calls == [1, 1]
    assert udp_calls == []
    assert [r.service_detail for r in rows] == ["etype:18:aes256-cts-hmac-sha1-96:SAFE"]


def test_two_zero_byte_drops_fall_back_to_udp(monkeypatch):
    drop = ks.KerberosTransportError("dropped", answered=False, kind="eof")
    rows, tcp_calls, udp_calls = _scan_with_tcp_sequence(monkeypatch, [drop, drop, [18]])
    assert tcp_calls == [1, 1]
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
