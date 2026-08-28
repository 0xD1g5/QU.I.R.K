#!/usr/bin/env python3
"""Normalize docs/UAT-SERIES.md to a single canonical result format with
zero duplicate case IDs and heading-count == result-block-count parity
(UATREC-01, UATREC-02 — Phase 167 Plan 01).

Why this exists: the 19,665-line UAT gating document accumulated 12 distinct
`**Result:**` spellings, 23 case declarations with no enclosing `### UAT-`
heading, 2 orphan result blocks under `## Phase 999.8x` section headers with
no case heading at all, and one misfiled duplicate Series-144 block. Phase
168/169's disposition drain needs heading-count == result-block-count to be
true *by construction* so it can be checked mechanically instead of asserted
by hand. See .planning/phases/167-uat-format-unification-deduplication/
167-01-PLAN.md for the full transform spec and measured ground truth.

Run modes:
    python scripts/uat_series_normalize.py audit docs/UAT-SERIES.md
    python scripts/uat_series_normalize.py normalize docs/UAT-SERIES.md

`audit` is read-only and exits non-zero if the document is not yet
canonical. `normalize` applies the transforms in place and is idempotent —
running it twice produces a byte-identical file.

Lives under scripts/ -- NOT imported by any runtime code.

Scope boundary (D-07): this script adds STRUCTURAL PARITY ONLY for
zero-result cases (an all-boxes-unchecked canonical result block). It never
records a disposition (no checked box, no **Date:**/**Tester:**/**Notes:**
addition) for a case that did not already carry one. Recording dispositions
is UATREC-03, Phases 168/169.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys
from dataclasses import dataclass, field

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

HEADING_RE = re.compile(r"^### *(UAT-[^\s:]+):?")
SUBHEADING_RE = re.compile(r"^#### *(UAT-[^\s:]+):?")
ID_RE = re.compile(r"^\*\*ID:\*\* *(UAT-\S+)")
RESULT_RE = re.compile(r"^\*\*Result:\*\*")
SECTION_RE = re.compile(r"^## ")

# Canonical shape: **Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP
# with optional inline " (annotation)" suffix after any box's label.
CANONICAL_RESULT_RE = re.compile(
    # Exactly ONE space after the label. This MUST stay in lockstep with
# tests/test_uat_series_format.py::CANONICAL_RESULT_RE -- a looser `+`
# here would call a two-space line canonical while the gate test rejects
# it, producing a normalizer-says-clean / CI-says-dirty split.
r"^\*\*Result:\*\* "
    r"- \[[ x]\] PASS( \([^)\n]*\))?  "
    r"- \[[ x]\] FAIL( \([^)\n]*\))?  "
    r"- \[[ x]\] SKIP( \([^)\n]*\))?$"
)

EMPTY_CANONICAL = "**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP\n"

# The 16 real zero-result cases enumerated in the measured ground truth.
# `UAT-129` is the series header (not a real case) and is excluded.
ZERO_RESULT_CASE_IDS = [
    "UAT-4-01",
    "UAT-6-01",
    "UAT-33-01",
    "UAT-33-02",
    "UAT-33-03",
    "UAT-33-04",
    "UAT-33-05",
    "UAT-33-06",
    "UAT-33-07",
    "UAT-33-08",
    "UAT-34-01",
    "UAT-34-02",
    "UAT-34-03",
    "UAT-35-01",
    "UAT-35-02",
    "UAT-35-03",
]

SERIES_HEADER_CASE_IDS = {"UAT-129"}


@dataclass
class AuditResult:
    total_lines: int
    case_heading_count: int = 0
    subheading_count: int = 0
    series_level_headings: list[str] = field(default_factory=list)
    result_count: int = 0
    orphan_result_lines: list[int] = field(default_factory=list)
    headingless: list[tuple[int, str, str | None]] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    zero_result_ids: list[str] = field(default_factory=list)
    multi_result_ids: dict[str, int] = field(default_factory=dict)
    variant_census: dict[str, int] = field(default_factory=dict)
    canonical_count: int = 0

    @property
    def is_canonical(self) -> bool:
        return (
            self.subheading_count == 0
            and not self.orphan_result_lines
            and not self.headingless
            and not self.duplicate_ids
            and not self.zero_result_ids
            and not self.multi_result_ids
            and self.result_count == self.canonical_count
            and self.case_heading_count == self.result_count
            and not self.series_level_headings
        )


def _read(path: pathlib.Path) -> list[str]:
    with open(path, encoding="utf-8", newline="") as f:
        return f.readlines()


def _write(path: pathlib.Path, lines: list[str]) -> None:
    """Write atomically. This rewrites a ~19.6k-line gating document in place;
    an interruption mid-write would leave it truncated with no recovery path
    other than git. Write to a sibling temp file, then os.replace()."""
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.writelines(lines)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _detect_series_headers(lines: list[str]) -> set[int]:
    """Return the set of line indices (0-based) whose `###` UAT heading is a
    series header, not a case: structurally, a `###` UAT heading that is
    immediately followed (before the next `##`-level line) by one or more
    `####` UAT subheadings."""
    series_header_lines: set[int] = set()
    i = 0
    n = len(lines)
    while i < n:
        m = HEADING_RE.match(lines[i])
        if m:
            j = i + 1
            has_sub = False
            while j < n and not SECTION_RE.match(lines[j]) and not HEADING_RE.match(lines[j]):
                if SUBHEADING_RE.match(lines[j]):
                    has_sub = True
                    break
                j += 1
            if has_sub:
                series_header_lines.add(i)
        i += 1
    return series_header_lines


def audit(path: pathlib.Path, lines: list[str] | None = None) -> AuditResult:
    if lines is None:
        lines = _read(path)

    series_header_lines = _detect_series_headers(lines)
    result = AuditResult(total_lines=len(lines))

    current_heading_case: str | None = None
    current_open_case: str | None = None
    case_result_count: dict[str, int] = {}
    all_case_ids: list[str] = []

    for idx, line in enumerate(lines):
        lineno = idx + 1
        if SECTION_RE.match(line) and not HEADING_RE.match(line):
            current_heading_case = None
            current_open_case = None

        m = HEADING_RE.match(line)
        if m:
            cid = m.group(1)
            current_heading_case = cid
            current_open_case = cid
            result.case_heading_count += 1
            if idx in series_header_lines:
                result.series_level_headings.append(cid)
            else:
                all_case_ids.append(cid)
            continue

        m2 = SUBHEADING_RE.match(line)
        if m2:
            cid = m2.group(1)
            current_heading_case = cid
            current_open_case = cid
            result.subheading_count += 1
            all_case_ids.append(cid)
            continue

        m3 = ID_RE.match(line)
        if m3:
            cid = m3.group(1)
            if current_heading_case != cid:
                result.headingless.append((lineno, cid, current_heading_case))
                if cid not in all_case_ids:
                    all_case_ids.append(cid)
            current_open_case = cid

        if RESULT_RE.match(line):
            result.result_count += 1
            annotation_key = re.sub(r"\([^)]*\)", "(ANN)", line.rstrip("\n"))
            result.variant_census[annotation_key] = (
                result.variant_census.get(annotation_key, 0) + 1
            )
            if CANONICAL_RESULT_RE.match(line):
                result.canonical_count += 1
            if current_open_case is None:
                result.orphan_result_lines.append(lineno)
            else:
                case_result_count[current_open_case] = (
                    case_result_count.get(current_open_case, 0) + 1
                )

    seen: dict[str, int] = {}
    for cid in all_case_ids:
        seen[cid] = seen.get(cid, 0) + 1
    result.duplicate_ids = sorted(cid for cid, n in seen.items() if n > 1)

    for cid in all_case_ids:
        if cid in SERIES_HEADER_CASE_IDS:
            continue
        n = case_result_count.get(cid, 0)
        if n == 0 and cid not in result.zero_result_ids:
            result.zero_result_ids.append(cid)
        elif n > 1:
            result.multi_result_ids[cid] = n

    return result


def print_ledger(result: AuditResult) -> None:
    print(f"total_lines: {result.total_lines}")
    print(f"case_heading_count (###): {result.case_heading_count}")
    print(f"subheading_count (####): {result.subheading_count}")
    print(f"series_level_headings: {result.series_level_headings}")
    print(f"result_count: {result.result_count}")
    print(f"canonical_result_count: {result.canonical_count}")
    print(f"orphan_result_lines: {result.orphan_result_lines}")
    print(f"headingless_count: {len(result.headingless)}")
    for lineno, cid, heading in result.headingless:
        print(f"  headingless: line {lineno} id={cid} enclosing_heading={heading}")
    print(f"duplicate_ids: {result.duplicate_ids}")
    print(f"zero_result_ids ({len(result.zero_result_ids)}): {result.zero_result_ids}")
    print(f"multi_result_ids: {result.multi_result_ids}")
    print("variant_census:")
    for variant, count in sorted(
        result.variant_census.items(), key=lambda kv: -kv[1]
    ):
        print(f"  {count:5d}  {variant}")
    print(f"is_canonical: {result.is_canonical}")


# ---------------------------------------------------------------------------
# normalize()
# ---------------------------------------------------------------------------


def _rewrite_result_line(line: str) -> str:
    """Rewrite a single **Result:** line to the canonical three-box shape,
    preserving checked state and annotations. Idempotent: a line already in
    canonical form is returned unchanged."""
    if CANONICAL_RESULT_RE.match(line):
        return line

    eol = "\n" if line.endswith("\n") else ""
    body = line[len("**Result:**") :].strip()

    # Four-box DEFERRED line: move its annotation onto SKIP, drop the box.
    m = re.match(
        r"^- \[([ x])\] PASS( \([^)]*\))?  - \[([ x])\] FAIL( \([^)]*\))?  "
        r"- \[([ x])\] SKIP( \([^)]*\))?  - \[ \] DEFERRED( \(([^)]*)\))?$",
        body,
    )
    if m:
        (pass_chk, pass_ann, fail_chk, fail_ann, skip_chk, existing_skip_ann,
         _da, deferred_ann) = m.groups()
        # Merge rather than overwrite: a line carrying BOTH `SKIP (foo)` and
        # `DEFERRED (bar)` must not silently lose `foo`.
        parts = [
            p for p in (
                (existing_skip_ann or "").strip().strip("()").strip() or None,
                (deferred_ann or "").strip() or None,
            ) if p
        ]
        skip_ann = f" ({'; '.join(parts)})" if parts else ""
        pass_a = pass_ann or ""
        fail_a = fail_ann or ""
        return (
            f"**Result:** - [{pass_chk}] PASS{pass_a}  "
            f"- [{fail_chk}] FAIL{fail_a}  - [{skip_chk}] SKIP{skip_ann}{eol}"
        )

    # Double-[x] BACnet/Modbus collapse: two checked PASS boxes -> one, with
    # combined annotation.
    m = re.match(
        r"^- \[x\] PASS \(([^)]*)\)  - \[x\] PASS \(([^)]*)\)  "
        r"- \[ \] FAIL  - \[ \] SKIP$",
        body,
    )
    if m:
        ann1, ann2 = m.groups()
        return f"**Result:** - [x] PASS ({ann1}; {ann2})  - [ ] FAIL  - [ ] SKIP{eol}"

    # Em-dash separator variant.
    m = re.match(
        r"^- \[x\] PASS( \(([^)]*)\))? — \[ \] FAIL  - \[ \] SKIP$", body
    )
    if m:
        ann = f" ({m.group(2)})" if m.group(2) else ""
        return f"**Result:** - [x] PASS{ann}  - [ ] FAIL  - [ ] SKIP{eol}"

    # Bare prose PASS.
    if body == "PASS":
        return f"**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP{eol}"

    # Two-box slash form, no recorded outcome.
    if re.match(r"^\[ \] PASS / \[ \] FAIL$", body):
        return f"**Result:** - [ ] PASS  - [ ] FAIL  - [ ] SKIP{eol}"

    # Missing leading hyphen (checked or unchecked), already three boxes.
    m = re.match(
        r"^\[([ x])\] PASS( \([^)]*\))?  - \[([ x])\] FAIL( \([^)]*\))?  "
        r"- \[([ x])\] SKIP( \([^)]*\))?$",
        body,
    )
    if m:
        pass_chk, pass_ann, fail_chk, fail_ann, skip_chk, skip_ann = m.groups()
        pass_a = pass_ann or ""
        fail_a = fail_ann or ""
        skip_a = skip_ann or ""
        return (
            f"**Result:** - [{pass_chk}] PASS{pass_a}  "
            f"- [{fail_chk}] FAIL{fail_a}  - [{skip_chk}] SKIP{skip_a}{eol}"
        )

    # Already hyphenated three-box but with an annotation shape not matched
    # by CANONICAL_RESULT_RE for some other reason (defensive fallback) --
    # leave unchanged rather than risk corrupting an unrecognized line.
    return line


def _promote_headingless(lines: list[str]) -> list[str]:
    """Insert a `### <ID>: <Title>` heading immediately above each
    genuinely-headingless **ID:** line (the 21 Phase 34/35/36/38/39 cases).
    The two `####`-headed UAT-129 cases are handled separately in
    `_fix_uat_129_heading_level`, not here."""
    out: list[str] = []
    current_heading_case: str | None = None
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if SECTION_RE.match(line) and not HEADING_RE.match(line):
            current_heading_case = None
        m = HEADING_RE.match(line)
        if m:
            current_heading_case = m.group(1)
        m2 = SUBHEADING_RE.match(line)
        if m2:
            current_heading_case = m2.group(1)

        m3 = ID_RE.match(line)
        if m3:
            cid = m3.group(1)
            if current_heading_case != cid:
                # Look ahead for the **Title:** line belonging to this case.
                title = None
                j = i + 1
                while j < n and j < i + 6:
                    tm = re.match(r"^\*\*Title:\*\* *(.+)$", lines[j])
                    if tm:
                        title = tm.group(1).strip()
                        break
                    if ID_RE.match(lines[j]) or HEADING_RE.match(lines[j]):
                        break
                    j += 1
                heading_title = title if title else cid
                out.append(f"### {cid}: {heading_title}\n")
                current_heading_case = cid
        out.append(line)
        i += 1
    return out


def _fix_uat_129_heading_level(lines: list[str]) -> list[str]:
    """Demote the `### UAT-129:` series header to `## Series 129: ...` and
    promote its two `#### UAT-129-0N` subheadings to `### `."""
    out = []
    for line in lines:
        m = HEADING_RE.match(line)
        if m and m.group(1) == "UAT-129":
            rest = line[len("### ") :]
            rest = re.sub(r"^UAT-129:", "Series 129:", rest)
            out.append(f"## {rest.rstrip()} (Phase 129)\n")
            continue
        m2 = SUBHEADING_RE.match(line)
        if m2 and m2.group(1).startswith("UAT-129-"):
            out.append(line[1:])  # drop one leading '#'
            continue
        out.append(line)
    return out


def _dedupe_uat_144(lines: list[str]) -> list[str]:
    """Delete the misfiled UAT-144 Block A (under `## UAT-143 Series ...`)
    in full, and fold its "with documented caveat" wording into Block B's
    UAT-144-03 result annotation."""
    text_lines = lines
    start = None
    end = None
    for i, line in enumerate(text_lines):
        if re.match(r"^### UAT-144-01:", line):
            start = i
            break
    if start is None:
        return lines  # already removed / not found -- idempotent no-op
    for i in range(start, len(text_lines)):
        if re.match(r"^## Series 144:", text_lines[i]):
            end = i
            break
    if end is None:
        return lines

    new_lines = text_lines[:start] + text_lines[end:]

    # Merge Block A's caveat wording into Block B's UAT-144-03 Result line.
    for i, line in enumerate(new_lines):
        if line.startswith("**Result:** - [x] PASS (with documented override)"):
            new_lines[i] = line.replace(
                "(with documented override)",
                "(with documented override; documented caveat)",
            )
            break

    return new_lines


def _adopt_orphan_results(lines: list[str]) -> list[str]:
    """Give the two orphan `## Phase 999.83`/`## Phase 999.84` result blocks
    a `### UAT-999.8N-01` case heading, placed right after the section's
    `**Last Updated:**` line."""
    orphan_map = {
        "## Phase 999.83 — Chaos Lab Service Config Drift (BACK-90)": (
            "### UAT-999.83-01: Chaos Lab Service Config Drift (BACK-90)\n"
        ),
        "## Phase 999.84 — Chaos Lab macOS Host-Mount Compat (BACK-91)": (
            "### UAT-999.84-01: Chaos Lab macOS Host-Mount Compat (BACK-91)\n"
        ),
    }
    already_present = {h.rstrip("\n") for h in orphan_map.values()} & {
        line.rstrip("\n") for line in lines
    }
    out: list[str] = []
    pending_heading: str | None = None
    for line in lines:
        stripped = line.rstrip("\n")
        if stripped in orphan_map and orphan_map[stripped].rstrip("\n") not in already_present:
            pending_heading = orphan_map[stripped]
            out.append(line)
            continue
        out.append(line)
        if pending_heading is not None and re.match(r"^\*\*Last Updated:\*\*", line):
            out.append("\n")
            out.append(pending_heading)
            pending_heading = None
    return out


def _append_empty_result_blocks(lines: list[str]) -> list[str]:
    """For each of the 16 real zero-result cases, append an all-unchecked
    canonical **Result:** block at the end of the case body (immediately
    before the next `---`/heading/section boundary), matching UAT-33-03's
    placement shape. STRUCTURAL PARITY ONLY -- no Date/Tester/Notes added."""
    zero_ids_remaining = set(ZERO_RESULT_CASE_IDS)
    out: list[str] = []
    current_case: str | None = None
    case_has_result = False
    i = 0
    n = len(lines)

    def flush_pending_empty_block(target_out: list[str]) -> None:
        nonlocal current_case, case_has_result
        if (
            current_case is not None
            and current_case in zero_ids_remaining
            and not case_has_result
        ):
            # Trim trailing blank lines and any trailing horizontal-rule
            # separator(s) (some sections have consecutive `---` rules) so
            # the block is inserted BEFORE the rule(s) that close the case
            # body, not after it/them.
            had_rule = False
            while target_out and target_out[-1] == "\n":
                target_out.pop()
            while target_out and target_out[-1].rstrip("\n") == "---":
                target_out.pop()
                had_rule = True
                while target_out and target_out[-1] == "\n":
                    target_out.pop()
            target_out.append("\n")
            target_out.append(EMPTY_CANONICAL)
            if had_rule:
                target_out.append("\n")
                target_out.append("---\n")
            zero_ids_remaining.discard(current_case)
        current_case = None
        case_has_result = False

    while i < n:
        line = lines[i]
        if SECTION_RE.match(line) and not HEADING_RE.match(line):
            flush_pending_empty_block(out)
        m = HEADING_RE.match(line)
        if m:
            flush_pending_empty_block(out)
            current_case = m.group(1)
            case_has_result = False
        else:
            m3 = ID_RE.match(line)
            if m3 and current_case is None:
                current_case = m3.group(1)
                case_has_result = False
        if RESULT_RE.match(line):
            case_has_result = True
        out.append(line)
        i += 1
    flush_pending_empty_block(out)
    return out


def normalize(path: pathlib.Path) -> None:
    lines = _read(path)

    lines = _dedupe_uat_144(lines)
    lines = _fix_uat_129_heading_level(lines)
    lines = _promote_headingless(lines)
    lines = _adopt_orphan_results(lines)
    lines = [_rewrite_result_line(line) for line in lines]
    lines = _append_empty_result_blocks(lines)

    _write(path, lines)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: uat_series_normalize.py {audit|normalize} <path-to-UAT-SERIES.md>",
            file=sys.stderr,
        )
        return 2

    mode, raw_path = argv[1], argv[2]
    path = pathlib.Path(raw_path)
    if not path.is_absolute():
        path = pathlib.Path.cwd() / path

    if mode == "audit":
        result = audit(path)
        print_ledger(result)
        return 0 if result.is_canonical else 1
    elif mode == "normalize":
        normalize(path)
        result = audit(path)
        print_ledger(result)
        return 0 if result.is_canonical else 1
    else:
        print(f"unknown mode: {mode}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
