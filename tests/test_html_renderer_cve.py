"""Phase 142 (CVE-01/03/D-11/D-13/D-14/D-15) — RED render-presence test scaffold
for the CVE advisory surface in quirk.reports.html_renderer.

Exercises render_hardware_section() with synthetic device dicts (the same
list-of-dicts shape html_renderer already consumes). Presence/content
assertions only, per this project's render-tests-assert-presence convention
(feedback_report_render_tests_presence_not_appearance) — not visual/pixel
checks. Fails RED until the CVE render surface is added (Plan 03).
"""
from __future__ import annotations


def _base_device(**overrides) -> dict:
    device = {
        "host": "10.0.0.5",
        "port": 22,
        "vendor": "Schneider Electric",
        "model": "M221",
        "pqc_status": "unsupported",
        "confidence": "high",
        "eol_date": None,
        "remediation_tier": "Tier 1",
    }
    device.update(overrides)
    return device


# ---------------- CVE-01/D-15: matched CVE renders with cited NVD link ----------------

def test_cve_match_renders_id_and_nvd_link() -> None:
    from quirk.reports.html_renderer import render_hardware_section

    device = _base_device(
        cve_matches=[{
            "cve_id": "CVE-2018-7789",
            "severity": "HIGH",
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2018-7789",
        }],
        cve_confidence="high",
        cve_attempted=True,
    )
    html = render_hardware_section([device])

    assert "CVE-2018-7789" in html
    assert 'href="https://nvd.nist.gov/vuln/detail/CVE-2018-7789"' in html
    assert "high" in html.lower()


# ---------------- D-14: neutral badge color, not green success / red severity ----------------

def test_cve_badge_uses_approved_neutral_color() -> None:
    from quirk.reports.html_renderer import render_hardware_section

    device = _base_device(
        cve_matches=[{
            "cve_id": "CVE-2018-7789",
            "severity": "HIGH",
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2018-7789",
        }],
        cve_confidence="high",
        cve_attempted=True,
    )
    html = render_hardware_section([device])

    approved_colors = ("hsl(213 94% 68%)", "hsl(38 92% 50%)")
    assert any(c in html for c in approved_colors), (
        "Expected an approved neutral hsl() badge color near the CVE cell"
    )
    # Never the green success hue near the CVE badge.
    assert "hsl(142 71% 45%)" not in html


# ---------------- CVE-03: attempted but empty -> caveat text ----------------

def test_attempted_no_match_renders_no_correlation_caveat() -> None:
    from quirk.reports.html_renderer import render_hardware_section

    device = _base_device(
        cve_matches=[],
        cve_confidence=None,
        cve_attempted=True,
    )
    html = render_hardware_section([device])

    assert "no CVE correlation attempted" in html


# ---------------- D-03: vendor Unknown -> no CVE cell/caveat at all ----------------

def test_unknown_vendor_renders_no_cve_cell() -> None:
    from quirk.reports.html_renderer import render_hardware_section

    device = _base_device(
        vendor="Unknown",
        model=None,
        cve_attempted=False,
        cve_matches=None,
    )
    html = render_hardware_section([device])

    assert "no CVE correlation attempted" not in html
    assert "CVE-" not in html


# ---------------- D-11: staleness caveat ----------------

def test_stale_cve_snapshot_renders_staleness_caveat() -> None:
    from quirk.reports.html_renderer import render_hardware_section

    device = _base_device(
        cve_matches=[{
            "cve_id": "CVE-2018-7789",
            "severity": "HIGH",
            "source_url": "https://nvd.nist.gov/vuln/detail/CVE-2018-7789",
        }],
        cve_confidence="high",
        cve_attempted=True,
        cve_snapshot_stale=True,
    )
    html = render_hardware_section([device])

    assert "last verified" in html.lower() or "may be outdated" in html.lower()
