#!/usr/bin/env python3
"""Ledger-driven, idempotent disposition writer + bucket classifier + scope
auditor for docs/UAT-SERIES.md (UATREC-03, Phase 168 Plan 01).

Why this exists: dispositioning 299 undispositioned UAT-1..100 cases by hand
would be 299 unreviewable document edits. This script makes the drain a
data-entry-into-JSONL operation: `docs/uat-disposition-ledger.jsonl` carries
one JSON object per case (id, bucket, outcome, evidence, recorded), and
`apply` mechanically rewrites the matching `**Result:**` line in
docs/UAT-SERIES.md from that ledger, idempotently. A reviewer diffs one
ledger line per case instead of scattered Markdown surgery.

Subcommands:
    audit-scope   print the in-scope (series <= 100, undispositioned) case
                  set with counts by series band; exit 0 always (read-only)
    classify      (re)generate/refresh docs/uat-disposition-ledger.jsonl,
                  preserving any existing non-null outcome/evidence/recorded
    apply         write ledger outcomes into docs/UAT-SERIES.md, idempotently
                  (--dry-run prints planned rewrites, writes nothing)
    verify        exit 1 with a per-case report if any document result line
                  disagrees with its ledger row

Case-ID parsing (independent re-derivation, matches
tests/test_uat_series_format.py's CASE_ID_PATTERN -- NOT the truncating
`UAT-[0-9]*-[0-9]*` form that manufactured Phase 167's phantom duplicates):

    UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*

Series extraction is alpha-prefix-aware: the series is the FIRST all-numeric
(optionally with one decimal point) hyphen-segment after `UAT-`. This makes
`UAT-COMPLY-52-01` series 52, `UAT-Q-53-01` series 53, and `UAT-56.1-01`
series "56.1" (in scope, <= 100). A naive `UAT-([0-9.]+)-` regex drops the
alpha-prefixed IDs entirely and undercounts in-scope cases.

Reuses scripts/uat_series_normalize.py's atomic _read/_write pattern so a
mid-write interruption on the ~19.7k-line gating document cannot truncate it.

Lives under scripts/ -- NOT imported by any runtime code.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from dataclasses import dataclass, field

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
UAT_SERIES_PATH = REPO_ROOT / "docs" / "UAT-SERIES.md"
LEDGER_PATH = REPO_ROOT / "docs" / "uat-disposition-ledger.jsonl"
UAT_RUNNER_PATH = REPO_ROOT / "uat_runner.py"

MAX_SERIES = 163  # Phase 169 extends coverage from series <=100 (Phase 168) through
# series <=163; classify's `prior` merge in cmd_classify preserves all existing
# series 1-100 ledger rows unchanged and idempotently on reclassify.

# --- Case-ID / heading / result grammar -----------------------------------
# Independently re-derived to match tests/test_uat_series_format.py exactly
# (same CASE_ID_PATTERN rationale: NOT the truncating UAT-[0-9]*-[0-9]* form).
CASE_ID_PATTERN = r"UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*"
HEADING_RE = re.compile(r"^### *(" + CASE_ID_PATTERN + r")")
SECTION_RE = re.compile(r"^## ")
RESULT_LINE_RE = re.compile(r"^\*\*Result:\*\*")

# Phase 167 canonical grammar (must stay in lockstep with
# scripts/uat_series_normalize.py::CANONICAL_RESULT_RE and
# tests/test_uat_series_format.py::CANONICAL_RESULT_RE).
# The annotation groups exclude newlines as well as ')'. A negated class like
# [^)]* matches newlines, and this pattern carries neither DOTALL nor MULTILINE
# -- so [^)]* would swallow an injected multi-line block while the line still
# "matched" (CR-01, Phase 169 review). Guarded by
# tests/test_uat_apply_injection_guard.py.
CANONICAL_RESULT_RE = re.compile(
    r"^\*\*Result:\*\* "
    r"- \[[ x]\] PASS(?: \([^)\n]*\))?  "
    r"- \[[ x]\] FAIL(?: \([^)\n]*\))?  "
    r"- \[[ x]\] SKIP(?: \([^)\n]*\))?$"
)

DISPOSITIONED_BOX_RE = re.compile(r"- \[[xX]\]")

# Series segment: one or more digits, optionally one decimal point + digits.
SERIES_SEGMENT_RE = re.compile(r"^[0-9]+(?:\.[0-9]+)?$")

# Node-reference shape used by the DEFERRED/GAP evidence guard (D-02):
# a real pytest node id, e.g. tests/test_foo.py::test_bar or with a
# trailing `*` glob on the test-name segment.
NODE_REF_RE = re.compile(r"tests/[\w/]+\.py::[\w*]+(?:::[\w*]+)?")
# A bare requirement-ID-shaped token (all caps + digits + hyphens, no
# tests/...py::... substring) -- NOT sufficient as a substitute (D-02).
REQ_ID_ONLY_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[0-9]+)+$")

LEDGER_KEYS = ("id", "series", "bucket", "runner_covered", "outcome", "evidence", "recorded")
VALID_OUTCOMES = {None, "PASS", "FAIL", "SKIP", "DEFERRED", "GAP"}

BUCKET_ORDER = ["A", "B", "C", "D", "E", "F"]

# --- Bucket classification patterns (first match wins) ---------------------
_BUCKET_A_RE = re.compile(r"tests/test_\w+\.py")
_BUCKET_B_RE = re.compile(r"\bpytest\b")
_BUCKET_C_RE = re.compile(r"docker compose|docker-compose|\blab\.sh\b")
_BUCKET_D_RE = re.compile(r"run_scan\.py|\bquirk\s")
_BUCKET_E_RE = re.compile(r"\bcurl\b|\bsqlite3\b|\bnpm\s|python3?\s+-c\b")


def classify_bucket(body_text: str) -> str:
    if _BUCKET_A_RE.search(body_text):
        return "A"
    if _BUCKET_B_RE.search(body_text):
        return "B"
    if _BUCKET_C_RE.search(body_text):
        return "C"
    if _BUCKET_D_RE.search(body_text):
        return "D"
    if _BUCKET_E_RE.search(body_text):
        return "E"
    return "F"


def extract_series(case_id: str) -> str | None:
    """Return the series string (e.g. '7', '56.1', '52') for a case id, or
    None if no numeric segment is found (should not happen for real cases)."""
    rest = case_id[len("UAT-"):] if case_id.startswith("UAT-") else case_id
    for segment in rest.split("-"):
        if SERIES_SEGMENT_RE.match(segment):
            return segment
    return None


def series_in_scope(series: str) -> bool:
    return float(series) <= MAX_SERIES


# --- Document I/O (atomic, matches scripts/uat_series_normalize.py) --------


def _read(path: pathlib.Path) -> list[str]:
    with open(path, encoding="utf-8", newline="") as f:
        return f.readlines()


def _write(path: pathlib.Path, lines: list[str]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


@dataclass
class Case:
    case_id: str
    heading_lineno: int  # 0-based index into lines
    end_lineno: int  # 0-based, exclusive
    result_lineno: int | None = None  # 0-based index of the **Result:** line
    body_lines: list[str] = field(default_factory=list)

    @property
    def series(self) -> str | None:
        return extract_series(self.case_id)

    @property
    def dispositioned(self) -> bool:
        # Scoped to the case's own Result line only (not the whole body) --
        # a case body containing a literal "- [x]" markdown example
        # elsewhere (e.g. UAT-151-01's own step-2 prose) must never
        # false-positive as already dispositioned.
        if self.result_lineno is None:
            return False
        result_line = self.body_lines[self.result_lineno - (self.heading_lineno + 1)]
        return bool(DISPOSITIONED_BOX_RE.search(result_line))

    @property
    def body_lines_joined(self) -> str:
        return "".join(self.body_lines)


def parse_cases(lines: list[str]) -> list[Case]:
    """Split the document into one Case per `### UAT-` heading. A case body
    runs from its heading (exclusive) to the next `##`/`###` boundary
    (exclusive). The **Result:** line is the first matching line in that
    span."""
    cases: list[Case] = []
    n = len(lines)
    i = 0
    heading_indices: list[int] = []
    for idx, line in enumerate(lines):
        if HEADING_RE.match(line) or (SECTION_RE.match(line) and not HEADING_RE.match(line)):
            heading_indices.append(idx)
    heading_indices.append(n)

    for pos in range(len(heading_indices) - 1):
        start = heading_indices[pos]
        line = lines[start]
        m = HEADING_RE.match(line)
        if not m:
            continue
        end = heading_indices[pos + 1]
        case = Case(case_id=m.group(1), heading_lineno=start, end_lineno=end)
        for j in range(start + 1, end):
            case.body_lines.append(lines[j])
            if case.result_lineno is None and RESULT_LINE_RE.match(lines[j]):
                case.result_lineno = j
        cases.append(case)
    return cases


def in_scope_undispositioned(cases: list[Case]) -> list[Case]:
    out = []
    for c in cases:
        series = c.series
        if series is None:
            continue
        if not series_in_scope(series):
            continue
        if c.dispositioned:
            continue
        out.append(c)
    return out


# --- uat_runner.py coverage -------------------------------------------------


def runner_covered_ids() -> set[str]:
    """Return the set of case IDs uat_runner.py logs via rlog(), located by
    scanning for single-quoted UAT-... string literals anywhere in the file
    (covers direct rlog('UAT-x-y', ...) calls as well as case IDs stored in
    tuple literals feeding a `for tid, ... in [...]:` loop before rlog(tid,
    ...)). Filters out non-case tokens (e.g. 'UAT-Auto', an assessment name)
    by requiring a valid numeric series segment."""
    if not UAT_RUNNER_PATH.is_file():
        return set()
    text = UAT_RUNNER_PATH.read_text(encoding="utf-8")
    pat = re.compile(r"'(" + CASE_ID_PATTERN + r")'")
    ids = set()
    for tok in pat.findall(text):
        if extract_series(tok) is not None:
            ids.add(tok)
    return ids


def runner_argparse_surface() -> list[str]:
    if not UAT_RUNNER_PATH.is_file():
        return []
    text = UAT_RUNNER_PATH.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"add_argument\('(--[\w-]+)'", text)))


# --- Ledger I/O --------------------------------------------------------------


def load_ledger() -> dict[str, dict]:
    if not LEDGER_PATH.is_file():
        return {}
    rows = {}
    with open(LEDGER_PATH, encoding="utf-8", newline="") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows[row["id"]] = row
    return rows


def write_ledger(rows: list[dict]) -> None:
    rows = sorted(rows, key=lambda r: r["id"])
    lines = []
    for row in rows:
        ordered = {k: row[k] for k in LEDGER_KEYS}
        lines.append(json.dumps(ordered, separators=(", ", ": ")) + "\n")
    tmp = LEDGER_PATH.with_name(LEDGER_PATH.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)
        os.replace(tmp, LEDGER_PATH)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


# --- Subcommands -------------------------------------------------------------


def cmd_audit_scope(_args: argparse.Namespace) -> int:
    lines = _read(UAT_SERIES_PATH)
    cases = parse_cases(lines)
    scope = in_scope_undispositioned(cases)
    bands = {"1-50": 0, "51-100": 0}
    for c in scope:
        series_val = float(c.series)
        if series_val <= 50:
            bands["1-50"] += 1
        else:
            bands["51-100"] += 1
    bucket_counts = {b: 0 for b in BUCKET_ORDER}
    for c in scope:
        bucket_counts[classify_bucket(c.body_lines_joined)] += 1
    covered = runner_covered_ids()
    runner_covered_count = sum(1 for c in scope if c.case_id in covered)

    print(f"in-scope undispositioned (series <= {MAX_SERIES}): {len(scope)}")
    print(f"  series 1-50:   {bands['1-50']}")
    print(f"  series 51-100: {bands['51-100']}")
    print("bucket counts:")
    for b in BUCKET_ORDER:
        print(f"  {b}: {bucket_counts[b]}")
    print(f"runner_covered: {runner_covered_count}")
    return 0


def cmd_classify(_args: argparse.Namespace) -> int:
    lines = _read(UAT_SERIES_PATH)
    cases = parse_cases(lines)
    scope = in_scope_undispositioned(cases)
    covered = runner_covered_ids()
    existing = load_ledger()

    # Start from every existing ledger row (already-dispositioned cases are,
    # by definition, excluded from `scope` below since scope is
    # undispositioned-only -- without preserving `existing` verbatim here,
    # write_ledger would silently drop every already-dispositioned row from
    # the file, which is the opposite of "(re)generate/refresh ... preserving
    # any existing non-null outcome/evidence/recorded" per this command's own
    # docstring).
    rows_by_id: dict[str, dict] = dict(existing)

    for c in scope:
        prior = existing.get(c.case_id)
        row = {
            "id": c.case_id,
            "series": c.series,
            "bucket": classify_bucket(c.body_lines_joined),
            "runner_covered": c.case_id in covered,
            "outcome": None,
            "evidence": "",
            "recorded": "",
        }
        if prior is not None:
            row["outcome"] = prior.get("outcome")
            row["evidence"] = prior.get("evidence", "")
            row["recorded"] = prior.get("recorded", "")
        rows_by_id[c.case_id] = row

    rows = list(rows_by_id.values())
    write_ledger(rows)
    print(f"wrote {len(rows)} rows to {LEDGER_PATH.relative_to(REPO_ROOT)}")
    return 0


def _validate_evidence(outcome: str, evidence: str) -> str | None:
    """Return an error string, or None if evidence is acceptable."""
    if ")" in evidence:
        return "evidence contains ')' -- would break the canonical grammar"
    # CR-01 (Phase 169 review): a JSON-escaped \n is legal JSONL but decodes to
    # a real newline. Spliced into the document by cmd_apply it can materialise
    # an entire fabricated, fully-PASSED case -- invisible to the zero-
    # undispositioned gate (the fake is marked PASS), to the heading/result
    # parity check (it adds one of each), and to ID uniqueness (its ID is new).
    if "\n" in evidence or "\r" in evidence:
        return "evidence contains a newline -- would inject document structure"
    if outcome in ("DEFERRED", "GAP"):
        if not NODE_REF_RE.search(evidence) and outcome == "DEFERRED":
            return "DEFERRED evidence has no <file>.py::<name> node reference"
        # A bare requirement-ID-shaped token is never sufficient (D-02).
        stripped = evidence
        for prefix in ("DEFERRED — covered by ", "DEFERRED - covered by "):
            if stripped.startswith(prefix):
                stripped = stripped[len(prefix):]
        if REQ_ID_ONLY_RE.match(stripped.strip()) and not NODE_REF_RE.search(evidence):
            return "evidence is only a requirement-ID-shaped token, not a node reference (D-02)"
    return None


def _render_result_line(bucket_outcome: str, evidence: str) -> str:
    boxes = {"PASS": " ", "FAIL": " ", "SKIP": " "}
    if bucket_outcome in ("PASS", "FAIL", "SKIP"):
        boxes[bucket_outcome] = "x"
        annotation = f" ({evidence})" if evidence else ""
        pass_ann = annotation if bucket_outcome == "PASS" else ""
        fail_ann = annotation if bucket_outcome == "FAIL" else ""
        skip_ann = annotation if bucket_outcome == "SKIP" else ""
    elif bucket_outcome in ("DEFERRED", "GAP"):
        boxes["SKIP"] = "x"
        pass_ann = ""
        fail_ann = ""
        skip_ann = f" ({evidence})" if evidence else ""
    else:
        raise ValueError(f"unknown outcome {bucket_outcome!r}")
    line = (
        f"**Result:** - [{boxes['PASS']}] PASS{pass_ann}  "
        f"- [{boxes['FAIL']}] FAIL{fail_ann}  "
        f"- [{boxes['SKIP']}] SKIP{skip_ann}"
    )
    return line + "\n"


def cmd_apply(args: argparse.Namespace) -> int:
    ledger = load_ledger()
    lines = _read(UAT_SERIES_PATH)
    cases = {c.case_id: c for c in parse_cases(lines)}

    planned: list[tuple[int, str, str]] = []  # (lineno, old, new)
    errors: list[str] = []

    for case_id, row in sorted(ledger.items()):
        outcome = row.get("outcome")
        if outcome is None:
            continue
        if outcome not in VALID_OUTCOMES:
            errors.append(f"{case_id}: invalid outcome {outcome!r}")
            continue
        evidence = row.get("evidence", "")
        err = _validate_evidence(outcome, evidence)
        if err:
            errors.append(f"{case_id}: {err}")
            continue
        case = cases.get(case_id)
        if case is None:
            errors.append(f"{case_id}: no matching '### UAT-' heading in {UAT_SERIES_PATH.name}")
            continue
        if case.result_lineno is None:
            errors.append(f"{case_id}: no **Result:** line found in case body")
            continue
        new_line = _render_result_line(outcome, evidence)
        if not CANONICAL_RESULT_RE.match(new_line.rstrip("\n")):
            errors.append(f"{case_id}: produced line fails CANONICAL_RESULT_RE: {new_line!r}")
            continue
        old_line = lines[case.result_lineno]
        if old_line != new_line:
            planned.append((case.result_lineno, old_line, new_line))

    if errors:
        for e in errors:
            print(f"REFUSED: {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"{len(planned)} pending rewrite(s) (dry run, nothing written):")
        for lineno, old, new in planned:
            print(f"  line {lineno + 1}: {old!r} -> {new!r}")
        return 0

    for lineno, _old, new in planned:
        lines[lineno] = new
    if planned:
        _write(UAT_SERIES_PATH, lines)
    print(f"applied {len(planned)} rewrite(s)")
    return 0


def cmd_verify(_args: argparse.Namespace) -> int:
    ledger = load_ledger()
    lines = _read(UAT_SERIES_PATH)
    cases = {c.case_id: c for c in parse_cases(lines)}
    mismatches: list[str] = []

    for case_id, row in sorted(ledger.items()):
        outcome = row.get("outcome")
        case = cases.get(case_id)
        if case is None or case.result_lineno is None:
            if outcome is not None:
                mismatches.append(f"{case_id}: ledger has outcome {outcome!r} but no result line found")
            continue
        doc_line = lines[case.result_lineno].rstrip("\n")
        if outcome is None:
            if DISPOSITIONED_BOX_RE.search(doc_line):
                mismatches.append(f"{case_id}: ledger outcome is null but document line is dispositioned: {doc_line!r}")
            continue
        expected = _render_result_line(outcome, row.get("evidence", "")).rstrip("\n")
        if doc_line != expected:
            mismatches.append(f"{case_id}: document line {doc_line!r} != ledger-expected {expected!r}")

    if mismatches:
        for m in mismatches:
            print(f"MISMATCH: {m}", file=sys.stderr)
        print(f"{len(mismatches)} mismatch(es)", file=sys.stderr)
        return 1
    print(f"verified {len(ledger)} ledger row(s) against document -- all agree")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="uat_disposition_apply.py")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("audit-scope")
    sub.add_parser("classify")
    apply_p = sub.add_parser("apply")
    apply_p.add_argument("--dry-run", action="store_true")
    sub.add_parser("verify")

    args = parser.parse_args(argv)

    handlers = {
        "audit-scope": cmd_audit_scope,
        "classify": cmd_classify,
        "apply": cmd_apply,
        "verify": cmd_verify,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
