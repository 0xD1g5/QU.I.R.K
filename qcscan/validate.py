"""
qcscan.validate

Automated validation for QuRisk / Quantum Crypto Scanner runs.

Usage:
  python -m qcscan.validate --output-dir output
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _is_intelligence_file(p: Path) -> bool:
    return p.name.startswith("intelligence-") and p.name.endswith(".json")


def _stamp_from_name(name: str) -> Optional[str]:
    base = name.rsplit(".", 1)[0]
    toks = base.split("-")
    if len(toks) < 3:
        return None
    return f"{toks[-2]}-{toks[-1]}"


def _latest_intelligence(output_dir: Path) -> Optional[Path]:
    files = sorted(
        [p for p in output_dir.iterdir() if p.is_file() and _is_intelligence_file(p)],
        reverse=True,
    )
    return files[0] if files else None


def _previous_intelligence(output_dir: Path, current: Path) -> Optional[Path]:
    files = sorted(
        [p for p in output_dir.iterdir() if p.is_file() and _is_intelligence_file(p)],
        reverse=True,
    )
    for p in files:
        if p.resolve() != current.resolve():
            return p
    return None


def _require_keys(obj: Any, keys: List[str], where: str, errors: List[str]) -> None:
    if not isinstance(obj, dict):
        errors.append(f"{where}: expected object/dict")
        return
    for k in keys:
        if k not in obj:
            errors.append(f"{where}: missing required key '{k}'")


def _validate_intelligence(intel: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
    _require_keys(
        intel,
        ["intelligence_version", "assessment", "evidence_summary", "score", "confidence", "roadmap"],
        "intelligence",
        errors,
    )

    score = intel.get("score")
    _require_keys(score, ["total", "subscores", "drivers"], "intelligence.score", errors)

    if isinstance(score, dict):
        drivers = score.get("drivers")
        if not isinstance(drivers, list):
            errors.append("intelligence.score.drivers must be a list")
        elif len(drivers) > 5:
            warnings.append("More than 5 drivers detected (expected <=5)")

    calref = intel.get("calibration")
    if not isinstance(calref, dict):
        warnings.append("intelligence.calibration missing/invalid (expected in v3.9+)")
    else:
        prof = str(calref.get("profile") or "").strip().lower()
        if prof and prof not in ("lenient", "balanced", "strict"):
            warnings.append(f"intelligence.calibration.profile has unexpected value: {prof}")
        if not prof:
            warnings.append("intelligence.calibration.profile missing/blank")

    conf = intel.get("confidence")
    _require_keys(conf, ["confidence", "confidence_factors"], "intelligence.confidence", errors)

    roadmap = intel.get("roadmap")
    if not isinstance(roadmap, list):
        errors.append("intelligence.roadmap must be a list")


def _validate_calibration(cal: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
    if not isinstance(cal, dict):
        errors.append("calibration: expected object/dict")
        return

    if not cal.get("profile"):
        warnings.append("calibration.profile missing")
    prof = str(cal.get("profile") or "").strip().lower()
    if prof and prof not in ("lenient", "balanced", "strict"):
        warnings.append(f"calibration.profile has unexpected value: {prof}")

    if "resolved" not in cal:
        warnings.append("calibration.resolved missing")


def _validate_delta(delta: Dict[str, Any], errors: List[str]) -> None:
    _require_keys(
        delta,
        ["delta_version", "score", "confidence", "drivers", "roadmap_now", "evidence_deltas"],
        "delta",
        errors,
    )


def validate_run(output_dir: Path, require_delta_if_baseline: bool = True) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    intel_path = _latest_intelligence(output_dir)
    if not intel_path:
        return ValidationResult(False, ["No intelligence-*.json found"], [])

    stamp = _stamp_from_name(intel_path.name)
    if not stamp:
        return ValidationResult(False, ["Could not parse timestamp from intelligence file"], [])

    expected_files = [
        f"findings-{stamp}.json",
        f"assessment-{stamp}.json",
        f"executive-summary-{stamp}.md",
        f"technical-findings-{stamp}.md",
        f"scorecard-{stamp}.md",
        f"roadmap-{stamp}.md",
        f"calibration-{stamp}.json",
    ]

    for fname in expected_files:
        if not (output_dir / fname).exists():
            errors.append(f"Missing artifact: {fname}")

    intel = _load_json(intel_path)
    _validate_intelligence(intel, errors, warnings)

    cal_path = output_dir / f"calibration-{stamp}.json"
    if cal_path.exists():
        cal = _load_json(cal_path)
        _validate_calibration(cal, errors, warnings)

    prev = _previous_intelligence(output_dir, intel_path)
    delta_json = output_dir / f"delta-{stamp}.json"

    if prev and require_delta_if_baseline and not delta_json.exists():
        errors.append("Baseline exists but delta JSON missing")

    return ValidationResult(ok=(len(errors) == 0), errors=errors, warnings=warnings)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--no-require-delta", action="store_true")
    args = parser.parse_args(argv)

    res = validate_run(Path(args.output_dir), not args.no_require_delta)

    print("✅ Validation PASSED" if res.ok else "❌ Validation FAILED")

    if res.warnings:
        print("\n⚠️ Warnings:")
        for w in res.warnings:
            print(f"- {w}")

    if res.errors:
        print("\n🛑 Errors:")
        for e in res.errors:
            print(f"- {e}")

    return 0 if res.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())