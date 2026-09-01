"""Phase 176 docs presence gate: enforce docs/operators-guide.md §6.2's SSH
scanner subsection continues to document `ssh-audit` as an OPTIONAL
prerequisite (07-T3, LABRUN-01), so this prose cannot silently regress or be
deleted with zero test signal.

Pattern modelled on tests/test_phase136_docs_presence.py — read source file
from disk, substring-check the (lower-cased) contents. One additional test
cross-checks the TRIAGE-176-03 `host:port` single-positional claim against
the live `_run_ssh_audit` f-string in quirk/scanner/ssh_scanner.py to guard
against future doc/code drift.
"""
import os
import re

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

_OPS_GUIDE = "docs/operators-guide.md"
_SSH_SCANNER = "quirk/scanner/ssh_scanner.py"

# §6.2 SSH scanner: ssh-audit is an OPTIONAL prerequisite, resolved via
# shutil.which, with the install command and per-algorithm classification
# scope stated.
_SSH_OPTIONAL_PREREQ: tuple[str, ...] = (
    "optional prerequisite",
    "ssh-audit",
    "per-algorithm classification",
    "kex",
    "host-key",
    "mac breakdown",
    'shutil.which("ssh-audit")',
    "pip install ssh-audit",
)

# Silent-fallback behavior when the binary is absent.
_SSH_FALLBACK_BEHAVIOR: tuple[str, ...] = (
    "the scanner does not fail",
    "silently falls back to a raw",
    "ssh banner grab",
    "single generic",
    "ssh quantum planning advisory",
    "no per-algorithm kex/host-key/mac breakdown",
)

# PATH caveat for a venv-installed binary.
_SSH_PATH_CAVEAT: tuple[str, ...] = (
    "must be on the `path`",
    "virtualenv",
    "without activating the environment",
    "added to `path`",
    "will not find it",
    "ensure the directory containing `ssh-audit` is on `path`",
)

# 2026-08-31 TRIAGE-176-03 malformed-command-line note.
_TRIAGE_176_03_NOTE: tuple[str, ...] = (
    "before 2026-08-31",
    "that was a",
    "bug, not your setup",
    "malformed command line",
    "silent-fallback path above ran on every scan",
    "no ssh algorithm data",
    "re-scan any ssh hosts",
)


def _read(rel: str) -> str:
    """Read a repo-relative file and return its lower-cased contents."""
    return open(os.path.join(_REPO_ROOT, rel), encoding="utf-8").read().lower()


def _read_raw(rel: str) -> str:
    """Read a repo-relative file and return its contents unmodified."""
    return open(os.path.join(_REPO_ROOT, rel), encoding="utf-8").read()


def test_operators_guide_resolves():
    """docs/operators-guide.md must exist on disk."""
    assert os.path.isfile(os.path.join(_REPO_ROOT, _OPS_GUIDE)), (
        f"Required doc missing: {_OPS_GUIDE}"
    )


def test_ssh_optional_prereq_documented():
    """§6.2 must state ssh-audit is an OPTIONAL prerequisite resolved via
    shutil.which, describe the KEX/host-key/MAC breakdown it enables, and
    give the pip install command."""
    text = _read(_OPS_GUIDE)
    missing = [needle for needle in _SSH_OPTIONAL_PREREQ if needle not in text]
    assert not missing, f"§6.2 SSH optional-prerequisite text missing: {missing}"


def test_ssh_silent_fallback_documented():
    """§6.2 must state the scanner does NOT fail when ssh-audit is absent —
    it silently falls back to a raw banner grab with only a single generic
    advisory, not a per-algorithm breakdown."""
    text = _read(_OPS_GUIDE)
    missing = [needle for needle in _SSH_FALLBACK_BEHAVIOR if needle not in text]
    assert not missing, f"§6.2 SSH silent-fallback text missing: {missing}"


def test_ssh_path_caveat_documented():
    """§6.2 must warn that a venv-installed ssh-audit binary is invisible to
    shutil.which unless the venv is activated / its bin dir is on PATH."""
    text = _read(_OPS_GUIDE)
    missing = [needle for needle in _SSH_PATH_CAVEAT if needle not in text]
    assert not missing, f"§6.2 SSH PATH-caveat text missing: {missing}"


def test_triage_176_03_note_documented():
    """§6.2 must retain the 2026-08-31 TRIAGE-176-03 callout explaining that
    an ssh-audit install before that date produced no extra detail because
    of the malformed command line."""
    text = _read(_OPS_GUIDE)
    missing = [needle for needle in _TRIAGE_176_03_NOTE if needle not in text]
    assert not missing, f"§6.2 TRIAGE-176-03 note missing: {missing}"


def test_triage_176_03_host_port_form_matches_live_scanner():
    """Cross-check: the doc's TRIAGE-176-03 note describes a single
    'host:port' positional argument as the fix. Assert that literal
    f-string form is actually what _run_ssh_audit builds in
    quirk/scanner/ssh_scanner.py, so the doc and the code cannot drift
    apart."""
    scanner_src = _read_raw(_SSH_SCANNER)

    func_match = re.search(
        r"def _run_ssh_audit\(.*?\n(?:    .*\n)*", scanner_src
    )
    assert func_match, "_run_ssh_audit function not found in ssh_scanner.py — has it been renamed/removed?"
    func_body = func_match.group(0)

    assert 'f"{host}:{port}"' in func_body, (
        "_run_ssh_audit no longer builds the single-positional 'host:port' "
        "argument the doc's TRIAGE-176-03 note describes — doc/code drift"
    )
    assert 'shutil.which("ssh-audit")' in scanner_src, (
        "ssh_scanner.py no longer resolves ssh-audit via shutil.which — "
        "doc's 'optional prerequisite' claim is now stale"
    )
