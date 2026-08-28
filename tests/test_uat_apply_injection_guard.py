"""Regression guard: a ledger ``evidence`` field cannot inject document structure.

Phase 169's code review (CR-01) found that ``scripts/uat_disposition_apply.py``
validated ``evidence`` against the canonical grammar's ``)`` delimiter but not
against *structural* characters. A JSON-escaped ``\\n`` is legal JSONL, decodes
to a real newline, and -- once ``cmd_apply`` splices it into
``docs/UAT-SERIES.md`` -- can materialise a complete, fully ``[x] PASS``
fabricated UAT case.

That injection was invisible to all three existing guards at once:

* ``tests/test_uat_zero_undispositioned_gate.py`` polices *undispositioned*
  cases; the fabricated case is marked PASS.
* ``tests/test_uat_series_format.py`` asserts heading count == result-block
  count; the injection adds exactly one of each, preserving parity.
* ID uniqueness holds, because the fabricated case ID is novel.

Root cause: ``CANONICAL_RESULT_RE``'s annotation group is ``[^)]*``. A negated
character class matches newlines, and the pattern carries neither ``DOTALL``
nor ``MULTILINE``, so ``[^)]*`` swallowed an entire injected block while the
line still "matched".

Defence is two-layer and this file tests both:

1. **Input validation** -- ``_validate_evidence`` rejects CR and LF outright.
2. **Grammar** -- the annotation group excludes newlines, so a multi-line
   render can never satisfy ``CANONICAL_RESULT_RE`` even if layer 1 is bypassed.

Unlike ``tests/test_uat_disposition_integrity.py`` (which deliberately imports
nothing from ``scripts/`` so a shared parsing bug cannot make writer and checker
agree while both are wrong), this file tests the *writer itself* and therefore
must import it.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "uat_disposition_apply.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "uat_disposition_apply", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Register before exec: the module defines dataclasses, and dataclass
    # annotation resolution looks the defining module up in sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def uda():
    return _load_module()


# The exact payload from the CR-01 reproduction: evidence that closes the
# annotation early and opens a fresh, fully-passed case heading.
INJECTION_EVIDENCE = (
    "verified\n\n"
    "### UAT-999-99: Fabricated case\n\n"
    "**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP\n"
    "**Notes:** injected"
)


@pytest.mark.parametrize("outcome", ["PASS", "FAIL", "SKIP", "DEFERRED", "GAP"])
def test_validate_evidence_rejects_embedded_newline(uda, outcome):
    """Layer 1: no outcome may carry a newline through evidence validation."""
    err = uda._validate_evidence(outcome, INJECTION_EVIDENCE)
    assert err is not None, (
        f"{outcome}: newline-bearing evidence was accepted -- CR-01 injection "
        f"is reachable again"
    )
    assert "newline" in err.lower()


@pytest.mark.parametrize("char,name", [("\n", "LF"), ("\r", "CR")])
def test_validate_evidence_rejects_bare_control_characters(uda, char, name):
    err = uda._validate_evidence("PASS", f"ok{char}still ok")
    assert err is not None, f"{name} accepted in evidence"


def test_canonical_result_re_rejects_multiline_render(uda):
    """Layer 2: even if validation were bypassed, the grammar must not match."""
    line = uda._render_result_line("PASS", INJECTION_EVIDENCE)
    assert "\n" in line, "fixture no longer produces a multi-line render"
    assert not uda.CANONICAL_RESULT_RE.match(line.rstrip("\n")), (
        "CANONICAL_RESULT_RE matched a multi-line result line -- the annotation "
        "group is matching newlines again (use [^)\\n]* not [^)]*)"
    )


def test_canonical_result_re_still_accepts_legitimate_annotations(uda):
    """The fix must not break real single-line annotations."""
    line = uda._render_result_line(
        "PASS", "2026-08-28 tests/test_example.py::test_thing"
    )
    assert uda.CANONICAL_RESULT_RE.match(line.rstrip("\n")), (
        "tightening the annotation group broke a legitimate annotation"
    )


def test_validate_evidence_still_accepts_ordinary_evidence(uda):
    assert uda._validate_evidence("PASS", "2026-08-28 ran locally, exit 0") is None
