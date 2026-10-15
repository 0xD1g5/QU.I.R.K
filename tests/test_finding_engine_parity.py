"""RVW-002: the dashboard and the report must not disagree about findings.

`quirk/dashboard/api/routes/scan.py::_derive_findings()` is a second, hand-rolled
finding engine, independent of `quirk/engine/findings_evaluator.py` which produces
the client-facing report. They drifted: the dashboard escalated a sub-2048 RSA key
to CRITICAL where the report calls it HIGH, and it had no self-signed or
untrusted-CA detection at all.

The consultant's report and the operator's console describing the same endpoint
differently is the defect — whichever surface is "right", they cannot both be.

These tests run both engines over one fixed endpoint set and compare. They are
deliberately condition-scoped rather than exhaustive: the dashboard legitimately
emits rows the report does not (per-endpoint `id`, `sensor_id`, `segment`
plumbing) and vice versa. What must agree is the severity and title of a
condition BOTH engines detect.
"""
from __future__ import annotations

import datetime
from types import SimpleNamespace

import pytest

from quirk.dashboard.api.routes.scan import _derive_findings
from quirk.engine.findings_evaluator import evaluate_endpoints
from quirk.models import CryptoEndpoint
from quirk.ticketing.base import TicketingChannel


def _cfg():
    return SimpleNamespace(scan=SimpleNamespace(ports_tls=[443, 8443]))


def _ep(**kw):
    base = dict(
        id=1, host="10.0.0.1", port=443, protocol="TLS",
        scanned_at=datetime.datetime(2026, 8, 25, 12, 0, 0),
    )
    base.update(kw)
    return CryptoEndpoint(**base)


# One endpoint per condition both engines are expected to detect.
_PAST = datetime.datetime(2020, 1, 1)
_FUTURE = datetime.datetime(2030, 1, 1)

_UNDERSIZED_RSA = _ep(
    id=1, host="10.0.0.1", cert_pubkey_alg="RSA", cert_pubkey_size=1024,
    cert_subject="CN=a.example", cert_issuer="CN=Real CA",
    cert_not_before=_PAST, cert_not_after=_FUTURE,
)
_SELF_SIGNED = _ep(
    id=2, host="10.0.0.2", cert_pubkey_alg="RSA", cert_pubkey_size=4096,
    cert_subject="CN=self.example", cert_issuer="CN=self.example",
    cert_not_before=_PAST, cert_not_after=_FUTURE,
)
_EXPIRED = _ep(
    id=3, host="10.0.0.3", cert_pubkey_alg="RSA", cert_pubkey_size=4096,
    cert_subject="CN=old.example", cert_issuer="CN=Real CA",
    cert_not_before=_PAST, cert_not_after=_PAST,
)

# Phase 228 D-01: near-expiry uses the wall clock (both generators do).
_NEAR_EXPIRY = _ep(
    id=4, host="10.0.0.4", cert_pubkey_alg="RSA", cert_pubkey_size=4096,
    cert_subject="CN=soon.example", cert_issuer="CN=Real CA",
    cert_not_before=_PAST,
    cert_not_after=datetime.datetime.now() + datetime.timedelta(days=10),
)

_ALL = [_UNDERSIZED_RSA, _SELF_SIGNED, _EXPIRED, _NEAR_EXPIRY]

# IDENT-03: the three conditions both derivation paths are expected to detect,
# named by (host, report_needle, dashboard_needle) so each side's title can be
# resolved independently even where wording diverges (see 10.0.0.3 below).
_SHARED_CONDITION_NEEDLES = [
    ("10.0.0.1", "undersized RSA", "undersized RSA"),
    ("10.0.0.2", "self-signed", "self-signed"),
    ("10.0.0.3", "expired", "expired"),
    ("10.0.0.4", "expiring", "expiring"),
]

# IDENT-03: known, bounded identity divergences between the report and
# dashboard derivation paths. Each entry is a (report_title, dashboard_title)
# pair whose fingerprints differ today by design, not by accident. Adding an
# entry here without a corresponding section in
# docs/reviews/178-derivation-path-divergence.md (and vice versa) is a drift
# `test_no_unbounded_identity_divergence` is built to catch.
_KNOWN_IDENTITY_DIVERGENCES = frozenset(
    [
        # D-178-A — docs/reviews/178-derivation-path-divergence.md
        # Same condition (expired cert, 10.0.0.3:443), two fixed-string
        # titles. Bounded, not fixed, per CONTEXT.md decision 12.
        ("TLS certificate expired", "Certificate expired"),
    ]
)


