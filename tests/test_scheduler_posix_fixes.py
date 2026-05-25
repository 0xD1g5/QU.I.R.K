"""SENSOR-05 regression guards: scheduler_cmd.py POSIX-ism fixes.

Static source analysis — these tests do NOT invoke the scheduler.
They guard against regressions of:
  1. CWD-relative output path (SENSOR-05 Fix 1)
  2. Unconditional SIGTERM registration (SENSOR-05 Fix 2)
"""
import io
import pathlib
import tokenize

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEDULER_SRC = REPO_ROOT / "quirk" / "cli" / "scheduler_cmd.py"


def _strip_comments(src: str) -> str:
    """Strip Python comments using tokenize (handles # in string literals correctly).

    Copied from tests/scanner/test_phase57_invariants.py — authoritative version.
    """
    chars = list(src)
    for tok_type, tok_string, tok_start, tok_end, _ in tokenize.generate_tokens(
        io.StringIO(src).readline
    ):
        if tok_type == tokenize.COMMENT:
            lines = src.splitlines(keepends=True)
            start_offset = sum(len(lines[i]) for i in range(tok_start[0] - 1)) + tok_start[1]
            end_offset = sum(len(lines[i]) for i in range(tok_end[0] - 1)) + tok_end[1]
            for i in range(start_offset, end_offset):
                chars[i] = " "
    return "".join(chars)


def test_output_dir_anchored():
    """SENSOR-05 Fix 1: output_dir must be anchored to cfg.output.directory, not CWD-relative."""
    src = _strip_comments(SCHEDULER_SRC.read_text())
    assert 'Path("output/scheduled")' not in src, (
        "scheduler_cmd.py still uses CWD-relative Path('output/scheduled') — "
        "regression of SENSOR-05 Fix 1"
    )
    assert "cfg.output.directory" in src, (
        "scheduler_cmd.py does not reference cfg.output.directory — "
        "SENSOR-05 Fix 1 not applied"
    )


def test_sigterm_guard():
    """SENSOR-05 Fix 2: SIGTERM registration must be guarded by sys.platform != 'win32'."""
    src = _strip_comments(SCHEDULER_SRC.read_text())
    assert 'sys.platform != "win32"' in src, (
        "scheduler_cmd.py missing sys.platform != 'win32' guard — "
        "regression of SENSOR-05 Fix 2"
    )
    assert "signal.SIGTERM" in src, (
        "scheduler_cmd.py missing signal.SIGTERM reference — unexpected"
    )
    # Assert the platform guard immediately governs SIGTERM registration.
    # Find the guard and verify SIGTERM appears within 5 lines after it.
    lines = src.splitlines()
    guard_line = None
    for i, line in enumerate(lines):
        if 'sys.platform != "win32"' in line:
            guard_line = i
            break
    assert guard_line is not None, "platform guard not found in source"
    nearby = "\n".join(lines[guard_line : guard_line + 5])
    assert "signal.SIGTERM" in nearby, (
        f"signal.SIGTERM not found within 5 lines after platform guard (line {guard_line + 1}) — "
        "platform check must immediately govern SIGTERM registration"
    )
