"""Phase 201 (ADVISORY-02) — permanent, falsifiable regression guard: the
scoring and persistence surfaces must never import, call, or transit
``quirk.intelligence.score_lift``.

This is the REVERSE of ADVISORY-01 (``tests/test_remediation_advisory_guard.py``,
Phase 179+): that guard bans the remediation/closure surface from importing the
score producer (``scoring.py``); this guard bans the score producer and its
persistence surfaces from importing the score CONSUMER
(``quirk.intelligence.score_lift``). A projected/simulated score that ever
leaks into a real score surface is the exact failure mode Phase 201 exists to
prevent (T-201-01).

Mirrors ``tests/test_remediation_advisory_guard.py``'s scaffold verbatim,
direction reversed: module tuple + `path.exists()` skip for wave-order
independence + companion all-exist test + `checked >=` floor that rises with
the tuple (D-39) + AST walk flagging only real import/from-import nodes +
mandatory negative control proving the walk can actually detect a planted
forbidden import.

This file additionally carries three runtime-purity legs with no ADVISORY-01
counterpart (RESEARCH §Runtime purity leg, T-201-02/T-201-04): deep-equality
of the caller's evidence dict across a projection call, DB-session isolation,
and base-score invariance. Those three legs, plus the whole of
``tests/test_score_lift.py``, import from ``quirk.intelligence.score_lift`` —
a module this plan deliberately does NOT create. They are RED until Plan
201-02 lands the module; that is the intended, recorded state of this file at
the end of Plan 201-01. Do NOT skip them (`pytest.importorskip` / `path.exists()`
skip) to hide the RED — a skipped purity leg is not a passing one.

``quirk/db.py`` is CRLF (see CLAUDE.md). This guard READS it only, via
``path.read_text()`` for the AST walk — it is never opened for writing here.
"""
from __future__ import annotations

import ast
import copy
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_QUIRK_INTELLIGENCE = _REPO_ROOT / "quirk" / "intelligence"
_QUIRK_MERGE = _REPO_ROOT / "quirk" / "merge"

# ADVISORY-02: the 8 modules that must never import score_lift. The score
# producer (scoring.py), the evidence producer (evidence.py), the two other
# score-computation call sites (trends.py, merge/scan.py), persistence
# (db.py), and the three remediation/closure persistence writers.
# routes/scan.py, writer.py, and executive.py are deliberately NOT guarded —
# they are score_lift's legitimate consumers (RESEARCH §ADVISORY-02 Firewall
# Design).
_GUARDED_MODULES = (
    _QUIRK_INTELLIGENCE / "scoring.py",
    _QUIRK_INTELLIGENCE / "evidence.py",
    _QUIRK_INTELLIGENCE / "trends.py",
    _QUIRK_MERGE / "scan.py",
    _REPO_ROOT / "quirk" / "db.py",
    _QUIRK_INTELLIGENCE / "remediation_persist.py",
    _QUIRK_INTELLIGENCE / "closure.py",
    _QUIRK_INTELLIGENCE / "burndown.py",
)

_FORBIDDEN_MODULE_NAMES = frozenset({"quirk.intelligence.score_lift", "score_lift"})


