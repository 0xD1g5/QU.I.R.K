"""Regression tests for TRIAGE-176-02 (Phase 186 plan 03).

`_postprocess_findings` used to relabel every "Plaintext HTTP service detected"
finding as "HTTP on TLS-designated port" whenever the port appeared in
`cfg.scan.ports_tls`. Per Phase 186 D-07, `ports_tls` is not a TLS-designation
signal at all -- it is the scan-target port set (the ports the scanner was told
to *probe*), populated by `nmap_provider.py` and `interactive.py`'s
`CONSULTING_TLS_PORTS`. Reading it here meant "we scanned this port", so any
plaintext-HTTP finding on any scanned port -- including deliberately-plaintext
ports like 8000 -- got relabelled as a TLS misconfiguration.

Per Phase 186 D-08, the classifier now derives "TLS-designated" from
`quirk.util.ports.WELL_KNOWN_TLS_PORTS` (a fixed well-known-port default)
UNIONED with the operator-controlled `cfg.scan.tls_designated_ports` override.
An earlier variant of D-08 considered a derived-set-only design with no
operator override; that variant was SUPERSEDED because it could not reproduce
UAT-6-07's currently-passing behavior for port 8444 (not a well-known TLS
port) without an explicit escape hatch. `test_explicit_override_rewrites_8444`
below is therefore not optional -- it is the only test in this file that
proves the override half of D-08 was actually wired into the classifier
rather than merely documented in CONTEXT.md.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from quirk.engine.findings_evaluator import evaluate_endpoints


def _cfg(ports_tls, tls_designated_ports):
    """Config stub with BOTH TLS-port fields explicitly set.

    CRITICAL fixture hazard (per plan 186-03 <action>): a bare MagicMock()
    with no spec= auto-vivifies unset attributes as truthy child MagicMock
    instances instead of raising or returning a default. If
    tls_designated_ports were left unset here, `getattr(cfg.scan,
    "tls_designated_ports", [])` would silently return a MagicMock rather
    than `[]`, and `port in <MagicMock>` would behave unpredictably. Every
    fixture in this file sets both fields explicitly -- never relies on the
    MagicMock default.
    """
    cfg = MagicMock()
    cfg.scan.ports_tls = ports_tls
    cfg.scan.tls_designated_ports = tls_designated_ports
    return cfg


def _http_ep(port):
    return SimpleNamespace(host="10.0.0.1", port=port, protocol="HTTP", scan_error=None)


def _title_for(findings, port):
    matches = [f for f in findings if f.get("port") == port]
    assert matches, f"No finding produced for port {port}: {findings}"
    return matches[0]["title"]


def test_plaintext_http_not_rewritten_on_ordinary_port():
    """Port 80 is in the scan-target set (ports_tls) but is NOT a
    TLS-designated port. Per D-07, ports_tls alone must no longer drive the
    rewrite -- the title must stay 'Plaintext HTTP service detected'."""
    cfg = _cfg(ports_tls=[80], tls_designated_ports=[])
    findings = evaluate_endpoints(cfg, [_http_ep(80)])
    assert _title_for(findings, 80) == "Plaintext HTTP service detected"


def test_http_on_well_known_tls_port_rewritten():
    """Port 443 is a well-known TLS port (WELL_KNOWN_TLS_PORTS). The derived
    default must fire even with no scan-target hint and no operator
    override."""
    cfg = _cfg(ports_tls=[], tls_designated_ports=[])
    findings = evaluate_endpoints(cfg, [_http_ep(443)])
    assert _title_for(findings, 443) == "HTTP on TLS-designated port"


def test_explicit_override_rewrites_8444():
    """8444 is NOT a well-known TLS port. This is the load-bearing case for
    D-08: the ONLY way to reach 'HTTP on TLS-designated port' for 8444 is the
    explicit cfg.scan.tls_designated_ports override -- the regression guard
    for UAT-6-07's current PASS."""
    cfg = _cfg(ports_tls=[], tls_designated_ports=[8444])
    findings = evaluate_endpoints(cfg, [_http_ep(8444)])
    assert _title_for(findings, 8444) == "HTTP on TLS-designated port"
