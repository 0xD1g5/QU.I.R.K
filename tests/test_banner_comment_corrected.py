"""Phase 77-03 D-17 (api-cli-core/IN-02): banner _FACES comment correction.

RESEARCH C-5 / Pitfall 4: the audit row + CONTEXT both misread the code.
`_FACES = (r"...")` is already a raw string, so `\\-` is literal text. The
COMMENT at banner.py:64 is misleading. Only the comment is wrong, not the code.
"""
from __future__ import annotations

import pathlib


def test_banner_faces_comment_states_raw_string() -> None:
    """D-17: banner.py must contain a corrected comment naming `_FACES` as a raw
    string. The audit closure phrase is checked verbatim so PLAN 77-05 can
    cross-reference."""
    src = pathlib.Path("quirk/cli/banner.py").read_text(encoding="utf-8")
    assert "raw string" in src, "D-17: corrected raw-string comment missing"
    # Closure citation so PLAN 77-05 can mechanical-grep the audit row flip.
    assert "api-cli-core/IN-02" in src, "D-17: audit-row closure citation missing"


def test_banner_faces_code_unchanged() -> None:
    """D-17: the `_FACES = (r"..."` raw string literal must be preserved exactly
    — the audit fix is comment-only per RESEARCH C-5."""
    src = pathlib.Path("quirk/cli/banner.py").read_text(encoding="utf-8")
    assert "_FACES = (\n" in src or "_FACES = (" in src
    # The raw string head must still start with r"
    assert 'r"     @__' in src, "D-17: _FACES raw string literal modified — must be untouched"
