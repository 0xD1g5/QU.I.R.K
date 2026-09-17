"""Phase 7 — BRAND-04: packaging and installability tests."""
import importlib
import os
import tomllib


def test_run_scan_importable():
    """quirk package must be importable and expose __version__."""
    from quirk import __version__
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_package_data_templates():
    """quirk/reports/templates/ directory must exist with report.html.j2 template."""
    import quirk
    pkg_dir = os.path.dirname(quirk.__file__)
    templates_dir = os.path.join(pkg_dir, "reports", "templates")
    assert os.path.isdir(templates_dir), f"templates dir missing: {templates_dir}"
    template_file = os.path.join(templates_dir, "report.html.j2")
    assert os.path.isfile(template_file), f"report.html.j2 missing: {template_file}"


def test_pyproject_has_jinja2():
    """pyproject.toml must declare jinja2 as a core dependency."""
    root = os.path.join(os.path.dirname(__file__), "..")
    pyproject = open(os.path.join(root, "pyproject.toml")).read()
    assert "jinja2" in pyproject.lower(), "jinja2 not found in pyproject.toml dependencies"


def test_pyproject_has_rich():
    """pyproject.toml must declare rich as a core dependency."""
    root = os.path.join(os.path.dirname(__file__), "..")
    pyproject = open(os.path.join(root, "pyproject.toml")).read()
    assert "rich" in pyproject.lower(), "rich not found in pyproject.toml dependencies"


# ---------------------------------------------------------------------------
# BACK-76: identity deps promoted to core (except impacket)
# ---------------------------------------------------------------------------

def _core_deps_section():
    """Return the [project] dependencies as newline-joined requirement specifiers.

    Parsed via tomllib rather than sliced out of the raw file text. The raw-text
    slice this replaced included COMMENTS, so a comment that merely *mentioned* a
    package read as a declaration *of* it: the `sslyze` entry's caveat comment
    explains its interaction with impacket's pyOpenSSL chain, and that prose alone
    tripped `test_impacket_not_in_core_deps` even though impacket is nowhere in
    `dependencies`. These tests assert what is DECLARED; parse the declarations.
    Every `in` / `not in` check below works unchanged against the specifier text
    (e.g. "dnspython" in "dnspython[dnssec]>=2.8.0").
    """
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, "pyproject.toml"), "rb") as fh:
        data = tomllib.load(fh)
    return "\n".join(data["project"]["dependencies"])


def test_dnspython_in_core_deps():
    """dnspython[dnssec] must be in core deps so DNSSEC scanning works without extras."""
    assert "dnspython" in _core_deps_section(), "dnspython not found in core dependencies"


def test_lxml_in_core_deps():
    """lxml must be in core deps so SAML scanning works without extras."""
    assert "lxml" in _core_deps_section(), "lxml not found in core dependencies"


def test_defusedxml_not_in_core_deps():
    """defusedxml must NOT be in core deps after Phase 87 DEP-02 migration."""
    assert "defusedxml" not in _core_deps_section(), (
        "defusedxml found in core dependencies — remove per Phase 87 DEP-02"
    )


def test_signxml_in_core_deps():
    """signxml must be in core deps so SAML signature verification works without extras."""
    assert "signxml" in _core_deps_section(), "signxml not found in core dependencies"


def test_impacket_not_in_core_deps():
    """impacket must remain in [identity] extras — pyOpenSSL transitive conflict risk."""
    core = _core_deps_section()
    assert "impacket" not in core, (
        "impacket must stay in [identity] extras, not core — "
        "it has a pyOpenSSL transitive conflict risk"
    )


def test_identity_scanners_importable_without_impacket():
    """DNSSEC, SAML, and OIDC scanner modules must import cleanly (core deps cover them)."""
    from quirk.scanner.dnssec_scanner import scan_dnssec_targets, DNSPYTHON_AVAILABLE
    from quirk.scanner.saml_scanner import scan_saml_targets, LXML_AVAILABLE
    assert DNSPYTHON_AVAILABLE, "dnspython[dnssec] should be available (now a core dep)"
    assert LXML_AVAILABLE, "lxml should be available (now a core dep)"
