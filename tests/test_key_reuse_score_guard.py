"""Phase 191 Plan 03 (SPKI-02 / D-02) — permanent regression guard: key-reuse
data must never influence the quantum-readiness score.

This is a dedicated file, mirroring ``tests/test_remediation_advisory_guard.py``'s
own precedent of staying separate from ``tests/test_cve_score_guard.py`` — that
file's own green result stays an independent signal, and none of its existing
skip-registry allowances are disturbed.

This guard stands forever, not just for this phase: the module it protects,
``quirk/intelligence/key_reuse.py``, is a permanent, read-only, advisory-only
surface (analogous to burndown/closure/remediation), and D-02 forbids it from
ever crossing into the scoring subsystem, directly or indirectly.

Four assertions, each protecting against a distinct leak path:

1. ``SCORE_WEIGHTS`` contains no key whose lowercase form contains "spki" or
   "key_reuse" — the most direct leak path (a scoring weight keyed on
   key-reuse data).
2. An AST-import-walk of ``quirk/intelligence/key_reuse.py``'s own source
   proves it contains no ``Import``/``ImportFrom`` node resolving to
   ``quirk.intelligence.scoring`` — a structural, not textual, guarantee
   that the module cannot call into scoring even if a future edit tried.
3. A negative control: the SAME checker function run against a fixture
   source string that DOES import ``quirk.intelligence.scoring`` must
   report a violation. Without this, assertion 2 would be green by
   omission and prove nothing (see
   ``test_remediation_advisory_guard.py``'s own module docstring: "a guard
   that can only ever pass is not a guard").
4. A structural-contract assertion backing RESEARCH.md's Pitfall 4 (the
   indirect leak path via the findings chokepoint): the real return value
   of ``compute_key_reuse_clusters`` — called against a seeded session, not
   a hand-written literal — has no top-level ``severity``, ``host``, or
   ``port`` key. That absence is what structurally prevents key-reuse data
   from ever entering ``_build_finding()``'s findings chokepoint, even by
   an indirect path a future refactor might otherwise open.
"""
from __future__ import annotations

import ast
import pathlib

from sqlalchemy.orm import sessionmaker

from quirk.intelligence.key_reuse import compute_key_reuse_clusters
from quirk.models import CryptoEndpoint

from tests.conftest import make_isolated_memory_engine

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
_KEY_REUSE_MODULE = _REPO_ROOT / "quirk" / "intelligence" / "key_reuse.py"

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


def test_score_weights_has_no_spki_or_key_reuse_key() -> None:
    from quirk.intelligence.scoring import SCORE_WEIGHTS

    bad_keys = [
        k for k in SCORE_WEIGHTS
        if "spki" in k.lower() or "key_reuse" in k.lower()
    ]
    assert bad_keys == [], (
        f"SCORE_WEIGHTS must never contain SPKI/key-reuse-derived keys (D-02): {bad_keys}"
    )


def test_key_reuse_module_never_imports_scoring() -> None:
    assert _KEY_REUSE_MODULE.exists(), f"{_KEY_REUSE_MODULE} not found"
    source = _KEY_REUSE_MODULE.read_text()
    assert not _imports_forbidden_module(source), (
        f"{_KEY_REUSE_MODULE} imports the quantum-readiness weighting module — D-02 violated"
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


def test_compute_key_reuse_clusters_result_has_no_finding_shaped_keys() -> None:
    """Structural-contract assertion backing Pitfall 4: the real return value
    of compute_key_reuse_clusters, called on a seeded session, has no
    top-level severity/host/port key — the structural absence that keeps it
    out of _build_finding()'s findings chokepoint even via an indirect path.
    """
    engine = make_isolated_memory_engine()
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        fp = "d" * 64
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

        result = compute_key_reuse_clusters(session)

        for forbidden_key in ("severity", "host", "port"):
            assert forbidden_key not in result, (
                f"compute_key_reuse_clusters result must never carry a top-level "
                f"'{forbidden_key}' key — D-02 findings-chokepoint firewall"
            )
    finally:
        session.close()
        engine.dispose()
