"""Structural tests for Phase 32 Plan 04 Task 2 — run_scan.py wiring.

These tests verify the scanner+findings are wired into run_scan.py without
requiring a live scan. Behavior validated:

- Imports for scan_email_targets and evaluate_email_endpoints exist.
- email_endpoints aggregation list is initialized and consumed.
- The phase timer is named "email_scanning".
- The cfg.connectors.enable_email gate is present.
- Findings merge happens (evaluate_email_endpoints called).
- Aggregation includes email_endpoints in the master endpoints tuple.
"""
from pathlib import Path

import pytest

RUN_SCAN = Path(__file__).resolve().parent.parent / "run_scan.py"


@pytest.fixture(scope="module")
def src() -> str:
    assert RUN_SCAN.exists(), f"run_scan.py not found at {RUN_SCAN}"
    return RUN_SCAN.read_text(encoding="utf-8")


def test_run_scan_imports_email_scanner(src: str):
    assert "from quirk.scanner.email_scanner import scan_email_targets" in src


def test_run_scan_imports_evaluate_email_endpoints(src: str):
    assert "evaluate_email_endpoints" in src
    assert src.count("evaluate_email_endpoints") >= 2, "import + call expected"


def test_run_scan_email_phase_timer_label(src: str):
    assert '"email_scanning"' in src


def test_run_scan_gates_on_enable_email(src: str):
    assert "cfg.connectors.enable_email" in src


def test_run_scan_aggregates_email_endpoints(src: str):
    # Must initialize, populate, and aggregate
    assert src.count("email_endpoints") >= 3, (
        "expected init + assignment + aggregation references"
    )
    # Aggregation block: '+ email_endpoints' inside the `endpoints = (...)` tuple
    assert "+ email_endpoints" in src or "email_endpoints +" in src


def test_run_scan_call_uses_session_start_and_logger(src: str):
    # The call should pass logger and session_start, matching scanner contract
    assert "scan_email_targets(" in src
    # Find substring around the call
    idx = src.index("scan_email_targets(")
    # Look up to the next 600 chars
    block = src[idx:idx + 600]
    assert "logger=logger" in block
    assert "session_start=session_start" in block


def test_run_scan_compileall(tmp_path):
    import compileall
    ok = compileall.compile_file(str(RUN_SCAN), quiet=1)
    assert ok, "run_scan.py failed to compile"


# ---------------------------------------------------------------------------
# Phase 32 Plan 08 / Task 2: Logger-signature smoke test.
#
# Regression for the bug fixed in 32-06 (commit 0c6a8c3): run_scan.py's
# email branch was calling `logger.info("...", arg1, arg2)` with stdlib
# %-style positional args, but quirk.logging_util.Logger.info(self, msg)
# only accepts a single string. The 32-04 wiring tests stubbed the logger,
# so the regression escaped until live execution.
#
# This test parses run_scan.py with `ast`, locates every logger.info()
# call inside the email-scanning block, and asserts each call has exactly
# one positional argument (matching the real Logger.info signature).
# It then drives a real Logger to confirm a sample call executes cleanly.
# ---------------------------------------------------------------------------

def test_email_branch_logger_calls_use_real_logger_signatures(capsys):
    """Regression: every logger.info() call inside the email-scanning block
    must match the canonical quirk.logging_util.Logger.info(self, msg)
    signature — exactly one positional argument, type str.

    Catches the class of bug fixed in commit 0c6a8c3 — stdlib-style
    positional %-args slipping into quirk.logging_util.Logger.info().
    """
    import ast
    import inspect
    from quirk.logging_util import Logger

    # Confirm the real Logger.info signature is what this test enforces.
    info_sig = inspect.signature(Logger.info)
    info_params = [
        p for p in info_sig.parameters.values() if p.name != "self"
    ]
    assert len(info_params) == 1, (
        f"quirk.logging_util.Logger.info must take exactly one non-self arg "
        f"(msg: str); current signature has {len(info_params)}: {info_sig}"
    )

    tree = ast.parse(RUN_SCAN.read_text(encoding="utf-8"))

    # Find the email-scanning `with _phase_timer(..., "email_scanning"):` block.
    email_block_node = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.With):
            continue
        for item in node.items:
            ctx = item.context_expr
            if isinstance(ctx, ast.Call):
                for arg in ctx.args:
                    if isinstance(arg, ast.Constant) and arg.value == "email_scanning":
                        email_block_node = node
                        break
        if email_block_node is not None:
            break

    assert email_block_node is not None, (
        "Could not find `with _phase_timer(..., 'email_scanning'):` block in run_scan.py"
    )

    # Collect every logger.info(...) call inside that block.
    info_calls = []
    for node in ast.walk(email_block_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (isinstance(func, ast.Attribute)
                and func.attr == "info"
                and isinstance(func.value, ast.Name)
                and func.value.id == "logger"):
            info_calls.append(node)

    assert info_calls, (
        "Expected at least one logger.info(...) call inside the email_scanning "
        "block (currently at run_scan.py:703); found none."
    )

    # Every captured call must have exactly one positional arg, no kwargs,
    # and that arg must be a string-producing expression (Constant str or JoinedStr).
    for call in info_calls:
        line = call.lineno
        n_args = len(call.args)
        n_kwargs = len(call.keywords)
        assert n_kwargs == 0, (
            f"logger.info() at run_scan.py:{line} has {n_kwargs} kwargs; "
            f"quirk.logging_util.Logger.info accepts no kwargs."
        )
        assert n_args == 1, (
            f"logger.info() at run_scan.py:{line} has {n_args} positional args; "
            f"quirk.logging_util.Logger.info accepts exactly ONE str arg. "
            f"Stdlib-style positional %-args (info('...', x, y)) are NOT supported "
            f"and will raise TypeError at runtime — see fix in commit 0c6a8c3."
        )
        arg = call.args[0]
        # Accept literal strings (Constant) and f-strings (JoinedStr).
        is_string_expr = (
            (isinstance(arg, ast.Constant) and isinstance(arg.value, str))
            or isinstance(arg, ast.JoinedStr)
        )
        assert is_string_expr, (
            f"logger.info() at run_scan.py:{line} must be called with a string "
            f"literal or f-string, got {type(arg).__name__}."
        )

    # Smoke test: drive a real Logger with a canonical email-branch message
    # to prove the signature is honored end-to-end (would have raised
    # TypeError pre-32-06 fix when the call was logger.info(fmt, n, m)).
    real_logger = Logger(verbose=True, use_tqdm=False)
    real_logger.info("Email scan: 0 endpoints from 0 hosts")

    captured = capsys.readouterr()
    assert "Email scan: 0 endpoints from 0 hosts" in captured.out, (
        f"Real Logger did not emit the expected line; stdout: {captured.out!r}"
    )
