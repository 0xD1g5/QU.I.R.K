"""Standing guard: every install hint in the product is shell-safe and names ``quirk-scanner``.

Phase 226 D-18 introduced this file; Phase 232 D-04/D-05 (todo 261015 WR-01/02)
widened it. What the code below checks, and nothing more:

* **Scan set.** The git-TRACKED files under four roots, ``quirk/``,
  ``run_scan.py``, ``scripts/`` and ``src/dashboard/src``, enumerated with
  ``git ls-files`` (never a recursive filesystem glob: that reaches the
  git-ignored ``quirk/.venv`` and other untracked files, so floors measured
  that way would pass locally and fail in a fresh CI checkout). Undecodable
  (binary) files are skipped by the line scan.
* **Quoting rule (any prefix).** Every ``quirk-scanner[`` or ``quirk[``
  occurrence, whether preceded by ``pip install``, a bare ``install``, prose, a
  comment marker or anything else, must lie inside a matching single- or
  double-quoted ``'quirk-scanner[<extra>]'`` / ``"quirk-scanner[<extra>]"`` on
  the same line. Unquoted, mismatched-quote and wrong-name (``quirk[``) forms
  are rejected. Unquoted brackets are glob characters in zsh, so an unquoted
  hint fails when pasted.
* **Wrong-name rule (retained).** ``WRONG_RE`` rejects ``pip install quirk``
  (with or without extras); ``quirk`` on PyPI is an unrelated project
  (supply-chain hazard).
* **Printed-hint rule.** In every tracked ``.py`` file under ``quirk/``,
  ``run_scan.py`` and ``scripts/`` (parsed with ``ast`` from bytes, so files
  with a UTF-8 BOM parse), every string literal that names ``quirk-scanner[``
  or ``quirk[`` and can reach a user (stdout, stderr, a log, an exception, a
  report) must contain the full command ``pip install 'quirk-scanner[<extra>]'``
  (or the double-quoted form) at every such occurrence. Docstrings and the
  value of an argparse-style ``help=`` keyword are excluded: they, comments and
  YAML comments may use the bare quoted form ``'quirk-scanner[<extra>]'``
  because nobody pastes them as a command. A ``.py`` file that fails to parse
  is a test failure, not a skip.
* **Floors.** The scan must see at least ``FILE_FLOOR`` tracked decodable
  files, ``SITE_FLOOR`` hint sites and ``PRINTED_FLOOR`` printed literals;
  ``quirk`` and ``run_scan.py`` must each contribute a site, and ``scripts``
  and ``src/dashboard/src`` must each contribute a scanned file. A guard that
  scans nothing fails instead of passing.
"""
from __future__ import annotations

import ast
import re
import shutil
from collections import Counter
from pathlib import Path

from tests.cli_helpers import run_fork_safe

REPO = Path(__file__).resolve().parent.parent
ROOTS = ("quirk", "run_scan.py", "scripts", "src/dashboard/src")
PY_ROOTS = ("quirk", "run_scan.py", "scripts")

WRONG_RE = re.compile(r"pip3?\s+install\s+(?:-[\w-]+\s+)*['\"]?quirk(?![\w-])")
SITE_RE = re.compile(r"(?<![\w-])quirk(?:-scanner)?\[")
QUOTED_RE = re.compile(r"""(['"])quirk-scanner\[[\w<>{},.-]+\]\1""")
PRINTED_RE = re.compile(r"""pip3? install (['"])quirk-scanner\[[\w<>{},.-]+\]\1""")
NAMES_HINT_RE = re.compile(r"(?<![\w-])quirk(?:-scanner)?\[")

# Measured on the git-TRACKED set (git ls-files) at 1197e608 (Phase 232-02):
# 465 tracked files under ROOTS, 459 decodable (quirk 210, run_scan.py 1,
# scripts 20, src/dashboard/src 228); 59 hint sites (quirk 51, run_scan.py 6,
# src/dashboard/src 2); 23 printed hint literals. Quoting does not change these
# counts. Floors are rounded down with headroom, never above the measurement.
FILE_FLOOR = 400
SITE_FLOOR = 50
PRINTED_FLOOR = 20


def tracked_files(roots=ROOTS) -> list[Path]:
    """Git-tracked files under ``roots`` (``git -C``; run_fork_safe takes no cwd)."""
    git = shutil.which("git") or "/usr/bin/git"
    r = run_fork_safe([git, "-C", str(REPO), "ls-files", "-z", "--", *roots], check=True)
    return [REPO / p for p in r.stdout.split("\0") if p]


