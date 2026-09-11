"""Phase 200 / RPT-02 — SSTI containment go/no-go gate.

This file is the phase's internal GO/NO-GO gate (ROADMAP criterion 2). It proves
two things through the REAL `write_reports` pipeline (never `env.from_string`,
so the assertion is about the production Jinja2 environment, not an isolated
sandbox instance):

1. Override/fallback/backward-compat behavior: an operator-supplied
   `report.html.j2` in `cfg.report.template_dir` is rendered instead of the
   packaged template; the packaged template is still used when no override is
   present (or when `cfg.report` does not exist at all — pre-Phase-200 cfgs
   must render unchanged).
2. SSTI containment: every payload in `CANONICAL_SSTI_PAYLOADS`, when embedded
   in an operator-supplied override template and rendered through the real
   pipeline, must either raise `jinja2.sandbox.SecurityError` OR produce HTML
   that contains none of `SENSITIVE_MARKERS`.

Per-payload assertion rationale (RESEARCH §Jinja2 3.1.6 SandboxedEnvironment,
empirically verified this session): under `SandboxedEnvironment` on jinja2
3.1.6, some payloads (e.g. `''.__class__.__bases__[0].__subclasses__()`) raise
`SecurityError` because they touch an unsafe *method call*. Others (e.g.
`{{ {}.__class__ }}`) are leaf *attribute* accesses that the sandbox silently
renders as an empty string rather than raising — `getattr` on an unsafe name
returns `Undefined`, which stringifies to `""`. A test that asserted
`pytest.raises(SecurityError)` as the SOLE pass condition would therefore be
WRONG for this payload class: it would never fail today, but it would also
never catch a REAL leak, because a leak looks exactly like "no exception,
attacker-controlled text in the output" — which is indistinguishable from the
already-passing empty-render case unless the output is also checked for
sensitive markers. Hence every SSTI leg accepts EITHER outcome and asserts on
markers, not on the exception's mere presence/absence.
"""
from __future__ import annotations

import glob
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from jinja2.sandbox import SecurityError

# ---------------------------------------------------------------------------
# Fixtures / helpers (copied from tests/test_report_injection_hardening.py;
# extended with a pinned `report` attribute — Pitfall 6, spec-mock
# auto-vivify trap — and an optional template_dir argument.)
# ---------------------------------------------------------------------------

PACKAGED_MARKER = "Endpoint Inventory"  # a string unique to the packaged report.html.j2
OVERRIDE_MARKER = "PHASE-200-OVERRIDE-MARKER-6f2b1e"

XSS_PAYLOAD = "<script>alert(1)</script>"


def _make_cfg(tmp_path, template_dir=None, no_report_section=False):
    """Build the standard write_reports cfg fixture.

    template_dir=None -> cfg.report present with template_dir=None (today's
    default rendering path). no_report_section=True -> cfg has NO `report`
    attribute at all (pre-Phase-200 backward-compat leg); template_dir is
    ignored in that case.
    """
    kwargs = dict(
        output=SimpleNamespace(directory=str(tmp_path)),
        assessment=SimpleNamespace(
            name="Phase 200 RPT-02 Sandbox Gate",
            report_owner="Test Owner",
            data_classification="Internal",
            timezone="UTC",
        ),
        intelligence=SimpleNamespace(profile="balanced", calibration_overrides=None),
    )
    if not no_report_section:
        kwargs["report"] = SimpleNamespace(template_dir=template_dir)
    return SimpleNamespace(**kwargs)


def _stub_evidence(endpoints, findings):
    return {
        "total_endpoints": len(endpoints),
        "tls_endpoints": len(endpoints),
        "ssh_endpoints": 0,
        "http_endpoints": 0,
        "expired_certs": 0,
        "expiring_soon_certs": 0,
        "weak_ciphers": 0,
        "vulns_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
        "findings_count": len(findings or []),
        "scan_error_rate": 0.0,
    }


def _stub_score(evidence, **kwargs):
    return {
        "score": 55,
        "subscores": {"inventory": 50, "cipher": 50, "certificate": 50, "protocol": 50},
        "drivers": [{"reason": "Test driver", "impact": -5}],
    }


def _stub_confidence(evidence):
    return {"confidence_score": 70, "factor_breakdown": {}}


def _stub_roadmap(evidence, score):
    return {
        "items": [
            {"title": "Test Action", "why": "Because testing", "timeframe": "NOW"},
        ]
    }


def _stub_waves(findings):
    return {"Wave 1": [], "Wave 2": [], "Wave 3": []}


