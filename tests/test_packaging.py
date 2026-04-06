"""Phase 7 — BRAND-04: packaging and installability tests."""
import importlib
import os


def test_run_scan_importable():
    """quirk package must be importable and expose __version__."""
    from quirk import __version__
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_is_4_1_0():
    """__version__ must be bumped to 4.1.0 for Phase 12 CLI correctness."""
    from quirk import __version__
    assert __version__ == "4.1.0", f"Expected 4.1.0, got {__version__!r}"


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