def _root_of(path: Path) -> str:
    try:
        rel = path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return "<external>"
    for root in ROOTS:
        if rel == root or rel.startswith(root + "/"):
            return root
    return "<other>"


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def scan_lines(files):
    """Return (offenders, files_scanned_per_root, sites_per_root) for the quoting rule."""
    offenders: list[tuple[str, int, str]] = []
    scanned: Counter = Counter()
    sites: Counter = Counter()
    for f in files:
        f = Path(f)
        if not f.is_file():
            continue
        text = _read_text(f)
        if text is None:
            continue
        root = _root_of(f)
        scanned[root] += 1
        for n, line in enumerate(text.splitlines(), 1):
            spans = [m.span() for m in QUOTED_RE.finditer(line)]
            for m in SITE_RE.finditer(line):
                sites[root] += 1
                if not any(a <= m.start() < b for a, b in spans):
                    offenders.append((_rel(f), n, line.strip()))
    return offenders, scanned, sites


def find_wrong_install_hints(files):
    hits = []
    for f in files:
        f = Path(f)
        if not f.is_file():
            continue
        text = _read_text(f)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if WRONG_RE.search(line):
                hits.append((_rel(f), n, line.strip()))
    return hits


def _excluded_string_nodes(tree: ast.AST) -> set[int]:
    """ids of string nodes that are docstrings or ``help=`` values."""
    excluded: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, (ast.Constant, ast.JoinedStr)):
                excluded.update(id(n) for n in ast.walk(body[0].value))
        elif isinstance(node, ast.keyword) and node.arg == "help":
            excluded.update(id(n) for n in ast.walk(node.value))
    return excluded


def _literal_text(node: ast.AST) -> str:
    """Constant str value, or a JoinedStr's constant parts with ``{}`` for each field."""
    if isinstance(node, ast.Constant):
        return node.value
    parts = []
    for v in node.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            parts.append(v.value)
        else:
            parts.append("{}")
    return "".join(parts)


def printed_hint_literals(files) -> list[tuple[str, int, str]]:
    """Every non-docstring, non-``help=`` string literal naming ``quirk-scanner[``/``quirk[``.

    Parses with ``ast.parse(path.read_bytes())`` so a UTF-8 BOM is honoured. A
    file that does not parse raises (the caller's test fails).
    """
    found: list[tuple[str, int, str]] = []
    for f in files:
        f = Path(f)
        if f.suffix != ".py" or not f.is_file():
            continue
        tree = ast.parse(f.read_bytes(), filename=str(f))
        excluded = _excluded_string_nodes(tree)
        inner: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                inner.update(id(n) for n in ast.walk(node) if n is not node)
        for node in ast.walk(tree):
            if id(node) in excluded or id(node) in inner:
                continue
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
            elif isinstance(node, ast.JoinedStr):
                text = _literal_text(node)
            else:
                continue
            if NAMES_HINT_RE.search(text):
                found.append((_rel(f), node.lineno, text))
    return found


def printed_offenders(literals):
    """Literals where some hint occurrence is not covered by a full ``pip install '...'``."""
    bad = []
    for path, n, text in literals:
        spans = [m.span() for m in PRINTED_RE.finditer(text)]
        for m in NAMES_HINT_RE.finditer(text):
            if not any(a <= m.start() < b for a, b in spans):
                bad.append((path, n, text))
                break
    return bad


def _py_files(files):
    return [f for f in files if f.suffix == ".py" and _root_of(f) in PY_ROOTS]


# ── product tests ────────────────────────────────────────────────────────────


def test_no_unquoted_install_hints_in_product():
    offenders, _, _ = scan_lines(tracked_files(ROOTS))
    listing = "\n".join(f"{p}:{n}: {t}" for p, n, t in offenders)
    assert offenders == [], (
        f"{len(offenders)} unquoted install-hint occurrence(s); quote them as "
        f"'quirk-scanner[<extra>]' (Phase 232 D-05):\n{listing}"
    )


def test_no_wrong_package_install_hints_in_product():
    hits = find_wrong_install_hints(tracked_files(ROOTS))
    listing = "\n".join(f"{p}:{n}: {t}" for p, n, t in hits)
    assert hits == [], f"wrong-name `pip install quirk` hint(s) (Phase 226 D-18):\n{listing}"


