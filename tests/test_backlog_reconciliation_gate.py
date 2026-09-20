"""Phase 189 Plan 03 (TRIAGE-09): the derived backlog-reconciliation gate.

WHAT THIS ENFORCES: `.planning/HORIZON.md` declared itself (2026-09-07) the single canonical
open-item ledger. This module makes that declaration mechanically true: no `BACK-*` / `999.*`
ID may be simultaneously un-closed and un-ledgered. Enumeration is regenerated from source at
every run -- there is no hand-written ID list anywhere in this file. That is a deliberate
reaction to this repo's own history (CLAUDE.md TOOL-01..05 / 186.1) of hand-derived site lists
silently undercounting reality five separate times.

RE-DERIVED TRACKED/UNTRACKED SPLIT (observed 2026-09-08, re-checked at Task 1 time -- do not
trust this note without re-running the `git ls-files` commands below, per 189-CONTEXT.md's own
correction to 189-RESEARCH.md):

    - Tracked `*-ROADMAP.md` under `.planning/milestones/`: exactly FIVE --
      v5.11, v5.12, v5.17, v5.18, v5.19.
    - On-disk `*-ROADMAP.md`: THIRTY-ONE (v3.9 through v5.19).
    - Tracked files containing the literal `BACK-`: `v5.19-ROADMAP.md`, `v5.19-REQUIREMENTS.md`,
      and two files under `v5.19-phases/184.4-rating-band-severity-floor/`
      (`184.4-HUMAN-UAT.md`, `184.4-VERIFICATION.md`).
    - `.planning/backlog/` (89 dirs on this checkout) and `.planning/reports/` (except one
      unrelated tracked file, `gsd-sdk-state-corruption-2026-09-03.md`) are UNTRACKED.
    - `.planning/HORIZON.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`,
      `.planning/PROJECT.md`, `.planning/STATE.md` ARE tracked (grandfathered exceptions).

    This confirms 189-CONTEXT.md's correction to 189-RESEARCH.md's "all 156 files ... are
    git-tracked" claim: they are not. It also surfaces a fact RESEARCH did not anticipate --
    `v5.19-ROADMAP.md`, the one tracked file that DOES carry `BACK-` text, carries it as bare
    prose citations of an already-largely-closed item (`BACK-89`), not as `| BACK-N | title | |`
    backlog-table rows. A table-row-only enumeration regex would therefore enumerate ZERO IDs
    from the entire tracked CI-visible corpus while that corpus still contains literal `BACK-`
    text -- exactly the vacuous-pass shape T-189-10 exists to catch. `_enumerate_back_ids` below
    is therefore NOT table-row-only: it also captures bare `BACK-\\d+` mentions, keyed by the
    nearest preceding Markdown heading as a synthetic title, specifically so the non-vacuity
    guard has something honest to find on a tracked-only checkout instead of failing for the
    wrong reason (a regex that structurally cannot ever match what little CI can see).

DESIGN (RQ-2, locked by 189-CONTEXT.md): two enforcement legs plus one always-on guard.

    1. `test_non_vacuity_guard_over_tracked_sources` -- ALWAYS RUNS. Fails if any git-tracked
       source contains the substring `BACK-` while enumeration over that same tracked set
       returns nothing. This is the control that stops the CI-enforced leg from going green on
       a fresh checkout where almost nothing is visible (T-189-10).
    2. `test_back_star_ci_enforced_leg` -- CI-ENFORCED. Enumerates BACK-* IDs from git-tracked
       sources only (ROADMAP + REQUIREMENTS + phase docs -- widened per Phase 189 review WR-05
       so an ID first/only declared outside a roadmap cannot escape), and asserts every
       enumerated id::title key is either closed-with-evidence or listed in HORIZON.md's
       Open-Item Ledger.
    3. `test_full_corpus_local_only_leg` -- LOCAL-ONLY, `skipif`-guarded on the presence of
       `.planning/backlog/` (the untracked 999.* source). Enumerates BOTH the full on-disk
       BACK-* corpus (every `*-ROADMAP.md`, `*-REQUIREMENTS.md`, and `*-phases/**/*.md`,
       tracked or not, per WR-05) AND the full `999.*` corpus
       (`.planning/backlog/` subdirectory names), and asserts the same closed-or-ledgered
       invariant across everything a human running this locally can see. Its skip reason names
       the exact missing paths so a skip in CI logs can never be misread as a pass (T-189-11).

CLOSURE SEMANTICS (locked by 189-CONTEXT.md, non-negotiable):

    - Keyed on title+ID, never ID alone -- `BACK-68` names two unrelated items across different
      roadmap eras (QRAMM, shipped, vs. the still-open broker-ports item). A bare-ID-only gate
      would let the still-open item hide behind the shipped one's closure evidence.
    - Closed: a `- [x]` line citing the ID (the real-world form is
      `- [x] **REQ-ID**: ... -- BACK-NN` in `*-REQUIREMENTS.md`), OR the ID being cited inside
      the enumerated occurrence's own checked-checkbox line (self-closure, the shape
      `v5.19-ROADMAP.md`'s bare `BACK-89` prose citations take), OR a `##`/`###`/`####` heading
      line citing the ID (the real-world form is `### Some Requirement (BACK-NN)`).
    - Ledgered: the ID string appears on a `|`-prefixed table row in `.planning/HORIZON.md`
      (word-boundary-safe -- `BACK-1` must not match inside `BACK-10`). Prose mentions do NOT
      count (WR-04): deleting a real ledger row must trip the gate even while narrative text
      still cites the ID, and the run-time ID-collision disambiguation applies to the ledger
      leg exactly as it does to closure.
    - Closure search runs across the whole visible file universe for that leg (not scoped to
      one milestone era), because the real-world closure path is routinely cross-era -- an ID
      first tabled in a v3.x/v4.x archived roadmap is commonly closed years later by a
      `v4.6-REQUIREMENTS.md`-style heading in a different milestone's files. To still uphold
      "BACK-68's two unrelated items are not conflated" against the one real hazard this
      creates (BACK-68/89/90's cross-era bare-ID reuse, documented in the 2026-09-07
      reconciliation audit's Surprise #4), any ID found with MORE THAN ONE distinct title
      anywhere in the current enumeration -- detected at run time from the enumeration itself,
      never from a hand-written collision list -- requires its closure match to also share a
      title keyword with the matching line/heading, so one title's closure evidence cannot
      silently close a same-ID, different-title item.

ARCHIVED-ROADMAP PROSE NARROWING (added 2026-09-20, see `_drop_archived_prose_duplicates`):
the title-keying above has a cost that went undiagnosed for three phases. Because an archived
roadmap NARRATES history ("...LIFT-01..LIFT-05 all Complete, BACK-51 closed by recorded
decision"), every such sentence mints a fresh `ID::nearest-heading` key for an ID already
closed under a different title -- a key that can never find matching evidence. `BACK-51::Phases`
kept `main` red across Phases 203/204/205 while BACK-51 was demonstrably closed at
HORIZON.md:49. Bare mentions whose sources are ALL archived `milestones/*-ROADMAP.md` are
therefore dropped, but ONLY for IDs also cited outside an archived roadmap, and NEVER for real
table-row declarations. Measured on the tracked corpus: 27 keys / 10 IDs -> 18 keys / the same
10 IDs; offenders 1 -> 0; the non-vacuity guard still sees 18 keys.

    Two things this narrowing must not become, each held by a mutation-proven test:
      - an exemption list -- `test_archived_prose_narrowing_still_catches_a_live_unclosed_id`
      - a silent coverage drop -- `test_archived_roadmap_only_id_keeps_its_coverage` (this is
        the `BACK-86` case: cited nowhere but archived prose, and it stays gated) and
        `test_archived_roadmap_table_row_survives_narrowing`.
    Note the literal reading of the original proposal -- "structured rows only" -- was checked
    and REJECTED: no ID in the tracked corpus has a table row at all, so it would enumerate
    ZERO and fail the non-vacuity guard, the exact T-189-10 shape.

HOUSE PRECEDENTS COPIED: `tests/test_uat_zero_undispositioned_gate.py` (name-every-offender
failure style, riding `pytest -q -m ""` for zero new CI wiring); `tests/test_gsd_state_patch.py`
(the honest-skip-names-the-path idiom; the run-time source-scan-not-a-written-list idiom).

WHAT THIS DOES NOT ENFORCE IN CI: the `999.*` corpus (`.planning/backlog/`) and 26 of the 31
on-disk milestone roadmaps are invisible to a fresh CI checkout (`.gitignore`d). The CI-enforced
leg (test 2) can therefore only ever prove the tracked BACK-* residue (in practice, as of this
writing, the bare-mention `BACK-89` citations inside `v5.19-ROADMAP.md`/`v5.19-REQUIREMENTS.md`)
is closed-or-ledgered. The full invariant over the whole corpus is proven only by test 3,
locally, and only when `.planning/backlog/` happens to be present on the machine running it.
"""
from __future__ import annotations

