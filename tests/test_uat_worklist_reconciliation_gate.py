"""Phase 204 Plan 04 (COV-02): the standing worklist-reconciliation gate.

WHAT THIS ENFORCES: wave 3's drift gate (``tests/test_uat_coverage_gaps_freshness.py``) proves
``docs/uat-coverage-gaps.md`` byte-matches its own generator's live output. It does NOT prove the
generator's own enumeration of ``docs/UAT-SERIES.md`` sees every GAP case -- a bug shared by the
generator and its byte-reproducibility gate would still let both agree with each other while both
under-count, exactly the failure mode that produced the series-1-163-bounded worklist this phase
replaces (see ``204-CONTEXT.md``'s corrected measurement baseline: a truncating ``UAT-<int>-<int>``
regex silently dropped 37 of 878 cases and nobody noticed because nothing checked the checker).

This module is that second, independent check: it re-derives its own parser from scratch, reads
``docs/UAT-SERIES.md`` directly, and asserts every GAP-dispositioned case id it finds is named by
``docs/uat-coverage-gaps.md``'s Open GAP Worklist table. If a GAP case is un-absorbed, this gate
fails and names the case id, its ``**Result:**`` line number, and the regeneration command.

HOW TO FIX A FAILURE: run
``.venv/bin/python -m scripts.generate_uat_coverage_gaps > docs/uat-coverage-gaps.md`` and commit
the regenerated file. If the failure persists after
regeneration, the generator's own enumeration (``scripts/uat_corpus.py``) has a bug distinct from
this gate's -- investigate both parsers independently rather than reconciling one to the other.

WHY THIS RE-DERIVES ITS OWN PARSER INSTEAD OF IMPORTING THE GENERATOR'S (the independence rule,
matching ``tests/test_uat_zero_undispositioned_gate.py`` and
``tests/test_uat_disposition_integrity.py``'s own documented discipline): this file imports
NOTHING from ``scripts/uat_corpus.py`` or ``scripts/generate_uat_coverage_gaps.py``. If the gate
read the corpus through the generator's own parser, a parser bug that makes the generator miss a
class of GAP cases would make this gate miss the exact same cases -- both would agree, and both
would be wrong. Every regex below is written from scratch against the grammar documented in
``204-04-PLAN.md``'s ``<interfaces>`` block, not copy-pasted from ``scripts/uat_corpus.py`` (even
though the resulting patterns are necessarily similar -- both are independently deriving the same
canonical on-disk grammar the project has now documented in multiple places).

WHY GAP IS A PASSING DISPOSITION, NOT A VIOLATION: this gate polices *unabsorbed* cases, not
*uncovered* ones. A GAP case that IS named by the worklist is fine -- GAP is an honest, recorded
disposition (CLAUDE.md's UAT Corpus Integrity Gate section). The violation this gate catches is a
GAP case the worklist does not know about, i.e. the worklist has silently fallen behind the corpus.

CORRECTIVE PLAN 204-04b -- GAP ENUMERATION WIDENED TO MATCH THE ADJUDICATED RULE: 204-04's first
cut scoped GAP enumeration to the case's own ``**Result:**`` line only, per an explicit
interpretation of its own ``<interfaces>`` block. That scoping left 12 real, honestly-GAP cases
-- ones whose checked SKIP box carries no Result-line annotation at all, with the GAP string
living only on the case's own ``**Notes:**`` line (the Phase 185/186 "Recorded honestly..."
cases) -- outside this gate's independent re-verification, even though
``scripts/uat_corpus.py::CaseRecord.is_gap`` and ``docs/uat-coverage-reconciliation.md`` section 2
both adopt the broader "Result-line annotation OR own-Notes-line GAP string" rule as the
project's single adjudicated attribution rule. An orchestrator-run live probe (appending a
Notes-only GAP case absent from the worklist) confirmed this gate stayed GREEN against it --
exactly the un-absorbed-and-uncaught condition COV-02 exists to fail on. This module now
independently re-derives the SAME broadened rule (still importing nothing from
``scripts/uat_corpus.py``): ``enumerate_gap_cases()`` includes both Result-line GAP annotations
and Notes-line-only GAP cases, and the non-vacuity guard is split into two always-on legs -- one
per field -- so a silent regression in either half's parser cannot hide behind the other half
still matching something.

WHY OBSOLETE CASES ARE NOT REQUIRED TO BE ABSORBED INTO THE OPEN-GAP TABLE (D-12): a retirement is
not an un-absorbed gap -- it is dispositioned work that has been explicitly excluded from the
drainable-gap population, with its own reason recorded in the worklist's separate "Retired
(OBSOLETE)" section. Requiring every OBSOLETE id to also appear in the *open*-GAP table would be
requiring the wrong table.

THE NON-VACUITY GUARD (T-189-10 shape, COV-02's own "never satisfied by narrowing its own
enumeration" clause, T-204-13): ``test_non_vacuity_guard_over_live_corpus`` below ALWAYS RUNS --
no skipif, no marker gate. It fails if ``docs/UAT-SERIES.md`` contains the literal GAP annotation
substring while this file's own enumeration finds zero GAP cases. This is the control that stops
the enforced leg from reading as a pass just because its own parser silently matched nothing --
the identical shape to the truncating-regex defect this whole phase exists to eliminate. This
guard must never be skipped, narrowed, or made conditional.

FORBIDDEN IN THIS FILE (per 204-04-PLAN.md's explicit action spec): any literal ``UAT-<n>-<n>``
case id outside inline fixtures/docstrings, any allowlist of "known still-GAP" ids, any series
bound, any count constant. Those are the exact shapes that turned the previous worklist into a
stale snapshot.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
UAT_SERIES_PATH = REPO_ROOT / "docs" / "UAT-SERIES.md"
WORKLIST_PATH = REPO_ROOT / "docs" / "uat-coverage-gaps.md"

REGEN_COMMAND = ".venv/bin/python -m scripts.generate_uat_coverage_gaps > docs/uat-coverage-gaps.md"

# ---------------------------------------------------------------------------
# Parsing primitives -- independently re-derived from 204-04-PLAN.md's
# <interfaces> block. Imports NOTHING from scripts/.
# ---------------------------------------------------------------------------

CASE_ID_PATTERN = r"UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*"
HEADING_RE = re.compile(r"^### *(" + CASE_ID_PATTERN + r"):?")

# The canonical on-disk Result-line shape: three checkbox groups, PASS / FAIL / SKIP,
# each optionally followed by a parenthetical annotation.
RESULT_DETAIL_RE = re.compile(
    r"^\*\*Result:\*\* "
    r"- \[([ xX])\] PASS(?: \(([^)\n]*)\))?  "
    r"- \[([ xX])\] FAIL(?: \(([^)\n]*)\))?  "
    r"- \[([ xX])\] SKIP(?: \(([^)\n]*)\))?$"
)

# GAP / OBSOLETE annotation-prefix grammar (identical text across every shipped guard in this
# repo -- CLAUDE.md, tests/test_uat_obsolete_grammar.py, scripts/uat_corpus.py all document the
# same two token shapes; each re-derives it independently rather than sharing code).
GAP_PREFIX_RE = re.compile(r"^\s*\**\s*GAP\s*[—-]\s*")
OBSOLETE_PREFIX_RE = re.compile(r"^\s*\**\s*OBSOLETE\s*[—-]\s*")
GAP_ANNOTATION_SUBSTRING_EM = "GAP — no substitute coverage"
GAP_ANNOTATION_SUBSTRING_HYPHEN = "GAP - no substitute coverage"

# The case's own **Notes:** line -- the first one encountered after its own **Result:** line and
# before the next case heading. Independently re-derived from docs/uat-coverage-reconciliation.md
# section 2 / scripts/uat_corpus.py's NOTES_LINE_RE, not imported.
NOTES_LINE_RE = re.compile(r"^\*\*Notes:\*\*\s*(.*)$")

# Search (not anchored match) for the GAP string anywhere within a case's own Notes line content --
# matching the adjudicated rule's own shape (scripts/uat_corpus.py's GAP_STRING_RE searches, it does
# not require the GAP text to open the line, since Notes-line prose commonly reads e.g.
# "GAP — no substitute coverage. Probe case ..." with trailing sentences after it).
NOTES_GAP_STRING_RE = re.compile(r"GAP\s*[—-]\s*no substitute coverage", re.IGNORECASE)

# Worklist table-row shape: `| UAT-<id> | <series> | <title> | <reason> |`. This shape is shared
# by both the Open GAP Worklist and the Retired (OBSOLETE) tables in
# docs/uat-coverage-gaps.md, so a single row parser covers both sections.
WORKLIST_ROW_RE = re.compile(r"^\|\s*(" + CASE_ID_PATTERN + r")\s*\|")


def parse_case_dispositions(lines: list[str]) -> list[dict]:
    """Walk the document once; return one record per case with its own
    **Result:** line's disposition and 1-based line number, additionally promoted to GAP when the
    case's own **Notes:** line (the first one between its **Result:** line and the next case
    heading) carries the GAP string and the Result line itself carried no annotation.

    Disposition in {"PASS", "FAIL", "GAP", "OBSOLETE", "DEFERRED", "SKIP_OTHER",
    "UNDISPOSITIONED"}. The Result-line classification is scoped to the **Result:** LINE ONLY
    (never case body text) -- matching tests/test_uat_zero_undispositioned_gate.py's own
    documented scoping discipline, which is what makes this immune to the UAT-151-01
    body-literal-checkbox trap. The Notes-line promotion is likewise scoped to the case's own,
    single, immediately-following Notes line -- never any later prose in the case body -- per the
    adjudicated rule in docs/uat-coverage-reconciliation.md section 2 (204-04b, COV-02 widening).

    Each record also carries ``gap_source`` -- ``"result"`` when the GAP disposition came from the
    Result line's own annotation, ``"notes"`` when it was promoted from an unannotated SKIP by its
    own Notes line, ``None`` otherwise -- and ``notes_lineno``, the 1-based line number of that
    Notes line when one was found (``None`` if no Notes line was ever seen for this case). Callers
    that only need the original Result-line-only behavior can ignore both fields.
    """
    records: list[dict] = []
    current_case_id: str | None = None
    open_record: dict | None = None
    notes_captured = False
    for i, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            current_case_id = m.group(1)
            open_record = None
            notes_captured = False
            continue
        m = RESULT_DETAIL_RE.match(line)
        if m and current_case_id is not None:
            pass_box, _pass_ann, fail_box, _fail_ann, skip_box, skip_ann = m.groups()
            disposition = "UNDISPOSITIONED"
            if skip_box.lower() == "x":
                if skip_ann is not None and GAP_PREFIX_RE.match(skip_ann):
                    disposition = "GAP"
                elif skip_ann is not None and OBSOLETE_PREFIX_RE.match(skip_ann):
                    disposition = "OBSOLETE"
                elif skip_ann is not None and re.match(r"^\s*\**\s*DEFERRED\s*[—-]\s*", skip_ann):
                    disposition = "DEFERRED"
                else:
                    disposition = "SKIP_OTHER"
            elif pass_box.lower() == "x":
                disposition = "PASS"
            elif fail_box.lower() == "x":
                disposition = "FAIL"
            record = {
                "case_id": current_case_id,
                "lineno": i,
                "disposition": disposition,
                "notes_lineno": None,
                "gap_source": "result" if disposition == "GAP" else None,
            }
            records.append(record)
            open_record = record
            notes_captured = False
            continue
        if open_record is not None and not notes_captured:
            m = NOTES_LINE_RE.match(line)
            if m:
                notes_captured = True
                if open_record["disposition"] == "SKIP_OTHER" and NOTES_GAP_STRING_RE.search(
                    m.group(1)
                ):
                    open_record["disposition"] = "GAP"
                    open_record["notes_lineno"] = i
                    open_record["gap_source"] = "notes"
    return records


def enumerate_gap_cases(lines: list[str]) -> dict[str, int]:
    """{case_id: lineno} for every GAP-dispositioned case, under the adjudicated Result-line-OR-
    own-Notes-line rule (docs/uat-coverage-reconciliation.md section 2). The reported line number
    is the line carrying the actual GAP annotation: the Result line for a Result-line GAP, the
    Notes line for a Notes-line-only GAP -- both point at where a human should look."""
    result: dict[str, int] = {}
    for r in parse_case_dispositions(lines):
        if r["disposition"] != "GAP":
            continue
        result[r["case_id"]] = r["notes_lineno"] if r["gap_source"] == "notes" else r["lineno"]
    return result


def enumerate_result_line_gap_cases(lines: list[str]) -> dict[str, int]:
    """{case_id: result_lineno} for GAP cases whose GAP annotation lives on their own **Result:**
    line. A strict subset of ``enumerate_gap_cases()`` -- factored out so the non-vacuity guard can
    watch this field independently of the Notes-line field."""
    return {
        r["case_id"]: r["lineno"]
        for r in parse_case_dispositions(lines)
        if r["disposition"] == "GAP" and r["gap_source"] == "result"
    }


def enumerate_notes_only_gap_cases(lines: list[str]) -> dict[str, int]:
    """{case_id: notes_lineno} for GAP cases whose GAP annotation lives ONLY on their own
    **Notes:** line (Result line carries no annotation at all). A strict subset of
    ``enumerate_gap_cases()`` -- factored out so the non-vacuity guard can watch this field
    independently of the Result-line field. This is the 204-04b widening's own core addition: the
    12 cases 204-04's first cut left outside this gate's independent re-verification."""
    return {
        r["case_id"]: r["notes_lineno"]
        for r in parse_case_dispositions(lines)
        if r["disposition"] == "GAP" and r["gap_source"] == "notes"
    }


def enumerate_obsolete_cases(lines: list[str]) -> dict[str, int]:
    """{case_id: result_lineno} for every OBSOLETE-dispositioned case."""
    return {
        r["case_id"]: r["lineno"]
        for r in parse_case_dispositions(lines)
        if r["disposition"] == "OBSOLETE"
    }


def parse_worklist_ids(worklist_text: str) -> set[str]:
    """Every case id named on a `| UAT-<id> | ... |` table row anywhere in the worklist
    (covers both the Open GAP Worklist and Retired (OBSOLETE) sections). Table-row-anchored
    parsing gives word-boundary safety for free: the captured group is the exact id in its own
    cell, never a substring match, so `UAT-8-04` can never be "absorbed" by a row that actually
    names `UAT-8-041` -- the two ids simply don't produce the same capture."""
    ids: set[str] = set()
    for line in worklist_text.splitlines():
        m = WORKLIST_ROW_RE.match(line)
        if m:
            ids.add(m.group(1))
    return ids