def test_printed_hints_are_full_pip_commands():
    literals = printed_hint_literals(_py_files(tracked_files(PY_ROOTS)))
    bad = printed_offenders(literals)
    listing = "\n".join(f"{p}:{n}: {t!r}" for p, n, t in bad)
    assert bad == [], (
        f"{len(bad)} printed hint(s) lack the full `pip install 'quirk-scanner[<extra>]'` "
        f"command (Phase 232 D-04):\n{listing}"
    )
    assert len(literals) >= PRINTED_FLOOR, (
        f"only {len(literals)} printed hint literals collected (< PRINTED_FLOOR={PRINTED_FLOOR})"
    )


def test_guard_scan_is_not_vacuous():
    _, scanned, sites = scan_lines(tracked_files(ROOTS))
    total_files = sum(scanned.values())
    total_sites = sum(sites.values())
    assert total_files >= FILE_FLOOR, (
        f"scanned {total_files} tracked decodable files (< FILE_FLOOR={FILE_FLOOR}): {dict(scanned)}"
    )
    assert total_sites >= SITE_FLOOR, (
        f"found {total_sites} hint sites (< SITE_FLOOR={SITE_FLOOR}): {dict(sites)}"
    )
    assert sites["quirk"] >= 1 and sites["run_scan.py"] >= 1, f"per-root sites: {dict(sites)}"
    assert scanned["scripts"] >= 1 and scanned["src/dashboard/src"] >= 1, (
        f"per-root scanned files: {dict(scanned)}"
    )


# ── detector cases (tmp files, bypass tracked_files) ─────────────────────────


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text + "\n", encoding="utf-8")
    return p


def test_detector_rejects_every_unquoted_form(tmp_path):
    cases = [
        "install quirk-scanner[hw] to enable",
        "pip install quirk-scanner[docx]",
        "requires quirk[cloud]",
        "see ``quirk-scanner[hw]`` extras",
        "requires 'quirk-scanner[hw]\" extras",
        "pip install quirk[db]",
        "# pip install quirk-scanner[hw]",
    ]
    for i, text in enumerate(cases):
        f = _write(tmp_path, f"bad{i}.txt", text)
        offenders, _, sites = scan_lines([f])
        assert sum(sites.values()) == 1, text
        assert len(offenders) == 1, f"not flagged: {text!r}"


def test_detector_accepts_quoted_forms(tmp_path):
    cases = [
        "pip install 'quirk-scanner[hw]'",
        'pip install "quirk-scanner[docx]"',
        "install the missing extra ('quirk-scanner[<extra>]')",
    ]
    for i, text in enumerate(cases):
        f = _write(tmp_path, f"good{i}.txt", text)
        offenders, _, sites = scan_lines([f])
        assert sum(sites.values()) == 1, text
        assert offenders == [], f"wrongly flagged: {text!r}"


def test_wrong_install_hint_scanner_is_not_vacuous(tmp_path):
    bad = _write(tmp_path, "bad.txt", "pip install quirk[db]")
    bare = _write(tmp_path, "bare.txt", "pip install quirk")
    good = _write(tmp_path, "good.txt", "pip install 'quirk-scanner[db]'")
    hits = find_wrong_install_hints([bad, bare, good])
    assert sorted(h[0] for h in hits) == sorted([str(bad), str(bare)])


def test_printed_hint_detector_cases(tmp_path):
    flagged = _write(tmp_path, "flagged.py", "msg = \"install 'quirk-scanner[hw]' to enable\"")
    ok = _write(tmp_path, "ok.py", "x = 1\nmsg = f\"run pip install 'quirk-scanner[hw]' now {x}\"")
    doc = _write(tmp_path, "doc.py", "def f():\n    \"\"\"needs 'quirk-scanner[hw]'\"\"\"\n")
    helpkw = _write(
        tmp_path,
        "helpkw.py",
        "parser.add_argument(\"--x\", help=\"Requires 'quirk-scanner[hw]' extras.\")",
    )
    lits = printed_hint_literals([flagged])
    assert len(lits) == 1 and len(printed_offenders(lits)) == 1
    lits = printed_hint_literals([ok])
    assert len(lits) == 1 and printed_offenders(lits) == []
    assert printed_hint_literals([doc]) == []
    assert printed_hint_literals([helpkw]) == []
