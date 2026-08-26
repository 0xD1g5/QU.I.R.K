"""Phase 164 FIRSTRUN-03 / D-15: repo-wide doc-form gate.

This test converts UAT-161-07's manual `grep` step into a CI gate. The manual
form is precisely why four `labs/` copies of the nonexistent `quirk scan
--target ...` invocation survived that prior sweep — nobody re-ran the grep.
This module walks every git-tracked file, so a future reintroduction of a
nonexistent `quirk` invocation fails the build instead of waiting for the
next human-driven sweep.

No existing test in this repo walks the full set of git-tracked files
(`grep -rn "git ls-files" tests/ quirk/` returns zero matches at authoring
time). This module is a synthesis of two existing conventions rather than a
direct copy of either:
  - tests/test_hygiene.py's "collect all violations into a list, fail once
    with the whole list" shape.
  - tests/test_skip_registry.py's "allowlist as a visible in-file module-
    level constant" convention (EXEMPT_FILES / ALLOWED_* naming mirrors it).
The file-source mechanism (`git ls-files -z`, not `rglob`) has no in-repo
precedent — it is required because the sweep must reach every tracked file
regardless of extension (.md, .tsx, .js, .sh, extensionless files like
lab.sh), not just `.py` files under one directory.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Forbidden-form matcher (D-15, widened per Phase 164 planning-time discovery).
#
# The terminator alternation below MUST include a backtick and end-of-line,
# not just a space. A space-only matcher is the exact blind spot that hid
# docs/UAT-SERIES.md:13052 (`` `quirk scan` ``, backtick-terminated) from the
# first sweep of this very phase -- and it is the same class of hole as the
# manual UAT-161-07 grep that let four labs/ files survive undetected. A
# gate built to replace a leaky grep must not inherit its leak.
#
# The terminator MUST be required, never optional: without it,
# "quirk --targets-file" would match on the "--targets" prefix alone and the
# legitimate canonical invocation would be flagged repo-wide.
FORBIDDEN_RE = re.compile(r"quirk (scan|--targets)( |`|$)")

# Path prefixes whose historical text must stay verbatim. Each entry quotes
# the defect deliberately as a historical record, not a live instruction.
ALLOWED_PREFIXES: tuple[str, ...] = (
    # Historical release-notes prose; the whole directory records past fixes.
    "docs/release-notes/",
    # Source-review evidence and its action plan quote the defect verbatim.
    "docs/reviews/",
    # Review-evidence scripts and historical BACK-* backlog records.
    "docs/superpowers/",
    # Archived milestone/planning records (HORIZON.md, MILESTONES.md,
    # PROJECT.md, REQUIREMENTS.md, and archived .planning/milestones/*
    # summaries including the v5.12-phases/149-test-suite-triage/ set) that
    # quote the defect deliberately as history, per D-14's
    # ".planning/milestones/" exclusion generalised to all of ".planning/".
    ".planning/",
    # Superseded oracle; its own header declares it retained for historical
    # reference only.
    "quantum-chaos-enterprise-lab/expected_results_v3.md",
)

# Files exempt from the walk entirely: the gate necessarily contains its own
# needles (in FORBIDDEN_RE's pattern text and in this module's docstring/
# test bodies), so it must not scan itself.
EXEMPT_FILES = {"test_doc_command_forms.py"}

# Individual historical lines inside otherwise-swept files, keyed on exact
# stripped line TEXT (not line number -- line numbers in docs/UAT-SERIES.md
# shift every time a new UAT series is appended).
ALLOWED_LINES: tuple[tuple[str, str], ...] = (
    # UAT-161-07 recorded PASS (2026-08-25); D-16 forbids re-litigating or
    # editing an already-recorded-PASS case. These three lines document the
    # historical defect and its fix as part of that case's own evidence.
    (
        "docs/UAT-SERIES.md",
        '1. `grep -rn "quirk scan " docs/*.md src/dashboard/src` — expect no hits outside',
    ),
    (
        "docs/UAT-SERIES.md",
        "Note the review's traceback claim applies to `quirk --targets X` (argparse prefix-matches",
    ),
    (
        "docs/UAT-SERIES.md",
        "`--targets-file`), not to `quirk scan --targets X`, which fails cleanly with",
    ),
    # CHANGELOG.md historical release prose recording a PAST fix, not a live
    # instruction. Allowlisted by line (not by adding CHANGELOG.md to
    # ALLOWED_PREFIXES) so the rest of the changelog stays swept and future
    # release prose cannot smuggle in a live bad form.
    (
        "CHANGELOG.md",
        "- Five legacy `quirk scan` CLI references in `docs/UAT-SERIES.md` (lines 1526, 3866, 4772,",
    ),
)


def _is_allowed_prefix(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def _is_exempt_file(path: str) -> bool:
    return Path(path).name in EXEMPT_FILES


def _is_allowed_line(path: str, line_text: str) -> bool:
    return (path, line_text) in ALLOWED_LINES


def test_no_nonexistent_command_forms() -> None:
    """No unallowlisted tracked file instructs a nonexistent quirk invocation."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"git ls-files failed (rc={result.returncode}): {result.stderr!r}. "
        "This gate requires a git checkout to enumerate tracked files."
    )
    files = [p for p in result.stdout.split("\0") if p]
    assert files, (
        "git ls-files returned an empty file list — the sweep would pass "
        "vacuously. Refusing to report success on zero swept files."
    )

    violations: list[tuple[str, int, str, str]] = []

    for rel_path in files:
        if _is_allowed_prefix(rel_path) or _is_exempt_file(rel_path):
            continue

        abs_path = REPO_ROOT / rel_path
        try:
            text = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for lineno, line in enumerate(text.split("\n"), start=1):
            stripped = line.rstrip("\n")
            match = FORBIDDEN_RE.search(stripped)
            if not match:
                continue
            if _is_allowed_line(rel_path, stripped.strip()):
                continue
            violations.append((rel_path, lineno, match.group(0), stripped.strip()))

    if violations:
        formatted = "\n".join(
            f"  {path}:{lineno} [{needle}] {text}"
            for path, lineno, needle, text in violations
        )
        pytest.fail(
            "Found tracked file(s) instructing a nonexistent quirk invocation:\n"
            f"{formatted}\n\n"
            "Remediation: use `quirk --targets-file targets.txt` or "
            "`quirk --config <file>.yaml` instead. If the text is deliberate "
            "history, add its path prefix to ALLOWED_PREFIXES or the exact "
            "line to ALLOWED_LINES (with a reason) in "
            "tests/test_doc_command_forms.py."
        )


