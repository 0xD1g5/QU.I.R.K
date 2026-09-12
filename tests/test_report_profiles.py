"""Phase 200 / RPT-04: report profile round-trip, precedence, and rejection
tests for quirk.report_profiles and quirk.cli.report_cmd.

Every test redirects the profiles directory via
``monkeypatch.setenv("QUIRK_PROFILES_DIR", str(tmp_path))`` — never patches
the user-home resolution directly (fragile on Windows CI) and never touches
the developer's real ``~/.quirk``.
"""
from __future__ import annotations

import textwrap

import pytest
import yaml

from quirk.config import config_from_dict
from quirk.report_profiles import (
    apply_report_profile,
    list_profiles,
    load_profile,
    profiles_dir,
    save_profile,
    validate_profile_name,
)

# Minimal raw config dict satisfying config_from_dict()'s required fields
# (mirrors tests/test_config.py::_SNMP_V3_MINIMAL_RAW).
_MINIMAL_RAW = {
    "assessment": {
        "name": "test",
        "data_classification": "internal",
        "report_owner": "tester",
        "timezone": "UTC",
    },
    "scan": {
        "timeout_seconds": 5,
        "concurrency": 200,
        "ports_tls": [443],
    },
    "targets": {
        "fqdns": [],
        "cidrs": [],
        "include_ips": [],
        "exclude_ips": [],
    },
    "output": {
        "directory": "/tmp/quirk-test",
        "db_path": "/tmp/quirk-test.db",
    },
}


def _raw_with_report(report_block):
    raw = dict(_MINIMAL_RAW)
    raw["report"] = report_block
    return raw


