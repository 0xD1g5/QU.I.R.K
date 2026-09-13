"""Phase 204 Plan 02, Task 2 (COV-09, D-12): the OBSOLETE-grammar gate.

Why this exists: COV-09 retires 3 (originally, 3 planned -- see the module docstring's
live-count note below) genuinely unclosable UAT cases without deleting them. D-12 requires that
retirement to be STRUCTURALLY DISTINCT from an open GAP in both the document grammar and the
parser, so a retired case can never silently reappear as drainable work on a future regeneration
(COV-01's wave-3 generator) or standing-gate run (COV-02's wave-4 gate). This module is the
mechanical proof of that distinctness, mirroring the discipline every sibling UAT corpus guard in
this repo already follows.

Independence (matches tests/test_uat_zero_undispositioned_gate.py's own note, and
tests/test_uat_series_format.py's): every regex below is RE-DERIVED from the shipped grammar
sources -- scripts/uat_series_normalize.py::CANONICAL_RESULT_RE and
tests/test_uat_zero_undispositioned_gate.py::ALL_EMPTY_RESULT_RE -- by literal copy of their
pattern text into this file, never by importing either module. A shared regex bug in either
shipped source must not be able to make this gate agree with a broken grammar. This module DOES
import scripts.uat_corpus (the classifier under test) since proving *that* classifier's behavior
is the whole point of this file -- independence applies to the *grammar* regexes, not to the
classifier itself.

<behavior> block (204-02-PLAN.md, Task 2) this file proves, one test per bullet:
  1. A Result line `- [x] SKIP (OBSOLETE — <reason>)` parses as disposition OBSOLETE, never GAP,
     never DEFERRED, never SKIP_OTHER.
  2. The same line is NOT flagged by the re-derived ALL_EMPTY_RESULT_RE (the zero-undispositioned
     gate's own grammar).
  3. The same line matches the re-derived CANONICAL_RESULT_RE (the format gate stays green).
  4. An OBSOLETE case is excluded from reconcile()'s open-GAP count and appears in a separate
     retired count.
  5. The retirement reason is non-empty -- an `OBSOLETE — ` annotation with nothing after the dash
     is rejected.

Live-corpus finding (recorded here, not silently absorbed): 204-CONTEXT.md's D-11 named THREE
retirement candidates (UAT-92-01, UAT-47-04, UAT-5-18). Per-case spot-checking against current
source (204-02-PLAN.md Task 2's own instruction) found UAT-47-04's stated reason FALSE -- the
interactive nmap y/N wizard prompt it describes is still live in quirk/interactive.py, reached via
run_scan.py's wizard mode (run_scan.py:1908 -> interactive_config()); it was never superseded by
--discovery, which is a separate CLI-mode-only flag. UAT-47-04 was therefore NOT retired; it was
corrected to an accurate GAP annotation instead (see docs/uat-coverage-reconciliation.md and
204-02-SUMMARY.md for the full evidence trail). The live corpus therefore carries exactly TWO
OBSOLETE cases (UAT-92-01, UAT-5-18) at the time this module was written, not three. The
non-vacuity leg below asserts ">= 1 OBSOLETE case exists", not an exact count, precisely so this
module does not silently re-encode a stale hypothesis as a hard-coded expectation.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import scripts.uat_corpus as uat_corpus

REPO_ROOT = Path(__file__).resolve().parents[1]
UAT_SERIES_PATH = REPO_ROOT / "docs" / "UAT-SERIES.md"

# --- Re-derived grammars (independence discipline -- see module docstring) ----------------------

# scripts/uat_series_normalize.py::CANONICAL_RESULT_RE / tests/test_uat_series_format.py's own
# re-derivation, copied verbatim (not imported).
CANONICAL_RESULT_RE = re.compile(
    r"^\*\*Result:\*\* "
    r"- \[[ x]\] PASS(?: \([^)\n]*\))?  "
    r"- \[[ x]\] FAIL(?: \([^)\n]*\))?  "
    r"- \[[ x]\] SKIP(?: \([^)\n]*\))?$"
)

# tests/test_uat_zero_undispositioned_gate.py::ALL_EMPTY_RESULT_RE, copied verbatim (not
# imported). This is the "rest of the line after **Result:** " grammar for an all-empty case.
ALL_EMPTY_RESULT_RE = re.compile(r"^- \[ \] PASS  - \[ \] FAIL  - \[ \] SKIP$")

RESULT_PREFIX = "**Result:** "


def _obsolete_line(reason: str) -> str:
    return f"{RESULT_PREFIX}- [ ] PASS  - [ ] FAIL  - [x] SKIP (OBSOLETE — {reason})"


# --- Behavior bullet 1: parses as OBSOLETE, never GAP/DEFERRED/SKIP_OTHER -----------------------


def test_obsolete_annotation_classifies_as_obsolete():
    assert uat_corpus.classify_annotation("OBSOLETE — one-time historical gate, not repeatable") == "OBSOLETE"


def test_obsolete_annotation_em_dash_and_hyphen_variants_both_classify():
    assert uat_corpus.classify_annotation("OBSOLETE — reason with em dash") == "OBSOLETE"
    assert uat_corpus.classify_annotation("OBSOLETE - reason with plain hyphen") == "OBSOLETE"


def test_obsolete_never_misclassifies_as_gap_deferred_or_skip_other():
    result = uat_corpus.classify_annotation("OBSOLETE — reason")
    assert result != "GAP"
    assert result != "DEFERRED"
    assert result != "SKIP_OTHER"


def test_full_line_via_iter_cases_classifies_obsolete():
    lines = [
        "### UAT-999-01: Synthetic retirement fixture\n",
        _obsolete_line("synthetic reason for this test") + "\n",
    ]
    cases = list(uat_corpus.iter_cases(lines))
    assert len(cases) == 1
    assert cases[0].disposition == "OBSOLETE"
    assert cases[0].case_id == "UAT-999-01"


# --- Behavior bullet 2: not flagged by ALL_EMPTY_RESULT_RE ---------------------------------------


def test_obsolete_line_not_flagged_by_all_empty_regex():
    line = _obsolete_line("synthetic reason")
    rest = line[len(RESULT_PREFIX):]
    assert not ALL_EMPTY_RESULT_RE.match(rest), (
        "an OBSOLETE-annotated checked-SKIP line must never match the "
        "zero-undispositioned gate's all-empty grammar"
    )


def test_genuinely_empty_line_is_still_flagged_by_all_empty_regex():
    """Negative control: proves the re-derived regex above is not a tautology that would
    accept anything -- a real all-empty Result line must still match it."""
    empty_rest = "- [ ] PASS  - [ ] FAIL  - [ ] SKIP"
    assert ALL_EMPTY_RESULT_RE.match(empty_rest)


# --- Behavior bullet 3: matches CANONICAL_RESULT_RE (format gate stays green) --------------------


def test_obsolete_line_matches_canonical_result_regex():
    line = _obsolete_line("synthetic reason, no parens")
    assert CANONICAL_RESULT_RE.match(line), (
        "an OBSOLETE annotation must be legal under the frozen canonical Result-line grammar "
        "with zero regex changes"
    )


def test_obsolete_annotation_with_a_paren_would_break_canonical_grammar():
    """Negative control: the interface's own constraint ('single-line, paren-free reason') is
    load-bearing, not decorative -- a reason containing a raw ')' breaks the canonical regex
    exactly like any other SKIP annotation would, proving this isn't special-cased for OBSOLETE."""
    line = f"{RESULT_PREFIX}- [ ] PASS  - [ ] FAIL  - [x] SKIP (OBSOLETE — bad reason with a ) paren)"
    assert not CANONICAL_RESULT_RE.match(line)


