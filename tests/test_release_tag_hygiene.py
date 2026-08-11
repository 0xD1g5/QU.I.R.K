"""Phase 148-02 RELEASE-03: Unit tests for the tag-hygiene decision script.

Exercises `evaluate_tags`, `load_baseline`, and `collect_backed_tags` from
`scripts/release_tag_hygiene.py` directly with literal inputs — no
subprocess, no network, no `gh`. `scripts/` is not an importable package, so
the module is loaded via `importlib.util.spec_from_file_location`.

Also contains static guards over `.github/workflows/release-tag-hygiene.yml`
and `.github/tag-hygiene-baseline.txt` (added in Task 2).
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "release_tag_hygiene.py"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release-tag-hygiene.yml"
BASELINE_PATH = REPO_ROOT / ".github" / "tag-hygiene-baseline.txt"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "release_tag_hygiene", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rth():
    return _load_module()


# ---------------------------------------------------------------------------
# evaluate_tags
# ---------------------------------------------------------------------------


def test_backed_tag_not_flagged(rth):
    flagged, exempted, _summary = rth.evaluate_tags(["v5.8.0"], {"v5.8.0"}, {})
    assert flagged == []
    assert exempted == []


def test_new_drift_flagged(rth):
    flagged, _exempted, _summary = rth.evaluate_tags(["v5.12.0"], set(), {})
    assert flagged == ["v5.12.0"]


def test_baselined_tag_exempted_not_flagged(rth):
    baseline = {"v5.9": "malformed — never matched v*.*.*"}
    flagged, exempted, summary = rth.evaluate_tags(["v5.9"], set(), baseline)
    assert flagged == []
    assert exempted == ["v5.9"]
    assert "malformed" in summary


def test_non_release_like_tags_ignored(rth):
    flagged, _exempted, _summary = rth.evaluate_tags(
        ["sensor-base-2024", "lab-snapshot"], set(), {}
    )
    assert flagged == []


def test_loose_pattern_catches_two_component_tag(rth):
    """The exact v5.9 incident: a two-component tag that `v*.*.*` would miss
    must still be caught by the loose `v[0-9]*` pattern."""
    flagged, _exempted, _summary = rth.evaluate_tags(["v5.9"], set(), {})
    assert flagged == ["v5.9"]


def test_summary_has_heading_and_names_flagged_tags(rth):
    _flagged, _exempted, summary = rth.evaluate_tags(["v9.9.9"], set(), {})
    assert "## Release Tag Hygiene" in summary
    assert "v9.9.9" in summary


def test_summary_always_has_heading_even_with_no_flags(rth):
    _flagged, _exempted, summary = rth.evaluate_tags(["v1.0.0"], {"v1.0.0"}, {})
    assert "## Release Tag Hygiene" in summary


# ---------------------------------------------------------------------------
# load_baseline
# ---------------------------------------------------------------------------


def test_load_baseline_ignores_comments_and_blanks(rth, tmp_path):
    path = tmp_path / "baseline.txt"
    path.write_text(
        "# comment header\n"
        "\n"
        "v5.9 malformed two-component tag\n"
        "v5.10.0 never pushed\n"
        "# another comment\n"
    )
    result = rth.load_baseline(path)
    assert result == {
        "v5.9": "malformed two-component tag",
        "v5.10.0": "never pushed",
    }


def test_load_baseline_missing_file_returns_empty(rth, tmp_path):
    result = rth.load_baseline(tmp_path / "does-not-exist.txt")
    assert result == {}


def test_load_baseline_keeps_reason_after_first_whitespace_run(rth, tmp_path):
    path = tmp_path / "baseline.txt"
    path.write_text("v5.11.0   PyPI-only release; Windows asset gap dispositioned\n")
    result = rth.load_baseline(path)
    assert result["v5.11.0"] == "PyPI-only release; Windows asset gap dispositioned"


# ---------------------------------------------------------------------------
# collect_backed_tags
# ---------------------------------------------------------------------------


def test_collect_backed_tags_run_records_only(rth):
    run_records = [{"headBranch": "v5.8.0", "displayTitle": ""}]
    result = rth.collect_backed_tags(run_records, [])
    assert result == {"v5.8.0"}


def test_collect_backed_tags_release_list_only_aged_out_case(rth):
    """The aged-out-history fallback: a tag with a real GitHub Release object
    counts as backed even when Actions run history no longer has a record."""
    result = rth.collect_backed_tags([], ["v5.8.0"])
    assert result == {"v5.8.0"}


def test_collect_backed_tags_both_empty_yields_empty_set(rth):
    """Never vacuously 'everything backed' when there is no data at all."""
    result = rth.collect_backed_tags([], [])
    assert result == set()


def test_collect_backed_tags_display_title_containment_fallback(rth):
    """A run record with an empty/mismatched headBranch can still back its
    tag via displayTitle containment."""
    run_records = [{"headBranch": "", "displayTitle": "Release v5.8.0"}]
    result = rth.collect_backed_tags(run_records, [])
    assert "v5.8.0" in result


def test_collect_backed_tags_union_of_both_sources(rth):
    run_records = [{"headBranch": "v5.7.0", "displayTitle": ""}]
    release_names = ["v5.8.0"]
    result = rth.collect_backed_tags(run_records, release_names)
    assert result == {"v5.7.0", "v5.8.0"}


# ---------------------------------------------------------------------------
# Static guards: workflow file + baseline file (Task 2)
# ---------------------------------------------------------------------------


def _load_workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_workflow_file_exists():
    assert WORKFLOW_PATH.exists(), f"{WORKFLOW_PATH} does not exist"


def test_workflow_is_valid_yaml():
    wf = _load_workflow()
    assert isinstance(wf, dict)


def test_workflow_triggers_contain_schedule_and_dispatch():
    wf = _load_workflow()
    # PyYAML 1.1 gotcha: `on:` parses to boolean True, not the string "on".
    triggers = wf.get("on", wf.get(True))
    assert "workflow_dispatch" in triggers
    assert "schedule" in triggers
    schedule_entries = triggers["schedule"]
    crons = [entry.get("cron") for entry in schedule_entries]
    assert "0 9 * * 1" in crons


def test_workflow_triggers_do_not_contain_push_or_pull_request():
    wf = _load_workflow()
    triggers = wf.get("on", wf.get(True))
    assert "push" not in triggers
    assert "pull_request" not in triggers


def test_workflow_declares_least_privilege_permissions():
    wf = _load_workflow()
    permissions = wf.get("permissions", {})
    assert permissions.get("contents") == "read"
    assert permissions.get("actions") == "read"
    for scope, level in permissions.items():
        assert level != "write", f"permission {scope} must not be write"


def test_workflow_checkout_step_sets_fetch_depth_zero():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "fetch-depth: 0" in text


def test_workflow_uses_lines_are_sha_pinned():
    import re

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    uses_lines = [
        line.strip() for line in text.splitlines() if line.strip().startswith("uses:")
    ]
    assert uses_lines, "expected at least one uses: line"
    pattern = re.compile(r"^uses:\s+[\w./-]+@[0-9a-f]{40}(\s+#.*)?$")
    for line in uses_lines:
        assert pattern.match(line), f"not SHA-pinned: {line}"


def test_workflow_references_the_script():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "scripts/release_tag_hygiene.py" in text


def test_baseline_file_exists_and_parses():
    assert BASELINE_PATH.exists()


def test_baseline_contains_required_entries(rth):
    baseline = rth.load_baseline(BASELINE_PATH)
    for tag in ("v5.9", "v5.10.0", "v5.11.0"):
        assert tag in baseline, f"{tag} missing from baseline"
        assert baseline[tag], f"{tag} has an empty reason"
