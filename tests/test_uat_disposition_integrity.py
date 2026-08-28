"""Phase 168 Plan 02 (UATREC-03): the anti-fabrication guard for
``docs/UAT-SERIES.md`` deferral annotations.

Why this exists: dispositioning ~300 UAT cases has one dominant failure
mode -- inventing coverage. Writing ``DEFERRED -- covered by
tests/test_foo.py::test_bar`` where that node does not exist, or exists but
tests something else, converts an honest gap into a false green. This
module makes that mechanically impossible by checking every named
substitute two ways:

  1. EXISTENCE -- the node ID must resolve against a real
     ``pytest --collect-only`` node set (globs included).
  2. EXECUTION -- the node must actually pass. Critically, a *skip* is
     NOT proof of coverage: ``pytest`` exits 0 for a run containing only
     passes and skips, so an exit-code-only check would accept a
     ``@pytest.mark.skipif``-guarded substitute as "coverage" with zero
     assertions executed. This module parses the pytest summary instead
     of trusting the return code, and treats any skip as a hard failure.

It also asserts the JSONL ledger (``docs/uat-disposition-ledger.jsonl``,
Phase 168 Plan 01) and the Markdown document cannot drift apart, and that a
bare requirement-ID token (``DISC-01``, ``LAB-03``) is never accepted as a
substitute -- only a real ``<file>.py::<test>`` node ID counts.

Independence (same discipline as ``tests/test_uat_series_format.py``,
Phase 167): every parsing helper below is written from scratch and imports
NOTHING from ``scripts/uat_series_normalize.py`` or
``scripts/uat_disposition_apply.py``. A shared parsing bug in either script
would otherwise let the writer and this checker agree with each other while
both are wrong about what the document actually says.

Phase 169 Plan 02 (D-05, first half): a second dialect, for a vitest
substitute under ``src/dashboard/src/**/__tests__/*.test.tsx``, checked with
the same two-way rigor as a pytest node -- EXISTENCE (source-text regex over
``it(``/``test(``/``describe(`` call sites, no subprocess) and EXECUTION
(a real ``npm --prefix <dashboard> test`` run via ``run_fork_safe``, JSON
reporter parsed for passed/failed/skipped). Vitest test titles are free-form
English sentences -- commas, conjunctions, punctuation -- unlike pytest's
identifier-shaped node names, so they cannot be delimited by a bare
``\\w+`` boundary the way ``NODE_REF_RE`` delimits a pytest test name. This module
therefore requires the title segment of a vitest citation to be wrapped in
double quotes, giving an unambiguous end-of-reference delimiter regardless
of surrounding prose, e.g.::

    DEFERRED — covered by src/dashboard/src/pages/__tests__/foo.test.tsx::"renders the error banner"

A deferral annotation may cite pytest refs, vitest refs, or both, without
the caller special-casing either kind -- ``iter_deferred_covered`` extracts
both via ``NODE_REF_RE`` and ``VITEST_REF_RE`` and yields them in one list.
The vitest execution leg requires the dashboard's Node toolchain
(``npm`` on PATH and ``src/dashboard/node_modules`` installed); when either
is absent -- as in the ``Linux Full Suite`` CI job, which does not set up
Node -- the slow vitest tests skip with an explicit, honest reason
(``VITEST_SKIP_REASON``) rather than faking a pass.

Non-vacuity: at the time this module was written, zero deferrals exist in
the document yet (Phase 168 plans 03-08 populate them; plan 09 re-runs this
guard against the fully dispositioned document). Every document-driven test
below therefore currently passes over zero real cases -- that is expected
and is explicitly NOT sufficient proof the guard works. The negative-control
and non-vacuity-demonstration tests exercise every helper against synthetic
input (fabricated node references, bare requirement IDs, ledger/document
mismatches, and real scratch pytest files that deliberately fail or skip)
to prove each helper flags exactly what it claims to flag.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

from tests.cli_helpers import run_fork_safe

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
UAT_SERIES_PATH = REPO_ROOT / "docs" / "UAT-SERIES.md"
LEDGER_PATH = REPO_ROOT / "docs" / "uat-disposition-ledger.jsonl"
DASHBOARD_DIR = REPO_ROOT / "src" / "dashboard"

# ---------------------------------------------------------------------------
# Grammar (independently re-derived -- see module docstring on independence).
# This mirrors the frozen interface grammar from 168-01-PLAN.md / the Phase
# 167 canonical **Result:** line, not any imported constant.
# ---------------------------------------------------------------------------

CASE_ID_PATTERN = r"UAT-[A-Za-z0-9.]+(?:-[A-Za-z0-9.]+)*"
HEADING_RE = re.compile(r"^### *(" + CASE_ID_PATTERN + r")")

# Canonical **Result:** line, with named capture groups for each box state
# and its (optional) trailing annotation.
RESULT_RE = re.compile(
    r"^\*\*Result:\*\* "
    r"- \[(?P<pass_box>[ x])\] PASS(?: \((?P<pass_ann>[^)]*)\))?  "
    r"- \[(?P<fail_box>[ x])\] FAIL(?: \((?P<fail_ann>[^)]*)\))?  "
    r"- \[(?P<skip_box>[ x])\] SKIP(?: \((?P<skip_ann>[^)]*)\))?$"
)

# A real pytest node reference: <path ending .py>::<test name>, where the
# test-name segment may end in a single `*` glob.
NODE_REF_RE = re.compile(r"tests/[\w/]+\.py::[\w*]+(?:::[\w*]+)?")

# A vitest test reference under src/dashboard/src/**/__tests__/*.test.tsx.
# The title segment MUST be double-quoted -- see module docstring (D-05) for
# why: vitest titles are free-form prose, not `\w+`-shaped identifiers, so a
# quoted string is the only unambiguous end-of-reference delimiter.
VITEST_REF_RE = re.compile(r'src/dashboard/src/(?:[\w-]+/)*__tests__/[\w.-]+\.test\.tsx::"[^"]+"')

# A bare requirement-ID-shaped token (e.g. DISC-01, LAB-03, HWCOMPAT-02) --
# NEVER sufficient as a substitute (D-02).
REQ_ID_ONLY_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[0-9]+)+$")

# Both em-dash and plain-hyphen spellings are accepted document text, per
# scripts/uat_disposition_apply.py's own evidence validator.
DEFERRED_COVERED_PREFIXES = ("DEFERRED — covered by ", "DEFERRED - covered by ")

NODE_ID_LINE_RE = re.compile(r"^tests/[\w/.-]+\.py::\S+$")


def _read_lines(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as f:
        return f.readlines()


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def iter_results(lines):
    """Yield (1-based lineno, case_id, groupdict) for every **Result:** line.

    ``case_id`` is the ID of the most recently seen ``### UAT-`` heading
    (None if a Result line somehow precedes any heading -- should not
    happen in a well-formed document, but the caller can detect it)."""
    current_id = None
    for i, line in enumerate(lines, start=1):
        hm = HEADING_RE.match(line)
        if hm:
            current_id = hm.group(1)
            continue
        rm = RESULT_RE.match(line.rstrip("\n"))
        if rm:
            yield i, current_id, rm.groupdict()


def iter_deferred_covered(lines):
    """Yield (lineno, case_id, annotation, refs) for every SKIP-checked
    Result line whose annotation is a 'DEFERRED — covered by ...' deferral.
    ``refs`` is the list of node references extracted via NODE_REF_RE
    (pytest) AND VITEST_REF_RE (D-05, vitest) combined -- a deferral may
    cite either kind, or both, without special-casing the caller. May be
    empty, e.g. for a bare-requirement-ID substitute -- that emptiness is
    exactly what find_deferrals_without_node_ref() below flags.

    'DEFERRED — no substitute coverage' annotations (D-06, legal) are
    deliberately NOT yielded here -- they carry no node reference by design
    and are exempt from existence/execution checks."""
    for lineno, case_id, groups in iter_results(lines):
        if groups["skip_box"] != "x":
            continue
        ann = groups["skip_ann"]
        if not ann:
            continue
        for prefix in DEFERRED_COVERED_PREFIXES:
            if ann.startswith(prefix):
                refs = NODE_REF_RE.findall(ann) + VITEST_REF_RE.findall(ann)
                yield lineno, case_id, ann, refs
                break


def find_deferrals_without_node_ref(lines):
    """Return [(lineno, case_id, annotation)] for every 'covered by'
    deferral that names zero real node references -- catches bare
    requirement-ID substitutes and any other malformed evidence."""
    return [
        (lineno, case_id, ann)
        for lineno, case_id, ann, refs in iter_deferred_covered(lines)
        if not refs
    ]


def find_unresolvable_node_refs(lines, node_id_set):
    """Return [(lineno, case_id, ref)] for every PYTEST node reference that
    fails to resolve (via fnmatch, so a `*` glob matching zero nodes counts
    as unresolvable) against ``node_id_set``. Vitest refs (D-05) are
    deliberately skipped here -- they are not pytest-node-shaped and are
    checked separately by find_unresolvable_vitest_refs()."""
    bad = []
    for lineno, case_id, _ann, refs in iter_deferred_covered(lines):
        for ref in refs:
            if not NODE_REF_RE.fullmatch(ref):
                continue
            if not fnmatch.filter(node_id_set, ref):
                bad.append((lineno, case_id, ref))
    return bad


def parse_vitest_ref(ref: str) -> tuple[str, str]:
    """Split a VITEST_REF_RE match into (file_path, test_name).
    ``file_path`` is repo-root-relative (e.g.
    'src/dashboard/src/pages/__tests__/foo.test.tsx'); ``test_name`` has its
    wrapping double quotes stripped."""
    file_part, _, quoted = ref.partition("::")
    return file_part, quoted[1:-1]


def _vitest_title_pattern(name: str) -> re.Pattern:
    """A regex matching an it()/test()/describe() call (including
    `.skip`/`.only`/`.todo`/`.each` chained variants) whose first argument
    is the literal string ``name``, quoted with a matching quote char."""
    return re.compile(r"(?:it|test|describe)(?:\.\w+)*\s*\(\s*(['\"`])" + re.escape(name) + r"\1")


def find_unresolvable_vitest_refs(lines):
    """Return [(lineno, case_id, ref)] for every vitest reference (D-05)
    whose file does not exist under the repo, or whose quoted test name does
    not appear as an it()/test()/describe() call argument in that file's
    source. A pure source-text check -- deliberately does NOT shell out to
    Node for existence (that is reserved for the execution leg,
    _run_vitest_nodes, which actually proves the test PASSES rather than
    merely exists)."""
    bad = []
    for lineno, case_id, _ann, refs in iter_deferred_covered(lines):
        for ref in refs:
            if not VITEST_REF_RE.fullmatch(ref):
                continue
            file_part, name = parse_vitest_ref(ref)
            path = REPO_ROOT / file_part
            if not path.is_file():
                bad.append((lineno, case_id, ref))
                continue
            src = path.read_text(encoding="utf-8")
            if not _vitest_title_pattern(name).search(src):
                bad.append((lineno, case_id, ref))
    return bad


def find_ledger_document_mismatches(ledger_rows, lines):
    """Return [str] describing every disagreement between a ledger row and
    the document's Result line for the same case ID, checked in both
    directions:

      - ledger outcome non-null -> document must show exactly the expected
        box checked, with the annotation matching the ledger evidence.
      - ledger outcome null -> document must show NO box checked (catches a
        hand-edit that dispositions the document while bypassing the
        ledger)."""
    results_by_id: dict[str, tuple[int, dict]] = {}
    for lineno, case_id, groups in iter_results(lines):
        if case_id is not None:
            results_by_id[case_id] = (lineno, groups)

    mismatches: list[str] = []
    for row in ledger_rows:
        case_id = row["id"]
        outcome = row.get("outcome")
        evidence = row.get("evidence") or ""
        entry = results_by_id.get(case_id)
        if entry is None:
            mismatches.append(f"{case_id}: no **Result:** line found for this ledger id")
            continue
        lineno, groups = entry
        checked = [label for label in ("pass", "fail", "skip") if groups[f"{label}_box"] == "x"]

        if outcome is None:
            if checked:
                mismatches.append(
                    f"{case_id}: ledger outcome is null but document line {lineno} "
                    f"has box(es) checked: {checked}"
                )
            continue

        if outcome in ("PASS", "FAIL", "SKIP"):
            expected_box = outcome.lower()
        elif outcome in ("DEFERRED", "GAP"):
            expected_box = "skip"
        else:
            mismatches.append(f"{case_id}: unknown ledger outcome {outcome!r}")
            continue

        if checked != [expected_box]:
            mismatches.append(
                f"{case_id}: expected only {expected_box!r} box checked, "
                f"found {checked} at line {lineno}"
            )
            continue

        ann = groups[f"{expected_box}_ann"] or ""
        if outcome is not None and not evidence:
            mismatches.append(f"{case_id}: ledger outcome is {outcome!r} but evidence is empty")
        elif ann != evidence:
            mismatches.append(
                f"{case_id}: ledger evidence {evidence!r} != document annotation "
                f"{ann!r} at line {lineno}"
            )
    return mismatches


def parse_ledger_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


SUMMARY_COUNT_PATTERNS = {
    "passed": re.compile(r"(\d+) passed"),
    "failed": re.compile(r"(\d+) failed"),
    "errors": re.compile(r"(\d+) error"),
    "skipped": re.compile(r"(\d+) skipped"),
}


def parse_pytest_summary(output: str) -> dict:
    """Parse pytest's -q terminal summary line into counts. Does NOT trust
    the return code -- a run containing only passes and skips exits 0, so
    callers must inspect these counts (especially ``skipped``) directly."""
    return {key: int(m.group(1)) if (m := pat.search(output)) else 0 for key, pat in SUMMARY_COUNT_PATTERNS.items()}


def _skipped_report_lines(output: str) -> list[str]:
    """Lines from a `-rA`/`-rs` pytest run naming each skipped node and its
    reason, e.g. 'SKIPPED [1] tests/test_x.py:12: reason text'."""
    return [line for line in output.splitlines() if line.startswith("SKIPPED ")]


def _absolutize_node_id(node_id: str) -> str:
    """Make the file-path portion of a pytest node ID absolute (relative to
    REPO_ROOT), leaving an already-absolute path (e.g. a tmp_path scratch
    file) untouched. ``run_fork_safe`` forbids a ``cwd`` kwarg (Phase 166
    fork-safety fix, tests/cli_helpers.py), so every path-like argv element
    must already be absolute before it reaches the child process."""
    path_part, sep, rest = node_id.partition("::")
    path = Path(path_part)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return f"{path}{sep}{rest}"


def _run_pytest_nodes(node_ids) -> tuple[int, str]:
    """Run the given node IDs in ONE subprocess. Returns (returncode,
    combined stdout+stderr). Empty input is a no-op (rc=0, no output).

    Uses ``run_fork_safe`` (Phase 166 GATE-03), not a raw ``subprocess.run``
    with ``cwd=`` -- that combination is the exact macOS fork()-after-
    Network.framework SIGSEGV documented in
    ``.planning/phases/164-first-run-correctness/164-FINDING-fork-crash.md``,
    reproduced by this module in a full unfiltered suite run (168-09)."""
    node_ids = sorted(node_ids)
    if not node_ids:
        return 0, ""
    abs_node_ids = [_absolutize_node_id(n) for n in node_ids]
    proc = run_fork_safe(
        [sys.executable, "-m", "pytest", "-q", "-rA", *abs_node_ids],
        timeout=180,
    )
    return proc.returncode, proc.stdout + "\n" + proc.stderr


# ---------------------------------------------------------------------------
# D-05: vitest execution dispatcher + JSON-reporter summary parser.
#
# The dashboard's Node toolchain is NOT guaranteed to be present -- the
# `Linux Full Suite` CI job (.github/workflows/python-ci.yml) that runs
# `pytest -q -m ""` never installs it. VITEST_TOOLCHAIN_AVAILABLE gates the
# slow vitest tests below with an honest skip (VITEST_SKIP_REASON) rather
# than faking a pass when npm or src/dashboard/node_modules is absent.
# ---------------------------------------------------------------------------

DASHBOARD_NODE_MODULES = DASHBOARD_DIR / "node_modules"
NPM_PATH = shutil.which("npm")
VITEST_TOOLCHAIN_AVAILABLE = NPM_PATH is not None and DASHBOARD_NODE_MODULES.is_dir()
VITEST_SKIP_REASON = (
    "vitest toolchain unavailable in this environment (npm on PATH: "
    f"{NPM_PATH is not None}, src/dashboard/node_modules present: "
    f"{DASHBOARD_NODE_MODULES.is_dir()}) -- the Linux Full Suite CI job does "
    "not install the dashboard's Node toolchain, so this leg is honestly "
    "skipped there rather than faked. Run `npm ci` in src/dashboard/ to "
    "exercise it locally."
)

_JS_REGEX_SPECIAL_RE = re.compile(r"[.*+?^${}()|[\]\\]")


def _js_regex_escape(name: str) -> str:
    """Escape JS regex metacharacters in ``name`` for safe use as a vitest
    `-t`/testNamePattern argument (vitest's `-t` is a regex, not a literal
    substring match)."""
    return _JS_REGEX_SPECIAL_RE.sub(lambda m: "\\" + m.group(0), name)


def _dashboard_relative_path(repo_relative_file: str) -> str:
    """Convert a repo-root-relative vitest ref file path (e.g.
    'src/dashboard/src/pages/__tests__/foo.test.tsx') into a path relative
    to DASHBOARD_DIR, as required by the `npm --prefix <dashboard> test --
    <file>` invocation."""
    return str(Path(repo_relative_file).relative_to("src/dashboard"))


def parse_vitest_summary(data: dict) -> dict:
    """Parse a vitest `--reporter=json` report into counts. Does NOT trust
    the process return code -- mirrors parse_pytest_summary's rationale.
    ``skipped`` folds in vitest's numPendingTests, which covers both
    `.skip` and `.todo` -- neither is proof of coverage."""
    if not data:
        return {"passed": 0, "failed": 0, "skipped": 0, "total": 0}
    return {
        "passed": data.get("numPassedTests", 0),
        "failed": data.get("numFailedTests", 0),
        "skipped": data.get("numPendingTests", 0),
        "total": data.get("numTotalTests", 0),
    }


def _vitest_assertion_lines(data: dict) -> list[str]:
    """Non-passed assertion result lines, for failure-message context."""
    lines = []
    for tr in data.get("testResults", []):
        for a in tr.get("assertionResults", []):
            if a.get("status") != "passed":
                lines.append(f"{a.get('status')}: {a.get('fullName')}")
    return lines


def _run_vitest_nodes(
    file_and_names: list[tuple[str, str]], *, root: Path | None = None, timeout: int = 180
) -> tuple[dict, str]:
    """Run the given (dashboard-relative-file, test-name) pairs in ONE
    subprocess via `npm --prefix <dashboard> test -- <files> -t <pattern>
    --reporter=json --outputFile=<tmp>`. Returns (summary_dict,
    combined_output_for_debugging). Empty input is a no-op.

    Never passes a `cwd` kwarg to run_fork_safe (Phase 166 GATE-03,
    identical constraint to _run_pytest_nodes) -- `root` (when given, for a
    synthetic scratch tree under a caller's tmp_path) is threaded through
    vitest's own `--root` flag instead of a subprocess working-directory
    change; the real-document call path passes root=None and relies on
    `npm --prefix` to locate the dashboard package without a cwd change
    either.
    """
    if not file_and_names:
        return {"passed": 0, "failed": 0, "skipped": 0, "total": 0}, ""
    assert NPM_PATH, (
        "npm not found on PATH -- cannot run the vitest execution leg. "
        "Callers must check VITEST_TOOLCHAIN_AVAILABLE and skip honestly "
        "instead of calling this helper when npm is absent."
    )
    files = sorted({f for f, _ in file_and_names})
    pattern = "|".join(_js_regex_escape(n) for _, n in file_and_names)

    fd, tmp_name = tempfile.mkstemp(suffix=".json", prefix="vitest_report_")
    os.close(fd)
    out_path = Path(tmp_name)
    try:
        argv = [NPM_PATH, "--prefix", str(DASHBOARD_DIR), "test", "--"]
        if root is not None:
            argv += ["--root", str(root)]
        argv += [*files, "-t", pattern, "--reporter=json", f"--outputFile={out_path}"]
        proc = run_fork_safe(argv, timeout=timeout)
        data = {}
        if out_path.exists() and out_path.stat().st_size:
            data = json.loads(out_path.read_text(encoding="utf-8"))
        summary = parse_vitest_summary(data)
        combined = proc.stdout + "\n" + proc.stderr
        assertion_lines = _vitest_assertion_lines(data)
        if assertion_lines:
            combined += "\n" + "\n".join(assertion_lines)
        return summary, combined
    finally:
        out_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def uat_series_lines() -> list[str]:
    assert UAT_SERIES_PATH.is_file(), f"UAT-SERIES.md not found at {UAT_SERIES_PATH}"
    return _read_lines(UAT_SERIES_PATH)


@pytest.fixture(scope="session")
def ledger_rows() -> list[dict]:
    assert LEDGER_PATH.is_file(), f"ledger not found at {LEDGER_PATH}"
    return parse_ledger_rows(LEDGER_PATH)


@pytest.fixture(scope="session")
def collected_node_ids() -> set[str]:
    """The real collect-only node ID set, collected exactly once per test
    session (collection over ~3700 nodes costs a few seconds; re-collecting
    per test would be wasteful and is explicitly disallowed by the plan)."""
    proc = run_fork_safe(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", str(REPO_ROOT / "tests")],
        timeout=180,
    )
    if proc.returncode != 0:
        pytest.fail(
            "pytest --collect-only failed (rc="
            f"{proc.returncode}) -- refusing to treat this as an empty node "
            f"set (that would make every existence assertion vacuously "
            f"fail in a confusing way).\nSTDOUT (tail):\n{proc.stdout[-3000:]}\n"
            f"STDERR (tail):\n{proc.stderr[-3000:]}"
        )
    node_ids = {line.strip() for line in proc.stdout.splitlines() if NODE_ID_LINE_RE.match(line.strip())}
    assert node_ids, "collect-only produced zero node ids -- collection is broken, not empty"
    return node_ids


# ---------------------------------------------------------------------------
# Task 1: document-driven checks (existence, ledger agreement)
#
# NOTE: at the time this module was written, zero deferrals exist in
# docs/UAT-SERIES.md yet (plans 03-08 populate them). The two
# `test_deferrals_*` / `test_substitute_nodes_resolve` assertions therefore
# currently iterate zero cases -- vacuously true today. `test_ledger_matches_document`
# is NOT vacuous today: it actively asserts all 299 ledger rows (outcome:
# null) correspond to document lines with NO box checked, which a stray
# hand-edit to the document would immediately violate.
# ---------------------------------------------------------------------------


def test_deferrals_name_a_real_node_reference(uat_series_lines):
    bad = find_deferrals_without_node_ref(uat_series_lines)
    assert bad == [], (
        f"{len(bad)} 'DEFERRED — covered by' annotation(s) name no resolvable "
        f"node reference (e.g. a bare requirement ID) -- vacuous over zero "
        f"real cases today, see module docstring: {bad}"
    )


def test_substitute_nodes_resolve(uat_series_lines, collected_node_ids):
    bad = find_unresolvable_node_refs(uat_series_lines, collected_node_ids)
    assert bad == [], f"{len(bad)} substitute node reference(s) do not resolve: {bad}"


def test_vitest_substitute_refs_resolve(uat_series_lines):
    """D-05 fast leg: every vitest reference in the document must resolve
    (file exists, quoted title found in source) -- no subprocess needed.
    Vacuous today (zero vitest citations exist until 169-06 spends this
    capability); see module docstring on non-vacuity."""
    bad = find_unresolvable_vitest_refs(uat_series_lines)
    assert bad == [], f"{len(bad)} vitest substitute reference(s) do not resolve: {bad}"


def test_ledger_matches_document(uat_series_lines, ledger_rows):
    mismatches = find_ledger_document_mismatches(ledger_rows, uat_series_lines)
    assert mismatches == [], (
        f"{len(mismatches)} ledger/document mismatch(es):\n" + "\n".join(mismatches)
    )


# ---------------------------------------------------------------------------
# Task 1: negative controls on synthetic input -- prove the helpers actually
# detect what they claim to, independent of the real document's current
# (empty) state.
# ---------------------------------------------------------------------------


def test_negative_control_bare_requirement_id_is_rejected():
    synthetic = [
        "### UAT-1-01: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (DEFERRED — covered by DISC-01)\n",
    ]
    bad = find_deferrals_without_node_ref(synthetic)
    assert bad == [(2, "UAT-1-01", "DEFERRED — covered by DISC-01")]
    # Sanity: the bare token really is requirement-ID-shaped, confirming
    # this is testing the intended failure mode, not an unrelated typo.
    assert REQ_ID_ONLY_RE.match("DISC-01")


def test_negative_control_fabricated_node_reference_is_rejected():
    synthetic = [
        "### UAT-2-01: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        "(DEFERRED — covered by tests/test_does_not_exist.py::test_nope)\n",
    ]
    bad = find_unresolvable_node_refs(synthetic, node_id_set=set())
    assert bad == [(2, "UAT-2-01", "tests/test_does_not_exist.py::test_nope")]


def test_negative_control_glob_matching_zero_nodes_is_rejected():
    synthetic = [
        "### UAT-6-01: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        "(DEFERRED — covered by tests/test_real.py::test_ok_*)\n",
    ]
    # Glob resolves against nothing -> rejected.
    assert find_unresolvable_node_refs(synthetic, node_id_set=set()) == [
        (2, "UAT-6-01", "tests/test_real.py::test_ok_*")
    ]
    # Same glob resolves against a matching node -> accepted.
    assert find_unresolvable_node_refs(
        synthetic, node_id_set={"tests/test_real.py::test_ok_one"}
    ) == []


def test_negative_control_well_formed_deferral_is_accepted():
    synthetic = [
        "### UAT-4-01: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        "(DEFERRED — covered by tests/test_real.py::test_ok)\n",
    ]
    assert find_deferrals_without_node_ref(synthetic) == []
    assert find_unresolvable_node_refs(synthetic, {"tests/test_real.py::test_ok"}) == []


def test_negative_control_no_substitute_coverage_is_exempt_not_flagged():
    """D-06: a 'no substitute coverage' deferral is a LEGAL, node-ref-free
    annotation and must not be treated as a fabrication."""
    synthetic = [
        "### UAT-7-01: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        "(DEFERRED — no substitute coverage; needs a broker-scanner unit test)\n",
    ]
    assert list(iter_deferred_covered(synthetic)) == []
    assert find_deferrals_without_node_ref(synthetic) == []


def test_negative_control_ledger_document_mismatch_detected():
    ledger_rows = [{"id": "UAT-3-01", "outcome": "PASS", "evidence": ""}]
    lines = [
        "### UAT-3-01: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP\n",
    ]
    mismatches = find_ledger_document_mismatches(ledger_rows, lines)
    assert len(mismatches) == 1
    assert "UAT-3-01" in mismatches[0]


def test_negative_control_null_ledger_but_dispositioned_document_detected():
    ledger_rows = [{"id": "UAT-5-01", "outcome": None, "evidence": ""}]
    lines = [
        "### UAT-5-01: Example\n",
        "**Result:** - [x] PASS  - [ ] FAIL  - [ ] SKIP\n",
    ]
    mismatches = find_ledger_document_mismatches(ledger_rows, lines)
    assert len(mismatches) == 1
    assert "UAT-5-01" in mismatches[0]


def test_negative_control_wr03_empty_evidence_nonnull_outcome_detected():
    """WR-03 (168-REVIEW.md): a ledger row with a non-null outcome and empty
    evidence must be flagged even when the document's annotation is
    non-empty garbage text. Before the fix, `if evidence and ann !=
    evidence` short-circuited to False whenever `evidence` was falsy,
    silently passing a malformed evidence-less non-null disposition. This
    test fails against the pre-fix predicate and passes against the fixed
    one."""
    ledger_rows = [{"id": "UAT-9-01", "outcome": "DEFERRED", "evidence": ""}]
    lines = [
        "### UAT-9-01: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (unrelated garbage annotation)\n",
    ]
    mismatches = find_ledger_document_mismatches(ledger_rows, lines)
    assert len(mismatches) == 1
    assert "UAT-9-01" in mismatches[0]
    assert "evidence is empty" in mismatches[0]


def test_negative_control_wr03_matching_evidence_still_passes():
    """WR-03 fix must not introduce a false positive: a non-null outcome
    whose evidence matches the document annotation exactly must still
    pass with zero mismatches."""
    ledger_rows = [
        {
            "id": "UAT-9-02",
            "outcome": "DEFERRED",
            "evidence": "DEFERRED — covered by tests/test_foo.py::test_bar",
        }
    ]
    lines = [
        "### UAT-9-02: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        "(DEFERRED — covered by tests/test_foo.py::test_bar)\n",
    ]
    mismatches = find_ledger_document_mismatches(ledger_rows, lines)
    assert mismatches == []


def test_negative_control_vitest_fabricated_file_is_rejected():
    synthetic = [
        "### UAT-10-01: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        '(DEFERRED — covered by src/dashboard/src/pages/__tests__/does_not_exist.test.tsx::"some test")\n',
    ]
    bad = find_unresolvable_vitest_refs(synthetic)
    assert len(bad) == 1
    assert bad[0][1] == "UAT-10-01"


def test_negative_control_vitest_fabricated_title_in_real_file_is_rejected():
    synthetic = [
        "### UAT-10-02: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        '(DEFERRED — covered by src/dashboard/src/context/__tests__/AuthProvider.test.tsx::'
        '"this title does not exist anywhere")\n',
    ]
    bad = find_unresolvable_vitest_refs(synthetic)
    assert len(bad) == 1
    assert bad[0][1] == "UAT-10-02"


def test_negative_control_vitest_well_formed_reference_is_accepted():
    synthetic = [
        "### UAT-10-03: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        '(DEFERRED — covered by src/dashboard/src/context/__tests__/AuthProvider.test.tsx::'
        '"setToken writes to sessionStorage, NOT localStorage")\n',
    ]
    assert find_unresolvable_vitest_refs(synthetic) == []
    assert find_deferrals_without_node_ref(synthetic) == []


def test_negative_control_mixed_pytest_and_vitest_refs_in_one_annotation():
    """D-05: a single deferral annotation may cite a pytest ref and a vitest
    ref together -- iter_deferred_covered must yield both without the
    caller special-casing either kind."""
    synthetic = [
        "### UAT-10-04: Example\n",
        "**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP "
        "(DEFERRED — covered by tests/test_real.py::test_ok and "
        'src/dashboard/src/context/__tests__/AuthProvider.test.tsx::'
        '"setToken writes to sessionStorage, NOT localStorage")\n',
    ]
    _lineno, _case_id, _ann, refs = next(iter(iter_deferred_covered(synthetic)))
    assert refs == [
        "tests/test_real.py::test_ok",
        'src/dashboard/src/context/__tests__/AuthProvider.test.tsx::'
        '"setToken writes to sessionStorage, NOT localStorage"',
    ]
    assert find_unresolvable_node_refs(synthetic, {"tests/test_real.py::test_ok"}) == []
    assert find_unresolvable_vitest_refs(synthetic) == []


# ---------------------------------------------------------------------------
# Task 2: execution check + non-vacuity proof
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_substitute_nodes_pass(uat_series_lines, collected_node_ids):
    """Deselected by default (addopts = -m 'not slow'); run explicitly with
    `-m slow`. Runs the deduplicated union of every named substitute node in
    ONE subprocess and asserts a clean pass -- failed==0, errors==0,
    skipped==0 (a skip is never proof of coverage), passed>=1. With zero
    deferrals present (today) it passes trivially without invoking pytest."""
    node_refs = sorted(
        {ref for _, _, _, refs in iter_deferred_covered(uat_series_lines) for ref in refs}
    )
    if not node_refs:
        return  # nothing to execute yet -- see module docstring

    expanded: set[str] = set()
    for ref in node_refs:
        expanded.update(fnmatch.filter(collected_node_ids, ref))
    assert expanded, f"no nodes expanded from refs {node_refs}"

    _rc, output = _run_pytest_nodes(expanded)
    summary = parse_pytest_summary(output)
    tail = output[-4000:]
    skipped_lines = _skipped_report_lines(output)

    assert summary["failed"] == 0, f"substitute node(s) failed:\n{tail}"
    assert summary["errors"] == 0, f"substitute node(s) errored:\n{tail}"
    assert summary["skipped"] == 0, (
        "substitute node(s) skipped -- a skip is NOT proof of coverage; pick "
        "a different substitute or record 'DEFERRED — no substitute "
        f"coverage' instead:\n" + "\n".join(skipped_lines) + f"\n{tail}"
    )
    assert summary["passed"] >= 1, f"substitute run collected nothing:\n{tail}"


def test_non_vacuity_demonstration_existence_vs_execution(tmp_path):
    """The flagship non-vacuity proof (168-02-PLAN.md Task 2): construct a
    synthetic scratch test file representing a substitute node that EXISTS
    but is deliberately made to FAIL, and a second node reference that does
    not exist at all. Demonstrate:

      1. the existence check (find_unresolvable_node_refs) flags the
         nonexistent node but NOT the existing-but-failing one (existence
         alone cannot see failure -- this is exactly why a second,
         execution-based check is required); and
      2. the execution check (parse_pytest_summary on a real subprocess
         run) flags the existing-but-failing node.

    Together these prove neither check alone is sufficient and both are
    necessary -- the core claim of the fabrication_hardening block."""
    scratch = tmp_path / "test_scratch_fail.py"
    scratch.write_text(
        "def test_deliberately_fails():\n"
        "    assert False, 'synthetic failure for non-vacuity proof'\n"
    )
    existing_but_failing = f"{scratch}::test_deliberately_fails"
    nonexistent = "tests/test_does_not_exist_synthetic_168_02.py::test_nope"

    synthetic_node_id_set = {existing_but_failing}  # the failing node DOES exist/collect

    synthetic_doc = [
        "### UAT-8-01: Existing but failing\n",
        f"**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (DEFERRED — covered by {existing_but_failing})\n",
        "### UAT-8-02: Nonexistent\n",
        f"**Result:** - [ ] PASS  - [ ] FAIL  - [x] SKIP (DEFERRED — covered by {nonexistent})\n",
    ]

    existence_violations = find_unresolvable_node_refs(synthetic_doc, synthetic_node_id_set)
    # Existence check: only the nonexistent node is flagged. The
    # existing-but-failing node resolves fine -- existence alone is blind
    # to it, which is exactly the gap the execution check closes.
    assert existence_violations == [(4, "UAT-8-02", nonexistent)]

    rc, output = _run_pytest_nodes({existing_but_failing})
    summary = parse_pytest_summary(output)
    # Execution check: the existing-but-resolvable node is caught here.
    assert summary["failed"] == 1, (
        "expected the deliberately-failing synthetic node to be caught by "
        f"the execution check (rc={rc}):\n{output[-2000:]}"
    )


def test_non_vacuity_skipped_substitute_is_flagged(tmp_path):
    """Constraint 5 scenario: 'a deferral naming a node that exists but is
    skipped.' Proves a @pytest.mark.skip substitute is NOT accepted as
    coverage -- the exact hole an exit-code-only check would miss."""
    scratch = tmp_path / "test_scratch_skip.py"
    scratch.write_text(
        "import pytest\n\n"
        "@pytest.mark.skip(reason='synthetic skip for non-vacuity proof')\n"
        "def test_deliberately_skipped():\n"
        "    assert True\n"
    )
    node = f"{scratch}::test_deliberately_skipped"
    rc, output = _run_pytest_nodes({node})
    summary = parse_pytest_summary(output)
    assert rc == 0, "a skip-only run is expected to exit 0 -- proving exit code alone is insufficient"
    assert summary["skipped"] == 1, f"expected the synthetic skip to be detected:\n{output[-2000:]}"
    skipped_lines = _skipped_report_lines(output)
    assert skipped_lines, "expected a SKIPPED report line naming the node and its reason"
    # pytest's -rA "SKIPPED [1] <path>:<line>: <reason>" line names the file
    # and reason, not the bare test name -- assert on what it actually emits.
    assert "test_scratch_skip.py" in skipped_lines[0]
    assert "synthetic skip for non-vacuity proof" in skipped_lines[0]


def test_non_vacuity_passing_substitute_is_not_flagged():
    """Constraint 5 scenario: 'a well-formed deferral naming a real passing
    node.' Positive control -- proves the execution check does NOT
    false-positive on a genuinely healthy substitute."""
    node = "tests/test_uat_series_format.py::test_negative_control_canonical_line_passes"
    _rc, output = _run_pytest_nodes({node})
    summary = parse_pytest_summary(output)
    assert summary["failed"] == 0
    assert summary["errors"] == 0
    assert summary["skipped"] == 0
    assert summary["passed"] == 1
