"""The master ledger lists every open item (operator decision, 2026-11-06).

WHAT THIS ENFORCES: `.planning/LEDGER.md` is the single source ledger for bugs, features,
ideas, audit findings and human-UAT leftovers. Every item is added there first; a todo file
under `.planning/todos/pending/` is optional supporting detail, never a second home. Before
this module, `.planning/HORIZON.md` declared its Open-Item Ledger "the single source of truth
for open items" while citing 16 of 197 pending todos -- a declaration nothing checked.

Enumeration is regenerated from disk on every run; there is no hand-written ID list here.

    1. Every pending todo has a ledger row, and that row is OPEN or DEFERRED. A todo whose
       row says DONE / DUPLICATE / OBSOLETE belongs in `.planning/todos/completed/`.
    2. Every ledger row is well formed: unique ID, a status from the vocabulary, P0-P3.
    3. LOCAL-ONLY: every `.planning/backlog/999.*` directory has a row. The backlog tree is
       mostly untracked, so this leg skips (naming the missing path) on a CI checkout.
    4. LOCAL-ONLY: no embargoed item's file stem appears in the ledger. The repo is public
       and the ledger is tracked; `.planning/security-embargo/` is untracked.

Status vocabulary: OPEN, DEFERRED (a recorded decision to push later), DONE (evidence on
main), DUPLICATE (evidence cell names the canonical ID), OBSOLETE (no longer applies).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / ".planning" / "LEDGER.md"
TODOS_PENDING_DIR = REPO_ROOT / ".planning" / "todos" / "pending"
BACKLOG_DIR = REPO_ROOT / ".planning" / "backlog"
EMBARGO_DIR = REPO_ROOT / ".planning" / "security-embargo"

STATUSES = {"OPEN", "DEFERRED", "DONE", "DUPLICATE", "OBSOLETE"}
LIVE_STATUSES = {"OPEN", "DEFERRED"}
PRIORITIES = {"P0", "P1", "P2", "P3"}

# A ledger row: `| ID | STATUS | Px | area | title | source | evidence |`. The header and
# separator rows are excluded by requiring a known status word in cell 2.
_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([A-Z]+)\s*\|\s*([^|]*?)\s*\|", re.M)


def _rows(text: str) -> list[tuple[str, str, str]]:
    return [(i, s, p) for i, s, p in _ROW_RE.findall(text) if i not in {"ID", "---"}]


def _ledger_text() -> str:
    if not LEDGER_PATH.exists():
        pytest.fail(f"{LEDGER_PATH.relative_to(REPO_ROOT)} is missing; it is git-tracked")
    return LEDGER_PATH.read_text(encoding="utf-8")


def test_ledger_rows_are_well_formed():
    rows = _rows(_ledger_text())
    assert len(rows) > 50, f"parsed only {len(rows)} ledger rows -- the row regex has drifted"
    seen: dict[str, int] = {}
    bad = []
    for item_id, status, prio in rows:
        seen[item_id] = seen.get(item_id, 0) + 1
        if status not in STATUSES:
            bad.append(f"{item_id}: status {status!r} not in {sorted(STATUSES)}")
        if prio not in PRIORITIES:
            bad.append(f"{item_id}: priority {prio!r} not in {sorted(PRIORITIES)}")
    bad += [f"{i}: listed {n} times" for i, n in seen.items() if n > 1]
    assert not bad, "Malformed ledger rows:\n" + "\n".join(f"  - {b}" for b in bad)


def test_every_pending_todo_has_a_live_ledger_row():
    todos = sorted(p.stem for p in TODOS_PENDING_DIR.glob("*.md"))
    assert todos, f"no todos under {TODOS_PENDING_DIR} -- the directory is git-tracked"
    status_of = {i: s for i, s, _ in _rows(_ledger_text())}
    missing = [t for t in todos if t not in status_of]
    closed = [f"{t} ({status_of[t]})" for t in todos
              if t in status_of and status_of[t] not in LIVE_STATUSES]
    problems = [f"no ledger row: {t}" for t in missing]
    problems += [f"row is closed but the todo is still pending: {t}" for t in closed]
    assert not problems, (
        f"{len(problems)} pending todo(s) are out of step with .planning/LEDGER.md:\n"
        + "\n".join(f"  - {p}" for p in problems)
        + "\n\nFix: add a row (ID = the todo's filename stem) to LEDGER.md, or move a resolved "
        "todo to .planning/todos/completed/ and mark its row DONE with evidence."
    )


def test_every_backlog_dir_has_a_ledger_row():
    if not BACKLOG_DIR.is_dir():
        pytest.skip(f"local-only leg: {BACKLOG_DIR.relative_to(REPO_ROOT)} is absent "
                    "(mostly untracked) -- this skip is not a pass")
    ids = sorted({m.group(1) for d in BACKLOG_DIR.iterdir()
                  if d.is_dir() and (m := re.match(r"(999\.\d+)", d.name))})
    assert ids, f"no 999.* directories found under {BACKLOG_DIR}"
    listed = {i for i, _, _ in _rows(_ledger_text())}
    missing = [i for i in ids if i not in listed]
    assert not missing, (
        "Backlog directories with no .planning/LEDGER.md row:\n"
        + "\n".join(f"  - {i}" for i in missing)
    )


def test_ledger_names_no_embargoed_item():
    if not EMBARGO_DIR.is_dir():
        pytest.skip(f"local-only leg: {EMBARGO_DIR.relative_to(REPO_ROOT)} is absent "
                    "(untracked) -- this skip is not a pass")
    stems = sorted({p.stem for p in EMBARGO_DIR.rglob("*.md")
                    if re.match(r"\d{6}-", p.name)})
    text = _ledger_text()
    leaked = [s for s in stems if s in text]
    assert not leaked, (
        "Embargoed items are named in the public ledger:\n"
        + "\n".join(f"  - {s}" for s in leaked)
        + "\n\nRemove them; embargoed items are tracked only under .planning/security-embargo/."
    )


TOOLING_AREAS = {"gsd-tooling", "dev-env"}
TOOLING_HEADING = "## Development tooling (not shipped)"
_SECTION_RE = re.compile(r"^## (.+?)(?: \(\d+\))?$", re.M)
_FULL_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([A-Z]+)\s*\|\s*P\d\s*\|\s*([^|]+?)\s*\|", re.M)


def _rows_by_section(text: str) -> dict[str, list[tuple[str, str, str]]]:
    """Section heading (count stripped) -> [(id, status, area)] for each row under it."""
    out: dict[str, list[tuple[str, str, str]]] = {}
    marks = [(m.start(), m.group(1)) for m in _SECTION_RE.finditer(text)]
    for (start, name), (end, _) in zip(marks, marks[1:] + [(len(text), "")]):
        out[name] = [r for r in _FULL_ROW_RE.findall(text[start:end]) if r[1] in STATUSES]
    return out


def test_tooling_rows_live_in_their_own_section():
    """Operator decision (2026-11-06): GSD-toolchain and dev-environment items stay in the
    ledger but outside the product's Open/Deferred tables and priority counts."""
    sections = _rows_by_section(_ledger_text())
    tooling_name = TOOLING_HEADING[3:]
    assert tooling_name in sections, f"{TOOLING_HEADING!r} section is missing"
    misplaced = [f"{i} (area {a}) is in § {s}" for s in ("Open", "Deferred")
                 for i, _, a in sections.get(s, []) if a in TOOLING_AREAS]
    misplaced += [f"{i} (area {a}) is in § {tooling_name} but is not tooling"
                  for i, _, a in sections[tooling_name] if a not in TOOLING_AREAS]
    misplaced += [f"{i} is {st} but still in § {tooling_name}; closed rows go to § Closed"
                  for i, st, _ in sections[tooling_name] if st not in LIVE_STATUSES]
    assert not misplaced, "Ledger rows in the wrong section:\n" + "\n".join(
        f"  - {m}" for m in misplaced)


def test_row_parser_reads_each_shape():
    text = (
        "| ID | Status | Priority | Area | Title | Source | Evidence |\n"
        "|---|---|---|---|---|---|---|\n"
        "| 999.104 | OPEN | P2 | config | t | s | e |\n"
        "| 261105-x | DONE | P1 | scoring | t \\| pipe | s | main abc123 |\n"
    )
    assert _rows(text) == [("999.104", "OPEN", "P2"), ("261105-x", "DONE", "P1")]
