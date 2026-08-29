"""Phase 172 D-05 gate: docs/configuration.md's documented --fuzz-budget ceiling
must equal quirk.scanner.rest_fuzzer.MAX_FUZZ_BUDGET.

Mirrors tests/test_error_codes_freshness.py and tests/test_compliance_freshness.py —
all three prevent silent drift between a source of truth and its documented/generated
counterpart. Unlike those two (byte-exact file diff / production-function call), this
gate regex-extracts a numeric ceiling out of prose and compares it to the enforced
Python constant, because no exact "docs table value == code constant" precedent exists
in this repo (confirmed by PATTERNS.md's targeted grep across test_*staleness*.py and
test_*freshness*.py).

Falsifiability: this file fails if MAX_FUZZ_BUDGET is changed to any value other than
500 without a corresponding edit here, OR if any "hard max" figure in
docs/configuration.md is edited to disagree with MAX_FUZZ_BUDGET (including the
canonical `--fuzz-budget N` reference-table row going missing or being reworded so the
anchor regex no longer matches). An unmatched anchor is a failure, never a silent pass.
"""
from __future__ import annotations

import re
from pathlib import Path

from quirk.scanner.rest_fuzzer import MAX_FUZZ_BUDGET

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_MD = REPO_ROOT / "docs" / "configuration.md"

# The canonical CLI-flag reference-table row, e.g.:
#   | `--fuzz-budget N` | `50` | Maximum number of probe requests (hard max 500 — ...). |
# Anchored on the literal flag token plus a "hard max" figure on the same line so a
# reworded or deleted row is a loud match-count failure, not a silent pass.
_CANONICAL_ROW_RE = re.compile(
    r"^\|\s*`--fuzz-budget N`\s*\|.*hard max\s*\*{0,2}(\d+)\*{0,2}",
    re.MULTILINE | re.IGNORECASE,
)

# Any line mentioning --fuzz-budget together with a "hard max"-style figure. This
# deliberately excludes usage-example lines like "--fuzz --fuzz-budget 100" (docs/
# configuration.md:666), which state a *value*, not a *ceiling* — they carry no
# "hard max" token and are correctly not gated here.
_HARD_MAX_MENTION_RE = re.compile(
    r"--fuzz-budget.*hard max\s*\*{0,2}(\d+)\*{0,2}",
    re.IGNORECASE,
)


def _config_md_text() -> str:
    assert CONFIG_MD.exists(), (
        f"{CONFIG_MD} is missing — cannot verify the --fuzz-budget ceiling is documented."
    )
    return CONFIG_MD.read_text()


def test_max_fuzz_budget_constant_is_500():
    """Pin the enforced ceiling. Changing this requires also updating the 'hard max'
    figure everywhere it appears in docs/configuration.md — that two-sided edit is the
    whole point of this gate."""
    assert MAX_FUZZ_BUDGET == 500, (
        "quirk.scanner.rest_fuzzer.MAX_FUZZ_BUDGET changed. Before changing this "
        "assertion, update every 'hard max' figure in docs/configuration.md to match, "
        "then update this pin."
    )


def test_canonical_reference_row_is_locatable():
    """The `--fuzz-budget N` reference-table row must exist (docs/configuration.md
    documents it twice — the main CLI reference table and a quick-reference summary
    near the end of the file) with a stated hard-max figure on each occurrence. Zero
    matches means the row was deleted or reworded away — that is a failure, never a
    vacuous pass."""
    text = _config_md_text()
    matches = _CANONICAL_ROW_RE.findall(text)
    assert len(matches) >= 1, (
        "Expected at least one canonical `--fuzz-budget N` reference-table row with a "
        "'hard max' figure in docs/configuration.md, found none. If the row was "
        "reworded, update _CANONICAL_ROW_RE in tests/test_fuzz_budget_docs_agree.py to "
        "match the new wording — do not delete this assertion."
    )


def test_canonical_row_ceiling_matches_constant():
    """The integer documented in every canonical row must equal MAX_FUZZ_BUDGET."""
    text = _config_md_text()
    matches = _CANONICAL_ROW_RE.findall(text)
    assert matches, "Canonical --fuzz-budget row not found (see prior test)."
    for documented_ceiling in (int(n) for n in matches):
        assert documented_ceiling == MAX_FUZZ_BUDGET, (
            f"docs/configuration.md documents a --fuzz-budget hard max of "
            f"{documented_ceiling}, but MAX_FUZZ_BUDGET (quirk/scanner/rest_fuzzer.py) "
            f"is {MAX_FUZZ_BUDGET}. Update docs/configuration.md's reference-table row "
            "to match the enforced constant (or vice versa) — do not clamp silently."
        )


def test_all_hard_max_mentions_agree_with_constant():
    """Every line pairing --fuzz-budget with a 'hard max' figure must agree with
    MAX_FUZZ_BUDGET, so fixing one of the multiple prose sites and forgetting the
    others still fails the gate."""
    text = _config_md_text()
    figures = [int(n) for n in _HARD_MAX_MENTION_RE.findall(text)]
    assert len(figures) >= 1, (
        "No '--fuzz-budget ... hard max N' mentions found in docs/configuration.md — "
        "the anchor pattern may be stale. This must never silently pass on zero "
        "matches."
    )
    disagreeing = {n for n in figures if n != MAX_FUZZ_BUDGET}
    assert not disagreeing, (
        f"docs/configuration.md has --fuzz-budget hard-max mentions disagreeing with "
        f"MAX_FUZZ_BUDGET ({MAX_FUZZ_BUDGET}): found values {sorted(disagreeing)} "
        f"among {figures}. Update every 'hard max' figure in docs/configuration.md to "
        "the same value."
    )
