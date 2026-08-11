"""Phase 148 RELEASE-04 / D-148-RELEASE04: static guard — the v5.11.0 Windows-asset
disposition facts must never silently drift.

Loads docs/release-notes/5.11.0.md and docs/release-notes/5.11.0-github-release-body.md
and asserts the required disposition facts are present in both, that neither file links
to the pre-existing missing 5.7.0.md-5.10.0.md release-notes files (D-04, out of scope),
and that the notes file never asserts a Windows zip exists without a negation on the same
line.
"""
from __future__ import annotations

import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTES_FILE = REPO_ROOT / "docs" / "release-notes" / "5.11.0.md"
BODY_FILE = REPO_ROOT / "docs" / "release-notes" / "5.11.0-github-release-body.md"

MISSING_NOTES = ("5.7.0.md", "5.8.0.md", "5.9.0.md", "5.10.0.md")
ZERO_ASSETS_PHRASE = "This release intentionally has zero attached assets"
NEGATION_TOKENS = ("no", "not", "never")


def test_notes_file_exists():
    assert NOTES_FILE.exists(), (
        f"{NOTES_FILE} does not exist — v5.11.0 Windows-asset disposition is missing "
        "(RELEASE-04 / D-148-RELEASE04)"
    )


def test_body_file_exists():
    assert BODY_FILE.exists(), (
        f"{BODY_FILE} does not exist — plan 148-04 has no Release body to publish "
        "(RELEASE-04 / D-148-RELEASE04)"
    )


def test_notes_file_states_pypi_only():
    text = NOTES_FILE.read_text(encoding="utf-8")
    assert "PyPI-only" in text, (
        f"{NOTES_FILE.name} must state the release is PyPI-only (D-03)"
    )


def test_body_file_states_pypi_only():
    text = BODY_FILE.read_text(encoding="utf-8")
    assert "PyPI-only" in text, (
        f"{BODY_FILE.name} must state the release is PyPI-only (D-03)"
    )


def test_notes_file_names_fix_commit():
    text = NOTES_FILE.read_text(encoding="utf-8")
    assert "1a6effc" in text, (
        f"{NOTES_FILE.name} must name fix commit 1a6effc (D-03)"
    )


def test_body_file_names_fix_commit():
    text = BODY_FILE.read_text(encoding="utf-8")
    assert "1a6effc" in text, (
        f"{BODY_FILE.name} must name fix commit 1a6effc (D-03)"
    )


def test_notes_file_names_first_fixed_version():
    text = NOTES_FILE.read_text(encoding="utf-8")
    assert "v5.12.0" in text, (
        f"{NOTES_FILE.name} must state v5.12.0 is the first version with a verified "
        "Windows artifact (D-03)"
    )


def test_body_file_names_first_fixed_version():
    text = BODY_FILE.read_text(encoding="utf-8")
    assert "v5.12.0" in text, (
        f"{BODY_FILE.name} must state v5.12.0 is the first version with a verified "
        "Windows artifact (D-03)"
    )


def test_notes_file_names_failing_job_and_step():
    text = NOTES_FILE.read_text(encoding="utf-8")
    assert "windows-package" in text, (
        f"{NOTES_FILE.name} must name the failing windows-package job (D-01/D-03)"
    )
    assert "signtool verify /pa" in text, (
        f"{NOTES_FILE.name} must name the root-cause command signtool verify /pa (D-03)"
    )


def test_body_file_has_install_line():
    text = BODY_FILE.read_text(encoding="utf-8")
    assert "pip install quirk-scanner==5.11.0" in text, (
        f"{BODY_FILE.name} must contain the exact install line "
        "'pip install quirk-scanner==5.11.0'"
    )


def test_body_file_links_full_notes():
    text = BODY_FILE.read_text(encoding="utf-8")
    assert re.search(r"\S+/docs/release-notes/5\.11\.0\.md", text), (
        f"{BODY_FILE.name} must link the full notes file at a URL ending in "
        "/docs/release-notes/5.11.0.md (D-04)"
    )


def test_body_file_matches_repo_name_with_owner():
    """The body's notes link must point at this repo (owner/repo), not a placeholder."""
    text = BODY_FILE.read_text(encoding="utf-8")
    assert "0xD1g5/QU.I.R.K" in text, (
        f"{BODY_FILE.name} must link via the resolved owner/repo "
        "(gh repo view --json nameWithOwner), not a guessed placeholder"
    )


def test_body_file_states_zero_attached_assets():
    text = BODY_FILE.read_text(encoding="utf-8")
    assert ZERO_ASSETS_PHRASE in text, (
        f"{BODY_FILE.name} must contain the literal phrase {ZERO_ASSETS_PHRASE!r} so an "
        "operator does not read the empty asset list as a page that failed to load (D-02)"
    )


def test_neither_file_links_missing_release_notes():
    for path in (NOTES_FILE, BODY_FILE):
        text = path.read_text(encoding="utf-8")
        for missing in MISSING_NOTES:
            assert missing not in text, (
                f"{path.name} references {missing}, which does not exist "
                "(D-04, out of scope for this phase)"
            )


def test_notes_file_never_asserts_windows_zip_exists_without_negation():
    """If 'quirk-windows-5.11.0.zip' appears, the same line must also negate it."""
    text = NOTES_FILE.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "quirk-windows-5.11.0.zip" in line:
            lowered = line.lower()
            assert any(token in lowered for token in NEGATION_TOKENS), (
                f"Line mentions quirk-windows-5.11.0.zip without a negation token "
                f"({NEGATION_TOKENS}) — must not read as asserting the zip exists: {line!r}"
            )
