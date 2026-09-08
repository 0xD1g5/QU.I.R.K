"""Phase 188 SCORE-07 gate: severity-bands.json must match dump_json() output.

Mirrors tests/test_error_codes_freshness.py — both prevent silent drift
between a generator and its committed output. Closes v5.19 SCORE-05's
deferred frontend half (backlog 999.92 / audit WARN-01): prior to this gate,
`quirk/severity_bands.py`'s BAND_THRESHOLDS could drift from whatever
ScoreGauge.tsx hardcoded, with nothing to catch it.
"""
from __future__ import annotations

from pathlib import Path

from quirk.severity_bands import dump_json

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


def test_severity_bands_gate_is_not_vacuous(monkeypatch):
    """Prove the gate would actually catch drift THROUGH the real generator,
    not through a hand-pasted copy of its payload shape.

    188 review WR-04: the prior version of this test pasted the entire payload
    (band_order, allowance table, generated_by literal) and serialized it
    locally — so if dump_json() ever stopped reading BAND_THRESHOLDS (e.g. an
    inlined literal during a refactor), the freshness gate would become truly
    vacuous while this "proof" stayed green. Sensitivity must be proven by
    mutating the module state dump_json() itself reads and asserting ITS
    output moves away from the committed artifact.
    """
    import quirk.severity_bands as sb

    mutated = dict(sb.BAND_THRESHOLDS, EXCELLENT=sb.BAND_THRESHOLDS["EXCELLENT"] + 1)
    monkeypatch.setattr(sb, "BAND_THRESHOLDS", mutated)

    assert sb.dump_json() != SEVERITY_BANDS_JSON.read_text(), (
        "Mutating BAND_THRESHOLDS did NOT change dump_json()'s output — the "
        "generator is no longer reading BAND_THRESHOLDS, so the freshness gate "
        "above is vacuous (regenerating from the broken generator would still "
        "byte-match the committed artifact)."
    )


def test_dump_json_is_deterministic():
    """Two calls in one process must be byte-identical."""
    assert dump_json() == dump_json()