import re
import subprocess
import warnings
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MILESTONES_DIR = REPO_ROOT / ".planning" / "milestones"
BACKLOG_DIR = REPO_ROOT / ".planning" / "backlog"
HORIZON_PATH = REPO_ROOT / ".planning" / "HORIZON.md"

# ---------------------------------------------------------------------------
# Parsing primitives -- independent, no imports from scripts/ or any sibling
# test module (matches the independence discipline the UAT gates document).
# ---------------------------------------------------------------------------

BACK_ID_RE = re.compile(r"BACK-\d+(?:\.\d+)?")
TABLE_ROW_RE = re.compile(r"^\|\s*(BACK-\d+(?:\.\d+)?)\s*\|\s*([^|]+?)\s*\|")
CHECKED_BOX_RE = re.compile(r"^\s*[-*]\s*\[[xX]\]")
HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")


def _git_tracked_files(pattern: str) -> list[Path]:
    """Ask git what is actually tracked, matching `pattern` relative to REPO_ROOT.

    Never hardcodes a filename list -- that would be the same hand-written-list
    anti-pattern the module docstring warns against, one level up. Falls back to
    an on-disk glob (clearly labeled) if git is unavailable, per Task 1's action spec.
    """
    try:
        # `git -C` instead of a cwd= kwarg, and explicit close_fds=False:
        # both are required by tests/test_cli_helper_usage.py's fork-safety
        # gate (cwd= or default close_fds defeats posix_spawn selection and
        # reintroduces the macOS fork-after-Network.framework SIGSEGV).
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", pattern],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
            close_fds=False,
        )
    except (subprocess.SubprocessError, OSError):
        # IN-01: label the fallback at runtime (the docstring's "clearly
        # labeled" claim was previously aspirational) and apply the same
        # is_file() filter as the git branch. The dead
        # pattern.replace(REPO_ROOT, ...) no-op is gone: call sites always
        # pass repo-relative patterns.
        warnings.warn(
            f"_git_tracked_files: git unavailable -- glob fallback engaged for {pattern!r}; "
            "the 'tracked-only' set is silently widened to the full on-disk glob.",
            stacklevel=2,
        )
        return sorted(p for p in REPO_ROOT.glob(pattern) if p.is_file())
    paths = [REPO_ROOT / line for line in out.stdout.splitlines() if line.strip()]
    return sorted(p for p in paths if p.is_file())