def _is_known_divergence(report_title, dash_title):
    """D-178-A exact pairs, plus D-178-C (Phase 228): the near-expiry dashboard
    title embeds a day count (so it cannot be an exact allowlist pair) and D-02
    forbids changing it. Bounded in docs/reviews/178-derivation-path-divergence.md."""
    if (report_title, dash_title) in _KNOWN_IDENTITY_DIVERGENCES:
        return True
    return (report_title == "TLS certificate expiring within 30 days"
            and dash_title.startswith("Certificate expiring in "))


def _report_titles():
    return {
        (f["host"], f["port"], f["title"]): f["severity"]
        for f in evaluate_endpoints(_cfg(), _ALL)
    }


def _dashboard_titles():
    return {
        (f.host, f.port, f.title): f.severity
        for f in _derive_findings(_ALL)
    }


def _severity_for(mapping, host, needle):
    """Severity of the single finding on `host` whose title contains `needle`."""
    hits = [(k, v) for k, v in mapping.items() if k[0] == host and needle.lower() in k[2].lower()]
    return hits[0][1] if hits else None


def _title_for(mapping, host, needle):
    """Title of the single finding on `host` whose title contains `needle`."""
    hits = [k[2] for k in mapping if k[0] == host and needle.lower() in k[2].lower()]
    return hits[0] if hits else None


class TestSeverityParity:
    def test_undersized_rsa_severity_agrees(self):
        """The dashboard escalated this to CRITICAL; the report calls it HIGH."""
        report = _severity_for(_report_titles(), "10.0.0.1", "undersized RSA")
        dash = _severity_for(_dashboard_titles(), "10.0.0.1", "RSA")
        assert report is not None, "report engine did not flag the 1024-bit key"
        assert dash is not None, "dashboard did not flag the 1024-bit key"
        assert dash == report, (
            f"RVW-002: dashboard says {dash} for a sub-2048 RSA key, report says "
            f"{report}. The operator console and the client deliverable cannot "
            f"disagree about severity."
        )

    def test_expired_certificate_severity_agrees(self):
        report = _severity_for(_report_titles(), "10.0.0.3", "expired")
        dash = _severity_for(_dashboard_titles(), "10.0.0.3", "expired")
        assert report is not None and dash is not None, "expired cert not flagged by both"
        assert dash == report, (
            f"RVW-002: expired-certificate severity differs — dashboard {dash}, "
            f"report {report}"
        )


class TestDetectionParity:
    def test_dashboard_detects_self_signed_certificates(self):
        """The report has had this detection since TLS-FIND-02; the dashboard did not,
        so an operator triaging in the console simply never saw it."""
        dash = _severity_for(_dashboard_titles(), "10.0.0.2", "self-signed")
        assert dash is not None, (
            "RVW-002: the dashboard has no self-signed certificate detection — "
            "the report flags this endpoint and the console shows nothing"
        )

    def test_self_signed_severity_agrees(self):
        report = _severity_for(_report_titles(), "10.0.0.2", "self-signed")
        dash = _severity_for(_dashboard_titles(), "10.0.0.2", "self-signed")
        assert report is not None, "report engine did not flag the self-signed cert"
        assert dash == report, (
            f"RVW-002: self-signed severity differs — dashboard {dash}, report {report}"
        )

    def test_self_signed_does_not_also_emit_untrusted_ca(self):
        """D-04 mutual exclusivity — a self-signed cert must not also be reported
        as untrusted-CA. Whatever the dashboard adds must honour that too."""
        dash = _dashboard_titles()
        for (host, _port, title) in dash:
            if host == "10.0.0.2":
                assert "untrusted ca" not in title.lower(), (
                    f"RVW-002/D-04: self-signed endpoint also reported as "
                    f"untrusted-CA ({title!r})"
                )


def test_no_shared_condition_diverges_in_severity():
    """Catch-all: any (host, port, title) both engines emit must carry the same
    severity. This is the guard that keeps the two surfaces from drifting again."""
    report = _report_titles()
    dash = _dashboard_titles()
    shared = set(report) & set(dash)
    mismatched = {k: (dash[k], report[k]) for k in shared if dash[k] != report[k]}
    assert not mismatched, (
        f"RVW-002: {len(mismatched)} finding(s) carry different severities on the "
        f"dashboard vs the report: "
        + "; ".join(f"{k[2]!r} dashboard={d} report={r}" for k, (d, r) in mismatched.items())
    )


