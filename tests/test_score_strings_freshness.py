"""Phase 188 review WR-05 gate: score-strings.json must match its generator.

Mirrors tests/test_severity_bands_freshness.py (same phase, same enforcement
shape): the not-computed statement is composed ONCE in
quirk/reports/content_model.py::NOT_COMPUTED_STATEMENT and rendered verbatim
on every surface. The executive dashboard page previously hardcoded a SECOND
copy of the sentence as a JSX string literal — this gate kills that drift
pattern by (a) byte-matching the committed generated artifact against the
live generator, (b) proving generator sensitivity through monkeypatch (the
WR-04 lesson: pins must be derived, not pasted), and (c) asserting
executive.tsx consumes the artifact instead of re-hardcoding the sentence.
"""
from __future__ import annotations

import json
from pathlib import Path

from quirk.reports.content_model import NOT_COMPUTED_STATEMENT, dump_score_strings_json

REPO_ROOT = Path(__file__).resolve().parent.parent
SCORE_STRINGS_JSON = REPO_ROOT / "src" / "dashboard" / "src" / "lib" / "score-strings.json"
EXECUTIVE_TSX = REPO_ROOT / "src" / "dashboard" / "src" / "pages" / "executive.tsx"

_REGEN_HINT = (
    "Regenerate with: python -c \"from quirk.reports.content_model import "
    "dump_score_strings_json; import sys; sys.stdout.write(dump_score_strings_json())\" "
    "> src/dashboard/src/lib/score-strings.json"
)


def test_score_strings_json_exists():
    assert SCORE_STRINGS_JSON.exists(), (
        f"src/dashboard/src/lib/score-strings.json is missing. {_REGEN_HINT}"
    )


def test_score_strings_json_is_current():
    """score-strings.json must byte-match live dump_score_strings_json() output."""
    generated = dump_score_strings_json().rstrip("\n")
    current = SCORE_STRINGS_JSON.read_text(encoding="utf-8").rstrip("\n")
    assert generated == current, (
        f"src/dashboard/src/lib/score-strings.json is stale. {_REGEN_HINT}"
    )


def test_score_strings_gate_is_not_vacuous(monkeypatch):
    """WR-04 lesson applied here from day one: prove sensitivity through the
    REAL generator, not a pasted payload copy."""
    import quirk.reports.content_model as cm

    monkeypatch.setattr(
        cm, "NOT_COMPUTED_STATEMENT", cm.NOT_COMPUTED_STATEMENT + " (mutated)"
    )
    assert cm.dump_score_strings_json() != SCORE_STRINGS_JSON.read_text(encoding="utf-8"), (
        "Mutating NOT_COMPUTED_STATEMENT did NOT change dump_score_strings_json()'s "
        "output — the generator is no longer reading the constant and this gate "
        "is vacuous."
    )


def test_artifact_carries_the_exact_statement():
    payload = json.loads(SCORE_STRINGS_JSON.read_text(encoding="utf-8"))
    assert payload["not_computed_statement"] == NOT_COMPUTED_STATEMENT


def test_executive_tsx_consumes_artifact_not_a_hardcoded_copy():
    """The frontend must import the generated artifact; a re-hardcoded copy of
    the sentence (the exact WR-05 defect) fails here even if it happens to be
    word-identical today, because a later backend rewording would silently
    diverge the two surfaces."""
    src = EXECUTIVE_TSX.read_text(encoding="utf-8")
    assert 'from "@/lib/score-strings.json"' in src, (
        "executive.tsx no longer imports the generated score-strings.json "
        "artifact — the not-computed statement must be consumed from the "
        "single producer, never re-hardcoded per surface (WR-05)."
    )
    # The literal sentence must not appear as a hardcoded JSX string. It is
    # allowed ONLY inside the imported JSON artifact, which this file is not.
    assert NOT_COMPUTED_STATEMENT not in src, (
        "executive.tsx hardcodes a second copy of the not-computed statement — "
        "delete it and render scoreStrings.not_computed_statement instead (WR-05)."
    )
