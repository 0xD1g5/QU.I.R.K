"""Phase 77 LEDGER-01 (D-31): AUDIT-TASKS.md milestone-completion invariants.

This module installs two CI gates that lock the v4.9 audit-ledger hygiene
invariants in perpetuity:

1. `test_audit_ledger_has_zero_bare_open_rows` — zero `[ ] open` rows remain.
   Every finding must carry an explicit disposition (`[x] closed`,
   `[ ] deferred-vX.Y with rationale`, or `[ ] wont-fix with rationale`).

2. `test_deferred_and_wontfix_rows_have_rationale` — every `[ ] deferred-*` and
   `[ ] wont-fix` row carries inline rationale (a `— <text>` suffix inside the
   disposition cell) so future auditors can reconstruct the decision.

Together these gates guarantee the AUDIT-TASKS.md ledger stays self-documenting
across the v5.0+ lifetime of the project.
"""

from __future__ import annotations

import re
from pathlib import Path

LEDGER = (
    Path(__file__).resolve().parent.parent
    / ".planning"
    / "audit-2026-05-08"
    / "AUDIT-TASKS.md"
)

# Bare-open row: `| ... | [ ] open |` at the END of a table row.
_OPEN_RE = re.compile(r"^\|\s.*\[ \] open\s*\|", re.MULTILINE)

# Bare-disposition row: `| ... | [ ] (deferred-* | wont-fix) |` with no inline
# rationale (no `— <text>` suffix inside the disposition cell). The disposition
# cell is the LAST `| ... |` pair; if it contains only `[ ] wont-fix` or
# `[ ] deferred-vN.M` with no em-dash rationale before the closing pipe, the
# row is "bare" and fails the gate.
_BARE_DISPOSITION_RE = re.compile(
    r"^\|\s.*\|\s*\[ \] (?:deferred-[\w\.]+|wont-fix)\s*\|\s*$",
    re.MULTILINE,
)


def test_audit_ledger_has_zero_bare_open_rows() -> None:
    """v4.9 milestone-completion gate (D-31): zero `[ ] open` rows.

    A bare-open row is one whose disposition cell still reads `[ ] open`,
    meaning no phase has adjudicated the finding. By the v4.9 milestone close,
    every audit row must be flipped to a final disposition.
    """
    text = LEDGER.read_text(encoding="utf-8")
    matches = _OPEN_RE.findall(text)
    assert not matches, (
        f"Audit ledger has {len(matches)} bare-open row(s); v4.9 milestone gate "
        f"requires zero. Each finding must be [x] closed, "
        f"[ ] deferred-vX.Y with rationale, or [ ] wont-fix with rationale."
    )


def test_deferred_and_wontfix_rows_have_rationale() -> None:
    """LEDGER-01 D-30 gate: deferred and wont-fix rows carry inline rationale.

    The closed-row format includes an inline `— <text>` rationale inside the
    disposition cell (e.g., `[x] closed — closed by Phase 73 (...)`). Deferred
    and wont-fix rows must match this format so future auditors can
    reconstruct the decision without spelunking phase summaries.
    """
    text = LEDGER.read_text(encoding="utf-8")
    bare = _BARE_DISPOSITION_RE.findall(text)
    assert not bare, (
        f"Audit ledger has {len(bare)} bare deferred/wont-fix row(s) lacking "
        f"inline rationale; D-30 invariant requires `[ ] <disposition> — <reason>` "
        f"format. First offender: {bare[0] if bare else '(none)'}"
    )