def _rel(path: Path) -> str:
    """Repo-relative path for evidence strings; falls back to the absolute
    path for files outside REPO_ROOT (e.g. tmp_path fixtures in the parser
    regression tests below)."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _boundary_search(id_str: str, text: str) -> bool:
    """Word-boundary-safe substring search: `BACK-1` must not match inside `BACK-10`."""
    pattern = re.escape(id_str) + r"(?!\.?\d)"
    return re.search(pattern, text) is not None


def _era_stem(roadmap_path: Path) -> str:
    name = roadmap_path.name
    if name.endswith("-ROADMAP.md"):
        return name[: -len("-ROADMAP.md")]
    return roadmap_path.stem


_TITLE_KEYWORD_RE = re.compile(r"[a-zA-Z]{4,}")


def _title_keywords(title: str) -> set[str]:
    return set(_TITLE_KEYWORD_RE.findall(title.lower()))


def _is_archived_roadmap(path: Path) -> bool:
    """True for `.planning/milestones/<era>-ROADMAP.md` -- a historical record.

    The LIVE roadmap is `.planning/ROADMAP.md`, which is not under
    `milestones/` and is therefore never archived by this predicate.

    Keyed on the parent directory's NAME rather than on equality with the
    absolute `MILESTONES_DIR`, so the narrowing can be exercised from a
    `tmp_path` fixture. A predicate only reachable via the real repo layout
    is a predicate whose negative control cannot be written.
    """
    return path.parent.name == "milestones" and path.name.endswith("-ROADMAP.md")


def _drop_archived_prose_duplicates(result: dict) -> dict:
    """Phase 206-era fix: archived-roadmap PROSE must not manufacture obligations.

    An archived roadmap narrates history ("...LIFT-01..LIFT-05 all Complete,
    BACK-51 closed by recorded decision"). Because keys are `ID::nearest-heading`,
    every such sentence mints a NEW key for an ID that is already closed under a
    different title elsewhere, and that key can never find matching closure
    evidence. That is how `BACK-51::Phases` kept CI red on `main` across Phases
    203/204/205 while BACK-51 was demonstrably closed at HORIZON.md:49.

    Two constraints make this a narrowing of *noise*, not of *coverage*:

      1. Only BARE mentions are dropped. A real `| BACK-N | Title |` table row in
         an archived roadmap is a structured declaration, not narration, and is
         always kept -- the full-corpus leg's `v3.9`-`v5.0` roadmaps carry exactly
         those.
      2. Only IDs that are ALSO cited outside archived roadmaps are dropped. An ID
         whose sole citation anywhere is archived-roadmap prose keeps its key and
         stays gated. Without this clause `BACK-86` -- cited only in
         `v5.23-ROADMAP.md` -- would silently leave the gate's coverage entirely,
         which is the "archived roadmaps swallow backlog items" failure this repo
         has already been bitten by once.

    Measured on the tracked corpus at 2026-09-20: 27 keys over 10 IDs -> 18 keys
    over the SAME 10 IDs, offenders 1 -> 0.
    """
    archived_prose = {
        key
        for key, entry in result.items()
        if not entry["table_row"] and all(_is_archived_roadmap(p) for p in entry["sources"])
    }
    cited_elsewhere = {
        entry["id"] for key, entry in result.items() if key not in archived_prose
    }
    return {
        key: entry
        for key, entry in result.items()
        if not (key in archived_prose and entry["id"] in cited_elsewhere)
    }


def _enumerate_back_ids(roadmap_paths: list[Path]) -> dict:
    """Enumerate BACK-* IDs from `roadmap_paths` at call time.

    Returns {"<ID>::<title>": {"id": ID, "title": title, "era": stem,
    "self_closed": bool, "sources": {path, ...}}}.

    Two enumeration shapes, matching what's actually on disk (see module docstring):
      1. Backlog table rows: `| BACK-N | Title | ... |` -- title is column 2.
      2. Bare `BACK-N` mentions outside table-row shape -- title is the nearest
         preceding Markdown heading text (or "(no heading)" if none precedes it).

    Shape 2 (the bare-mention fallback) is applied ONLY for IDs that have ZERO real table-row
    declaration ANYWHERE across `roadmap_paths` (not just the current file). A file that carries
    no table of its own (`v5.19-ROADMAP.md`, which has none) may still bare-cite an ID that IS
    declared with a real title elsewhere in the same `roadmap_paths` set (the full-corpus leg's
    `BACK-87` is declared with a real title in `v4.8-ROADMAP.md`/`v5.0-ROADMAP.md` but also
    bare-cited once in `v4.6-ROADMAP.md`'s prose); scanning that bare citation as a fresh
    declaration would synthesize a bogus second id::heading-title key for an ID that already has
    a real title. Suppressing shape 2 for any ID with a real table-row title anywhere in this
    call's input is what correctly enumerates `v5.19-ROADMAP.md`'s bare `BACK-89` citations for
    the CI-enforced leg (whose `roadmap_paths` is the 5 tracked files, NONE of which carry a
    table row for `BACK-89`) while not polluting the full-corpus leg (whose `roadmap_paths`
    includes the real `BACK-89` table rows from `v3.9`-`v5.0`) with a spurious duplicate.
    """
    table_row_ids: set[str] = set()
    for path in roadmap_paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            tm = TABLE_ROW_RE.match(line)
            if tm:
                table_row_ids.add(tm.group(1))

    result: dict = {}
    for path in roadmap_paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        stem = _era_stem(path)
        current_heading = "(no heading)"
        for line in lines:
            hm = HEADING_RE.match(line)
            if hm:
                current_heading = hm.group(2).strip()
                continue
            tm = TABLE_ROW_RE.match(line)
            if tm:
                matches = [(tm.group(1), tm.group(2).strip())]
            else:
                # WR-02: iterate ALL bare mentions on the line — a prose line
                # like "BACK-89 shipped, but BACK-99 remains open" must
                # enumerate BOTH IDs, never just the first. (`\d+` is greedy,
                # so finditer can never yield BACK-1 inside BACK-10.)
                matches = [
                    (bm.group(0), current_heading)
                    for bm in BACK_ID_RE.finditer(line)
                    if bm.group(0) not in table_row_ids
                ]
            for back_id, title in matches:
                key = f"{back_id}::{title}"
                entry = result.setdefault(
                    key,
                    {
                        "id": back_id,
                        "title": title,
                        "era": stem,
                        "self_closed": False,
                        "sources": set(),
                        # Whether this key was ever declared by a real
                        # `| BACK-N | Title |` row, as opposed to being
                        # synthesized from a bare mention plus its nearest
                        # heading. _drop_archived_prose_duplicates() keeps
                        # table-row declarations unconditionally.
                        "table_row": False,
                    },
                )
                entry["sources"].add(path)
                if tm:
                    entry["table_row"] = True
                if CHECKED_BOX_RE.match(line) and _boundary_search(back_id, line):
                    entry["self_closed"] = True
    return _drop_archived_prose_duplicates(result)


def _enumerate_999_ids(backlog_dir: Path) -> dict:
    """Enumerate 999.* IDs from `.planning/backlog/` subdirectory names."""
    result: dict = {}
    if not backlog_dir.is_dir():
        return result
    id_re = re.compile(r"^(999\.\d+)-(.+)$")
    for child in sorted(backlog_dir.iterdir()):
        if not child.is_dir():
            continue
        m = id_re.match(child.name)
        if not m:
            continue
        back_id = m.group(1)
        title = m.group(2).replace("-", " ")
        key = f"{back_id}::{title}"
        result[key] = {"id": back_id, "title": title, "era": None, "self_closed": False, "sources": {child}}
    return result


def _is_closed(entry: dict, closure_universe: list[Path], disambiguate: bool) -> tuple[bool, str | None]:
    """Search `closure_universe` (either the tracked-only or full on-disk file list, matching
    the calling leg's visibility) for a `- [x]` line or heading citing `entry["id"]`.

    `disambiguate`: when True (this ID has more than one distinct title anywhere in the
    current enumeration -- i.e. a genuine BACK-68/89/90-style number reuse, detected at run
    time rather than from a hand-written list), a match only counts if the matching line (or
    its immediately preceding heading, for closure lines that sit under one) shares at least
    one 4+ letter keyword with the entry's own title. This is what keeps one era's closure
    evidence for one title from silently closing an unrelated item that happens to reuse the
    same bare ID (the truth this gate must uphold: 'BACK-68's two unrelated items are not
    conflated')."""
    if entry["self_closed"]:
        src = next(iter(entry["sources"]))
        return True, f"self-referential [x] line in {_rel(src)}"
    back_id = entry["id"]
    title_kw = _title_keywords(entry["title"]) if disambiguate else set()
    for path in closure_universe:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        current_heading = "(no heading)"
        for line in lines:
            hm = HEADING_RE.match(line)
            if hm:
                current_heading = hm.group(2).strip()
            if not _boundary_search(back_id, line):
                continue
            if CHECKED_BOX_RE.match(line):
                # WR-03: the heading fallback documented above is real — a
                # `- [x] BACK-NN` closure line whose own text lacks a title
                # keyword still counts if its immediately preceding heading
                # carries one (e.g. `- [x] BACK-68` under `### Broker
                # Scanner Ports`).
                if disambiguate and not (
                    title_kw & (_title_keywords(line) | _title_keywords(current_heading))
                ):
                    continue
                return True, f"[x] line in {_rel(path)}"
            if HEADING_RE.match(line):
                if disambiguate and not (
                    title_kw & (_title_keywords(line) | _title_keywords(current_heading))
                ):
                    continue
                return True, f"heading in {_rel(path)}"
    return False, None


def _is_ledgered(entry: dict, horizon_text: str, disambiguate: bool) -> bool:
    """WR-04: a ledger claim requires a real `|`-prefixed table row in
    HORIZON.md citing the ID -- a residual prose mention (rationale
    paragraph, completeness-patch narrative) must NOT keep the gate green
    after the actual ledger row is deleted. When `disambiguate` is true
    (same run-time collision detection as `_is_closed`), the matching row
    must also share a title keyword with the entry, so a NEW differently-
    titled item reusing an already-ledgered ID (the BACK-68/89/90 pattern)
    cannot pass instantly via an unrelated row."""
    title_kw = _title_keywords(entry["title"]) if disambiguate else set()
    for line in horizon_text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        if not _boundary_search(entry["id"], line):
            continue
        if disambiguate and not (title_kw & _title_keywords(line)):
            continue
        return True
    return False


def _offenders(entries: dict, closure_universe: list[Path], horizon_text: str) -> list[str]:
    id_titles: dict[str, set[str]] = {}
    for entry in entries.values():
        id_titles.setdefault(entry["id"], set()).add(entry["title"])

    offenders = []
    for key, entry in sorted(entries.items()):
        disambiguate = len(id_titles.get(entry["id"], set())) > 1
        closed, evidence = _is_closed(entry, closure_universe, disambiguate)
        if closed:
            continue
        if _is_ledgered(entry, horizon_text, disambiguate):
            continue
        src = ", ".join(sorted(str(p.relative_to(REPO_ROOT)) for p in entry["sources"]))
        offenders.append(f"{key} (source: {src})")
    return offenders


# ---------------------------------------------------------------------------
# Test 1: non-vacuity guard -- ALWAYS RUNS, no skipif.
# ---------------------------------------------------------------------------


def test_non_vacuity_guard_over_tracked_sources():
    """T-189-10: a CI-visible source set that still contains literal `BACK-` text must never
    read as a pass just because the enumeration regex found nothing. This is the control that
    stops the CI-enforced leg (test 2) from going green vacuously."""
    tracked_sources = (
        _git_tracked_files(".planning/milestones/*-ROADMAP.md")
        + _git_tracked_files(".planning/milestones/*-REQUIREMENTS.md")
        + _git_tracked_files(".planning/milestones/*-phases/**/*.md")
    )
    contains_back_text = [
        p for p in tracked_sources if "BACK-" in p.read_text(encoding="utf-8", errors="replace")
    ]
    enumerated = _enumerate_back_ids(tracked_sources)
    if contains_back_text and not enumerated:
        pytest.fail(
            "Non-vacuity guard tripped: "
            f"{[str(p.relative_to(REPO_ROOT)) for p in contains_back_text]} "
            "contain the literal substring 'BACK-' but _enumerate_back_ids() found zero IDs. "
            "The enumeration regex is the suspect here -- a silently-non-matching regex must "
            "never read as 'nothing to enforce'. (T-189-10)"
        )


# ---------------------------------------------------------------------------
# Test 2: the CI-enforced BACK-* leg.
# ---------------------------------------------------------------------------


def test_back_star_ci_enforced_leg():
    """CI-enforced (RQ-2): every BACK-* ID enumerable from git-tracked sources must be either
    closed-with-evidence (within its own milestone era) or listed in HORIZON.md's Open-Item
    Ledger. Runs on every `pytest -q -m ""` invocation, including a fresh CI checkout, because
    it only ever touches git-tracked files."""
    tracked_roadmaps = _git_tracked_files(".planning/milestones/*-ROADMAP.md")
    tracked_requirements = _git_tracked_files(".planning/milestones/*-REQUIREMENTS.md")
    tracked_phase_docs = _git_tracked_files(".planning/milestones/*-phases/**/*.md")
    closure_universe = tracked_roadmaps + tracked_requirements + tracked_phase_docs

    # WR-05: enumeration reads the SAME widened set as closure -- an ID first
    # (or only) declared in a REQUIREMENTS file or phase doc must not escape.
    entries = _enumerate_back_ids(closure_universe)
    horizon_text = HORIZON_PATH.read_text(encoding="utf-8", errors="replace")
    offenders = _offenders(entries, closure_universe, horizon_text)

    if offenders:
        detail = "\n".join(f"  - {o}" for o in offenders)
        pytest.fail(
            f"{len(offenders)} BACK-* ID(s) found neither closed-with-evidence nor listed in "
            f".planning/HORIZON.md's Open-Item Ledger:\n{detail}\n\n"
            "Fix: add an honest row (or a 'Resolved by' subsection entry) to "
            ".planning/HORIZON.md's Open-Item Ledger for each ID above."
        )


# ---------------------------------------------------------------------------
# Test 3: the full-corpus local-only leg.
# ---------------------------------------------------------------------------


def _missing_local_only_paths() -> list[str]:
    missing = []
    if not BACKLOG_DIR.is_dir():
        missing.append(str(BACKLOG_DIR.relative_to(REPO_ROOT)))
    # A representative sample of untracked archived roadmaps -- if these are absent,
    # this is a checkout that can't see the full corpus (e.g. a fresh CI clone).
    for probe in ("v5.0-ROADMAP.md", "v4.8-ROADMAP.md", "v4.1-ROADMAP.md"):
        probe_path = MILESTONES_DIR / probe
        if not probe_path.is_file():
            missing.append(str(probe_path.relative_to(REPO_ROOT)))
    return missing


_MISSING_LOCAL_PATHS = _missing_local_only_paths()


@pytest.mark.skipif(
    bool(_MISSING_LOCAL_PATHS),
    reason=(
        "Full-corpus leg skipped -- this is a CI-visibility limit, not a bypass. Missing "
        f"paths: {_MISSING_LOCAL_PATHS}. These live under .planning/backlog/ and "
        ".planning/milestones/, both of which are git-ignored except for a small set of "
        "grandfathered files, so a fresh CI checkout cannot see them. Run locally on a full "
        "working tree to exercise this leg."
    ),
)
def test_full_corpus_local_only_leg():
    """Local-only (RQ-2): the full on-disk BACK-* corpus (every *-ROADMAP.md, tracked or not)
    plus the full 999.* corpus (.planning/backlog/ subdirectory names) must be entirely
    closed-with-evidence or ledgered. Skips honestly (naming the missing paths) when the
    untracked sources this leg needs are absent, e.g. on a fresh CI checkout."""
    all_roadmaps = sorted(MILESTONES_DIR.glob("*-ROADMAP.md"))
    all_requirements = sorted(MILESTONES_DIR.glob("*-REQUIREMENTS.md"))
    all_phase_docs = sorted(MILESTONES_DIR.glob("*-phases/**/*.md"))
    closure_universe = all_roadmaps + all_requirements + all_phase_docs

    # WR-05: same widening as the CI leg -- enumerate over the full closure set.
    back_entries = _enumerate_back_ids(closure_universe)
    id_999_entries = _enumerate_999_ids(BACKLOG_DIR)
    entries = {**back_entries, **id_999_entries}

    horizon_text = HORIZON_PATH.read_text(encoding="utf-8", errors="replace")
    offenders = _offenders(entries, closure_universe, horizon_text)

    if offenders:
        detail = "\n".join(f"  - {o}" for o in offenders)
        pytest.fail(
            f"{len(offenders)} BACK-*/999.* ID(s) found neither closed-with-evidence nor "
            f"listed in .planning/HORIZON.md's Open-Item Ledger:\n{detail}\n\n"
            "Fix: add an honest row (or a 'Resolved by' subsection entry) to "
            ".planning/HORIZON.md's Open-Item Ledger for each ID above. Do not narrow "
            "enumeration or hand-exempt IDs to make this pass."
        )


# ---------------------------------------------------------------------------
# Parser regression tests (Phase 189 review fixes).
# ---------------------------------------------------------------------------


def test_enumerate_captures_every_id_on_a_multi_id_line(tmp_path):
    """WR-02 regression: two bare IDs on one prose line must BOTH enumerate —
    the pre-fix `.search()` took only the first, a silent-escape vector."""
    doc = tmp_path / "vX-ROADMAP.md"
    doc.write_text(
        "## Some Heading\n"
        "BACK-9001 shipped, but BACK-9002 remains open\n",
        encoding="utf-8",
    )
    entries = _enumerate_back_ids([doc])
    ids = {e["id"] for e in entries.values()}
    assert ids == {"BACK-9001", "BACK-9002"}


def test_is_closed_heading_fallback_disambiguates(tmp_path):
    """WR-03 regression: for a collided ID, a `- [x] BACK-NN` line with no
    title keywords of its own must still count as closure when its
    immediately preceding heading shares a keyword with the entry title —
    the documented (previously unimplemented) fallback."""
    doc = tmp_path / "vY-REQUIREMENTS.md"
    doc.write_text(
        "### Broker Scanner Ports\n"
        "- [x] BACK-9003\n",
        encoding="utf-8",
    )
    entry = {
        "id": "BACK-9003",
        "title": "Broker scanner ports hardcoded",
        "era": "vY",
        "self_closed": False,
        "sources": {doc},
    }
    closed, evidence = _is_closed(entry, [doc], disambiguate=True)
    assert closed, "heading-fallback disambiguation must accept this closure"

    # Negative control: an unrelated heading must NOT disambiguate.
    other = tmp_path / "vZ-REQUIREMENTS.md"
    other.write_text(
        "### Completely Unrelated Theme\n"
        "- [x] BACK-9003\n",
        encoding="utf-8",
    )
    closed, _ = _is_closed(entry, [other], disambiguate=True)
    assert not closed, "keyword-free closure under an unrelated heading must not count"


def test_is_ledgered_requires_table_row_not_prose():
    """WR-04 regression: deleting the real ledger row must be noticed even
    when a prose mention of the ID survives elsewhere in HORIZON.md."""
    entry = {
        "id": "BACK-9004",
        "title": "Widget frobnicator drift",
        "era": "vY",
        "self_closed": False,
        "sources": set(),
    }
    prose_only = (
        "The completeness patch narrative still cites BACK-9004 as resolved\n"
        "in a rationale paragraph, but its ledger row was deleted.\n"
    )
    assert not _is_ledgered(entry, prose_only, disambiguate=False), (
        "a prose-only mention must NOT satisfy the ledger check"
    )
    with_row = prose_only + "| BACK-9004 | Widget frobnicator drift | P3 | open |\n"
    assert _is_ledgered(entry, with_row, disambiguate=False)


def test_is_ledgered_collision_requires_title_keyword_on_row():
    """WR-04 regression: a NEW differently-titled item reusing an
    already-ledgered ID must not pass via the old, unrelated row."""
    horizon = "| BACK-9005 | Broker scanner ports hardcoded | P3 | open |\n"
    old_item = {
        "id": "BACK-9005",
        "title": "Broker scanner ports hardcoded",
        "era": "vY",
        "self_closed": False,
        "sources": set(),
    }
    new_item = {**old_item, "title": "Dashboard theme regression"}
    assert _is_ledgered(old_item, horizon, disambiguate=True)
    assert not _is_ledgered(new_item, horizon, disambiguate=True), (
        "an unrelated same-ID item must not hide behind the old ledger row"
    )


# ---------------------------------------------------------------------------
# Archived-roadmap prose narrowing (2026-09-20): `BACK-51::Phases`.
#
# These four tests are the price of narrowing enumeration. Narrowing a gate's
# input set to turn it green is the exact anti-pattern Phase 204's COV-02 work
# existed to stop, so the narrowing ships with a negative control proving what
# it must STILL catch, and two coverage tests proving what it must NOT drop.
# ---------------------------------------------------------------------------


def _milestones(tmp_path):
    d = tmp_path / "milestones"
    d.mkdir()
    return d


def test_archived_prose_narrowing_still_catches_a_live_unclosed_id(tmp_path):
    """NEGATIVE CONTROL (mandatory): a genuinely-unclosed BACK-* cited in a
    NON-archived source must still be enumerated and still reach _offenders.

    If this ever goes green-by-omission the narrowing has become an exemption
    list, which is the failure mode it was written to avoid.
    """
    ms = _milestones(tmp_path)
    (ms / "v9.0-ROADMAP.md").write_text(
        "## Phases\nBACK-9100 closed by recorded decision\n", encoding="utf-8"
    )
    live = ms / "v9.0-REQUIREMENTS.md"
    live.write_text("## Standing Drain\nBACK-9100 is still open\n", encoding="utf-8")

    entries = _enumerate_back_ids([ms / "v9.0-ROADMAP.md", live])

    assert "BACK-9100::Phases" not in entries, "archived prose key should be dropped"
    assert "BACK-9100::Standing Drain" in entries, (
        "the live, non-archived citation must survive the narrowing"
    )
    # _offenders() formats sources relative to REPO_ROOT and so cannot take
    # tmp_path inputs; assert the same invariant through the two predicates it
    # is built from. Surviving enumeration while being neither closed nor
    # ledgered is exactly what makes an entry an offender.
    entry = entries["BACK-9100::Standing Drain"]
    closed, _ = _is_closed(entry, [live], disambiguate=False)
    assert not closed, "nothing closes BACK-9100 in the live source"
    assert not _is_ledgered(entry, "(empty ledger)", disambiguate=False), (
        "an empty ledger must not satisfy the ledgered leg"
    )


def test_archived_roadmap_only_id_keeps_its_coverage(tmp_path):
    """BACK-86 protection: an ID whose ONLY citation anywhere is archived-roadmap
    prose must stay enumerated. Dropping it would remove it from the gate
    silently -- the 'archived roadmaps swallow backlog items' failure."""
    ms = _milestones(tmp_path)
    only = ms / "v9.1-ROADMAP.md"
    only.write_text("## Phases\nBACK-9200 promoted into v9.2\n", encoding="utf-8")

    entries = _enumerate_back_ids([only])
    assert {e["id"] for e in entries.values()} == {"BACK-9200"}, (
        "an archived-roadmap-only ID must not be narrowed away"
    )


def test_archived_roadmap_table_row_survives_narrowing(tmp_path):
    """A real `| BACK-N | Title |` row is a structured declaration, not
    narration, and is kept even in an archived roadmap even when the same ID is
    cited elsewhere. The full-corpus leg's v3.9-v5.0 roadmaps carry these.

    The second declaration must itself be a TABLE ROW in a non-archived file,
    not a bare mention: `_enumerate_back_ids`'s shape-2 suppression already
    discards bare mentions for any ID that has a table row anywhere, so a
    bare-mention fixture leaves the ID with a single archived-roadmap-only key,
    which the `cited_elsewhere` clause keeps on its own. That fixture passes
    whether or not the table-row protection exists -- verified by mutation on
    2026-09-20, where removing the protection left it green.
    """
    ms = _milestones(tmp_path)
    archived = ms / "v9.2-ROADMAP.md"
    archived.write_text(
        "## Backlog\n| BACK-9300 | Real declared title | open |\n", encoding="utf-8"
    )
    other = ms / "v9.2-REQUIREMENTS.md"
    other.write_text(
        "## Elsewhere\n| BACK-9300 | A second declared title | open |\n",
        encoding="utf-8",
    )

    entries = _enumerate_back_ids([archived, other])
    assert "BACK-9300::A second declared title" in entries, (
        "fixture precondition: the non-archived declaration must enumerate, "
        "otherwise this test cannot exercise the protection at all"
    )
    assert "BACK-9300::Real declared title" in entries, (
        "a table-row declaration must never be narrowed away as prose"
    )


def test_narrowing_is_not_vacuous_on_the_real_corpus():
    """Prove the narrowing actually fires here, rather than being dead code that
    happens to sit next to a green gate.

    Deliberately carries NO skip guard for an empty corpus. The sibling
    `test_non_vacuity_guard_over_tracked_sources` faces the same possibility and
    degrades to a conditional failure rather than skipping, because in this
    module a skip reads as a pass -- the exact confusion T-189-11 exists to
    prevent. An empty enumeration here fails loudly instead; `_git_tracked_files`
    already falls back to an on-disk glob and warns when git is unavailable, so
    reaching zero paths means something is wrong and worth hearing about.
    """
    paths = (
        _git_tracked_files(".planning/milestones/*-ROADMAP.md")
        + _git_tracked_files(".planning/milestones/*-REQUIREMENTS.md")
        + _git_tracked_files(".planning/milestones/*-phases/**/*.md")
    )
    kept = _enumerate_back_ids(paths)
    assert kept, (
        "enumeration returned nothing over "
        f"{len(paths)} milestone source(s) -- the narrowing cannot be shown to "
        "fire, and the non-vacuity guard (T-189-10) is the test to read next"
    )
    assert not any(
        entry["id"] == "BACK-51" and entry["title"] == "Phases"
        for entry in kept.values()
    ), "BACK-51::Phases should be narrowed away"
