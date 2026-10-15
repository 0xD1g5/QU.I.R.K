"""Standing guard: product files must never tell users ``pip install quirk[...]``.

The PyPI distribution is ``quirk-scanner``. ``pip install quirk[extra]`` resolves
whatever unrelated project owns the name ``quirk`` (supply-chain hazard). The
ledger gate only scans user-facing docs; this scans every file under ``quirk/``
plus ``run_scan.py`` (Phase 226 D-18).
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WRONG_RE = re.compile(r"pip3?\s+install\s+(?:-[\w-]+\s+)*['\"]?quirk(?![\w-])")


def find_wrong_install_hints(paths):
    hits = []
    for root in paths:
        root = Path(root)
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for f in files:
            if not f.is_file() or "__pycache__" in f.parts:
                continue
            try:
                text = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if WRONG_RE.search(line):
                    hits.append((str(f), n, line.strip()))
    return hits


def test_no_wrong_package_install_hints_in_product():
    hits = find_wrong_install_hints([REPO / "quirk", REPO / "run_scan.py"])
    for path, n, line in hits:
        print(f"{path}:{n}: {line}")
    assert hits == []


def test_wrong_install_hint_scanner_is_not_vacuous(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("pip install quirk[db]\n", encoding="utf-8")
    good = tmp_path / "good.txt"
    good.write_text("pip install 'quirk-scanner[db]'\n", encoding="utf-8")
    hits = find_wrong_install_hints([bad, good])
    assert len(hits) == 1
    assert hits[0][0] == str(bad)