def _patches():
    """Standard intelligence-pipeline patches for write_reports (same set
    used by tests/test_report_injection_hardening.py / test_reports_writer.py)."""
    return (
        patch("quirk.reports.writer.categorize_waves", side_effect=_stub_waves),
        patch("quirk.reports.writer.build_phased_roadmap", side_effect=_stub_roadmap),
        patch("quirk.reports.writer.compute_confidence", side_effect=_stub_confidence),
        patch("quirk.reports.writer.compute_readiness_score", side_effect=_stub_score),
        patch("quirk.reports.writer.build_evidence_summary", side_effect=_stub_evidence),
        # Phase 200 close-out: patch the PDF leg at the writer seam. These
        # tests assert HTML/CLI content only — reaching sync_playwright()
        # in-suite is the TRIAGE-149 order-pollution class (asyncio-loop
        # state left by earlier full-suite tests), and skipping the leg
        # here keeps the tests deterministic in any collection order.
        patch("quirk.reports.writer.render_pdf_report", return_value=False),
    )


def _run_write_reports(tmp_path, template_dir=None, no_report_section=False):
    """Run write_reports through the real pipeline; return the rendered HTML
    contents as a single string. Never uses env.from_string — this proves the
    PRODUCTION env (constructed inside html_renderer.render_html_report) is
    the one under test."""
    from quirk.reports.writer import write_reports

    cfg = _make_cfg(tmp_path, template_dir=template_dir, no_report_section=no_report_section)
    endpoints = []
    findings = []
    p1, p2, p3, p4, p5, p6 = _patches()
    with p1, p2, p3, p4, p5, p6:
        write_reports(cfg, endpoints=endpoints, findings=findings)

    html_files = glob.glob(os.path.join(str(tmp_path), "report-*.html"))
    assert html_files, "No HTML report written"
    with open(html_files[0], "r", encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Override / fallback / backward-compat legs
# ---------------------------------------------------------------------------


def test_operator_override_template_renders_instead_of_packaged(tmp_path):
    """A report.html.j2 written into cfg.report.template_dir is the template
    that renders — its marker appears, the packaged marker does not."""
    override_dir = tmp_path / "override"
    override_dir.mkdir()
    (override_dir / "report.html.j2").write_text(
        f"<html><body>{OVERRIDE_MARKER}</body></html>", encoding="utf-8"
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    html = _run_write_reports(out_dir, template_dir=str(override_dir))

    assert OVERRIDE_MARKER in html, "Operator override template did not render"
    assert PACKAGED_MARKER not in html, "Packaged template rendered despite an override being present"


def test_fallback_to_packaged_template_when_override_dir_has_no_report_template(tmp_path):
    """template_dir set but containing no report.html.j2 -> packaged template
    still renders normally (ChoiceLoader fallback)."""
    override_dir = tmp_path / "empty_override"
    override_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    html = _run_write_reports(out_dir, template_dir=str(override_dir))

    assert PACKAGED_MARKER in html, "Packaged template did not render via ChoiceLoader fallback"


def test_no_report_section_renders_exactly_as_today(tmp_path):
    """cfg with NO `report` attribute at all -> packaged template, no
    exception — the backward-compat contract for every pre-Phase-200 cfg."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    html = _run_write_reports(out_dir, no_report_section=True)

    assert PACKAGED_MARKER in html, "Packaged template did not render for a cfg with no report section"


# ---------------------------------------------------------------------------
# Autoescape / sanitize-filter legs (T-200-02 — must not regress on the swap)
# ---------------------------------------------------------------------------


def test_autoescape_still_active_on_override_template(tmp_path):
    """An override template that emits a scan-derived <script> string must
    still come out escaped or stripped, never raw — autoescape must be on
    the SAME sandboxed instance, not dropped during the class swap."""
    override_dir = tmp_path / "override"
    override_dir.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    # Drive this leg by embedding the payload in a real scanner-controlled
    # field (mirrors test_report_injection_hardening.py's approach) — the
    # override template renders it via the `findings` context variable it can
    # reach.
    (override_dir / "report.html.j2").write_text(
        "<html><body>{% for f in findings %}{{ f.get('title','') }}{% endfor %}</body></html>",
        encoding="utf-8",
    )

    from quirk.reports.writer import write_reports

    cfg = _make_cfg(out_dir, template_dir=str(override_dir))
    endpoints = []
    findings = [{"severity": "HIGH", "host": "x", "port": 443, "title": XSS_PAYLOAD, "description": "d"}]
    p1, p2, p3, p4, p5, p6 = _patches()
    with p1, p2, p3, p4, p5, p6:
        write_reports(cfg, endpoints=endpoints, findings=findings)

    html_files = glob.glob(os.path.join(str(out_dir), "report-*.html"))
    assert html_files, "No HTML report written"
    with open(html_files[0], "r", encoding="utf-8") as fh:
        html = fh.read()

    assert XSS_PAYLOAD not in html, "Raw <script> payload rendered unescaped through an override template"
    escaped_present = "&lt;script&gt;" in html
    stripped_payload_absent = "<script" not in html
    assert escaped_present or stripped_payload_absent, (
        "Override template neither escaped nor stripped the adversarial payload"
    )


def test_sanitize_filter_registered_on_override_template(tmp_path):
    """An override template using `| sanitize` must render without an
    'unknown filter' error — proving the filter is registered on the
    SandboxedEnvironment instance, not only on a legacy Environment."""
    override_dir = tmp_path / "override"
    override_dir.mkdir()
    (override_dir / "report.html.j2").write_text(
        "<html><body>{{ 'hello world' | sanitize }}</body></html>", encoding="utf-8"
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    html = _run_write_reports(out_dir, template_dir=str(override_dir))

    assert "hello world" in html, "sanitize filter did not render through cleanly"


# ---------------------------------------------------------------------------
# SSTI containment legs (T-200-01 / T-200-03) — the go/no-go payload corpus
# ---------------------------------------------------------------------------

CANONICAL_SSTI_PAYLOADS = (
    "''.__class__.__mro__",
    "''.__class__.__bases__[0].__subclasses__()",
    "cycler.__init__.__globals__",
    "joiner.__init__.__globals__",
    "namespace.__init__.__globals__",
    "{}.__class__",
    "lipsum.__globals__",
    "self._TemplateReference__context",
    "{% set x = ''.join.__globals__ %}{{ x }}",
    "findings.__class__",
    "config.__class__",
    "'{0.__init__.__globals__}'.format(namespace)",
    "x|attr('__class__')",
)

# Phase 200 review WR-03: the override template ends in `.j2`, so autoescape
# is ACTIVE on any leaked value — a real leak of `<class 'dict'>` reaches the
# HTML as `&lt;class &#39;dict&#39;&gt;`. Every marker that contains an HTML
# metacharacter must therefore be present in BOTH its raw form (belt: a
# non-autoescaping regression) and its HTML-escaped form (what a
# leaked-but-escaped value actually looks like), or the leaf-attribute payload
# class ({}.__class__ etc.) passes vacuously even with a plain Environment.
SENSITIVE_MARKERS = (
    "<class ",
    "&lt;class ",
    "&#39;object&#39;",
    "__globals__",
    "subprocess",
    "/bin/",
    "builtins",
    "os.popen",
)


@pytest.mark.parametrize("payload", CANONICAL_SSTI_PAYLOADS)
def test_ssti_payload_is_contained(tmp_path, payload):
    """Every canonical SSTI payload, rendered through an operator override
    template via the real write_reports pipeline, must either raise
    SecurityError or produce output free of every sensitive marker. Both
    outcomes are acceptable passes — see module docstring for why a
    raises-only assertion would be wrong for this corpus."""
    override_dir = tmp_path / "override"
    override_dir.mkdir()
    # A payload that already embeds its own {% ... %}/{{ ... }} tags (the
    # `{% set %}`-bound idiom) is used verbatim; every other payload is a bare
    # expression that needs wrapping in {{ }}.
    body = payload if "{%" in payload or "{{" in payload else f"{{{{ {payload} }}}}"
    (override_dir / "report.html.j2").write_text(
        f"<html><body>{body}</body></html>", encoding="utf-8"
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    try:
        html = _run_write_reports(out_dir, template_dir=str(override_dir))
    except SecurityError:
        return  # contained — acceptable outcome #1

    lowered = html.lower()
    leaked = [m for m in SENSITIVE_MARKERS if m.lower() in lowered]
    assert not leaked, (
        f"SSTI payload {payload!r} leaked sensitive markers {leaked!r} into "
        "rendered HTML without raising SecurityError"
    )


# ---------------------------------------------------------------------------
# Falsifiability leg (Phase 200 review WR-03) — a gate that cannot fail is
# not a gate. Downgrade the production env to a plain (non-sandboxed)
# Environment through the SAME render path and prove the marker scan above
# DOES flag the resulting leak. If the sandbox were ever removed, this is the
# leak shape the parametrized legs must catch — so this test proves they can.
# ---------------------------------------------------------------------------


def test_marker_scan_flags_a_plain_environment_leak(tmp_path, monkeypatch):
    """With SandboxedEnvironment monkeypatched to jinja2.Environment at the
    single construction site, the leaf-attribute payload `{}.__class__`
    renders an (autoescaped) class repr — and the SENSITIVE_MARKERS scan used
    by test_ssti_payload_is_contained must flag it. This proves the go/no-go
    gate is falsifiable for precisely the payload class that never raises
    SecurityError."""
    from jinja2 import Environment

    import quirk.reports.html_renderer as html_renderer

    monkeypatch.setattr(html_renderer, "SandboxedEnvironment", Environment)

    override_dir = tmp_path / "override"
    override_dir.mkdir()
    (override_dir / "report.html.j2").write_text(
        "<html><body>{{ {}.__class__ }}</body></html>", encoding="utf-8"
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    html = _run_write_reports(out_dir, template_dir=str(override_dir))

    lowered = html.lower()
    leaked = [m for m in SENSITIVE_MARKERS if m.lower() in lowered]
    assert leaked, (
        "A plain (non-sandboxed) Environment leaked a class repr through the "
        "real render path, but no SENSITIVE_MARKER flagged it — the SSTI "
        "containment gate would pass vacuously if the sandbox were removed"
    )
