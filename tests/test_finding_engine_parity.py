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

_ALL = [_UNDERSIZED_RSA, _SELF_SIGNED, _EXPIRED]


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