class TestIdentityParity:
    """IDENT-03: the two derivation paths must agree on finding IDENTITY, not full
    field parity. Identity means `TicketingChannel.compute_fingerprint` produces the
    same value from both paths for the same underlying condition. Full field parity
    (matching every attribute of a finding) would be the RVW-002 merge wearing a
    disguise — that refactor stays excluded (v5.16). Where the two paths genuinely
    diverge on identity, the divergence is enumerated in
    docs/reviews/178-derivation-path-divergence.md and allowlisted below, not
    silently reconciled.
    """

    def test_shared_condition_titles_yield_identical_fingerprints(self):
        """The two AGREEING conditions must already fingerprint identically —
        proven at the fingerprint layer, not just by string equality."""
        report = _report_titles()
        dash = _dashboard_titles()
        for host, report_needle, dash_needle in _SHARED_CONDITION_NEEDLES:
            report_title = _title_for(report, host, report_needle)
            dash_title = _title_for(dash, host, dash_needle)
            if report_title is None or dash_title is None:
                continue
            if _is_known_divergence(report_title, dash_title):
                continue
            report_fp = TicketingChannel.compute_fingerprint(
                {"host": host, "port": 443, "title": report_title}
            )
            dash_fp = TicketingChannel.compute_fingerprint(
                {"host": host, "port": 443, "title": dash_title}
            )
            assert report_fp == dash_fp, (
                f"IDENT-03: {host} report title {report_title!r} and dashboard "
                f"title {dash_title!r} produce different fingerprints, and this "
                f"pair is not in _KNOWN_IDENTITY_DIVERGENCES"
            )

    def test_expired_certificate_divergence_is_bounded_not_silent(self):
        """D-178-A: this documents reality, it does not demand a fix. The
        expired-certificate condition at 10.0.0.3:443 fingerprints differently
        across the two paths, and that divergence is bounded in writing."""
        report = _report_titles()
        dash = _dashboard_titles()
        report_title = _title_for(report, "10.0.0.3", "expired")
        dash_title = _title_for(dash, "10.0.0.3", "expired")
        assert report_title == "TLS certificate expired"
        assert dash_title == "Certificate expired"
        report_fp = TicketingChannel.compute_fingerprint(
            {"host": "10.0.0.3", "port": 443, "title": report_title}
        )
        dash_fp = TicketingChannel.compute_fingerprint(
            {"host": "10.0.0.3", "port": 443, "title": dash_title}
        )
        assert report_fp != dash_fp, (
            "IDENT-03: expired-certificate titles now fingerprint identically — "
            "if this is intentional, remove the D-178-A allowlist entry and "
            "update docs/reviews/178-derivation-path-divergence.md"
        )
        assert (report_title, dash_title) in _KNOWN_IDENTITY_DIVERGENCES, (
            f"IDENT-03: {(report_title, dash_title)} diverges but is not in "
            f"_KNOWN_IDENTITY_DIVERGENCES — see "
            f"docs/reviews/178-derivation-path-divergence.md D-178-A"
        )

    def test_no_unbounded_identity_divergence(self):
        """Catch-all: any shared condition whose fingerprints differ across the
        two paths MUST be on the allowlist, or this fails. This is the guard
        that makes a NEW, unbounded divergence loud instead of silent."""
        report = _report_titles()
        dash = _dashboard_titles()
        unbounded = []
        for host, report_needle, dash_needle in _SHARED_CONDITION_NEEDLES:
            report_title = _title_for(report, host, report_needle)
            dash_title = _title_for(dash, host, dash_needle)
            if report_title is None or dash_title is None:
                continue
            report_fp = TicketingChannel.compute_fingerprint(
                {"host": host, "port": 443, "title": report_title}
            )
            dash_fp = TicketingChannel.compute_fingerprint(
                {"host": host, "port": 443, "title": dash_title}
            )
            if report_fp == dash_fp:
                continue
            if not _is_known_divergence(report_title, dash_title):
                unbounded.append((host, report_title, dash_title))
        assert not unbounded, (
            "IDENT-03: unbounded identity divergence(s) found — add to "
            "_KNOWN_IDENTITY_DIVERGENCES and "
            "docs/reviews/178-derivation-path-divergence.md, or fix the "
            f"underlying titles: {unbounded}"
        )


# --- Phase 228 (XSURF-05 / XSURF-06) -------------------------------------

import ast
from pathlib import Path