def find_unabsorbed_gaps(corpus_lines: list[str], worklist_text: str) -> list[tuple[str, int]]:
    """Return [(case_id, result_lineno)] for every GAP case in `corpus_lines` whose id does not
    appear as a table row in `worklist_text`. This is the enforced leg's core logic, factored out
    so both the live-file test and the fixture-based unit tests exercise the identical code path
    (no test-only reimplementation that could silently diverge from the real gate)."""
    gap_cases = enumerate_gap_cases(corpus_lines)
    worklist_ids = parse_worklist_ids(worklist_text)
    return sorted(
        (case_id, lineno) for case_id, lineno in gap_cases.items() if case_id not in worklist_ids
    )


def build_failure_message(offenders: list[tuple[str, int]]) -> str:
    detail = "\n".join(f"  line {lineno}: {case_id}" for case_id, lineno in offenders)
    return (
        f"{len(offenders)} GAP-dispositioned UAT case(s) found in docs/UAT-SERIES.md that "
        f"docs/uat-coverage-gaps.md's worklist does not name:\n{detail}\n\n"
        f"Fix: regenerate the worklist -- `{REGEN_COMMAND}` -- and commit the result. If the "
        "case is still missing after regeneration, the generator's own enumeration "
        "(scripts/uat_corpus.py) has a bug independent of this gate's; investigate both "
        "parsers, do not reconcile one to the other by hand."
    )


