"""Phase 12 — CLI Correctness: contract tests for CLI-01, CLI-02, CLI-03, CLI-04.

These tests define the Phase 12 correctness contract (Nyquist validation strategy).
At creation time:
  RED (expected failures): test_version_consistency, test_config_default_version,
                           test_no_owner_placeholder
  GREEN (regression guards): test_init_config_loads_without_error,
                             test_template_field_alignment,
                             test_no_quirk_scan_references

Plan 02 must make all six tests GREEN.
"""

import dataclasses
import pathlib
import shutil
import tempfile

import yaml


# ---------------------------------------------------------------------------
# CLI-04 — Version consistency
# ---------------------------------------------------------------------------


def test_version_consistency():
    """All version constants across the codebase must equal '4.1.0'.

    Covers D-01 (quirk.__version__), D-02 (PLATFORM_VERSION / INTELLIGENCE_VERSION in
    reports/writer.py), D-02 (PLATFORM_VERSION in cbom/builder.py), and IntelligenceCfg
    default intelligence_version in config.py.

    RED: current values are "4.0.0" (writer INTELLIGENCE_VERSION) and "4.0"
         (writer/builder PLATFORM_VERSION).
    """
    import quirk
    from quirk.reports.writer import PLATFORM_VERSION, INTELLIGENCE_VERSION
    from quirk.cbom.builder import PLATFORM_VERSION as CBOM_VERSION
    from quirk.config import IntelligenceCfg

    TARGET = "4.4.0"
    assert quirk.__version__ == TARGET, (
        f"quirk.__version__ is {quirk.__version__!r}, expected {TARGET!r}"
    )
    assert PLATFORM_VERSION == TARGET, (
        f"quirk.reports.writer.PLATFORM_VERSION is {PLATFORM_VERSION!r}, expected {TARGET!r}"
    )
    assert INTELLIGENCE_VERSION == TARGET, (
        f"quirk.reports.writer.INTELLIGENCE_VERSION is {INTELLIGENCE_VERSION!r}, expected {TARGET!r}"
    )
    assert CBOM_VERSION == TARGET, (
        f"quirk.cbom.builder.PLATFORM_VERSION is {CBOM_VERSION!r}, expected {TARGET!r}"
    )
    assert IntelligenceCfg().intelligence_version == TARGET, (
        f"IntelligenceCfg().intelligence_version is "
        f"{IntelligenceCfg().intelligence_version!r}, expected {TARGET!r}"
    )


# ---------------------------------------------------------------------------
# CLI-04 — config_from_dict fallback version (D-03 / Pitfall 2)
# ---------------------------------------------------------------------------


def test_config_default_version():
    """The fallback string in config_from_dict's intel_raw.get() call must be '4.1.0'.

    Reads quirk/config.py source text and asserts the default value passed to
    intel_raw.get('intelligence_version', ...) is '4.1.0'.

    RED: current fallback is '4.0.0'.
    """
    config_path = pathlib.Path(__file__).parent.parent / "quirk" / "config.py"
    source = config_path.read_text(encoding="utf-8")
    # The line reads: intel_raw.get("intelligence_version", "4.2.0")
    assert '"4.2.0"' in source or "'4.1.0'" in source, (
        "quirk/config.py does not contain '4.1.0' — "
        "the intelligence_version fallback in config_from_dict must be updated"
    )
    # More precise: the get() call default must be 4.1.0 (not just appear elsewhere)
    assert 'get("intelligence_version", "4.2.0")' in source or (
        "get('intelligence_version', '4.1.0')" in source
    ), (
        "config_from_dict fallback for intelligence_version is not '4.1.0'; "
        f"found content around 'intelligence_version': "
        + str([l.strip() for l in source.splitlines() if "intelligence_version" in l])
    )


# ---------------------------------------------------------------------------
# CLI-01 — quirk init generates config that loads without TypeError (D-07)
# ---------------------------------------------------------------------------


