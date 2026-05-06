"""Tests for quirk.validate — artifact validation."""
import json
import time
from pathlib import Path

import pytest

from quirk.validate import validate_run, _latest_intelligence


STAMP = "20260401-120000"


def _create_intelligence_json(path: Path) -> None:
    """Create a minimal valid intelligence JSON."""
    data = {
        "intelligence_version": "4.0.0",
        "assessment": {"name": "Test"},
        "evidence_summary": {},
        "score": {
            "total": 75,
            "subscores": {},
            "drivers": ["driver1"],
        },
        "confidence": {
            "confidence": 80,
            "confidence_factors": [],
        },
        "roadmap": [],
        "calibration": {
            "profile": "balanced",
            "resolved": {},
        },
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def _create_all_artifacts(output_dir: Path, stamp: str = STAMP) -> None:
    """Create all artifacts that writer.py produces."""
    output_dir.mkdir(parents=True, exist_ok=True)
    _create_intelligence_json(output_dir / f"intelligence-{stamp}.json")
    (output_dir / f"findings-{stamp}.json").write_text("[]")
    (output_dir / f"executive-summary-{stamp}.md").write_text("# Exec")
    (output_dir / f"technical-findings-{stamp}.md").write_text("# Tech")
    (output_dir / f"scorecard-{stamp}.md").write_text("# Score")
    (output_dir / f"roadmap-{stamp}.md").write_text("# Roadmap")
    (output_dir / f"run-stats-{stamp}.json").write_text("{}")
    (output_dir / f"cbom-{stamp}.cdx.json").write_text("{}")
    (output_dir / f"cbom-{stamp}.cdx.xml").write_text("<bom/>")


def test_validate_run_passes_on_complete_output(tmp_path):
    _create_all_artifacts(tmp_path)
    result = validate_run(tmp_path)
    assert result.ok is True, f"Expected pass, got errors: {result.errors}"
    assert result.errors == []


def test_validate_run_fails_on_missing_findings(tmp_path):
    _create_all_artifacts(tmp_path)
    (tmp_path / f"findings-{STAMP}.json").unlink()
    result = validate_run(tmp_path)
    assert result.ok is False
    assert any("findings-" in e for e in result.errors)


def test_validate_run_fails_on_missing_intelligence(tmp_path):
    result = validate_run(tmp_path)
    assert result.ok is False
    assert any("intelligence" in e.lower() for e in result.errors)


def test_latest_intelligence_uses_mtime(tmp_path):
    # Create two files with slightly different stamps and mtime
    older = tmp_path / "intelligence-20260401-120000.json"
    newer = tmp_path / "intelligence-20260401-120001.json"
    _create_intelligence_json(older)
    time.sleep(0.05)  # ensure mtime differs
    _create_intelligence_json(newer)
    result = _latest_intelligence(tmp_path)
    assert result is not None
    assert result.name == "intelligence-20260401-120001.json"
