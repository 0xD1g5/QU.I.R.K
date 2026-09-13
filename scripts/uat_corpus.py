#!/usr/bin/env python3
"""Run-time corpus + ledger parser for docs/UAT-SERIES.md (Phase 204 Plan 01, COV-03).

Why this exists: the gap worklist (`docs/uat-coverage-gaps.md`) and its reconciliation against
`docs/uat-disposition-ledger.jsonl` had drifted into a hand-maintained snapshot bounded at series
163, with counts transcribed rather than recomputed. This module is the single place both COV-01's
generator (wave 3) and this plan's own reconciliation document are derived from: it re-reads
`docs/UAT-SERIES.md` at run time, classifies every case's disposition, and reconciles it against
the ledger -- with the arithmetic asserted to close rather than trusted.

Independence discipline (matches tests/test_uat_zero_undispositioned_gate.py's own note): the
grammar constants below are re-derived from the <interfaces> block of 204-01-PLAN.md, NOT imported
from scripts/uat_disposition_apply.py or any sibling guard module. A shared parsing bug must not be
able to make two independent artifacts agree with each other while both are wrong.

Case-ID grammar (NOT the truncating `UAT-[0-9]*-[0-9]*` form that dropped 37 of 878 cases during
this phase's own scouting -- see 204-CONTEXT.md's correction notice):

    CASE_ID_PATTERN = r"UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*"
    HEADING_RE      = re.compile(r"^### *(" + CASE_ID_PATTERN + r"):?")

Series extraction is alpha-prefix-aware: the series is the FIRST all-numeric (optionally one
decimal point) hyphen-segment after `UAT-`. A named-prefix id's series is the first numeric
segment after the name (e.g. `COMPLY-52-01` or `Q-53-01` -> series 52 / 53); a decimal-series id's
series keeps its decimal point (e.g. a `56.1-01` suffix -> series "56.1"). See
tests/test_uat_corpus_parser.py for concrete worked examples of every shape.

GAP-attribution rule (the live finding this plan had to adjudicate -- see
docs/uat-coverage-reconciliation.md section 2 for full evidence): a case's own disposition is
scoped to its **Result:** line ONLY (this is what `CaseRecord.disposition` reflects, and what the
standing zero-undispositioned gate also does). But a number of real, honestly-GAP cases in the
corpus carry a checked SKIP box with NO parenthetical annotation on the Result line -- their GAP
string lives on the case's own **Notes:** line instead (several Phase 185/186 "Recorded
honestly..." cases). A Result-line-only rule undercounts the true GAP population by exactly that
many. This module
therefore also captures `notes_has_gap_string` per case, and `reconcile()` computes the doc-GAP
population under the "Result-line annotation OR own-Notes-line GAP string" rule -- not the looser
"any GAP string anywhere in the case's span" rule, which was measured to over-count by 4 (a
trailing series-summary paragraph bleeding into the final case of a series; see
docs/uat-coverage-reconciliation.md section 2's "prior documents claimed / live parse says" table).

Lives under scripts/ -- NOT imported by any runtime code.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
UAT_SERIES_PATH = REPO_ROOT / "docs" / "UAT-SERIES.md"
LEDGER_PATH = REPO_ROOT / "docs" / "uat-disposition-ledger.jsonl"

# --- Grammar, independently re-derived from 204-01-PLAN.md's <interfaces> block -----------------

CASE_ID_PATTERN = r"UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*"
HEADING_RE = re.compile(r"^### *(" + CASE_ID_PATTERN + r"):?")

# Canonical Result-line grammar (scripts/uat_series_normalize.py::CANONICAL_RESULT_RE lockstep).
# Capture groups: 1=PASS box, 2=PASS annotation, 3=FAIL box, 4=FAIL annotation, 5=SKIP box,
# 6=SKIP annotation. Annotation groups exclude ')' and newlines by design (CR-01, Phase 169).
RESULT_LINE_RE = re.compile(
    r"^\*\*Result:\*\* "
    r"- \[([ x])\] PASS(?: \(([^)\n]*)\))?  "
    r"- \[([ x])\] FAIL(?: \(([^)\n]*)\))?  "
    r"- \[([ x])\] SKIP(?: \(([^)\n]*)\))?$"
)

NOTES_LINE_RE = re.compile(r"^\*\*Notes:\*\*\s*(.*)$")

SERIES_SEGMENT_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")

# Annotation-prefix classification for a checked SKIP box. Bold markers (`**`) are stripped before
# the prefix check since annotations may appear either bare (Result line) or bold (Notes line).
GAP_STRING_RE = re.compile(r"GAP\s*[—-]\s*no substitute coverage", re.IGNORECASE)


def _strip_markup(text: str) -> str:
    return text.strip().lstrip("*").strip()


def classify_annotation(annotation: Optional[str]) -> str:
    """Classify a checked-SKIP annotation string into GAP / DEFERRED / OBSOLETE / SKIP_OTHER.

    OBSOLETE is not yet present in the live corpus as of this plan (wave 2 introduces it) --
    this classifier supports it now so waves 2-4 have one place to read it from.
    """
    if annotation is None:
        return "SKIP_OTHER"
    plain = _strip_markup(annotation)
    if plain.startswith("GAP — ") or plain.startswith("GAP - "):
        return "GAP"
    if plain.startswith("DEFERRED — ") or plain.startswith("DEFERRED - "):
        return "DEFERRED"
    if plain.startswith("OBSOLETE — ") or plain.startswith("OBSOLETE - "):
        return "OBSOLETE"
    return "SKIP_OTHER"


def extract_series(case_id: str) -> str:
    """Alpha-prefix-aware series extraction: the first all-numeric (optionally one decimal
    point) hyphen segment after 'UAT-'."""
    rest = case_id[len("UAT-"):] if case_id.startswith("UAT-") else case_id
    segments = rest.split("-")
    for seg in segments:
        if SERIES_SEGMENT_RE.match(seg):
            return seg
    # No numeric segment at all (should not happen for real corpus IDs) -- fall back to the
    # first segment rather than raising, so a malformed id is reported, not crashed on.
    return segments[0] if segments else rest


@dataclass
class CaseRecord:
    case_id: str
    series: str
    heading_lineno: int
    result_lineno: Optional[int] = None
    boxes: set = field(default_factory=set)  # subset of {"PASS", "FAIL", "SKIP"}
    annotation: Optional[str] = None
    disposition: str = "UNDISPOSITIONED"
    notes_lineno: Optional[int] = None
    notes_text: Optional[str] = None
    notes_has_gap_string: bool = False

    @property
    def is_gap(self) -> bool:
        """The adjudicated doc-GAP rule: Result-line GAP annotation, OR a checked SKIP with no
        Result-line annotation whose OWN **Notes:** line carries the GAP string. See module
        docstring and docs/uat-coverage-reconciliation.md section 2 for the evidence this rule is
        based on."""
        if self.disposition == "GAP":
            return True
        if self.disposition == "SKIP_OTHER" and self.notes_has_gap_string:
            return True
        return False


def iter_cases(lines: Iterable[str]) -> Iterable[CaseRecord]:
    """Yield one CaseRecord per '^### UAT-' heading, in document order.

    Only the case's own **Result:** line (the first one encountered after its heading) and its
    own immediately-parseable **Notes:** line (the first one after that Result line) are ever
    inspected -- never case body text. This is the same body-literal-checkbox discipline
    tests/test_uat_zero_undispositioned_gate.py documents (its own known-trap case is a pre-commit
    artifact-gate walkthrough whose procedure text quotes a literal '- [x]' checkbox example from
    an unrelated UI): a case whose BODY contains such a literal checked-looking string, but whose
    **Result:** line is all-empty, must still classify UNDISPOSITIONED.
    """
    current: Optional[CaseRecord] = None
    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\n").rstrip("\r")
        m = HEADING_RE.match(line)
        if m:
            if current is not None:
                yield current
            case_id = m.group(1)
            current = CaseRecord(case_id=case_id, series=extract_series(case_id), heading_lineno=lineno)
            continue
        if current is None:
            continue
        if current.result_lineno is None:
            m = RESULT_LINE_RE.match(line)
            if m:
                current.result_lineno = lineno
                boxes = set()
                if m.group(1) == "x":
                    boxes.add("PASS")
                if m.group(3) == "x":
                    boxes.add("FAIL")
                if m.group(5) == "x":
                    boxes.add("SKIP")
                current.boxes = boxes
                annotation = None
                if "SKIP" in boxes and m.group(6) is not None:
                    annotation = m.group(6)
                elif "PASS" in boxes and m.group(2) is not None:
                    annotation = m.group(2)
                elif "FAIL" in boxes and m.group(4) is not None:
                    annotation = m.group(4)
                current.annotation = annotation
                if not boxes:
                    current.disposition = "UNDISPOSITIONED"
                elif "PASS" in boxes:
                    current.disposition = "PASS"
                elif "FAIL" in boxes:
                    current.disposition = "FAIL"
                else:  # SKIP
                    current.disposition = classify_annotation(annotation)
                continue
        elif current.notes_lineno is None:
            m = NOTES_LINE_RE.match(line)
            if m:
                current.notes_lineno = lineno
                current.notes_text = m.group(1)
                current.notes_has_gap_string = bool(GAP_STRING_RE.search(m.group(1)))
                continue
    if current is not None:
        yield current


def load_ledger(path: Path = LEDGER_PATH) -> list[dict]:
    """Return one dict per JSONL line. Does not raise on malformed/orphan rows -- reconcile()
    reports them instead."""
    rows: list[dict] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


@dataclass
class Reconciliation:
    total_headings: int
    disposition_counts: dict
    doc_gap_ids: list
    doc_gap_result_line_ids: list
    doc_gap_notes_only_ids: list
    ledger_max_series: Optional[float]
    doc_gap_with_ledger_row: list
    doc_gap_without_ledger_row: list  # cause 1: beyond ledger's max series, no row
    doc_deferred_ledger_gap: list  # cause 2: doc DEFERRED, ledger GAP
    doc_unannotated_ledger_gap: list  # cause 3: doc SKIP_OTHER (no notes gap), ledger GAP
    ledger_ids_absent_from_doc: list  # cause 4: ledger id matches no heading
    doc_obsolete_ledger_gap: list  # cause 5: doc OBSOLETE (COV-09 retirement), ledger GAP
    retired_obsolete_ids: list  # ALL doc-OBSOLETE cases, whether or not a ledger row exists
    arithmetic_ok: bool
    arithmetic_detail: dict


def _series_sort_key(series: str):
    try:
        return (0, float(series))
    except ValueError:
        return (1, series)


def reconcile(cases: list, ledger_rows: list) -> Reconciliation:
    by_id = {c.case_id: c for c in cases}
    total_headings = len(cases)

    disposition_counts: dict = {}
    for c in cases:
        disposition_counts[c.disposition] = disposition_counts.get(c.disposition, 0) + 1

    doc_gap_ids = sorted((c.case_id for c in cases if c.is_gap), key=lambda cid: by_id[cid].heading_lineno)
    doc_gap_result_line_ids = sorted(
        (c.case_id for c in cases if c.disposition == "GAP"), key=lambda cid: by_id[cid].heading_lineno
    )
    doc_gap_notes_only_ids = sorted(
        (c.case_id for c in cases if c.disposition == "SKIP_OTHER" and c.notes_has_gap_string),
        key=lambda cid: by_id[cid].heading_lineno,
    )

    ledger_by_id = {}
    for row in ledger_rows:
        rid = row.get("id")
        if rid is not None:
            ledger_by_id.setdefault(rid, row)

    numeric_ledger_series = []
    for row in ledger_rows:
        series = row.get("series")
        try:
            numeric_ledger_series.append(float(series))
        except (TypeError, ValueError):
            continue
    ledger_max_series = max(numeric_ledger_series) if numeric_ledger_series else None

    doc_gap_with_ledger_row = sorted(cid for cid in doc_gap_ids if cid in ledger_by_id)
    doc_gap_without_ledger_row = sorted(cid for cid in doc_gap_ids if cid not in ledger_by_id)

    # Cause 2: doc says DEFERRED, ledger says GAP.
    doc_deferred_ledger_gap = sorted(
        cid
        for cid, row in ledger_by_id.items()
        if row.get("outcome") == "GAP" and cid in by_id and by_id[cid].disposition == "DEFERRED"
    )
    # Cause 3: doc carries no GAP-attributable annotation at all (SKIP_OTHER, no notes-gap
    # string), ledger says GAP.
    doc_unannotated_ledger_gap = sorted(
        cid
        for cid, row in ledger_by_id.items()
        if row.get("outcome") == "GAP"
        and cid in by_id
        and by_id[cid].disposition == "SKIP_OTHER"
        and not by_id[cid].notes_has_gap_string
    )
    # Cause 4: ledger id matches no document heading at all.
    ledger_ids_absent_from_doc = sorted(cid for cid in ledger_by_id if cid not in by_id)

    # Cause 5 (204-02, D-12): doc retired the case OBSOLETE (COV-09), ledger still says GAP.
    # An OBSOLETE case is NOT an open doc-GAP (excluded from is_gap/doc_gap_ids by design) so it
    # would otherwise fall out of both arithmetic directions below -- retired work must be
    # accounted for, not silently dropped from the closure check.
    doc_obsolete_ledger_gap = sorted(
        cid
        for cid, row in ledger_by_id.items()
        if row.get("outcome") == "GAP" and cid in by_id and by_id[cid].disposition == "OBSOLETE"
    )
    # ALL doc-OBSOLETE cases, whether or not the ledger ever had a row for them (an OBSOLETE case
    # in a series beyond the ledger's max series is still retired, just never had cause-1-style
    # ledger coverage to begin with).
    retired_obsolete_ids = sorted(
        (c.case_id for c in cases if c.disposition == "OBSOLETE"), key=lambda cid: by_id[cid].heading_lineno
    )

    ledger_gap_ids = sorted(cid for cid, row in ledger_by_id.items() if row.get("outcome") == "GAP")
    ledger_gap_in_doc = [cid for cid in ledger_gap_ids if cid in by_id]
    ledger_gap_not_in_doc = [cid for cid in ledger_gap_ids if cid not in by_id]

    # Arithmetic closure, direction 1: every ledger-GAP id in the document falls into exactly one
    # of {already doc-GAP, cause-2 DEFERRED-conflict, cause-3 unannotated-conflict,
    # cause-5 OBSOLETE-retirement}.
    accounted_ledger_gap = (
        set(doc_gap_with_ledger_row)
        | set(doc_deferred_ledger_gap)
        | set(doc_unannotated_ledger_gap)
        | set(doc_obsolete_ledger_gap)
    )
    ledger_gap_direction_ok = set(ledger_gap_in_doc).issubset(accounted_ledger_gap) and (
        len(ledger_gap_in_doc) == len(set(ledger_gap_in_doc) & accounted_ledger_gap)
    )

    # Arithmetic closure, direction 2: doc-GAP total = (has a ledger row) + (no ledger row, cause 1).
    # OBSOLETE cases are never counted here -- retired_obsolete is reported separately (D-12: a
    # retired case must never reappear as drainable work, i.e. never inflate doc_gap_total).
    doc_direction_ok = len(doc_gap_ids) == len(doc_gap_with_ledger_row) + len(doc_gap_without_ledger_row)

    arithmetic_detail = {
        "doc_gap_total": len(doc_gap_ids),
        "doc_gap_with_ledger_row": len(doc_gap_with_ledger_row),
        "doc_gap_without_ledger_row_cause1": len(doc_gap_without_ledger_row),
        "ledger_gap_total": len(ledger_gap_ids),
        "ledger_gap_in_doc": len(ledger_gap_in_doc),
        "ledger_gap_not_in_doc": len(ledger_gap_not_in_doc),
        "cause2_doc_deferred_ledger_gap": len(doc_deferred_ledger_gap),
        "cause3_doc_unannotated_ledger_gap": len(doc_unannotated_ledger_gap),
        "cause4_ledger_ids_absent_from_doc": len(ledger_ids_absent_from_doc),
        "cause5_doc_obsolete_ledger_gap": len(doc_obsolete_ledger_gap),
        "retired_obsolete_total": len(retired_obsolete_ids),
    }

    arithmetic_ok = doc_direction_ok and ledger_gap_direction_ok

    return Reconciliation(
        total_headings=total_headings,
        disposition_counts=disposition_counts,
        doc_gap_ids=doc_gap_ids,
        doc_gap_result_line_ids=doc_gap_result_line_ids,
        doc_gap_notes_only_ids=doc_gap_notes_only_ids,
        ledger_max_series=ledger_max_series,
        doc_gap_with_ledger_row=doc_gap_with_ledger_row,
        doc_gap_without_ledger_row=doc_gap_without_ledger_row,
        doc_deferred_ledger_gap=doc_deferred_ledger_gap,
        doc_unannotated_ledger_gap=doc_unannotated_ledger_gap,
        ledger_ids_absent_from_doc=ledger_ids_absent_from_doc,
        doc_obsolete_ledger_gap=doc_obsolete_ledger_gap,
        retired_obsolete_ids=retired_obsolete_ids,
        arithmetic_ok=arithmetic_ok,
        arithmetic_detail=arithmetic_detail,
    )


def _read_lines(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        return f.readlines()


def run_reconcile(series_path: Path = UAT_SERIES_PATH, ledger_path: Path = LEDGER_PATH) -> Reconciliation:
    lines = _read_lines(series_path)
    cases = list(iter_cases(lines))
    ledger_rows = load_ledger(ledger_path)
    return reconcile(cases, ledger_rows)


def _print_reconciliation(r: Reconciliation) -> None:
    print(f"Total case headings: {r.total_headings}")
    print(f"Disposition counts: {r.disposition_counts}")
    print(f"Doc-GAP (Result-line annotation): {len(r.doc_gap_result_line_ids)}")
    print(f"Doc-GAP (Notes-line only, no Result annotation): {len(r.doc_gap_notes_only_ids)}")
    print(f"Doc-GAP total (adjudicated rule, Result OR own-Notes): {len(r.doc_gap_ids)}")
    print(f"Ledger max series: {r.ledger_max_series}")
    print(f"Cause 1 -- doc-GAP beyond ledger max series, no ledger row: {len(r.doc_gap_without_ledger_row)}")
    print(f"Cause 2 -- doc DEFERRED, ledger GAP: {len(r.doc_deferred_ledger_gap)} {r.doc_deferred_ledger_gap}")
    print(f"Cause 3 -- doc unannotated, ledger GAP: {len(r.doc_unannotated_ledger_gap)} {r.doc_unannotated_ledger_gap}")
    print(f"Cause 4 -- ledger id absent from document: {len(r.ledger_ids_absent_from_doc)} {r.ledger_ids_absent_from_doc}")
    print(f"Cause 5 -- doc OBSOLETE (COV-09 retirement), ledger GAP: {len(r.doc_obsolete_ledger_gap)} {r.doc_obsolete_ledger_gap}")
    print(f"Retired OBSOLETE (all, excluded from open-GAP count): {len(r.retired_obsolete_ids)} {r.retired_obsolete_ids}")
    print(f"Arithmetic detail: {r.arithmetic_detail}")
    print(f"Arithmetic closes: {r.arithmetic_ok}")
    if not r.arithmetic_ok:
        print("MISMATCH -- reconciliation arithmetic does NOT close. See arithmetic_detail above.", file=sys.stderr)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="uat_corpus")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("reconcile", help="Print the run-time corpus/ledger reconciliation.")
    args = parser.parse_args(argv)

    if args.command == "reconcile":
        r = run_reconcile()
        _print_reconciliation(r)
        return 0 if r.arithmetic_ok else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
