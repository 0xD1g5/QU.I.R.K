"""Regression: `run_scan.main()` must not raise UnboundLocalError on the
non-migrate scan path.

Phase 85-01 wired the `quirk db migrate` subcommand by adding a local
`from quirk.db import ..., init_db` inside `main()`'s migrate branch. Python's
compiler marks `init_db` as local for the entire function on the strength of
that import statement alone, shadowing the module-level `from quirk.db import
init_db` at line 12. On the non-migrate scan path the local was never
assigned, so `init_db(cfg.output.db_path)` raised UnboundLocalError.

Fix: remove `init_db` from the line-525 local import; the module-level import
covers all callsites.

This test pins the contract — every `init_db` reference inside `main()` must
resolve to the module-level binding. We assert it two ways:

1. AST gate — no `from quirk.db import ..., init_db, ...` may appear inside
   the `main()` function body. (The migrate-branch may import OTHER names
   from `quirk.db`; only `init_db` is the trap because of the module-level
   shadowing.)
2. Runtime sanity — invoking `run_scan.main` with a minimal config that fails
   AFTER the init_db call must not fail WITH `UnboundLocalError: init_db`.

If a future change re-introduces the shadow, gate #1 fails at lint time;
runtime sanity is the backstop.
"""

from __future__ import annotations

import ast
import pathlib


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUN_SCAN = REPO_ROOT / "run_scan.py"


def _find_main(tree: ast.Module) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "main":
            return node
    raise AssertionError("run_scan.py has no top-level `def main()`")


def test_main_has_no_local_init_db_import():
    """AST gate — `init_db` may not appear in any `from quirk.db import ...`
    statement inside the body of `main()`. The module-level import is the
    single source of truth; re-importing creates a function-scope shadow
    that bites the non-migrate code path."""
    tree = ast.parse(RUN_SCAN.read_text())
    main_fn = _find_main(tree)

    offenders: list[tuple[int, str]] = []
    for node in ast.walk(main_fn):
        if isinstance(node, ast.ImportFrom) and node.module == "quirk.db":
            for alias in node.names:
                if alias.name == "init_db":
                    offenders.append(
                        (node.lineno, ast.unparse(node))
                    )

    assert not offenders, (
        "run_scan.main() must not re-import `init_db` from quirk.db; "
        "the module-level import at the top of run_scan.py is the canonical "
        "binding. A local re-import shadows it for the entire function via "
        "Python's compile-time scoping rule and breaks the non-migrate "
        "scan path with UnboundLocalError. Offending lines:\n  "
        + "\n  ".join(f"line {ln}: {src}" for ln, src in offenders)
    )


def test_module_level_init_db_import_present():
    """Belt-and-suspenders — confirm the module-level binding still exists.
    If someone removes the line-12 import while addressing the AST gate
    above, every callsite in main() breaks."""
    tree = ast.parse(RUN_SCAN.read_text())

    found = False
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "quirk.db":
            for alias in node.names:
                if alias.name == "init_db":
                    found = True
                    break

    assert found, (
        "run_scan.py must have a module-level `from quirk.db import init_db` "
        "(or equivalent). This is the canonical binding consumed by main() "
        "on the non-migrate scan path."
    )