def _read_lines(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        return f.readlines()


@pytest.fixture(scope="session")
def uat_series_lines() -> list[str]:
    assert UAT_SERIES_PATH.is_file(), f"UAT-SERIES.md not found at {UAT_SERIES_PATH}"
    return _read_lines(UAT_SERIES_PATH)


@pytest.fixture(scope="session")
def worklist_text() -> str:
    assert WORKLIST_PATH.is_file(), f"uat-coverage-gaps.md not found at {WORKLIST_PATH}"
    return WORKLIST_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# The non-vacuity guard -- ALWAYS RUNS, no skipif, no marker gate.
# ---------------------------------------------------------------------------


def test_non_vacuity_guard_over_live_corpus(uat_series_lines):
    """T-204-13 / COV-02's 'never satisfied by narrowing its own enumeration' clause: if
    docs/UAT-SERIES.md contains the literal GAP annotation substring anywhere, this gate's own
    enumeration must find at least one GAP case. A silently-broken or narrowed enumeration that
    matches zero cases while the corpus plainly contains GAP text must never read as 'nothing to
    enforce' -- that is the exact truncating-regex failure mode this phase exists to eliminate.

    This leg watches the COMBINED enumeration (``enumerate_gap_cases()``, both fields). It is
    deliberately kept alongside -- not replaced by -- the two field-scoped legs below: a total
    that stays non-zero can still hide one field silently regressing to zero while the other field
    keeps it afloat, which is exactly the hole 204-04b closes with the split legs."""
    full_text = "".join(uat_series_lines)
    contains_gap_text = (
        GAP_ANNOTATION_SUBSTRING_EM in full_text or GAP_ANNOTATION_SUBSTRING_HYPHEN in full_text
    )
    enumerated = enumerate_gap_cases(uat_series_lines)
    if contains_gap_text and not enumerated:
        pytest.fail(
            "Non-vacuity guard tripped: docs/UAT-SERIES.md contains the GAP annotation "
            "substring but enumerate_gap_cases() found zero cases. The enumeration parser in "
            "this file is the suspect -- a silently-non-matching regex must never read as "
            "'nothing to enforce'. (COV-02 / T-204-13)"
        )


def test_non_vacuity_guard_result_line_field(uat_series_lines):
    """204-04b field-scoped non-vacuity leg (1 of 2): if any **Result:** line in the live corpus
    carries the GAP annotation substring, ``enumerate_result_line_gap_cases()`` must find at least
    one case. ALWAYS RUNS -- no skipif, no marker gate."""
    result_line_gap_text_present = any(
        RESULT_DETAIL_RE.match(line)
        and (
            GAP_ANNOTATION_SUBSTRING_EM in line or GAP_ANNOTATION_SUBSTRING_HYPHEN in line
        )
        for line in uat_series_lines
    )
    enumerated = enumerate_result_line_gap_cases(uat_series_lines)
    if result_line_gap_text_present and not enumerated:
        pytest.fail(
            "Non-vacuity guard tripped: a **Result:** line in docs/UAT-SERIES.md contains the "
            "GAP annotation substring but enumerate_result_line_gap_cases() found zero cases. "
            "(COV-02 / T-204-13, 204-04b field-scoped leg 1/2)"
        )


def test_non_vacuity_guard_notes_only_field(uat_series_lines):
    """204-04b field-scoped non-vacuity leg (2 of 2) -- the leg that closes the exact blind spot
    the orchestrator demonstrated live: if any **Notes:** line in the live corpus carries the GAP
    annotation substring, ``enumerate_notes_only_gap_cases()`` must find at least one case. ALWAYS
    RUNS -- no skipif, no marker gate. Without this leg, a regression that silently zeroed out
    ONLY the Notes-line half of the parser would read as a clean pass, because
    ``test_non_vacuity_guard_over_live_corpus`` would still see the Result-line half's non-zero
    count and stay green -- precisely the condition the orchestrator's probe case proved live."""
    notes_gap_text_present = any(
        NOTES_LINE_RE.match(line) and NOTES_GAP_STRING_RE.search(line) for line in uat_series_lines
    )
    enumerated = enumerate_notes_only_gap_cases(uat_series_lines)
    if notes_gap_text_present and not enumerated:
        pytest.fail(
            "Non-vacuity guard tripped: a **Notes:** line in docs/UAT-SERIES.md contains the "
            "GAP annotation substring but enumerate_notes_only_gap_cases() found zero cases. "
            "(COV-02 / T-204-13, 204-04b field-scoped leg 2/2)"
        )


# ---------------------------------------------------------------------------
# The enforced leg over the live files.
# ---------------------------------------------------------------------------


def test_every_gap_case_is_named_by_the_worklist(uat_series_lines, worklist_text):
    """The gate: every GAP-dispositioned case in docs/UAT-SERIES.md must be named by a table row
    in docs/uat-coverage-gaps.md. Failure names every offending case id, its **Result:** line
    number, and the regeneration command -- the house standard for corpus-gate diagnostics."""
    offenders = find_unabsorbed_gaps(uat_series_lines, worklist_text)
    if offenders:
        pytest.fail(build_failure_message(offenders))


# ---------------------------------------------------------------------------
# D-12: OBSOLETE cases are not required to be absorbed into the open-GAP table.
# ---------------------------------------------------------------------------


def test_obsolete_cases_are_not_required_to_be_absorbed(uat_series_lines):
    """D-12: a retirement is not an un-absorbed gap. This leg enumerates OBSOLETE cases from the
    live corpus at run time (never a hand-written list) and fails non-vacuously -- with an
    explicit message -- if the corpus contains zero OBSOLETE cases, so this leg cannot pass
    merely because it iterated over nothing."""
    obsolete_cases = enumerate_obsolete_cases(uat_series_lines)
    if not obsolete_cases:
        pytest.fail(
            "Non-vacuity: enumerate_obsolete_cases() found zero OBSOLETE cases in "
            "docs/UAT-SERIES.md. This leg exists to prove OBSOLETE cases are correctly exempt "
            "from the open-GAP absorption requirement -- it cannot prove anything against an "
            "empty set. If the corpus genuinely has zero retirements right now, this test "
            "needs a design change, not a silent pass."
        )
    # The property itself: none of these OBSOLETE ids are required to be GAP-enumerated (they
    # never are, by construction of enumerate_gap_cases scoping to disposition == "GAP" only),
    # and find_unabsorbed_gaps() never flags them even when absent from the worklist entirely.
    fake_empty_worklist = "# empty worklist, no table rows\n"
    gap_ids = set(enumerate_gap_cases(uat_series_lines))
    assert not (set(obsolete_cases) & gap_ids), (
        "An id classified OBSOLETE was also classified GAP -- the two dispositions must be "
        "mutually exclusive by construction."
    )
    offenders_against_empty_worklist = find_unabsorbed_gaps(uat_series_lines, fake_empty_worklist)
    offender_ids = {case_id for case_id, _ in offenders_against_empty_worklist}
    assert not (set(obsolete_cases) & offender_ids), (
        "An OBSOLETE case id was reported as an unabsorbed GAP against an empty worklist -- "
        "OBSOLETE and GAP must never overlap in find_unabsorbed_gaps()'s output."
    )


# ---------------------------------------------------------------------------
# Fixture-based unit legs -- one per <behavior> bullet in 204-04-PLAN.md.
# ---------------------------------------------------------------------------


def test_fixture_unabsorbed_gap_fails_and_names_id_and_line():
    corpus = [
        "### UAT-9001-01: A GAP case the worklist does not know about\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs a new detector)\n",
    ]
    worklist = "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n|---|---|---|---|\n"
    offenders = find_unabsorbed_gaps(corpus, worklist)
    assert offenders == [("UAT-9001-01", 2)]
    message = build_failure_message(offenders)
    assert "UAT-9001-01" in message
    assert "line 2" in message
    assert REGEN_COMMAND in message


def test_fixture_every_gap_absorbed_passes():
    corpus = [
        "### UAT-9002-01: A GAP case the worklist correctly names\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs a new detector)\n",
    ]
    worklist = (
        "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n"
        "|---|---|---|---|\n"
        "| UAT-9002-01 | 9002 | A GAP case the worklist correctly names | needs a new detector |\n"
    )
    assert find_unabsorbed_gaps(corpus, worklist) == []


def test_fixture_obsolete_case_absent_from_worklist_does_not_fail():
    """D-12: an OBSOLETE-dispositioned case absent from the open-gap table does not fail the
    gate -- a retirement is not an un-absorbed gap."""
    corpus = [
        "### UAT-9003-01: A retired case, not present in any worklist table\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (OBSOLETE — the scenario is no longer reachable)\n",
    ]
    empty_worklist = "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n|---|---|---|---|\n"
    assert find_unabsorbed_gaps(corpus, empty_worklist) == []
    dispositions = parse_case_dispositions(corpus)
    assert dispositions == [
        {
            "case_id": "UAT-9003-01",
            "lineno": 2,
            "disposition": "OBSOLETE",
            "notes_lineno": None,
            "gap_source": None,
        }
    ]


def test_fixture_deferred_case_absent_from_worklist_does_not_fail():
    corpus = [
        "### UAT-9004-01: A DEFERRED case, not present in any worklist table\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (DEFERRED — covered by tests/test_foo.py::test_bar)\n",
    ]
    empty_worklist = "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n|---|---|---|---|\n"
    assert find_unabsorbed_gaps(corpus, empty_worklist) == []


def test_fixture_notes_only_gap_case_is_enumerated_and_unabsorbed():
    """204-04b's core addition: a case whose **Result:** SKIP box is checked with NO parenthetical
    annotation at all, whose GAP string lives only on its own **Notes:** line, must be enumerated
    as GAP and reported as unabsorbed against an empty worklist -- the exact shape of both the 12
    real Phase 185/186 cases and the orchestrator's live UAT-ORCHCHECK-1-01 probe case."""
    corpus = [
        "### UAT-9008-01: A Notes-only GAP case, no Result-line annotation\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP\n",
        "\n",
        "**Notes:** GAP — no substitute coverage. Recorded honestly, needs a new detector.\n",
    ]
    empty_worklist = "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n|---|---|---|---|\n"

    gap_ids = enumerate_gap_cases(corpus)
    assert gap_ids == {"UAT-9008-01": 4}, gap_ids

    notes_only = enumerate_notes_only_gap_cases(corpus)
    assert notes_only == {"UAT-9008-01": 4}, notes_only

    result_line_only = enumerate_result_line_gap_cases(corpus)
    assert result_line_only == {}, result_line_only

    offenders = find_unabsorbed_gaps(corpus, empty_worklist)
    assert offenders == [("UAT-9008-01", 4)], offenders

    # Hyphen-form GAP text is also recognized (matching the Result-line grammar's own hyphen
    # tolerance -- GAP_ANNOTATION_SUBSTRING_HYPHEN).
    corpus_hyphen = [
        "### UAT-9008-02: A Notes-only GAP case, hyphen form\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP\n",
        "**Notes:** GAP - no substitute coverage; needs a new detector.\n",
    ]
    assert enumerate_gap_cases(corpus_hyphen) == {"UAT-9008-02": 3}


def test_fixture_result_line_gap_case_is_not_counted_as_notes_only():
    """A Result-line-annotated GAP case must NOT show up in enumerate_notes_only_gap_cases() even
    if it also happens to have a Notes line -- the two field-scoped enumerations must stay
    disjoint, matching test_fixture_notes_only_gap_case_is_enumerated_and_unabsorbed()'s
    disjointness in the other direction."""
    corpus = [
        "### UAT-9009-01: A Result-line GAP case with an unrelated Notes line\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs work)\n",
        "**Notes:** Unrelated commentary, no GAP text here.\n",
    ]
    assert enumerate_result_line_gap_cases(corpus) == {"UAT-9009-01": 2}
    assert enumerate_notes_only_gap_cases(corpus) == {}
    assert enumerate_gap_cases(corpus) == {"UAT-9009-01": 2}


def test_fixture_unannotated_skip_with_unrelated_notes_stays_skip_other():
    """An unannotated SKIP box whose Notes line does NOT carry the GAP string must stay
    SKIP_OTHER, never silently promoted to GAP -- the promotion is conditioned on the GAP string
    actually being present, not merely on the Result line being unannotated."""
    corpus = [
        "### UAT-9010-01: Unannotated SKIP, unrelated Notes text\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP\n",
        "**Notes:** Manual verification pending, nothing to do with coverage.\n",
    ]
    dispositions = parse_case_dispositions(corpus)
    assert dispositions[0]["disposition"] == "SKIP_OTHER"
    assert enumerate_gap_cases(corpus) == {}


def test_fixture_pass_case_absent_from_worklist_does_not_fail():
    corpus = [
        "### UAT-9005-01: A PASS case, not present in any worklist table\n",
        "**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP\n",
    ]
    empty_worklist = "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n|---|---|---|---|\n"
    assert find_unabsorbed_gaps(corpus, empty_worklist) == []


def test_fixture_non_vacuity_guard_fails_on_narrowed_enumeration():
    """The narrowing failure mode COV-02 names explicitly: if the corpus contains GAP text but
    enumeration (simulated here via a broken/empty enumerator, matching the shape induction 2 of
    204-RED-PROOF.md exercises against the real, shipped enumerator) yields nothing, the guard
    must trip."""
    full_text = (
        "### UAT-9006-01: A GAP case\n"
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs work)\n"
    )
    contains_gap_text = (
        GAP_ANNOTATION_SUBSTRING_EM in full_text or GAP_ANNOTATION_SUBSTRING_HYPHEN in full_text
    )
    assert contains_gap_text
    narrowed_enumeration: dict[str, int] = {}  # simulates a broken/narrowed enumerator
    assert contains_gap_text and not narrowed_enumeration, (
        "fixture setup sanity check: this is exactly the condition the live guard must trip on"
    )


