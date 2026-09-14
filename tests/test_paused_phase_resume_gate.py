"""Standing gate: a PAUSED phase cannot be silently abandoned (RESUME-01..03).

Why this exists
---------------
On 2026-09-13, Phase 206 (Dashboard UI Coverage Drain) was paused at 5 of 13
plans, mid-milestone, to free the week before a client demo. The operator's
stated concern was the right one: *"I need a way to ensure we come back to
phase 206 after these efforts."*

A prose note is not that guarantee, and this project has three recorded proofs:

  - ``BACK-A11Y-01`` sat invisible for ~3 months after the v5.0 archive
    swallowed it (see ``project_archived_roadmap_loses_backlog_items``).
  - ``BACK-89`` drifted P2 -> P1 while invisible for 3.5 months, the pathology
    HORIZON.md's Open-Item Ledger was created to stop.
  - v5.24 itself was deferred at THREE consecutive milestone boundaries and was
    only held by being *committed* at the v5.23 boundary "so it cannot slip a
    fourth time".

In every case the work was written down somewhere. Writing it down is what
failed. So this gate is mechanical, it rides the ``Linux Full Suite`` CI job
(``pytest -q -m ""`` selects everything, including ``slow``), and it cannot be
satisfied by editing a note.

What it enforces
----------------
RESUME-01  A phase declared PAUSED in ``.planning/STATE.md`` must still carry an
           unchecked ``- [ ]`` box in ``.planning/ROADMAP.md``. Flipping a paused
           phase to ``[x]`` without resuming it is exactly the silent-abandon
           move, and ``phase.complete`` is independently known to flip boxes
           without checking whether the phase's plans are done (see
           ``project_gsd_phase_complete_premature``).

RESUME-02  While ANY phase of the current milestone is unchecked, that milestone
           must NOT be archived under ``.planning/milestones/<version>-ROADMAP.md``.
           This is the ``BACK-A11Y-01`` failure mode stated as an assertion: an
           archive is what makes open work invisible.

RESUME-03  A PAUSE RECORD must name a resume command, so the gate's failure
           message tells the next session what to actually run rather than
           merely that something is wrong.

How to satisfy it
-----------------
Resume and finish the phase, or make a deliberate, recorded decision to drop it
(remove the PAUSE RECORD from STATE.md and say why in ROADMAP.md). Do not
"fix" a failure here by flipping a checkbox — that is the defect, not the remedy.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PLANNING = REPO_ROOT / ".planning"
STATE_PATH = PLANNING / "STATE.md"
ROADMAP_PATH = PLANNING / "ROADMAP.md"
MILESTONES_DIR = PLANNING / "milestones"

# `- [ ] **Phase 206: Dashboard UI Coverage Drain** - ...`
_PHASE_BOX_RE = re.compile(
    r"^- \[(?P<box>[ x])\] \*\*Phase (?P<num>[0-9]+(?:\.[0-9]+)?):",
    re.MULTILINE,
)

# `### Phase 206 PAUSE RECORD (2026-09-13) — ...`
_PAUSE_RECORD_RE = re.compile(
    r"^#+\s+Phase\s+(?P<num>[0-9]+(?:\.[0-9]+)?)\s+PAUSE RECORD\b",
    re.MULTILINE | re.IGNORECASE,
)

_MILESTONE_RE = re.compile(r"^milestone:\s*(?P<version>\S+)\s*$", re.MULTILINE)

# `.planning/` is gitignored; a checkout without it (or a CI job that does not
# provision it) has nothing to police. Skip honestly rather than pass vacuously.
_PLANNING_AVAILABLE = STATE_PATH.is_file() and ROADMAP_PATH.is_file()

pytestmark = pytest.mark.skipif(
    not _PLANNING_AVAILABLE,
    reason="`.planning/STATE.md` and/or ROADMAP.md absent (gitignored) — nothing to gate",
)


def _state_text() -> str:
    return STATE_PATH.read_text(encoding="utf-8")


def _roadmap_text() -> str:
    return ROADMAP_PATH.read_text(encoding="utf-8")


def _paused_phases() -> list[str]:
    """Phase numbers carrying a PAUSE RECORD heading in STATE.md."""
    return [m.group("num") for m in _PAUSE_RECORD_RE.finditer(_state_text())]


def _phase_boxes() -> dict[str, str]:
    """Map phase number -> checkbox char (' ' or 'x') from ROADMAP.md."""
    return {m.group("num"): m.group("box") for m in _PHASE_BOX_RE.finditer(_roadmap_text())}


def _current_milestone() -> str | None:
    m = _MILESTONE_RE.search(_state_text())
    return m.group("version") if m else None


def test_roadmap_phase_boxes_are_parseable() -> None:
    """Positive control: the extractor must find real rows.

    Without this, a regex that silently matches nothing would make every
    assertion below pass vacuously — the exact failure mode recorded in
    `feedback_measure_with_a_method_independent_of_the_audited_code`.
    """
    boxes = _phase_boxes()
    assert boxes, (
        "Parsed zero phase checkboxes from .planning/ROADMAP.md. The heading "
        "format likely changed; _PHASE_BOX_RE needs updating. Until it is, "
        "RESUME-01 and RESUME-02 below are not actually checking anything."
    )
    # RESUME-02 resolves the archive path from this key. If it ever goes missing,
    # fail HERE rather than letting RESUME-02 skip — a silent skip on the
    # archive check is precisely the invisibility this gate exists to prevent.
    assert _current_milestone() is not None, (
        "No `milestone:` key in .planning/STATE.md frontmatter. RESUME-02 cannot "
        "resolve which milestone archive to police without it, so the archive "
        "check would pass without checking anything."
    )


def test_resume_01_paused_phase_box_stays_unchecked() -> None:
    """RESUME-01: a PAUSED phase must not be marked complete in ROADMAP.md."""
    boxes = _phase_boxes()
    offenders = []
    for num in _paused_phases():
        box = boxes.get(num)
        if box is None:
            offenders.append(
                f"Phase {num} has a PAUSE RECORD in STATE.md but no `- [ ] **Phase {num}:` "
                f"row in ROADMAP.md — the phase is now invisible where phases are tracked."
            )
        elif box == "x":
            offenders.append(
                f"Phase {num} is marked COMPLETE (`[x]`) in ROADMAP.md while STATE.md still "
                f"carries its PAUSE RECORD. Either it was resumed and the record was never "
                f"removed, or the box was flipped without the work being done — "
                f"`phase.complete` is known to do exactly that on this machine."
            )
    assert not offenders, "RESUME-01 violated:\n  - " + "\n  - ".join(offenders)


def test_resume_02_open_milestone_is_not_archived() -> None:
    """RESUME-02: do not archive a milestone that still has unchecked phases."""
    version = _current_milestone()
    # Guaranteed non-None by test_roadmap_phase_boxes_are_parseable's control
    # assertion. Asserted rather than skipped: a skip here would silently retire
    # the archive check (Phase 184 D-01/D-09 — do not add skip markers).
    assert version is not None, "unreachable: guarded by the positive-control test"

    unchecked = sorted(
        (num for num, box in _phase_boxes().items() if box == " "),
        key=lambda n: float(n),
    )
    if not unchecked:
        return  # every phase done; archiving is legitimate

    archive = MILESTONES_DIR / f"{version}-ROADMAP.md"
    assert not archive.is_file(), (
        f"RESUME-02 violated: milestone {version} has been archived to {archive} "
        f"while {len(unchecked)} phase(s) remain unchecked in .planning/ROADMAP.md: "
        f"{', '.join(unchecked)}.\n\n"
        "This is the BACK-A11Y-01 failure mode: an archive is what makes open work "
        "invisible. It sat unnoticed for ~3 months last time. Either finish those "
        "phases, or carry them forward into the next milestone's ROADMAP.md "
        "explicitly before archiving this one."
    )


def test_resume_03_pause_record_names_a_resume_command() -> None:
    """RESUME-03: the pause record must say how to resume, not just that it paused."""
    paused = _paused_phases()
    if not paused:
        return  # nothing paused; nothing to require

    text = _state_text()
    missing = [
        num
        for num in paused
        if not re.search(
            rf"/gsd-\S*\s+--from\s+{re.escape(num)}\b|/gsd-\S*\s+--only\s+{re.escape(num)}\b",
            text,
        )
    ]
    assert not missing, (
        "RESUME-03 violated: PAUSE RECORD(s) for phase(s) "
        f"{', '.join(missing)} do not name a resume command. Add the literal command "
        "(e.g. `/gsd-autonomous --from 206 --to 206`) to STATE.md so the next session "
        "can act on it without reconstructing the intent."
    )
