"""Integration tests for --targets-file override (Phase 47 / MULTI-03, D-03, D-05).

Tests import apply_targets_file_override directly from quirk.util.targets to
avoid run_scan.py import side-effects (run_scan.py imports SQLAlchemy, multiple
scanners, etc.) — keeps tests fast and deterministic.

Covers:
  - D-03/MULTI-03: --targets-file REPLACES (not merges) cfg.targets.fqdns + cidrs
  - D-05/MULTI-05: missing path raises FileNotFoundError with path in message
  - D-05/MULTI-05: malformed CIDR in file raises ValueError with token in message
  - Risks #3 regression: targets-file CIDR produces same nmap_targets as YAML config
"""
import pytest

from quirk.util.targets import apply_targets_file_override


# ---------------------------------------------------------------------------
# Minimal stub cfg to avoid full AppConfig instantiation overhead
# ---------------------------------------------------------------------------

class _TargetsStub:
    def __init__(self, fqdns=None, cidrs=None, include_ips=None, exclude_ips=None):
        self.fqdns = fqdns or []
        self.cidrs = cidrs or []
        self.include_ips = include_ips or []
        self.exclude_ips = exclude_ips or []


class _CfgStub:
    def __init__(self, fqdns=None, cidrs=None, include_ips=None, exclude_ips=None):
        self.targets = _TargetsStub(
            fqdns=fqdns or [],
            cidrs=cidrs or [],
            include_ips=include_ips or [],
            exclude_ips=exclude_ips or [],
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_targets_file_replaces_config_fqdns(tmp_path):
    """D-03/MULTI-03: apply_targets_file_override REPLACES fqdns and cidrs (does NOT merge)."""
    targets_file = tmp_path / "hosts.txt"
    targets_file.write_text("actual-host.com\n10.99.0.0/30\n#skip\n\n")

    cfg = _CfgStub(
        fqdns=["should-be-discarded.com"],
        cidrs=["10.0.0.0/24"],
    )

    apply_targets_file_override(cfg, str(targets_file))

    # REPLACED — not merged
    assert cfg.targets.fqdns == ["actual-host.com"]
    assert cfg.targets.cidrs == ["10.99.0.0/30"]
    # Original values must be gone
    assert "should-be-discarded.com" not in cfg.targets.fqdns
    assert "10.0.0.0/24" not in cfg.targets.cidrs


def test_targets_file_missing_path_surfaces_clear_error(tmp_path):
    """D-05/MULTI-05: missing targets-file path raises FileNotFoundError containing the path."""
    missing = str(tmp_path / "does-not-exist.txt")
    cfg = _CfgStub()
    with pytest.raises(FileNotFoundError) as exc_info:
        apply_targets_file_override(cfg, missing)
    assert missing in str(exc_info.value)


def test_targets_file_malformed_cidr_surfaces_clear_error(tmp_path):
    """D-05/MULTI-05: malformed CIDR in targets-file raises ValueError with the token."""
    targets_file = tmp_path / "bad.txt"
    targets_file.write_text("10.0.0.0/99\n")
    cfg = _CfgStub()
    with pytest.raises(ValueError) as exc_info:
        apply_targets_file_override(cfg, str(targets_file))
    assert "10.0.0.0/99" in str(exc_info.value)


def test_targets_file_cidr_produces_same_nmap_targets_as_yaml_config(tmp_path):
    """Risks #3 regression: CIDR from targets-file feeds _build_nmap_target_list identically.

    A targets-file with one CIDR and one FQDN should produce the same list as
    a config that has those values set directly.
    """
    # Simulate what _build_nmap_target_list does (run_scan.py:55-60)
    def _build_nmap_target_list(cfg):
        targets = []
        targets.extend(cfg.targets.cidrs or [])
        targets.extend(cfg.targets.fqdns or [])
        targets.extend(cfg.targets.include_ips or [])
        return [t for t in targets if t]

    # Baseline: config set directly (equivalent of YAML config)
    cfg_yaml = _CfgStub(fqdns=["myhost.example.com"], cidrs=["192.168.1.0/24"])
    yaml_nmap_targets = _build_nmap_target_list(cfg_yaml)

    # Via targets-file override
    targets_file = tmp_path / "targets.txt"
    targets_file.write_text("myhost.example.com\n192.168.1.0/24\n")
    cfg_file = _CfgStub(fqdns=["old.host"], cidrs=["10.0.0.0/8"])
    apply_targets_file_override(cfg_file, str(targets_file))
    file_nmap_targets = _build_nmap_target_list(cfg_file)

    # Both should produce the same nmap target set (order may differ by fqdns/cidrs ordering)
    assert sorted(yaml_nmap_targets) == sorted(file_nmap_targets)