@pytest.mark.parametrize(
    "path",
    [
        "docs/release-notes/4.6.0.md",
        "docs/reviews/2026-08-24-functional-review-findings.md",
        "quantum-chaos-enterprise-lab/expected_results_v3.md",
    ],
)
def test_allowlisted_history_is_still_present(path: str) -> None:
    """The allowlist must be load-bearing, not decorative.

    If someone "helpfully" sanitises the historical record inside an
    allowlisted file, this test catches it — the allowlisted files must
    still genuinely contain the historical forbidden text they were
    allowlisted for.
    """
    abs_path = REPO_ROOT / path
    text = abs_path.read_text(encoding="utf-8", errors="replace")
    found = any(FORBIDDEN_RE.search(line) for line in text.split("\n"))
    assert found, (
        f"{path} no longer contains any forbidden-form text. It was "
        "allowlisted because it records history containing the defect — "
        "if the historical text was removed, remove the allowlist entry too."
    )


def test_matcher_detects_every_terminator_form() -> None:
    """Negative control: FORBIDDEN_RE must not be blind to any terminator.

    A space-only matcher would pass the backtick- and end-of-line-terminated
    cases below and is therefore forbidden. This is the exact defect class
    that hid docs/UAT-SERIES.md:13052 from the first sweep of this phase —
    a future editor who "simplifies" FORBIDDEN_RE back to space-suffixed
    substrings will get a failing test with this reason attached.
    """
    detected_cases = [
        "quirk scan --target localhost",  # space terminator (labs/ residue form)
        "5. `quirk scan` runs unchanged against an existing pre-v5.4 SQLite database",  # backtick terminator (UAT-SERIES.md:13052 form)
        "Run a scan first: quirk scan",  # end-of-line terminator
        "quirk --targets 127.0.0.1",  # space terminator, abbreviation form
        "the review's claim applies to `quirk --targets` here",  # backtick terminator
    ]
    for case in detected_cases:
        assert FORBIDDEN_RE.search(case), (
            f"FORBIDDEN_RE failed to detect a known-bad form: {case!r}"
        )

    not_detected_cases = [
        "quirk --targets-file targets.txt",  # canonical invocation — must NOT match
        "quirk --targets-file targets.txt --profile standard",
        "quirk --config config-lab-core.yaml",
        "quirk scanner",  # a word merely prefixed by "scan"
    ]
    for case in not_detected_cases:
        assert not FORBIDDEN_RE.search(case), (
            f"FORBIDDEN_RE over-matched a legitimate invocation: {case!r}"
        )


def test_findings_empty_state_command_is_real() -> None:
    """D-11: findings.tsx's locked empty-state command stays pinned against regression."""
    findings_tsx = REPO_ROOT / "src" / "dashboard" / "src" / "pages" / "findings.tsx"
    text = findings_tsx.read_text(encoding="utf-8")
    assert "quirk --targets-file targets.txt" in text, (
        "findings.tsx must instruct the real quirk --targets-file invocation"
    )
    assert "quirk scan" not in text, (
        "findings.tsx must not regress to the nonexistent quirk scan form"
    )