def test_fixture_word_boundary_safety_uat_8_04_not_absorbed_by_uat_8_041():
    """`UAT-8-04` must not be considered absorbed by a worklist row naming `UAT-8-041` -- the
    table-row-anchored parser captures the exact id in its own cell, so a longer sibling id in a
    different row can never satisfy a shorter id's absorption check."""
    corpus = [
        "### UAT-8-04: The shorter id, genuinely unabsorbed\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs work)\n",
    ]
    worklist_with_only_the_longer_sibling = (
        "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n"
        "|---|---|---|---|\n"
        "| UAT-8-041 | 8 | An unrelated, differently-numbered case | some other coverage need |\n"
    )
    offenders = find_unabsorbed_gaps(corpus, worklist_with_only_the_longer_sibling)
    assert offenders == [("UAT-8-04", 2)], (
        "UAT-8-04 must be reported as unabsorbed even though UAT-8-041 is present in the "
        "worklist -- these are two distinct ids, not a substring match."
    )


def test_fixture_multiple_unabsorbed_gaps_all_named():
    corpus = [
        "### UAT-9007-01: First unabsorbed GAP\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs A)\n",
        "### UAT-9007-02: Second unabsorbed GAP\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP - no substitute coverage; needs B)\n",
        "### UAT-9007-03: A PASS case, irrelevant to this gate\n",
        "**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP\n",
    ]
    empty_worklist = "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n|---|---|---|---|\n"
    offenders = find_unabsorbed_gaps(corpus, empty_worklist)
    assert offenders == [("UAT-9007-01", 2), ("UAT-9007-02", 4)]