def test_init_config_loads_without_error():
    """Load the config_template.yaml via load_config() — must not raise TypeError.

    This is a regression guard: the template was aligned in Phase 8 and must
    remain loadable as a valid AppConfig without any TypeError.

    GREEN at test creation time.
    """
    from quirk.config import load_config

    tmpdir = tempfile.mkdtemp()
    try:
        dest = f"{tmpdir}/config.yaml"
        shutil.copy("quirk/config_template.yaml", dest)
        cfg = load_config(dest)
        assert hasattr(cfg, "targets"), "AppConfig missing 'targets' attribute"
        assert hasattr(cfg, "scan"), "AppConfig missing 'scan' attribute"
        assert hasattr(cfg, "connectors"), "AppConfig missing 'connectors' attribute"
        assert hasattr(cfg, "intelligence"), "AppConfig missing 'intelligence' attribute"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# CLI-01 — Template field alignment: connectors and scan blocks (D-07/D-08)
# ---------------------------------------------------------------------------


def test_template_field_alignment():
    """Every key in the template's connectors: and scan: blocks must map to a real dataclass field.

    Also asserts that the removed 'enable_windows_adcs' dead field is absent.

    GREEN at test creation time (template was cleaned in Phase 8).
    """
    from quirk.config import ConnectorsCfg, ScanCfg

    template_path = pathlib.Path("quirk/config_template.yaml")
    raw = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    # --- connectors block ---
    connector_keys = set((raw.get("connectors") or {}).keys())
    connector_field_names = {f.name for f in dataclasses.fields(ConnectorsCfg)}
    unknown_connector_keys = connector_keys - connector_field_names
    assert not unknown_connector_keys, (
        f"config_template.yaml connectors: block has unknown keys: {unknown_connector_keys}. "
        f"Valid ConnectorsCfg fields: {connector_field_names}"
    )
    assert "enable_windows_adcs" not in connector_keys, (
        "Dead field 'enable_windows_adcs' found in config_template.yaml connectors: block — "
        "it was removed in Phase 8 and must not reappear"
    )

    # --- scan block ---
    scan_keys = set((raw.get("scan") or {}).keys())
    scan_field_names = {f.name for f in dataclasses.fields(ScanCfg)}
    unknown_scan_keys = scan_keys - scan_field_names
    assert not unknown_scan_keys, (
        f"config_template.yaml scan: block has unknown keys: {unknown_scan_keys}. "
        f"Valid ScanCfg fields: {scan_field_names}"
    )


# ---------------------------------------------------------------------------
# CLI-02 — No "quirk scan" references in live codebase (D-09 / Pitfall 5)
# ---------------------------------------------------------------------------


def test_no_quirk_scan_references():
    """No file in quirk/**/*.py, docs/**/*.md, or quirk/**/*.yaml contains 'quirk scan'.

    Files under docs/superpowers/ are excluded (historical spec docs).

    GREEN at test creation time.
    """
    repo_root = pathlib.Path(__file__).parent.parent
    patterns = [
        list(repo_root.glob("quirk/**/*.py")),
        list(repo_root.glob("docs/**/*.md")),
        list(repo_root.glob("quirk/**/*.yaml")),
    ]
    violations = []
    for file_list in patterns:
        for fpath in file_list:
            # Exclude historical superpowers spec docs
            if "superpowers" in fpath.parts:
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "quirk scan" in content:
                # Find specific lines for diagnostics
                lines = [
                    f"  line {i+1}: {line.rstrip()}"
                    for i, line in enumerate(content.splitlines())
                    if "quirk scan" in line
                ]
                violations.append(f"{fpath.relative_to(repo_root)}:\n" + "\n".join(lines))

    assert not violations, (
        "Found 'quirk scan' references (should be 'quirk --config') in:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# CLI-03 — No [owner] placeholder in docs/getting-started.md (D-04)
# ---------------------------------------------------------------------------


def test_no_owner_placeholder():
    """docs/getting-started.md must not contain '[owner]' placeholder.

    RED: current file has '[owner]' on lines 22 and 28 in the pip install URLs.
    Plan 02 must replace '[owner]' with the real GitHub organization/user handle.
    """
    content = pathlib.Path("docs/getting-started.md").read_text(encoding="utf-8")
    assert "[owner]" not in content, (
        "docs/getting-started.md contains '[owner]' placeholder — "
        "replace with the real GitHub organization/user (e.g. 'quantum-apps')"
    )
