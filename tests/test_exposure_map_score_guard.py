"""Phase 195 Plan 03 (MAP-03 / D-10) — permanent regression guard: quantum
exposure-map data must never influence the quantum-readiness score.

This is a dedicated NEW file, mirroring ``tests/test_key_reuse_score_guard.py``'s
own precedent of staying separate from ``tests/test_cve_score_guard.py`` — that
file's own green result stays an independent signal, and none of its existing
skip-registry allowances are disturbed. This file, in turn, never extends
``tests/test_cve_score_guard.py`` or ``tests/test_key_reuse_score_guard.py``
(Pitfall 4) — it is a fully independent copy, adapted for the module this
phase adds.

This guard stands forever, not just for this phase: ``quirk/intelligence/
exposure_map.py`` is a permanent, read-only, advisory-only derivation surface
(analogous to key_reuse/burndown/closure/remediation), and D-10 forbids it
from ever crossing into the scoring subsystem, directly or indirectly.

Four assertions, each protecting against a distinct leak path:

1. ``SCORE_WEIGHTS`` contains no key whose lowercase form contains
   "exposure_map", "reachability", or "crown_jewel" — the most direct leak
   path (a scoring weight keyed on exposure-map data).
2. An AST-import-walk of ``quirk/intelligence/exposure_map.py``'s own source
   proves it contains no ``Import``/``ImportFrom`` node resolving to
   ``quirk.intelligence.scoring`` — a structural, not textual, guarantee
   that the module cannot call into scoring even if a future edit tried.
3. A negative control: the SAME checker function run against a fixture
   source string that DOES import ``quirk.intelligence.scoring`` must
   report a violation. Without this, assertion 2 would be green by
   omission and prove nothing — a guard that can only ever pass is not a
   guard.
4. A structural-contract assertion: the real return value of
   ``derive_exposure_map``, called against a seeded session (not a
   hand-written literal), has no top-level ``severity``, ``host``, or
   ``port`` key, and every edge dict carries a non-empty ``evidence``
   string (D-11's evidence-required invariant, checked here as an extra
   firewall signal in addition to the dedicated test_exposure_map_edges.py
   guard).
"""
from __future__ import annotations

import ast
import pathlib

from sqlalchemy.orm import sessionmaker

from quirk.intelligence.exposure_map import derive_exposure_map
from quirk.models import CryptoEndpoint

from tests.conftest import make_isolated_memory_engine

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_EXPOSURE_MAP_MODULE = _REPO_ROOT / "quirk" / "intelligence" / "exposure_map.py"

_FORBIDDEN_MODULE_NAMES = frozenset({"quirk.intelligence.scoring", "scoring"})


def _imports_forbidden_module(source: str) -> bool:
    """AST-walk `source`, return True iff it imports a forbidden module name.

    Deliberately does NOT use substring/grep matching on the source text —
    an AST walk only flags genuine `import`/`from ... import` statements, so
    a comment or docstring mentioning the module name in prose (as this very
    file's own docstring does) can never produce a false positive.
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


def test_score_weights_has_no_exposure_map_key() -> None:
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    bad_substrings = ("exposure_map", "reachability", "crown_jewel")
    bad_keys = [
        k for k in SCORE_WEIGHTS
        if any(sub in k.lower() for sub in bad_substrings)
    ]
    assert bad_keys == [], (
        f"SCORE_WEIGHTS must never contain exposure-map-derived keys (D-10): {bad_keys}"
    )


def test_exposure_map_module_never_imports_scoring() -> None:
    assert _EXPOSURE_MAP_MODULE.exists(), f"{_EXPOSURE_MAP_MODULE} not found"
    source = _EXPOSURE_MAP_MODULE.read_text()
    assert not _imports_forbidden_module(source), (
        f"{_EXPOSURE_MAP_MODULE} imports the quantum-readiness weighting module — D-10 violated"
    )


def test_negative_control_ast_walk_detects_a_real_forbidden_import() -> None:
    """Prove the guard CAN fail: apply the same AST walk to a fixture source
    string that DOES import the forbidden module, two different ways, and
    assert detection. A guard that can only ever pass is not a guard.
    """
    fixture_plain_import = (
        "from __future__ import annotations\n"
        "import quirk.intelligence.scoring\n"
        "\n"
        "def foo():\n"
        "    return quirk.intelligence.scoring.SCORE_WEIGHTS\n"
    )
    assert _imports_forbidden_module(fixture_plain_import) is True

    fixture_from_import = (
        "from __future__ import annotations\n"
        "from quirk.intelligence import scoring\n"
        "\n"
        "def bar():\n"
        "    return scoring.SCORE_WEIGHTS\n"
    )
    assert _imports_forbidden_module(fixture_from_import) is True

    fixture_clean = (
        "from __future__ import annotations\n"
        "# this comment mentions quirk.intelligence.scoring in prose only\n"
        "def baz():\n"
        "    return 1\n"
    )
    assert _imports_forbidden_module(fixture_clean) is False


def test_derive_exposure_map_result_has_no_finding_shaped_keys() -> None:
    """Structural-contract assertion: the real return value of
    derive_exposure_map, called on a seeded session, has no top-level
    severity/host/port key — the structural absence that keeps exposure-map
    data out of _build_finding()'s findings chokepoint even via an indirect
    path. Also asserts every edge's evidence field is non-empty (D-11 signal,
    duplicated here as belt-and-suspenders alongside test_exposure_map_edges.py).
    """
    engine = make_isolated_memory_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        fp = "e" * 64
        session.add_all(
            [
                CryptoEndpoint(
                    host="a.example.com",
                    port=443,
                    protocol="TLS",
                    cert_spki_fingerprint=fp,
                    cert_subject="CN=example.com",
                    cert_pubkey_alg="RSA",
                    cert_pubkey_size=2048,
                ),
                CryptoEndpoint(
                    host="b.example.com",
                    port=443,
                    protocol="TLS",
                    cert_spki_fingerprint=fp,
                    cert_subject="CN=example.com",
                    cert_pubkey_alg="RSA",
                    cert_pubkey_size=2048,
                ),
            ]
        )
        session.commit()

        result = derive_exposure_map(session)

        for forbidden_key in ("severity", "host", "port"):
            assert forbidden_key not in result, (
                f"derive_exposure_map result must never carry a top-level "
                f"'{forbidden_key}' key — D-10 findings-chokepoint firewall"
            )

        assert result["edges"], "expected at least one key-reuse edge from the seed"
        for edge in result["edges"]:
            assert edge.get("evidence"), (
                f"every exposure-map edge must carry non-empty evidence (D-11): {edge}"
            )
    finally:
        session.close()
        engine.dispose()