from quirk.dashboard.api.routes.scan import findings_for_endpoint
from quirk.scanner.jwt_scanner import ADVISORY_JWKS_VERIFY_DISABLED

_REPO = Path(__file__).resolve().parent.parent


def test_near_expiry_is_medium_on_both_surfaces():
    """D-01: within 30 days is MEDIUM on dashboard and report; expired stays CRITICAL."""
    report = _severity_for(_report_titles(), "10.0.0.4", "expiring")
    dash = _severity_for(_dashboard_titles(), "10.0.0.4", "expiring")
    assert report == "MEDIUM"
    assert dash == "MEDIUM"
    assert _severity_for(_dashboard_titles(), "10.0.0.3", "expired") == "CRITICAL"


_NON_TLS_PROTOCOLS = [
    "SMTP-STARTTLS", "SMTPS", "IMAPS", "POP3S", "KAFKA-TLS", "AMQPS",
    "REDIS-TLS", "CODE_SIGNING", "SMIME", "ADCS", "VAULT", "AWS", "AZURE",
    "AZURE_BLOB", "GCP", "CLOUD_SQL", "JWT", "OPENAPI", "ZZZ-UNKNOWN",
]

_TLS_TITLE_PREFIXES = (
    "Legacy TLS version", "Weak cipher suites enabled", "Certificate expired",
    "Certificate expiring in", "TLS certificate uses undersized RSA key",
    "TLS certificate is self-signed", "TLS certificate issued by untrusted CA",
    "Quantum-",
)


def _tls_shaped_row(protocol):
    return _ep(
        id=50, host="10.9.9.9", port=9999, protocol=protocol,
        tls_version="TLSv1", tls_weak_ciphers_present=True,
        cert_pubkey_alg="RSA", cert_pubkey_size=1024,
        cert_subject="CN=x.example", cert_issuer="CN=x.example",
        cert_not_before=_PAST,
        cert_not_after=datetime.datetime.now() + datetime.timedelta(days=10),
    )


@pytest.mark.parametrize("protocol", _NON_TLS_PROTOCOLS)
def test_non_tls_rows_get_no_tls_certificate_findings(protocol):
    titles = [f.title for f in findings_for_endpoint(_tls_shaped_row(protocol))]
    bad = [t for t in titles if t.startswith(_TLS_TITLE_PREFIXES)]
    assert not bad, f"D-05: {protocol} row got TLS/cert findings {bad}"


def test_tls_row_still_gets_tls_certificate_findings():
    titles = [f.title for f in findings_for_endpoint(_tls_shaped_row("TLS"))]
    for prefix in ("Legacy TLS version", "Weak cipher suites enabled",
                   "Certificate expiring in", "TLS certificate uses undersized RSA key",
                   "TLS certificate is self-signed"):
        assert any(t.startswith(prefix) for t in titles), (prefix, titles)


def test_jwks_and_http_blocks_are_ungated():
    jwks = _ep(id=60, host="10.8.8.8", port=443, protocol="ADVISORY",
               service_detail=ADVISORY_JWKS_VERIFY_DISABLED)
    http = _ep(id=61, host="10.8.8.9", port=80, protocol="HTTP")
    assert findings_for_endpoint(jwks), "JWKS advisory finding lost"
    assert any(f.title == "Unencrypted HTTP service" for f in findings_for_endpoint(http))


def _func_node(path, name):
    tree = ast.parse((_REPO / path).read_text())
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError(f"{name} not found in {path}")


def _is_bare_tls_compare(test):
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)):
        return False
    consts = [c for c in [test.left, *test.comparators]
              if isinstance(c, ast.Constant) and c.value == "TLS"]
    return bool(consts)


def test_both_pipelines_call_the_shared_tls_predicate():
    for path, name in (
        ("quirk/dashboard/api/routes/scan.py", "findings_for_endpoint"),
        ("quirk/engine/findings_evaluator.py", "evaluate_endpoints"),
    ):
        fn = _func_node(path, name)
        calls = [
            c for c in ast.walk(fn)
            if isinstance(c, ast.Call)
            and getattr(c.func, "id", getattr(c.func, "attr", None)) == "runs_tls_certificate_checks"
        ]
        assert calls, f"{name} must call runs_tls_certificate_checks"
        inline = [n for n in ast.walk(fn)
                  if isinstance(n, ast.If) and _is_bare_tls_compare(n.test)]
        assert not inline, f"{name} has an inline copy of the TLS gate"
