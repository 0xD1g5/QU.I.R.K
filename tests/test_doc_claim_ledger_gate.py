"""Structural gate for the doc classification and the doc-claim ledger (Phase 224).

WHAT THIS ENFORCES
    1. ``docs/doc-classification.jsonl`` has exactly one row per tracked doc
       file: every tracked ``docs/**`` path plus every tracked root file that
       is not code or config (``ROOT_NON_DOC_FILES``). The expected set is
       re-derived from ``git ls-files`` on every run (SC#1).
    2. Every classification row is well formed (class, reason, gate, claims).
    3. Every row of ``docs/doc-claim-ledger.jsonl`` carries every key in
       ``LEDGER_KEYS`` with a value from the closed enums, a unique id, a doc
       that is classified user-facing, an anchor that still resolves in that
       doc (TRUE/FIXED), evidence whose FORMAT matches its method, a ``live``
       flag consistent with the method, and evidence that is not the doc
       itself or planning-internal prose (SC#3, DOC-04).
    3a. Every live (TRUE/FIXED) row names exactly ONE line of its doc as
       committed, through ``section`` (the enclosing heading's label, or null
       before the first heading) + ``anchor`` + ``occurrence`` (1-based among
       the section's lines holding the anchor; null when only one does). An
       anchor that merely occurs somewhere in the doc is not enough: the
       merge used to place a row on the k-th copy of a repeated line, which
       attributed claims to the wrong copy (SC#2).
    4. Every user-facing doc has at least one ledger row, or is classified
       ``no-checkable-claims`` with a reason (D-06).
    5. The ledger holds more than ``LEDGER_ROW_FLOOR`` rows, so a truncated
       file or a broken parser cannot pass as an empty, vacuously-green set.
    6. No user-facing doc tells a reader to ``pip install`` the wrong PyPI
       package (``quirk`` instead of ``quirk-scanner``, or the unrelated
       ``syft`` project). Only ``CHANGELOG.md``'s ``[Unreleased]`` section is
       swept (D-04: released sections are a dated record).

HOW TO FIX A FAILURE
    Every failing message ends with a ``Fix:`` line. In short: add or remove
    the row in ``docs/doc-classification.jsonl``; correct the ledger row; or,
    if a doc edit moved the claim text, update the row's ``anchor``.
    ``line`` is informational and is never compared.

WHY A PYTEST TEST, NOT A PRE-COMMIT HOOK OR DEDICATED CI STEP
    It rides the existing ``Linux Full Suite`` job (``pytest -q -m ""``), so it
    cannot be bypassed with ``--no-verify`` and adds no CI wiring. It carries
    no ``slow`` marker and never skips (a missing ``git`` is a
    hard failure, since CI always has git). It never re-executes claims: the
    executable install gate remains deferred (REQUIREMENTS, Future).

INDEPENDENCE
    Every helper here is written from scratch. Nothing is imported from any
    extraction or merge script under ``.planning/`` or ``scripts/``, so the
    gate cannot share a bug with the tooling that produced the rows.

KNOWN TRAP
    Rows are keyed by ``anchor`` (a verbatim substring), not by line number.
    ``tests/skip_registry.py`` retired line keys in Phase 184 because they
    re-broke on any unrelated line shift. ``LEDGER_ROW_FLOOR`` guards against
    a broken parser, not a quota: the merged ledger held 8,927 rows at Phase
    224 close, and the floor is set well below that so ordinary edits never
    trip it. Never lower it to make the test pass.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Callable

import pytest

from tests.cli_helpers import run_fork_safe

REPO_ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = REPO_ROOT / "docs" / "doc-claim-ledger.jsonl"
CLASSIFICATION_PATH = REPO_ROOT / "docs" / "doc-classification.jsonl"

LEDGER_KEYS = (
    "id", "doc", "line", "line_end", "pre_edit_line", "anchor", "claim",
    "kind", "status", "method", "live", "evidence", "fix", "verified",
)
VALID_CLASSES = frozenset(
    {"user-facing", "generated", "historical", "internal", "asset"})
VALID_CLAIMS = frozenset({"ledger", "no-checkable-claims", "n/a"})
VALID_STATUS = frozenset({"TRUE", "FIXED", "REMOVED"})
VALID_METHODS = frozenset(
    {"command-run", "registry", "source-grep", "test-node", "primary-source"})
VALID_KINDS = frozenset({
    "command", "flag", "install-path", "scanner", "connector", "config-key",
    "output-path", "version", "feature", "link", "contact", "license",
})
NON_LIVE_METHODS = frozenset({"source-grep", "test-node"})
ID_RE = re.compile(r"^DCL-[A-Z0-9]+(-[A-Z0-9]+)*-[0-9]{4}$")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
ROOT_NON_DOC_FILES = frozenset({
    ".dockerignore", ".gitignore", ".gitleaks.toml", "Dockerfile",
    "config.yaml", "lab-registry.yaml", "pyproject.toml", "run_scan.py",
    "uat_runner.py",
})
MIN_ANCHOR_LEN = 12

# Phase 224 merged 8,927 rows (RESEARCH hypothesised ~4,200 claim atoms). The
# floor is a parser guard, not a target (plan 224-17: 1000 when >= 1250 rows).
LEDGER_ROW_FLOOR = 1000

FORBIDDEN_INSTALL_RE = re.compile(
    r"pip3?\s+install\s+(?:-[\w-]+\s+)*['\"]?(?:quirk|syft)(?![\w-])")
# (path, verbatim substring of the line) -> why the line may quote a wrong
# install command. Each entry must still match (see the stale-exemption test).
WRONG_INSTALL_EXEMPTIONS: dict[tuple[str, str], str] = {
    ("docs/report-interpretation.md",
     "`DOCX requires the optional extra: pip install quirk[docx]`"): (
        "verbatim quote of the dashboard's DOCX-unavailable message "
        "(quirk/dashboard/api/routes/reports.py REASON_DOCX_EXTRA_MISSING); "
        "the doc names quirk-scanner[docx] beside it; product defect tracked "
        "in todo 261012-doc224-install-hints-name-wrong-pypi-package"),
}
_RELEASED_HEADING_RE = re.compile(r"^## \[\d", re.MULTILINE)

_SRC_EXT = r"(?:py|md|ts|tsx|js|yaml|yml|toml|json|jsonl|cfg|txt|sh|html|css|ini|rst)"
EVIDENCE_CMD_RE = re.compile(r"^\S.*? -> \S", re.DOTALL)
EVIDENCE_PATH_RE = re.compile(
    r"(?<![\w/.:-])((?:[\w.-]+/)*[\w.-]+\." + _SRC_EXT + r"):(\d+)(?:-(\d+))?\b")
EVIDENCE_TEST_RE = re.compile(
    r"(tests/[\w/.-]+\.py)::\S+.*\b\d+ passed\b", re.DOTALL)
EVIDENCE_URL_RE = re.compile(r'https://\S+\s->\s"[^"]+"')
_DOC_CITE_RE = re.compile(r"docs/[\w/.-]+\.md")
_FORBIDDEN_EVIDENCE = (".planning/", "CLAUDE.md", "SUMMARY.md", "MEMORY.md")


# --------------------------------------------------------------------------
# Enumeration and parsing
# --------------------------------------------------------------------------

def _tracked_doc_paths() -> set[str]:
    """Tracked docs/** plus tracked root doc files, from git ls-files."""
    git = shutil.which("git")
    if git is None:
        pytest.fail("git binary not available; this gate requires a git checkout")
    result = run_fork_safe(
        [git, "-C", str(REPO_ROOT), "ls-files", "-z"], timeout=30)
    assert result.returncode == 0, (
        f"git ls-files failed (rc={result.returncode}): {result.stderr!r}")
    files = [p for p in result.stdout.split("\0") if p]
    assert files, "git ls-files returned nothing; refusing to pass vacuously"
    docs = {p for p in files if p.startswith("docs/")}
    root = {p for p in files if "/" not in p and p not in ROOT_NON_DOC_FILES}
    return docs | root


def parse_jsonl(text: str) -> tuple[list[dict], list[tuple[int, str]]]:
    """Return (rows, [(lineno, error)]) without raising on bad lines."""
    rows: list[dict] = []
    errors: list[tuple[int, str]] = []
    for n, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append((n, str(exc)))
            continue
        if not isinstance(obj, dict):
            errors.append((n, "row is not a JSON object"))
            continue
        rows.append(obj)
    return rows, errors


def _read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def _load(path: Path) -> tuple[list[dict], list[tuple[int, str]]]:
    return parse_jsonl(_read(path))


def _repo_file_exists(rel: str) -> bool:
    return (REPO_ROOT / rel).is_file()


# --------------------------------------------------------------------------
# Pure helpers (each returns violation messages)
# --------------------------------------------------------------------------

def find_classification_set_mismatches(
    expected: set[str], actual: set[str],
) -> tuple[list[str], list[str]]:
    """Return (missing from classification, extra in classification)."""
    return sorted(expected - actual), sorted(actual - expected)


def find_malformed_classification_rows(
    rows: list[dict],
    gate_exists: Callable[[str], bool] = _repo_file_exists,
) -> list[str]:
    msgs: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows, start=1):
        path = row.get("path")
        tag = f"{path!r}" if path else f"row {i}"
        if not isinstance(path, str) or not path:
            msgs.append(f"{tag}: missing path")
            continue
        if path in seen:
            msgs.append(f"{tag}: duplicate path")
        seen.add(path)
        cls = row.get("class")
        if cls not in VALID_CLASSES:
            msgs.append(f"{tag}: class {cls!r} not in {sorted(VALID_CLASSES)}")
        reason = row.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            msgs.append(f"{tag}: empty reason")
        gate = row.get("gate")
        if cls == "generated":
            if (not isinstance(gate, str)
                    or not re.fullmatch(r"tests/test_[\w]+\.py", gate)
                    or not gate_exists(gate)):
                msgs.append(
                    f"{tag}: generated row needs an existing tests/test_*.py "
                    f"gate, got {gate!r}")
        claims = row.get("claims")
        if claims not in VALID_CLAIMS:
            msgs.append(f"{tag}: claims {claims!r} not in {sorted(VALID_CLAIMS)}")
        if cls == "user-facing" and claims not in ("ledger", "no-checkable-claims"):
            msgs.append(f"{tag}: user-facing row must have claims ledger or "
                        f"no-checkable-claims, got {claims!r}")
        if claims == "no-checkable-claims":
            ncr = row.get("no_claims_reason")
            if not isinstance(ncr, str) or not ncr.strip():
                msgs.append(f"{tag}: no-checkable-claims needs no_claims_reason")
        if cls in VALID_CLASSES and cls != "user-facing" and claims != "n/a":
            msgs.append(f"{tag}: non-user-facing row must have claims n/a")
    return msgs


def _ident(row: dict, i: int) -> str:
    rid = row.get("id")
    return str(rid) if isinstance(rid, str) and rid else f"row#{i}"


def find_incomplete_ledger_rows(
    rows: list[dict], user_facing_docs: set[str],
) -> list[str]:
    msgs: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows, start=1):
        rid = _ident(row, i)
        missing = [k for k in LEDGER_KEYS if k not in row]
        if missing:
            msgs.append(f"{rid}: missing keys {missing}")
            continue
        if not isinstance(row["id"], str) or not ID_RE.match(row["id"]):
            msgs.append(f"{rid}: id does not match {ID_RE.pattern}")
        elif row["id"] in seen:
            msgs.append(f"{rid}: duplicate id")
        else:
            seen.add(row["id"])
        if row["status"] not in VALID_STATUS:
            msgs.append(f"{rid}: status {row['status']!r} not in {sorted(VALID_STATUS)}")
        if row["method"] not in VALID_METHODS:
            msgs.append(f"{rid}: method {row['method']!r} not in {sorted(VALID_METHODS)}")
        if row["kind"] not in VALID_KINDS:
            msgs.append(f"{rid}: kind {row['kind']!r} not in {sorted(VALID_KINDS)}")
        ev = row["evidence"]
        if not isinstance(ev, str) or not ev.strip():
            msgs.append(f"{rid}: empty evidence")
        fix = row["fix"]
        has_fix = isinstance(fix, str) and bool(fix.strip())
        if row["status"] == "TRUE" and fix is not None:
            msgs.append(f"{rid}: TRUE row must have fix null")
        if row["status"] in ("FIXED", "REMOVED") and not has_fix:
            msgs.append(f"{rid}: {row['status']} row needs a non-empty fix")
        if row["doc"] not in user_facing_docs:
            msgs.append(f"{rid}: doc {row['doc']!r} is not classified user-facing")
        anchor = row["anchor"]
        if (not isinstance(anchor, str) or len(anchor) < MIN_ANCHOR_LEN
                or "\n" in anchor or "\r" in anchor):
            msgs.append(f"{rid}: anchor must be a single line of >= "
                        f"{MIN_ANCHOR_LEN} chars")
        if not isinstance(row["verified"], str) or not DATE_RE.match(row["verified"]):
            msgs.append(f"{rid}: verified must be YYYY-MM-DD")
        for k in ("claim",):
            if not isinstance(row[k], str) or not row[k].strip():
                msgs.append(f"{rid}: empty {k}")
    return msgs


def find_live_method_violations(rows: list[dict]) -> list[str]:
    msgs: list[str] = []
    for i, row in enumerate(rows, start=1):
        rid = _ident(row, i)
        live = row.get("live")
        method = row.get("method")
        if not isinstance(live, bool):
            msgs.append(f"{rid}: live must be a bool, got {live!r}")
        elif live is False and method not in NON_LIVE_METHODS:
            msgs.append(f"{rid}: live:false is only allowed with "
                        f"{sorted(NON_LIVE_METHODS)}, got method {method!r}")
    return msgs


def find_unresolved_anchors(
    rows: list[dict], read_doc: Callable[[str], str | None],
) -> list[str]:
    msgs: list[str] = []
    for i, row in enumerate(rows, start=1):
        rid = _ident(row, i)
        if row.get("status") not in ("TRUE", "FIXED"):
            continue  # REMOVED anchors hold removed text; not checked
        text = read_doc(row.get("doc", ""))
        if text is None:
            msgs.append(f"{rid}: doc {row.get('doc')!r} cannot be read")
        elif row.get("anchor", "") not in text:
            msgs.append(f"{rid}: anchor not found in {row.get('doc')}: "
                        f"{str(row.get('anchor'))[:60]!r}")
    return msgs


_FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_ATX_HEADING_RE = re.compile(r"^(#{1,6})\s")


def _heading_labels(lines: list[str], doc: str) -> list[tuple[int, str]]:
    """``[(line_no, label)]`` for every markdown heading outside a fence.

    Only ``.md`` docs have headings. A label is the heading line with trailing
    whitespace removed. When the doc repeats a heading line, each copy is
    prefixed by the fewest nearest ancestor headings (joined with ``" > "``)
    that tell the copies apart, and ``" [k]"`` is appended if even the full
    ancestor path repeats."""
    if not doc.lower().endswith(".md"):
        return []
    heads: list[tuple[int, int, str]] = []
    fence: str | None = None
    for n, line in enumerate(lines, start=1):
        fm = _FENCE_OPEN_RE.match(line)
        if fm:
            ch = fm.group(1)[0]
            if fence is None:
                fence = ch
            elif ch == fence:
                fence = None
            continue
        hm = _ATX_HEADING_RE.match(line) if fence is None else None
        if hm:
            heads.append((n, len(hm.group(1)), line.rstrip()))
    ancestors: list[list[str]] = []
    for i, (_, level, _) in enumerate(heads):
        chain: list[str] = []
        for j in range(i - 1, -1, -1):
            if heads[j][1] < level:
                chain.append(heads[j][2])
                level = heads[j][1]
        ancestors.append(chain)

    def path(i: int, k: int) -> str:
        return " > ".join(list(reversed(ancestors[i][:k])) + [heads[i][2]])

    labels = [h[2] for h in heads]
    for text in {h[2] for h in heads}:
        same = [i for i, h in enumerate(heads) if h[2] == text]
        if len(same) < 2:
            continue
        for i in same:
            k = 0
            while (k < len(ancestors[i])
                   and sum(path(j, k) == path(i, k) for j in same) > 1):
                k += 1
            labels[i] = path(i, k)
        full = list(labels)
        for i in same:
            twins = [j for j in same if full[j] == full[i]]
            if len(twins) > 1:
                labels[i] = f"{full[i]} [{twins.index(i) + 1}]"
    return [(heads[i][0], labels[i]) for i in range(len(heads))]


def find_unresolvable_or_ambiguous_rows(
    rows: list[dict], read_doc: Callable[[str], str | None],
) -> list[str]:
    """Live rows whose ``section`` + ``anchor`` + ``occurrence`` do not name
    exactly one line of their doc as committed.

    ``section`` is a heading label (see ``_heading_labels``) or ``None`` for
    the text before the first heading; a section runs from its heading to the
    line before the next heading of any level. ``occurrence`` is the 1-based
    index among the section's lines that contain the anchor, and must be
    ``None`` when exactly one does. REMOVED rows must carry ``None`` for
    both. ``line`` is never consulted."""
    msgs: list[str] = []
    cache: dict[str, tuple[list[str], list[tuple[int, str]]] | None] = {}
    for i, row in enumerate(rows, start=1):
        rid = _ident(row, i)
        if "section" not in row or "occurrence" not in row:
            msgs.append(f"{rid}: missing section/occurrence keys")
            continue
        section, occ = row["section"], row["occurrence"]
        if row.get("status") not in ("TRUE", "FIXED"):
            if section is not None or occ is not None:
                msgs.append(f"{rid}: REMOVED row must have section and "
                            "occurrence null")
            continue
        if section is not None and (not isinstance(section, str)
                                    or not section.strip()):
            msgs.append(f"{rid}: section must be null or a heading label")
            continue
        if occ is not None and (isinstance(occ, bool) or not isinstance(occ, int)
                                or occ < 1):
            msgs.append(f"{rid}: occurrence must be null or a positive int, "
                        f"got {occ!r}")
            continue
        doc = row.get("doc", "")
        if doc not in cache:
            text = read_doc(doc)
            if text is None:
                cache[doc] = None
            else:
                lines = text.split("\n")
                cache[doc] = (lines, _heading_labels(lines, doc))
        entry = cache[doc]
        if entry is None:
            msgs.append(f"{rid}: doc {doc!r} cannot be read")
            continue
        lines, heads = entry
        if section is None:
            lo, hi = 1, (heads[0][0] - 1) if heads else len(lines)
        else:
            idx = [k for k, (_, label) in enumerate(heads) if label == section]
            if len(idx) != 1:
                msgs.append(f"{rid}: section {section!r} matches {len(idx)} "
                            f"headings in {doc}")
                continue
            k = idx[0]
            lo = heads[k][0]
            hi = heads[k + 1][0] - 1 if k + 1 < len(heads) else len(lines)
        anchor = row.get("anchor")
        hits = [n for n in range(lo, hi + 1)
                if isinstance(anchor, str) and anchor and anchor in lines[n - 1]]
        where = f"section {section!r} of {doc} (lines {lo}-{hi})"
        if not hits:
            msgs.append(f"{rid}: anchor not found in {where}: "
                        f"{str(anchor)[:60]!r}")
        elif occ is None and len(hits) > 1:
            msgs.append(f"{rid}: anchor occurs on {len(hits)} lines of {where} "
                        f"({hits[:6]}) and occurrence is null")
        elif occ is not None and len(hits) == 1:
            msgs.append(f"{rid}: occurrence {occ} set but the anchor occurs on "
                        f"one line of {where}; use null")
        elif occ is not None and occ > len(hits):
            msgs.append(f"{rid}: occurrence {occ} out of range 1..{len(hits)} "
                        f"in {where}")
    return msgs


def find_malformed_evidence(
    rows: list[dict],
    path_exists: Callable[[str], bool] = _repo_file_exists,
) -> list[str]:
    msgs: list[str] = []
    for i, row in enumerate(rows, start=1):
        rid = _ident(row, i)
        ev = row.get("evidence")
        method = row.get("method")
        if not isinstance(ev, str) or not ev.strip():
            continue  # reported by find_incomplete_ledger_rows
        cites = [m.group(1) for m in EVIDENCE_PATH_RE.finditer(ev)]
        if method in ("command-run", "registry"):
            if not EVIDENCE_CMD_RE.search(ev):
                msgs.append(f"{rid}: {method} evidence needs '<command> -> "
                            f"<observation>'")
        elif method == "source-grep":
            if not cites:
                msgs.append(f"{rid}: source-grep evidence needs "
                            f"'<path>:<line> <text>'")
        elif method == "test-node":
            m = EVIDENCE_TEST_RE.search(ev)
            if not m:
                msgs.append(f"{rid}: test-node evidence needs "
                            f"'tests/<file>.py::<name> -> N passed'")
            elif not path_exists(m.group(1)):
                msgs.append(f"{rid}: test file {m.group(1)} does not exist")
        elif method == "primary-source":
            if not EVIDENCE_URL_RE.search(ev):
                msgs.append(f"{rid}: primary-source evidence needs "
                            f'\'https://<url> -> "<quoted text>"\'')
        for cite in cites:
            if not path_exists(cite):
                msgs.append(f"{rid}: evidence cites {cite} which does not exist")
    return msgs


def find_self_referential_evidence(rows: list[dict]) -> list[str]:
    msgs: list[str] = []
    for i, row in enumerate(rows, start=1):
        rid = _ident(row, i)
        ev = row.get("evidence")
        if not isinstance(ev, str):
            continue
        hit = [f for f in _FORBIDDEN_EVIDENCE if f in ev]
        if hit:
            msgs.append(f"{rid}: evidence cites planning-internal source {hit}")
            continue
        doc_cites = _DOC_CITE_RE.findall(ev)
        other_src = [
            m.group(1) for m in EVIDENCE_PATH_RE.finditer(ev)
            if not m.group(1).startswith("docs/")
        ]
        if doc_cites and " -> " not in ev and "https://" not in ev and not other_src:
            msgs.append(f"{rid}: evidence is only a docs/*.md citation; a doc "
                        f"cannot be evidence for itself")
    return msgs


def find_uncovered_user_facing_docs(
    classification_rows: list[dict], ledger_rows: list[dict],
) -> list[str]:
    """Sorted user-facing paths with no ledger row and no reasoned exemption.

    A row classified ``no-checkable-claims`` with a non-empty
    ``no_claims_reason`` is covered by that reason; anything else needs at
    least one ledger row."""
    covered = {r.get("doc") for r in ledger_rows}
    out: list[str] = []
    for row in classification_rows:
        if row.get("class") != "user-facing":
            continue
        path = row.get("path")
        reason = row.get("no_claims_reason")
        exempt = (row.get("claims") == "no-checkable-claims"
                  and isinstance(reason, str) and bool(reason.strip()))
        if path not in covered and not exempt:
            out.append(path)
    return sorted(out)


def user_facing_text(path: str, text: str) -> str:
    """The part of a doc that is user-facing (D-04).

    For ``CHANGELOG.md`` that is everything before the first released
    ``## [x.y.z]`` heading; a prefix keeps line numbers unchanged."""
    if path != "CHANGELOG.md":
        return text
    m = _RELEASED_HEADING_RE.search(text)
    return text[:m.start()] if m else text


def _exempt(path: str, line: str,
            exemptions: dict[tuple[str, str], str]) -> bool:
    return any(p == path and s in line for (p, s) in exemptions)


def find_wrong_package_installs(
    docs: dict[str, str],
    exemptions: dict[tuple[str, str], str] | None = None,
) -> list[str]:
    """``<path>:<line>: <text>`` for each line installing the wrong package."""
    exemptions = exemptions or {}
    msgs: list[str] = []
    for path in sorted(docs):
        for n, line in enumerate(docs[path].split("\n"), start=1):
            if FORBIDDEN_INSTALL_RE.search(line) and not _exempt(
                    path, line, exemptions):
                msgs.append(f"{path}:{n}: {line.strip()[:120]}")
    return msgs


def find_stale_install_exemptions(
    docs: dict[str, str], exemptions: dict[tuple[str, str], str],
) -> list[tuple[str, str]]:
    """Exemptions whose substring no longer appears on a flagged line."""
    stale: list[tuple[str, str]] = []
    for (path, sub) in sorted(exemptions):
        lines = docs.get(path, "").split("\n")
        if not any(sub in ln and FORBIDDEN_INSTALL_RE.search(ln)
                   for ln in lines):
            stale.append((path, sub))
    return stale


# --------------------------------------------------------------------------
# Standing tests against the committed artifacts
# --------------------------------------------------------------------------

def _classification_rows() -> list[dict]:
    rows, errors = _load(CLASSIFICATION_PATH)
    assert not errors, f"invalid JSON in classification: {errors}"
    return rows


def _user_facing_docs() -> set[str]:
    return {r["path"] for r in _classification_rows()
            if r.get("class") == "user-facing"}


def _ledger_rows() -> list[dict]:
    rows, errors = _load(LEDGER_PATH)
    assert not errors, f"invalid JSON in ledger: {errors}"
    return rows


def test_classification_matches_tracked_docs() -> None:
    expected = _tracked_doc_paths()
    actual = {r.get("path") for r in _classification_rows()}
    missing, extra = find_classification_set_mismatches(expected, actual)
    assert not missing and not extra, (
        f"docs/doc-classification.jsonl drifted from git ls-files.\n"
        f"  tracked but unclassified: {missing}\n"
        f"  classified but not tracked: {extra}\n"
        "Fix: add or remove the row in docs/doc-classification.jsonl.")


def test_classification_rows_well_formed() -> None:
    msgs = find_malformed_classification_rows(_classification_rows())
    assert not msgs, "\n".join(msgs) + (
        "\nFix: correct the row in docs/doc-classification.jsonl.")


def test_classification_is_not_vacuous() -> None:
    n = len(_classification_rows())
    assert n > 60, (
        f"only {n} classification rows; the artifact looks truncated.\n"
        "Fix: regenerate docs/doc-classification.jsonl from git ls-files.")


def test_ledger_lines_are_valid_json() -> None:
    _, errors = _load(LEDGER_PATH)
    assert not errors, (
        f"invalid JSON lines in docs/doc-claim-ledger.jsonl: {errors}\n"
        "Fix: one JSON object per line.")


def test_ledger_rows_complete() -> None:
    msgs = find_incomplete_ledger_rows(_ledger_rows(), _user_facing_docs())
    assert not msgs, "\n".join(msgs) + (
        "\nFix: every row needs every LEDGER_KEYS key with valid values.")


def test_ledger_live_flag_matches_method() -> None:
    msgs = find_live_method_violations(_ledger_rows())
    assert not msgs, "\n".join(msgs) + (
        "\nFix: live:false is only valid for source-grep or test-node; "
        "command-run rows must be live:true.")


def test_ledger_evidence_format_matches_method() -> None:
    msgs = find_malformed_evidence(_ledger_rows())
    assert not msgs, "\n".join(msgs) + (
        "\nFix: rewrite the evidence in the form its method requires.")


def test_ledger_anchors_resolve() -> None:
    def read_doc(rel: str) -> str | None:
        p = REPO_ROOT / rel
        return _read(p) if p.is_file() else None

    msgs = find_unresolved_anchors(_ledger_rows(), read_doc)
    assert not msgs, "\n".join(msgs) + (
        "\nFix: update the row's anchor to the doc's current wording, or "
        "re-disposition the row.")


def test_live_rows_resolve_to_exactly_one_line() -> None:
    def read_doc(rel: str) -> str | None:
        p = REPO_ROOT / rel
        return _read(p) if p.is_file() else None

    msgs = find_unresolvable_or_ambiguous_rows(_ledger_rows(), read_doc)
    assert not msgs, "\n".join(msgs[:200]) + (
        f"\n({len(msgs)} rows)\nFix: set the row's section to the label of the "
        "heading it sits under, and occurrence to the anchor's 1-based line "
        "index in that section (null when the anchor occurs on one line of "
        "it); or lengthen the anchor. Regenerate the ledger with merge_ledger.")


def test_evidence_is_never_the_doc_itself() -> None:
    msgs = find_self_referential_evidence(_ledger_rows())
    assert not msgs, "\n".join(msgs) + (
        "\nFix: cite a command, source line, test node or primary source.")


# --------------------------------------------------------------------------
# Negative controls: each helper must flag bad input and pass good input
# --------------------------------------------------------------------------

def _good_row(**over: object) -> dict:
    row: dict = {
        "id": "DCL-README-0001", "doc": "README.md", "line": None,
        "line_end": None, "pre_edit_line": 10,
        "anchor": "quirk run --config config.yaml", "claim": "run command",
        "kind": "command", "status": "TRUE", "method": "primary-source",
        "live": True,
        "evidence": 'https://csrc.nist.gov/pubs/fips/203/final -> '
                    '"Module-Lattice-Based Key-Encapsulation Mechanism Standard"',
        "fix": None, "verified": "2026-10-12",
    }
    row.update(over)
    return row


def _good_class_row(**over: object) -> dict:
    row: dict = {
        "path": "README.md", "class": "user-facing", "reason": "front page",
        "gate": None, "master_guide_source": False, "claims": "ledger",
        "no_claims_reason": None,
    }
    row.update(over)
    return row


_UF = {"README.md"}


def test_negative_control_set_mismatch_flagged() -> None:
    assert find_classification_set_mismatches({"a", "b"}, {"b", "c"}) == (
        ["a"], ["c"])


def test_negative_control_set_mismatch_not_flagged() -> None:
    assert find_classification_set_mismatches({"a"}, {"a"}) == ([], [])


def test_negative_control_classification_unknown_class_flagged() -> None:
    assert find_malformed_classification_rows(
        [_good_class_row(**{"class": "bogus"})])


def test_negative_control_classification_empty_reason_flagged() -> None:
    assert find_malformed_classification_rows([_good_class_row(reason=" ")])


def test_negative_control_classification_duplicate_flagged() -> None:
    assert find_malformed_classification_rows(
        [_good_class_row(), _good_class_row()])


def test_negative_control_classification_generated_gate_flagged() -> None:
    row = _good_class_row(**{"class": "generated", "claims": "n/a"})
    assert find_malformed_classification_rows([row])
    row["gate"] = "tests/test_nope_freshness.py"
    assert find_malformed_classification_rows([row], lambda g: False)


def test_negative_control_classification_user_facing_na_flagged() -> None:
    assert find_malformed_classification_rows([_good_class_row(claims="n/a")])


def test_negative_control_classification_no_claims_reason_flagged() -> None:
    assert find_malformed_classification_rows(
        [_good_class_row(claims="no-checkable-claims", no_claims_reason="")])


def test_negative_control_classification_well_formed_not_flagged() -> None:
    gen = _good_class_row(**{
        "path": "docs/error-codes.md", "class": "generated", "claims": "n/a",
        "gate": "tests/test_error_codes_freshness.py"})
    nc = _good_class_row(path="CHANGELOG.md", claims="no-checkable-claims",
                         no_claims_reason="empty Unreleased")
    hist = _good_class_row(path="docs/x.md", **{"class": "historical"},
                           claims="n/a")
    assert find_malformed_classification_rows(
        [_good_class_row(), gen, nc, hist], lambda g: True) == []


def test_negative_control_ledger_missing_key_flagged() -> None:
    row = _good_row()
    del row["evidence"]
    msgs = find_incomplete_ledger_rows([row], _UF)
    assert msgs and "DCL-README-0001" in msgs[0]


@pytest.mark.parametrize("over", [
    {"id": "bad-id"},
    {"status": "MAYBE"},
    {"method": "guess"},
    {"kind": "vibes"},
    {"evidence": "  "},
    {"fix": "should be null"},
    {"doc": "docs/other.md"},
    {"anchor": "short"},
    {"anchor": "two\nlines of anchor text"},
    {"verified": "yesterday"},
])
def test_negative_control_ledger_row_flagged(over: dict) -> None:
    assert find_incomplete_ledger_rows([_good_row(**over)], _UF)


def test_negative_control_ledger_fixed_without_fix_flagged() -> None:
    assert find_incomplete_ledger_rows([_good_row(status="FIXED", fix="")], _UF)
    assert find_incomplete_ledger_rows([_good_row(status="REMOVED")], _UF)


def test_negative_control_ledger_duplicate_id_flagged() -> None:
    assert find_incomplete_ledger_rows([_good_row(), _good_row()], _UF)


def test_negative_control_ledger_complete_not_flagged() -> None:
    fixed = _good_row(id="DCL-README-0002", status="FIXED", fix="changed it")
    assert find_incomplete_ledger_rows([_good_row(), fixed], _UF) == []


def test_negative_control_live_false_flagged() -> None:
    for method in ("command-run", "registry", "primary-source"):
        msgs = find_live_method_violations(
            [_good_row(method=method, live=False)])
        assert len(msgs) == 1, (method, msgs)


def test_negative_control_live_not_flagged() -> None:
    rows = [
        _good_row(method="source-grep", live=False),
        _good_row(method="test-node", live=False),
        _good_row(method="command-run", live=True),
    ]
    assert find_live_method_violations(rows) == []


def test_negative_control_unresolved_anchor_flagged() -> None:
    row = _good_row()
    assert find_unresolved_anchors([row], lambda d: "other text")
    assert find_unresolved_anchors([row], lambda d: None)


def test_negative_control_anchor_not_flagged() -> None:
    row = _good_row()
    assert find_unresolved_anchors([row], lambda d: row["anchor"] + " x") == []
    removed = _good_row(status="REMOVED", fix="deleted")
    assert find_unresolved_anchors([removed], lambda d: "absent") == []


# A doc with a repeated anchor in two sections, a duplicated heading and a
# fenced "# comment" that is not a heading.
_SECTION_DOC = "\n".join([
    "intro: run quirk serve-like",    # 1  (before any heading: section None)
    "# Guide",                        # 2
    "## Usage",                       # 3
    "Run quirk serve here.",          # 4
    "```bash",                        # 5
    "# not a heading",                # 6
    "quirk serve --port 1",           # 7
    "```",                            # 8
    "## Repeat",                      # 9
    "quirk serve again once",         # 10
    "## Alpha",                       # 11
    "### Notes",                      # 12
    "same note line here",            # 13
    "## Beta",                        # 14
    "### Notes",                      # 15
    "same note line here",            # 16
    "",
])


def _sec_row(**over: object) -> dict:
    row = _good_row(doc="docs/sec.md", anchor="quirk serve", section="## Usage",
                    occurrence=None)
    row.update(over)
    return row


def _sec_flags(*rows: dict) -> list[str]:
    return find_unresolvable_or_ambiguous_rows(
        list(rows), lambda d: _SECTION_DOC if d == "docs/sec.md" else None)


def test_negative_control_ambiguous_anchor_without_occurrence_flagged() -> None:
    # "quirk serve" is on lines 4 and 7 of ## Usage (the fenced "#" line is
    # not a heading, so both sit in one section).
    msgs = _sec_flags(_sec_row())
    assert len(msgs) == 1 and "DCL-README-0001" in msgs[0], msgs


def test_negative_control_missing_section_heading_flagged() -> None:
    assert _sec_flags(_sec_row(section="## Nowhere"))
    assert _sec_flags(_sec_row(section="### Notes"))  # 2 headings carry it


def test_negative_control_occurrence_out_of_range_flagged() -> None:
    for occ in (0, 3, -1, True, "1"):
        assert _sec_flags(_sec_row(occurrence=occ)), occ


def test_negative_control_occurrence_on_single_line_flagged() -> None:
    assert _sec_flags(_sec_row(section="## Repeat", occurrence=1))


def test_negative_control_anchor_outside_its_section_flagged() -> None:
    # the anchor exists in the doc, but not in the named section
    assert _sec_flags(_sec_row(anchor="quirk serve again", section="## Usage"))
    assert _sec_flags(_sec_row(anchor="intro: run quirk", section="## Usage"))


def test_negative_control_removed_row_carrying_section_flagged() -> None:
    assert _sec_flags(_sec_row(status="REMOVED", fix="gone", occurrence=1))
    assert _sec_flags(_sec_row(status="REMOVED", fix="gone"))


def test_negative_control_missing_section_keys_flagged() -> None:
    row = _sec_row()
    del row["section"]
    assert _sec_flags(row)


def test_negative_control_section_plus_occurrence_not_flagged() -> None:
    rows = [
        _sec_row(occurrence=1),
        _sec_row(id="DCL-README-0002", occurrence=2),
        _sec_row(id="DCL-README-0003", section="## Repeat"),
        _sec_row(id="DCL-README-0004", anchor="intro: run quirk", section=None),
        _sec_row(id="DCL-README-0005", anchor="same note line",
                 section="## Beta > ### Notes"),
        _sec_row(id="DCL-README-0006", status="REMOVED", fix="gone",
                 anchor="text that is gone", section=None),
    ]
    assert _sec_flags(*rows) == []


def test_negative_control_rows_sharing_unique_anchor_not_flagged() -> None:
    rows = [_sec_row(section="## Repeat", anchor="quirk serve again"),
            _sec_row(id="DCL-README-0002", section="## Repeat",
                     anchor="quirk serve again")]
    assert _sec_flags(*rows) == []


def test_negative_control_non_markdown_doc_is_one_section() -> None:
    text = "# comment\nkey: one\n# comment\nkey: two\n"
    row = _good_row(doc="docs/x.yaml", anchor="key: two", section=None,
                    occurrence=None)
    reader = lambda d: text  # noqa: E731
    assert find_unresolvable_or_ambiguous_rows([row], reader) == []
    assert find_unresolvable_or_ambiguous_rows(
        [dict(row, section="# comment")], reader)


_EXISTS = {"quirk/config.py", "tests/test_jobs_api.py"}


def _exists(p: str) -> bool:
    return p in _EXISTS


def test_negative_control_evidence_command_flagged() -> None:
    row = _good_row(method="command-run", evidence="ran it and it worked")
    assert find_malformed_evidence([row], _exists)


def test_negative_control_evidence_command_not_flagged() -> None:
    row = _good_row(
        method="command-run",
        evidence=".venv/bin/python run_scan.py --help -> '--profile PROFILE'")
    assert find_malformed_evidence([row], _exists) == []


def test_negative_control_evidence_registry_flagged() -> None:
    assert find_malformed_evidence(
        [_good_row(method="registry", evidence="pypi has it")], _exists)


def test_negative_control_evidence_registry_not_flagged() -> None:
    row = _good_row(method="registry", evidence=(
        "curl https://pypi.org/pypi/quirk-scanner/json -> version 5.25.0"))
    assert find_malformed_evidence([row], _exists) == []


def test_negative_control_evidence_source_grep_flagged() -> None:
    no_line = _good_row(method="source-grep", live=False,
                        evidence="it is in the config module")
    missing = _good_row(method="source-grep", live=False,
                        evidence="quirk/nope.py:12 x")
    assert find_malformed_evidence([no_line], _exists)
    assert find_malformed_evidence([missing], _exists)


def test_negative_control_evidence_source_grep_not_flagged() -> None:
    row = _good_row(method="source-grep", live=False,
                    evidence="quirk/config.py:321 enable_gcp: bool = False")
    assert find_malformed_evidence([row], _exists) == []


def test_negative_control_evidence_test_node_flagged() -> None:
    no_pass = _good_row(method="test-node", live=False,
                        evidence="tests/test_jobs_api.py::test_x")
    no_node = _good_row(method="test-node", live=False, evidence="1 passed")
    assert find_malformed_evidence([no_pass], _exists)
    assert find_malformed_evidence([no_node], _exists)


def test_negative_control_evidence_test_node_not_flagged() -> None:
    row = _good_row(method="test-node", live=False, evidence=(
        "tests/test_jobs_api.py::test_post_job_creates_row -> 1 passed"))
    assert find_malformed_evidence([row], _exists) == []


def test_negative_control_evidence_primary_source_flagged() -> None:
    assert find_malformed_evidence(
        [_good_row(evidence="https://example.org says so")], _exists)
    assert find_malformed_evidence(
        [_good_row(evidence="http://example.org -> \"x\"")], _exists)


def test_negative_control_evidence_primary_source_not_flagged() -> None:
    assert find_malformed_evidence([_good_row()], _exists) == []


def test_negative_control_evidence_nonexistent_citation_flagged() -> None:
    row = _good_row(method="command-run",
                    evidence="grep -n x -> quirk/nope.py:3 found")
    assert find_malformed_evidence([row], _exists)


def test_negative_control_self_referential_flagged() -> None:
    for ev in (
        "see .planning/phases/x -> ok",
        "CLAUDE.md:12 says so",
        "224-03-SUMMARY.md -> done",
        "MEMORY.md:3 says so",
        "docs/operators-guide.md:40 says so",
    ):
        assert find_self_referential_evidence([_good_row(evidence=ev)]), ev


def test_negative_control_self_referential_not_flagged() -> None:
    for ev in (
        "quirk/config.py:321 enable_gcp: bool = False",
        ".venv/bin/python run_scan.py --help -> '--profile PROFILE'",
        "https://pypi.org/pypi/quirk-scanner/json -> version 5.25.0",
    ):
        assert find_self_referential_evidence([_good_row(evidence=ev)]) == [], ev


def test_negative_control_mixed_input_flags_exactly_one_row() -> None:
    good = _good_row()
    bad = _good_row(id="DCL-README-0002", method="command-run",
                    evidence="no arrow here")
    msgs = find_malformed_evidence([good, bad], _exists)
    assert len(msgs) == 1 and "DCL-README-0002" in msgs[0]


# --------------------------------------------------------------------------
# Coverage, non-vacuity floor and wrong-package sweep (plan 224-17)
# --------------------------------------------------------------------------

def test_every_user_facing_doc_is_covered() -> None:
    msgs = find_uncovered_user_facing_docs(
        _classification_rows(), _ledger_rows())
    assert not msgs, (
        f"user-facing docs with no ledger rows: {msgs}\n"
        "Fix: add rows for <doc> or mark it no-checkable-claims with a reason.")


def test_ledger_is_not_vacuous() -> None:
    n = len(_ledger_rows())
    assert n > LEDGER_ROW_FLOOR, (
        f"only {n} ledger rows (floor {LEDGER_ROW_FLOOR}); the ledger looks "
        "truncated or its parser broke.\n"
        "Fix: re-merge docs/doc-claim-ledger.jsonl; never lower the floor to "
        "pass this test.")


def _user_facing_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in sorted(_user_facing_docs()):
        p = REPO_ROOT / path
        if p.is_file():
            texts[path] = user_facing_text(path, _read(p))
    assert texts, "no user-facing doc could be read; refusing to pass vacuously"
    return texts


def test_no_wrong_package_install_instructions() -> None:
    msgs = find_wrong_package_installs(
        _user_facing_texts(), WRONG_INSTALL_EXEMPTIONS)
    assert not msgs, "\n".join(msgs) + (
        "\nFix: the PyPI package is quirk-scanner (pip install "
        "'quirk-scanner[all]'); Syft is a binary from Anchore, not the PyPI "
        "'syft' project. Reword the line; quote a wrong product string only "
        "with an entry in WRONG_INSTALL_EXEMPTIONS that says why.")


def test_wrong_install_exemptions_are_not_stale() -> None:
    stale = find_stale_install_exemptions(
        _user_facing_texts(), WRONG_INSTALL_EXEMPTIONS)
    assert not stale, (
        f"exemptions that no longer match any line: {stale}\n"
        "Fix: delete the stale entry from WRONG_INSTALL_EXEMPTIONS.")


def _class(path: str, claims: str = "ledger", cls: str = "user-facing",
           ncr: str | None = None) -> dict:
    return {"path": path, "class": cls, "claims": claims,
            "no_claims_reason": ncr}


def test_negative_control_uncovered_doc_flagged() -> None:
    rows = [_class("README.md"), _class("docs/a.md")]
    ledger = [_good_row(doc="docs/a.md")]
    assert find_uncovered_user_facing_docs(rows, ledger) == ["README.md"]
    empty_reason = [_class("docs/b.md", claims="no-checkable-claims", ncr=" ")]
    assert find_uncovered_user_facing_docs(empty_reason, []) == ["docs/b.md"]


def test_negative_control_uncovered_doc_not_flagged() -> None:
    rows = [
        _class("README.md"),
        _class("CODE_OF_CONDUCT.md", claims="no-checkable-claims",
               ncr="contact route only"),
        _class("docs/hist.md", claims="n/a", cls="historical"),
    ]
    assert find_uncovered_user_facing_docs(rows, [_good_row()]) == []


def test_negative_control_wrong_install_flagged() -> None:
    msgs = find_wrong_package_installs(
        {"README.md": "pip install 'quirk-scanner[all]'\npip install quirk\n"})
    assert len(msgs) == 1 and msgs[0].startswith("README.md:2:"), msgs
    for line in ("pip install syft", "pip3 install --upgrade quirk",
                 "python -m pip install 'quirk[docx]'",
                 'pip install "syft"'):
        assert find_wrong_package_installs({"d.md": line}), line


def test_negative_control_wrong_install_not_flagged() -> None:
    for line in ("pip install quirk-scanner", "pipx install quirk-scanner",
                 "brew install syft", "pip install 'quirk-scanner[docx]'",
                 "pip install quirk_tools_other", "pip install syft-cli-x"):
        assert find_wrong_package_installs({"d.md": line}) == [], line


def test_negative_control_wrong_install_exemption() -> None:
    docs = {"d.md": "quoted: `pip install quirk[docx]` from the UI\n"}
    ex = {("d.md", "`pip install quirk[docx]` from the UI"): "verbatim UI"}
    assert find_wrong_package_installs(docs, ex) == []
    assert find_wrong_package_installs(docs, {("e.md", "x" * 12): "r"})
    assert find_stale_install_exemptions(docs, ex) == []
    assert find_stale_install_exemptions(
        docs, {("d.md", "no such text here"): "r"}) == [
        ("d.md", "no such text here")]


def test_negative_control_changelog_released_sections_not_swept() -> None:
    text = ("# Changelog\n\n## [Unreleased]\n\n- pip install syft\n\n"
            "## [5.25.0] - 2026-09-28\n\n- pip install quirk[motion]\n")
    sliced = user_facing_text("CHANGELOG.md", text)
    msgs = find_wrong_package_installs({"CHANGELOG.md": sliced})
    assert len(msgs) == 1 and msgs[0].startswith("CHANGELOG.md:5:"), msgs
    assert user_facing_text("README.md", text) == text