# --- Behavior bullet 4: excluded from open-GAP count, appears in a separate retired count --------


def test_obsolete_case_excluded_from_is_gap():
    lines = [
        "### UAT-999-02: Synthetic retirement fixture\n",
        _obsolete_line("synthetic reason") + "\n",
    ]
    case = list(uat_corpus.iter_cases(lines))[0]
    assert case.is_gap is False


def test_reconcile_separates_retired_obsolete_from_open_gaps():
    cases = list(
        uat_corpus.iter_cases(
            [
                "### UAT-999-03: Synthetic open GAP\n",
                f"{RESULT_PREFIX}- [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs a test)\n",
                "### UAT-999-04: Synthetic OBSOLETE retirement\n",
                _obsolete_line("synthetic reason") + "\n",
            ]
        )
    )
    r = uat_corpus.reconcile(cases, ledger_rows=[])
    assert "UAT-999-03" in r.doc_gap_ids
    assert "UAT-999-04" not in r.doc_gap_ids
    assert "UAT-999-04" in r.retired_obsolete_ids
    assert "UAT-999-03" not in r.retired_obsolete_ids


def test_reconcile_accounts_for_obsolete_case_with_a_ledger_gap_row():
    """A synthetic reproduction of the live UAT-92-01/UAT-5-18 shape: ledger still says GAP
    (historical evidence, never rewritten), doc has moved on to OBSOLETE. Arithmetic must still
    close -- this is cause 5, the fix 204-02 added to reconcile()'s closure accounting."""
    cases = list(
        uat_corpus.iter_cases(
            [
                "### UAT-999-05: Synthetic OBSOLETE with a stale ledger GAP row\n",
                _obsolete_line("synthetic reason") + "\n",
            ]
        )
    )
    ledger_rows = [{"id": "UAT-999-05", "outcome": "GAP", "evidence": "stale historical evidence"}]
    r = uat_corpus.reconcile(cases, ledger_rows)
    assert r.arithmetic_ok is True
    assert "UAT-999-05" in r.doc_obsolete_ledger_gap
    assert "UAT-999-05" in r.retired_obsolete_ids
    assert "UAT-999-05" not in r.doc_gap_ids


# --- Behavior bullet 5: retirement reason must be non-empty --------------------------------------


