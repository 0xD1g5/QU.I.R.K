"""Phase 172 D-01/D-02: CLI-level regression tests for the argparse-time
``--fuzz`` safety refusals.

Covers SAFE-01 (``--fuzz`` with non-interactive stdin) and SAFE-02
(``--fuzz-budget`` above the 500 ceiling), both of which are refused at
``run_scan.py``'s post-``parse_args()`` layer before any config load, banner,
or scan phase machinery runs (see the block added just after the
``targets_file`` validation in ``run_scan.py``).

Falsifiability: reverting the ``run_scan.py`` post-parse-args FUZZ-001/
FUZZ-002 check block added in Phase 172-01 Task 2 (or moving those checks
back inside ``_run_fuzz_phase``, where ``_wrapped_phase``'s
``except BaseException`` handler swallows a raised ``ValueError`` and the
non-TTY gate's ``False`` return is treated as an ordinary empty phase
result) makes every subprocess-level test in this file fail with
``returncode == 0`` instead of the expected ``2``, and the unit-level
predicate tests fail because ``_fuzz_budget_exceeds_ceiling`` /
``_fuzz_requires_interactive_refusal`` would no longer exist to import.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

from tests.cli_helpers import run_fork_safe

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_scan_path() -> Path:
    return _REPO_ROOT / "run_scan.py"


def _write_repro_fixtures(tmp_path: Path) -> tuple[Path, Path]:
    """Build a minimal OpenAPI spec + scratch config, mirroring
    RESEARCH.md § 7's setup so --fuzz reaches a real, non-empty
    openapi_endpoints result rather than short-circuiting earlier."""
    spec_path = tmp_path / "mini-spec.json"
    spec_path.write_text(
        '{"openapi":"3.0.0","info":{"title":"t","version":"1"},'
        '"paths":{"/x":{"get":{"responses":{"200":{"description":"ok"}}}}}}'
    )

    config_path = tmp_path / "repro-config.yaml"
    cfg = yaml.safe_load((_REPO_ROOT / "config.yaml").read_text())
    db_path = tmp_path / "quirk.db"
    cfg.setdefault("scan", {})["openapi_spec_path"] = str(spec_path)
    cfg.setdefault("targets", {})["fqdns"] = []
    cfg.setdefault("output", {})["db_path"] = str(db_path)
    config_path.write_text(yaml.safe_dump(cfg))
    return spec_path, config_path


def _base_argv(spec_path: Path, config_path: Path) -> list[str]:
    db_path = config_path.parent / "quirk.db"
    return [
        sys.executable,
        str(_run_scan_path()),
        "--config",
        str(config_path),
        "--openapi-spec",
        str(spec_path),
        "--db-path",
        str(db_path),
        "--quiet",
    ]


def test_fuzz_non_tty_stdin_refused_exit_2(tmp_path: Path) -> None:
    """--fuzz with non-TTY stdin (input="") exits 2 with [QRK-FUZZ-001]."""
    spec_path, config_path = _write_repro_fixtures(tmp_path)
    argv = _base_argv(spec_path, config_path) + ["--fuzz"]
    result = run_fork_safe(argv, timeout=30, input="")
    assert result.returncode == 2, (
        f"expected exit=2, got exit={result.returncode}; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "[QRK-FUZZ-001]" in result.stderr, (
        f"expected [QRK-FUZZ-001] in stderr; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_fuzz_budget_over_ceiling_refused_exit_2(tmp_path: Path) -> None:
    """--fuzz --fuzz-budget 501 exits 2 with [QRK-FUZZ-002]."""
    spec_path, config_path = _write_repro_fixtures(tmp_path)
    argv = _base_argv(spec_path, config_path) + [
        "--fuzz",
        "--fuzz-budget",
        "501",
    ]
    result = run_fork_safe(argv, timeout=30, input="")
    assert result.returncode == 2, (
        f"expected exit=2, got exit={result.returncode}; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "[QRK-FUZZ-002]" in result.stderr, (
        f"expected [QRK-FUZZ-002] in stderr; "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_fuzz_budget_at_ceiling_is_legal(tmp_path: Path) -> None:
    """--fuzz --fuzz-budget 500 (the inclusive boundary) never produces
    FUZZ-002. It is still refused by FUZZ-001 in this non-TTY test
    environment -- assert on the absence of FUZZ-002, not the exit code."""
    spec_path, config_path = _write_repro_fixtures(tmp_path)
    argv = _base_argv(spec_path, config_path) + [
        "--fuzz",
        "--fuzz-budget",
        "500",
    ]
    result = run_fork_safe(argv, timeout=30, input="")
    assert "[QRK-FUZZ-002]" not in result.stderr, (
        f"500 is the inclusive legal boundary and must never trigger "
        f"FUZZ-002; stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_no_fuzz_flag_no_fuzz_errors(tmp_path: Path) -> None:
    """Without --fuzz at all, neither FUZZ-001 nor FUZZ-002 appears --
    the new check block does not fire for non-fuzz invocations."""
    spec_path, config_path = _write_repro_fixtures(tmp_path)
    argv = _base_argv(spec_path, config_path)
    result = run_fork_safe(argv, timeout=30, input="")
    assert "[QRK-FUZZ-001]" not in result.stderr
    assert "[QRK-FUZZ-002]" not in result.stderr


def test_fuzz_budget_predicate_unit() -> None:
    """Unit-level (no subprocess) check of the extracted budget predicate."""
    import run_scan

    assert run_scan._fuzz_budget_exceeds_ceiling(501) is True
    assert run_scan._fuzz_budget_exceeds_ceiling(500) is False


def test_fuzz_tty_predicate_unit() -> None:
    """Unit-level (no subprocess) check of the extracted TTY predicate,
    using the injectable is_tty override so no real pty is needed."""
    import run_scan

    assert run_scan._fuzz_requires_interactive_refusal(is_tty=False) is True
    assert run_scan._fuzz_requires_interactive_refusal(is_tty=True) is False