@pytest.fixture(autouse=True)
def _redirect_profiles_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("QUIRK_PROFILES_DIR", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# Round trip
# ---------------------------------------------------------------------------


def test_save_then_load_round_trips_branding_and_template_dir(tmp_path):
    (tmp_path / "templates").mkdir()
    cfg = config_from_dict(
        _raw_with_report(
            {
                "template_dir": str(tmp_path / "templates"),
                "branding": {
                    "client_name": "Acme Corp",
                    "engagement_name": "Q3 PQC Readiness",
                    "prepared_by": "Jane Analyst",
                },
            }
        )
    )

    save_profile("housestyle", cfg)
    loaded = load_profile("housestyle")

    assert loaded["template_dir"] == str(tmp_path / "templates")
    assert loaded["branding"]["client_name"] == "Acme Corp"
    assert loaded["branding"]["engagement_name"] == "Q3 PQC Readiness"
    assert loaded["branding"]["prepared_by"] == "Jane Analyst"

    with open(tmp_path / "housestyle.yaml", "r", encoding="utf-8") as fh:
        written_raw = yaml.safe_load(fh)
    assert "profile" not in written_raw
    assert "profile" not in written_raw.get("branding", {})


# ---------------------------------------------------------------------------
# list_profiles
# ---------------------------------------------------------------------------


def test_list_profiles_sorted(tmp_path):
    cfg = config_from_dict(
        _raw_with_report({"branding": {"client_name": "Zeta"}})
    )
    save_profile("zeta", cfg)
    save_profile("alpha", cfg)
    assert list_profiles() == ["alpha", "zeta"]


def test_list_profiles_empty_directory_returns_empty_list(tmp_path):
    nonexistent = tmp_path / "does-not-exist-yet"
    import os

    os.environ["QUIRK_PROFILES_DIR"] = str(nonexistent)
    assert list_profiles() == []


# ---------------------------------------------------------------------------
# Precedence (the load-bearing leg): explicit config always wins
# ---------------------------------------------------------------------------


def test_explicit_config_value_survives_profile_application(tmp_path):
    # Profile supplies client_name (different) and engagement_name (new).
    profile_cfg = config_from_dict(
        _raw_with_report(
            {
                "branding": {
                    "client_name": "Profile Corp",
                    "engagement_name": "From Profile",
                }
            }
        )
    )
    save_profile("houseprofile", profile_cfg)

    # Engagement cfg sets client_name explicitly, leaves engagement_name unset.
    engagement_cfg = config_from_dict(
        _raw_with_report({"branding": {"client_name": "Explicit Client"}})
    )
    assert "branding.client_name" in engagement_cfg.report._user_set_fields
    assert "branding.engagement_name" not in engagement_cfg.report._user_set_fields

    apply_report_profile(engagement_cfg, "houseprofile")

    # Half 1: explicit value survived unchanged.
    assert engagement_cfg.report.branding.client_name == "Explicit Client"
    # Half 2: unset field was filled from the profile.
    assert engagement_cfg.report.branding.engagement_name == "From Profile"


# ---------------------------------------------------------------------------
# Name rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_name", ["..", "../evil", "a/b", "", "x" * 100])
def test_bad_profile_names_rejected(tmp_path, bad_name):
    with pytest.raises(ValueError) as excinfo:
        validate_profile_name(bad_name)
    message = str(excinfo.value)
    assert "QRK-CONFIG-004" in message
    assert repr(bad_name) in message or bad_name in message

    # No file was created outside the tmp profiles directory as a side effect.
    created = list(tmp_path.glob("**/*.yaml"))
    assert created == []


def test_bad_profile_name_rejected_by_save(tmp_path):
    cfg = config_from_dict(_raw_with_report({"branding": {"client_name": "X"}}))
    with pytest.raises(ValueError) as excinfo:
        save_profile("../evil", cfg)
    assert "QRK-CONFIG-004" in str(excinfo.value)
    assert list(tmp_path.glob("**/*.yaml")) == []


# ---------------------------------------------------------------------------
# Traversal-in-profile-file: a profile file must not bypass the config guard
# ---------------------------------------------------------------------------


def test_traversal_template_dir_in_profile_file_rejected_on_apply(tmp_path):
    (tmp_path / "traversal.yaml").write_text(
        yaml.safe_dump({"template_dir": "../../etc"}), encoding="utf-8"
    )
    engagement_cfg = config_from_dict(_raw_with_report({}))

    with pytest.raises(ValueError) as excinfo:
        apply_report_profile(engagement_cfg, "traversal")
    message = str(excinfo.value)
    assert "QRK-CONFIG-003" in message


# ---------------------------------------------------------------------------
# Malformed profile file / unknown keys
# ---------------------------------------------------------------------------


def test_malformed_profile_file_not_a_mapping_raises_coded_error(tmp_path):
    (tmp_path / "malformed.yaml").write_text(
        yaml.safe_dump(["not", "a", "mapping"]), encoding="utf-8"
    )
    with pytest.raises(ValueError) as excinfo:
        load_profile("malformed")
    message = str(excinfo.value)
    assert "QRK-CONFIG-004" in message
    assert "malformed.yaml" in message


def test_unknown_key_in_profile_file_warns_and_is_ignored(tmp_path, caplog):
    (tmp_path / "hasunknown.yaml").write_text(
        yaml.safe_dump(
            {
                "branding": {"client_name": "Known", "not_a_real_field": "ignored"},
                "not_a_real_top_level_field": "ignored too",
            }
        ),
        encoding="utf-8",
    )
    with caplog.at_level("WARNING"):
        loaded = load_profile("hasunknown")

    assert loaded["branding"]["client_name"] == "Known"
    assert "not_a_real_field" not in loaded["branding"]
    assert "not_a_real_top_level_field" not in loaded
    assert any("not_a_real_field" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# Unsafe YAML: prove safe_load, not merely value absence
# ---------------------------------------------------------------------------


def test_unsafe_yaml_tag_does_not_execute(tmp_path):
    malicious = textwrap.dedent(
        """\
        branding:
          client_name: !!python/object/apply:os.system ["echo pwned"]
        """
    )
    (tmp_path / "malicious.yaml").write_text(malicious, encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        load_profile("malicious")


# ---------------------------------------------------------------------------
# CLI: save then list
# ---------------------------------------------------------------------------


def test_cli_save_then_list(tmp_path, capsys):
    from quirk.cli.report_cmd import run_report

    config_path = tmp_path / "engagement-config.yaml"
    config_yaml = dict(_MINIMAL_RAW)
    config_yaml["report"] = {"branding": {"client_name": "CLI Corp"}}
    with open(config_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(config_yaml, fh)

    with pytest.raises(SystemExit) as save_exit:
        run_report(["profile", "save", "cliprofile", "--config", str(config_path)])
    assert save_exit.value.code == 0

    assert (tmp_path / "cliprofile.yaml").is_file()

    with pytest.raises(SystemExit) as list_exit:
        run_report(["profile", "list"])
    assert list_exit.value.code == 0

    captured = capsys.readouterr()
    assert "cliprofile" in captured.out