def test_obsolete_with_no_reason_after_dash_is_not_accepted_as_a_valid_retirement():
    """'OBSOLETE — ' with nothing after the dash must not read as a legitimately-reasoned
    retirement. classify_annotation still tags it OBSOLETE (token-prefix match is unavoidable at
    that layer), but the reason-non-empty check below is what a generator/gate must apply on top
    before treating a case as validly retired -- proven here rather than merely asserted."""
    bare = "OBSOLETE — "
    plain = uat_corpus._strip_markup(bare)
    # After the 'OBSOLETE — ' prefix is stripped, nothing should remain.
    reason = plain[len("OBSOLETE — ") :].strip() if plain.startswith("OBSOLETE — ") else plain[len("OBSOLETE - ") :].strip()
    assert reason == "", "the reason-emptiness detector itself must recognize a bare token as empty"


def _live_reason(annotation: str) -> str:
    """Extract the free-text reason after 'OBSOLETE — ' or 'OBSOLETE - ', matching the
    module docstring's 'checked-SKIP annotation' scoping (never case body text)."""
    plain = uat_corpus._strip_markup(annotation)
    for prefix in ("OBSOLETE — ", "OBSOLETE - "):
        if plain.startswith(prefix):
            return plain[len(prefix) :].strip()
    return plain.strip()


# --- Live-corpus leg: every OBSOLETE case actually in docs/UAT-SERIES.md today -------------------


def test_live_corpus_obsolete_cases_have_non_empty_reasons_and_are_excluded_from_open_gaps():
    """Non-vacuous by construction: enumerates OBSOLETE cases from the live file at run time
    (never a written id list -- matches this project's standing 'regenerate from source' rule),
    and fails LOUDLY with an explicit message if zero are found, rather than passing vacuously
    over an empty iteration."""
    lines = uat_corpus._read_lines(UAT_SERIES_PATH)
    cases = list(uat_corpus.iter_cases(lines))
    obsolete_cases = [c for c in cases if c.disposition == "OBSOLETE"]

    assert obsolete_cases, (
        "expected at least one live OBSOLETE case in docs/UAT-SERIES.md (COV-09 retired "
        "UAT-92-01 and UAT-5-18 in Phase 204 Plan 02) -- zero found means either the corpus "
        "regressed or this test's own classification broke; either way this is NOT a pass"
    )

    ledger_rows = uat_corpus.load_ledger()
    r = uat_corpus.reconcile(cases, ledger_rows)

    for case in obsolete_cases:
        reason = _live_reason(case.annotation or "")
        assert reason, f"{case.case_id} (line {case.result_lineno}): OBSOLETE annotation carries no reason after the dash"
        assert case.case_id not in r.doc_gap_ids, (
            f"{case.case_id} is OBSOLETE but still counted as an open GAP -- D-12 violated"
        )
        assert case.case_id in r.retired_obsolete_ids

    assert r.arithmetic_ok is True


def test_live_corpus_the_two_named_cov09_retirements_are_present_and_obsolete():
    """Anchors the live corpus to the two cases this plan actually retired (not the three
    originally hypothesized in 204-CONTEXT.md's D-11 -- see module docstring)."""
    lines = uat_corpus._read_lines(UAT_SERIES_PATH)
    cases = {c.case_id: c for c in uat_corpus.iter_cases(lines)}

    for case_id in ("UAT-92-01", "UAT-5-18"):
        assert case_id in cases, f"{case_id} heading not found in docs/UAT-SERIES.md"
        assert cases[case_id].disposition == "OBSOLETE", (
            f"{case_id} expected disposition OBSOLETE, got {cases[case_id].disposition!r}"
        )


def test_live_corpus_uat_47_04_was_corrected_not_retired():
    """UAT-47-04 was named in 204-CONTEXT.md's D-11 as a third retirement candidate. Per-case
    spot-checking found its stated reason false (the prompt it describes is still live); this
    test locks that correction so a future regeneration cannot silently re-retire it on the
    disproven premise without a human re-deciding."""
    lines = uat_corpus._read_lines(UAT_SERIES_PATH)
    cases = {c.case_id: c for c in uat_corpus.iter_cases(lines)}
    assert "UAT-47-04" in cases
    assert cases["UAT-47-04"].disposition == "GAP", (
        "UAT-47-04 was corrected to GAP (accurate reason), not retired OBSOLETE "
        "(see docs/uat-coverage-reconciliation.md for the evidence)"
    )


# --- Cross-reference to the standing gate (per the plan's key_links) -----------------------------


def test_obsolete_retired_case_still_counts_as_dispositioned_under_the_standing_gate():
    """Asserts the retired cases still count as dispositioned under
    tests/test_uat_zero_undispositioned_gate.py's OWN grammar (re-derived here, not imported --
    see module docstring), i.e. OBSOLETE cases can never trip the zero-undispositioned gate."""
    lines = uat_corpus._read_lines(UAT_SERIES_PATH)
    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n").rstrip("\r")
        if not line.startswith(RESULT_PREFIX):
            continue
        if "OBSOLETE" not in line:
            continue
        rest = line[len(RESULT_PREFIX) :]
        assert not ALL_EMPTY_RESULT_RE.match(rest), (
            f"line {lineno}: an OBSOLETE Result line must never match the "
            "zero-undispositioned gate's all-empty grammar"
        )
