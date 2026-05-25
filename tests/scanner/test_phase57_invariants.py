"""Phase 57 phase-wide invariants. Single grep gate that asserts no
regression of the six closed audit blockers reintroduces a forbidden
pattern.

Phase 109 extension: INGEST_FILES safe_str gate covers the two new ingest
modules (console_cmd.py + sensor.py) — CONSOLE-04.
"""
import io
import pathlib
import re
import tokenize
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

SCANNER_FILES = [
    REPO_ROOT / "quirk" / "scanner" / "jwt_scanner.py",
    REPO_ROOT / "quirk" / "scanner" / "saml_scanner.py",
    REPO_ROOT / "quirk" / "scanner" / "source_scanner.py",
    REPO_ROOT / "quirk" / "scanner" / "container_scanner.py",
    REPO_ROOT / "quirk" / "scanner" / "broker_scanner.py",
]

# Phase 109 CONSOLE-04: ingest modules must not use raw str(exc) or repr(exc)
INGEST_FILES = [
    REPO_ROOT / "quirk" / "cli" / "console_cmd.py",
    REPO_ROOT / "quirk" / "dashboard" / "api" / "routes" / "sensor.py",
]


def _strip_comments(src: str) -> str:
    """Strip Python comments accurately using the tokenize module.

    Unlike splitting on '#', this correctly handles '#' inside string literals
    so that grep gates do not produce false-negatives when patterns appear in
    comments adjacent to code that uses '#' in strings.

    The source text is rebuilt as a list of characters; each comment token is
    blanked out (replaced with spaces of the same length) so that all other
    offsets — and therefore line structure — are preserved exactly.
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


@pytest.mark.parametrize("scanner_file", SCANNER_FILES, ids=lambda p: p.name)
def test_no_unconditional_verify_false(scanner_file):
    """CR-01: no verify=False literal outside comments (jwt only — but check all)."""
    src = _strip_comments(scanner_file.read_text())
    # The only acceptable form is `verify=verify_tls` (parameter pass-through).
    # A literal `verify=False` outside comments fails.
    assert "verify=False" not in src, (
        f"{scanner_file.name} contains literal verify=False outside comments — "
        "regression of CR-01"
    )


def test_broker_no_hardcoded_guest_creds():
    """CR-05: no `guest:guest` literal anywhere in broker_scanner.py."""
    src = (REPO_ROOT / "quirk" / "scanner" / "broker_scanner.py").read_text()
    assert "guest:guest" not in src, "Regression of CR-05 — guest:guest literal"
    assert b"guest:guest" not in src.encode(), "Regression of CR-05 — guest:guest bytes"


def test_broker_no_unconditional_ssl_cert_reqs_none():
    """CR-06: ssl_cert_reqs="none" must be conditional only."""
    src = _strip_comments((REPO_ROOT / "quirk" / "scanner" / "broker_scanner.py").read_text())
    # Acceptable: `ssl_cert_reqs = "none" if allow_cleartext else "required"`
    # Acceptable: `ssl_cert_reqs=ssl_cert_reqs`
    # NOT acceptable: a kwarg literal `ssl_cert_reqs="none"` in a Redis() call.
    # Match `ssl_cert_reqs="none"` occurring as a function-call kwarg pattern.
    kwarg_pattern = re.compile(r'ssl_cert_reqs\s*=\s*"none"')
    # Each match must be inside a conditional expression (either after `if`
    # on the same line or in a ternary). Heuristic: filter matches that
    # appear after an `if ` token on the same line.
    matches = []
    for line in src.splitlines():
        if kwarg_pattern.search(line) and " if " not in line:
            matches.append(line)
    assert matches == [], (
        f'Regression of CR-06 — unconditional ssl_cert_reqs="none": {matches}'
    )


def test_audit_tasks_six_blockers_closed():
    ledger = (REPO_ROOT / ".planning" / "audit-2026-05-08" / "AUDIT-TASKS.md").read_text()
    for cr in ["CR-01", "CR-02", "CR-03", "CR-04", "CR-05", "CR-06"]:
        row_pattern = re.compile(
            r"\|\s*scanners-protocol/" + cr + r"\s*\|.*\|\s*\[x\] closed\s*\|"
        )
        assert row_pattern.search(ledger), (
            f"AUDIT-TASKS.md row scanners-protocol/{cr} is not [x] closed"
        )


# ---------------------------------------------------------------------------
# Phase 109 CONSOLE-04: ingest modules must use safe_str(exc), never raw
# str(exc) or repr(exc) outside comments.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("ingest_file", INGEST_FILES, ids=lambda p: p.name)
def test_ingest_no_raw_exception_stringification(ingest_file):
    """CONSOLE-04: no str(exc) or repr(exc) in ingest path outside comments.

    Uses the existing _strip_comments tokenize helper to avoid false-positives
    from patterns appearing only in comments.
    """
    src = _strip_comments(ingest_file.read_text())
    raw_str_pattern = re.compile(r'\bstr\s*\(\s*exc\b')
    raw_repr_pattern = re.compile(r'\brepr\s*\(\s*exc\b')
    assert not raw_str_pattern.search(src), (
        f"{ingest_file.name}: raw str(exc) found outside comments — use safe_str(exc) (CONSOLE-04)"
    )
    assert not raw_repr_pattern.search(src), (
        f"{ingest_file.name}: raw repr(exc) found outside comments — use safe_str(exc) (CONSOLE-04)"
    )
