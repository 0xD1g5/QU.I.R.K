"""Phase 10 — Gap closure: PACKAGE-01 and MISSING-01 regression tests."""
import os
import yaml


def _repo_root() -> str:
    return os.path.join(os.path.dirname(__file__), "..")


def test_pyproject_includes_dashboard_static():
    """PACKAGE-01: pyproject.toml must include dashboard/static/**/* in package-data."""
    pyproject_path = os.path.join(_repo_root(), "pyproject.toml")
    content = open(pyproject_path).read()
    assert "dashboard/static/**/*" in content, (
        "pyproject.toml [tool.setuptools.package-data] missing 'dashboard/static/**/*' — "
        "pip wheel will not include the React bundle"
    )


def test_config_template_has_intelligence_block():
    """MISSING-01: config_template.yaml must contain a commented intelligence: block."""
    template_path = os.path.join(_repo_root(), "quirk", "config_template.yaml")
    content = open(template_path).read()
    assert "intelligence:" in content, (
        "config_template.yaml missing 'intelligence:' block — "
        "users cannot discover the scoring profile knob via quirk init"
    )


def test_config_template_valid_yaml():
    """Config template must remain valid YAML after edits."""
    template_path = os.path.join(_repo_root(), "quirk", "config_template.yaml")
    with open(template_path) as f:
        # This should not raise — commented lines are ignored by YAML parser
        data = yaml.safe_load(f)
    assert isinstance(data, dict), "config_template.yaml did not parse as a YAML dict"
    assert "assessment" in data, "config_template.yaml missing 'assessment' key"