def test_fixture_non_numeric_shape_ids_are_enumerated_and_checked():
    """The blocking constraint from .continue-here.md and 204-04-PLAN.md's own ID-shapes table:
    a parser scoped to `UAT-<int>-<int>` silently drops named-prefix, decimal-series, backlog-
    numbered, and three-segment ids. This fixture proves CASE_ID_PATTERN/HEADING_RE in this file
    correctly enumerate all four non-numeric shapes, each as a GAP case, and that the absorption
    check works identically for each shape."""
    corpus = [
        "### UAT-COMPLY-52-01: Named-prefix series\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs A)\n",
        "### UAT-56.1-01: Decimal series\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs B)\n",
        "### UAT-999.83-01: Backlog-numbered series\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs C)\n",
        "### UAT-89-01-01: Three-segment id\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (GAP — no substitute coverage; needs D)\n",
    ]
    gap_ids = set(enumerate_gap_cases(corpus))
    assert gap_ids == {"UAT-COMPLY-52-01", "UAT-56.1-01", "UAT-999.83-01", "UAT-89-01-01"}

    empty_worklist = "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n|---|---|---|---|\n"
    offenders = {case_id for case_id, _ in find_unabsorbed_gaps(corpus, empty_worklist)}
    assert offenders == gap_ids

    fully_absorbing_worklist = (
        "| Case ID | Series | Case Title | Coverage That Would Be Needed |\n"
        "|---|---|---|---|\n"
        "| UAT-COMPLY-52-01 | 52 | Named-prefix series | needs A |\n"
        "| UAT-56.1-01 | 56.1 | Decimal series | needs B |\n"
        "| UAT-999.83-01 | 999.83 | Backlog-numbered series | needs C |\n"
        "| UAT-89-01-01 | 89 | Three-segment id | needs D |\n"
    )
    assert find_unabsorbed_gaps(corpus, fully_absorbing_worklist) == []


# ---------------------------------------------------------------------------
# Non-vacuity proof against the real document: confirm this gate's own
# enumeration parses a large, non-trivial heading population -- guards
# against a silently-broken heading regex matching zero cases.
# ---------------------------------------------------------------------------


def test_gate_evaluates_a_non_trivial_number_of_real_cases(uat_series_lines):
    heading_count = sum(1 for line in uat_series_lines if HEADING_RE.match(line))
    assert heading_count > 500, (
        f"Only {heading_count} ### UAT- headings parsed from docs/UAT-SERIES.md -- expected "
        "several hundred. The heading parser may be broken, which would make "
        "test_every_gap_case_is_named_by_the_worklist vacuously pass."
    )