def _imports_forbidden_module(source: str) -> bool:
    """AST-walk `source`, return True iff it imports a forbidden module name.

    Deliberately does NOT use substring/grep matching on the source text —
    an AST walk only flags genuine `import`/`from ... import` statements, so
    a comment or docstring mentioning the module name (as this very file's
    own docstring does, in prose) can never produce a false positive.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _FORBIDDEN_MODULE_NAMES:
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in _FORBIDDEN_MODULE_NAMES:
                return True
            for alias in node.names:
                if alias.name in _FORBIDDEN_MODULE_NAMES:
                    return True
    return False


def test_scoring_and_persistence_modules_never_import_score_lift() -> None:
    checked = 0
    for path in _GUARDED_MODULES:
        if not path.exists():
            # A not-yet-landed module (wave-order independence) — skip
            # gracefully. test_guarded_modules_all_exist catches a module
            # that is STILL missing once the phase has landed.
            continue
        checked += 1
        source = path.read_text()
        assert not _imports_forbidden_module(source), (
            f"{path} imports the forward-projection module "
            "quirk.intelligence.score_lift — ADVISORY-02 violated"
        )
    # D-39: the floor rises with _GUARDED_MODULES. All 8 of scoring.py,
    # evidence.py, trends.py, merge/scan.py, db.py, remediation_persist.py,
    # closure.py, and burndown.py exist as of this plan; a checked count
    # below 8 means one of them was silently skipped.
    assert checked >= 8, (
        "expected all 8 guarded modules to be checked "
        "(scoring.py, evidence.py, trends.py, merge/scan.py, db.py, "
        f"remediation_persist.py, closure.py, burndown.py) but only checked={checked}"
    )


def test_guarded_modules_all_exist() -> None:
    """Companion to the `path.exists(): continue` skip above: that skip keeps
    the guard wave-order independent DURING a phase, but once a phase has
    landed, a permanently-missing guarded module must fail loudly rather
    than silently reduce `checked` below the floor.
    """
    missing = [str(p) for p in _GUARDED_MODULES if not p.exists()]
    assert missing == [], f"guarded module(s) missing on disk: {missing}"


def test_negative_control_ast_walk_detects_a_real_forbidden_import() -> None:
    """Prove the guard CAN fail: apply the same AST walk to a fixture source
    string that DOES import the forbidden module, two different ways, and
    assert detection; a clean fixture that only mentions the module name in
    prose (comment/string) must NOT be detected.

    This is the mandatory negative control. It was RE-RUN live during
    execution of this plan (201-01): a temporary
    `import quirk.intelligence.score_lift` line was added to
    `quirk/intelligence/scoring.py`,
    `test_scoring_and_persistence_modules_never_import_score_lift` was
    observed to fail RED naming that path with the ADVISORY-02 message above,
    and the line was then reverted (`git diff --stat quirk/` confirmed
    empty). See 201-01-SUMMARY.md for the recorded RED transcript.
    `quirk/db.py` was deliberately NOT used as the injection target (CRLF
    hazard, per CLAUDE.md) — `scoring.py` is the safe injection target for
    this protocol.
    """
    fixture_plain_import = (
        "from __future__ import annotations\n"
        "import quirk.intelligence.score_lift\n"
        "\n"
        "def foo():\n"
        "    return quirk.intelligence.score_lift.compute_projected_score\n"
    )
    assert _imports_forbidden_module(fixture_plain_import) is True

    fixture_from_import = (
        "from __future__ import annotations\n"
        "from quirk.intelligence import score_lift\n"
        "\n"
        "def bar():\n"
        "    return score_lift.compute_item_lifts\n"
    )
    assert _imports_forbidden_module(fixture_from_import) is True

    fixture_clean = (
        "from __future__ import annotations\n"
        "# this comment mentions quirk.intelligence.score_lift in prose only\n"
        "def baz():\n"
        "    return \"quirk.intelligence.score_lift is also fine inside a string\"\n"
    )
    assert _imports_forbidden_module(fixture_clean) is False


def _purity_evidence() -> dict:
    """A nested evidence fixture exercising every sub-Mapping key the
    delta-scoring functions read/mutate (RESEARCH §Evidence-Delta Map),
    used to prove the projection API never shallow-copies and leaks
    mutations back into the caller's live evidence dict (Pitfall 5).
    """
    return {
        "totals": {"endpoints": 10, "findings": 7},
        "protocol_counts": {"TLS": 6, "HTTP": 2, "SSH": 1, "UNKNOWN": 1},
        "plaintext_http_count": 1,
        "http_on_tls_port_count": 1,
        "mtls_present_count": 1,
        "certificate_observations": {
            "expired_count": 1,
            "expiring_count": 2,
            "self_signed_count": 1,
            "certs_observed": 8,
        },
        "cert_key_type_counts": {"RSA": 6, "ECDSA": 0},
        "scan_error": {"rate": 0.3},
        "finding_severity_counts": {
            "CRITICAL": 0,
            "HIGH": 2,
            "MEDIUM": 1,
            "LOW": 1,
            "INFO": 1,
        },
    }


def _purity_items(evidence: dict):
    from quirk.intelligence.roadmap import build_phased_roadmap
    from quirk.intelligence.scoring import compute_readiness_score

    return build_phased_roadmap(evidence, compute_readiness_score(evidence))["items"]


def test_projection_api_does_not_mutate_input_evidence() -> None:
    """Runtime purity leg 1 (T-201-02): the projection API must never leak a
    mutation back into the caller's live evidence dict — a shallow `dict()`
    copy of the top level shares every nested sub-Mapping (Pitfall 5), and a
    leaked mutation would move the REAL score computed later from the same
    evidence object.
    """
    from quirk.intelligence.score_lift import (
        compute_item_lifts,
        compute_projected_score,
    )

    evidence = _purity_evidence()
    pre_image = copy.deepcopy(evidence)
    items = _purity_items(evidence)

    compute_item_lifts(evidence, items)
    compute_projected_score(evidence, items)

    assert evidence == pre_image, (
        "compute_item_lifts/compute_projected_score mutated the caller's "
        "evidence dict — ADVISORY-02 / T-201-02 violated"
    )


def test_projection_api_touches_no_db_session() -> None:
    """Runtime purity leg 2 (T-201-04): the projection API must never reach a
    DB session — monkeypatch `quirk.db.get_session` to raise, and prove both
    projection calls still succeed.
    """
    import quirk.db as quirk_db
    from quirk.intelligence.score_lift import (
        compute_item_lifts,
        compute_projected_score,
    )

    def _raise(*args, **kwargs):
        raise AssertionError(
            "projection API touched a DB session — ADVISORY-02 / T-201-04 violated"
        )

    original = quirk_db.get_session
    quirk_db.get_session = _raise
    try:
        evidence = _purity_evidence()
        items = _purity_items(evidence)
        # Must not raise.
        compute_item_lifts(evidence, items)
        compute_projected_score(evidence, items)
    finally:
        quirk_db.get_session = original


def test_base_score_is_invariant_across_projection() -> None:
    """Runtime purity leg 3: the REAL base score must be byte-identical
    before and after running the projection API over the same evidence dict.
    """
    from quirk.intelligence.score_lift import (
        compute_item_lifts,
        compute_projected_score,
    )
    from quirk.intelligence.scoring import compute_readiness_score

    evidence = _purity_evidence()
    items = _purity_items(evidence)

    before = compute_readiness_score(evidence, profile=None)["score"]
    compute_item_lifts(evidence, items)
    compute_projected_score(evidence, items)
    after = compute_readiness_score(evidence, profile=None)["score"]

    assert before == after, (
        f"base score moved across projection calls: {before!r} -> {after!r} "
        "— ADVISORY-02 violated"
    )


def test_real_score_surfaces_carry_no_projected_key() -> None:
    """Static leg (T-201-01): the real score surfaces must never gain a
    `projected`/`lift`-named key.

    - `quirk/reports/writer.py`'s intelligence-JSON `"score"` allowlist
      block (the dict literal whose values are `score.get(...)` calls,
      opened by the `"score": {` marker inside the `intelligence = {...}`
      literal) must contain no key whose name contains "projected" or
      "lift".
    - `ScoreData.model_fields` (quirk/dashboard/api/schemas.py) must contain
      no field name containing "projected" or "lift" — `projected_score`
      belongs at the `ScanLatestResponse` top level, a sibling of `score`,
      never inside `ScoreData` itself (UI-SPEC locked).
    """
    writer_path = _REPO_ROOT / "quirk" / "reports" / "writer.py"
    source = writer_path.read_text()

    marker = '"score": {'
    start = source.index(marker)
    # The allowlist block closes at the next top-level "}," at the same
    # indentation as the opening brace's own line; the simplest robust
    # scope is "up to the next sibling top-level key" — "confidence": is
    # the very next key emitted after the score block (writer.py:616).
    end_marker = '"confidence": conf,'
    end = source.index(end_marker, start)
    score_block = source[start:end]

    bad_keys = [
        line.strip()
        for line in score_block.splitlines()
        if ('"' in line and ":" in line)
        and (
            "projected" in line.split(":")[0].lower()
            or "lift" in line.split(":")[0].lower()
        )
    ]
    assert bad_keys == [], (
        f"intelligence-JSON 'score' allowlist block gained a projected/lift "
        f"key — ADVISORY-02 violated: {bad_keys}"
    )

    from quirk.dashboard.api.schemas import ScoreData

    bad_fields = [
        name
        for name in ScoreData.model_fields
        if "projected" in name.lower() or "lift" in name.lower()
    ]
    assert bad_fields == [], (
        f"ScoreData gained a projected/lift field — ADVISORY-02 violated "
        f"(projected_score must live at ScanLatestResponse top level): {bad_fields}"
    )
