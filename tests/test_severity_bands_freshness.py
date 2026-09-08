"""Phase 188 SCORE-07 gate: severity-bands.json must match dump_json() output.

Mirrors tests/test_error_codes_freshness.py — both prevent silent drift
between a generator and its committed output. Closes v5.19 SCORE-05's
deferred frontend half (backlog 999.92 / audit WARN-01): prior to this gate,
`quirk/severity_bands.py`'s BAND_THRESHOLDS could drift from whatever
ScoreGauge.tsx hardcoded, with nothing to catch it.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from quirk.severity_bands import BAND_THRESHOLDS, dump_json

REPO_ROOT = Path(__file__).resolve().parent.parent
SEVERITY_BANDS_JSON = REPO_ROOT / "src" / "dashboard" / "src" / "lib" / "severity-bands.json"


def test_severity_bands_json_exists():
    assert SEVERITY_BANDS_JSON.exists(), (
        "src/dashboard/src/lib/severity-bands.json is missing. Generate with: "
        'python -c "from quirk.severity_bands import dump_json; import sys; '
        'sys.stdout.write(dump_json())" > src/dashboard/src/lib/severity-bands.json'
    )


def test_severity_bands_json_is_current():
    """severity-bands.json must byte-match live dump_json() output."""
    generated = dump_json().rstrip("\n")
    current = SEVERITY_BANDS_JSON.read_text().rstrip("\n")
    assert generated == current, (
        "src/dashboard/src/lib/severity-bands.json is stale. Regenerate with: "
        'python -c "from quirk.severity_bands import dump_json; import sys; '
        'sys.stdout.write(dump_json())" > src/dashboard/src/lib/severity-bands.json'
    )


def test_severity_bands_gate_is_not_vacuous():
    """Prove the gate would actually catch drift, not just compare a constant
    to itself.

    Mutate a copy of BAND_THRESHOLDS, re-serialize using the same shape
    dump_json() produces, and assert the result differs from the committed
    artifact. If this test cannot fail (i.e. any mutation still matches),
    the freshness gate above is not load-bearing.
    """
    mutated_thresholds = copy.deepcopy(BAND_THRESHOLDS)
    mutated_thresholds["EXCELLENT"] = mutated_thresholds["EXCELLENT"] + 1

    payload = {
        "band_order": ["EXCELLENT", "GOOD", "MODERATE", "FAIR", "POOR"],
        "band_thresholds": mutated_thresholds,
        "band_critical_allowance": {
            "EXCELLENT": 0,
            "GOOD": 0,
            "MODERATE": 0,
            "FAIR": None,
            "POOR": None,
        },
        "generated_by": "quirk.severity_bands.dump_json",
    }
    mutated_serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    committed = SEVERITY_BANDS_JSON.read_text()
    assert mutated_serialized != committed, (
        "Mutating BAND_THRESHOLDS produced the same serialization as the "
        "committed artifact — the freshness gate would not catch drift."
    )


def test_dump_json_is_deterministic():
    """Two calls in one process must be byte-identical."""
    assert dump_json() == dump_json()
