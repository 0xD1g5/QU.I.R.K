"""Phase 48 CI gate: forbid stale PQC terminology in two locked source files.

D-07: scope is exactly quirk/engine/risk_engine.py + quirk/dashboard/api/routes/scan.py.
D-08: case-insensitive substring match on 'kyber', 'dilithium',
      'when standards are adopted'. No exemptions.

This test pair acts as the project-wide regression guard for Phase 48 (Rich
Finding Context). Pattern modelled on tests/test_packaging.py — read source
file from disk, substring-check the contents.
"""
import os

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

_GATED_FILES = [
    "quirk/engine/risk_engine.py",
    "quirk/dashboard/api/routes/scan.py",
]

_FORBIDDEN = ("kyber", "dilithium", "when standards are adopted")


def _read(rel: str) -> str:
    """Read a repo-relative file and return its lower-cased contents."""
    return open(os.path.join(_REPO_ROOT, rel), encoding="utf-8").read().lower()


def test_gated_files_resolve():
    """Catch accidental file rename — both gated paths must exist."""
    for rel in _GATED_FILES:
        assert os.path.isfile(os.path.join(_REPO_ROOT, rel)), (
            f"Gated file missing: {rel}. Update _GATED_FILES if file was renamed."
        )


def test_no_stale_pqc_terminology_in_gated_files():
    """D-07/D-08: forbidden substrings must not appear in the two gated source files."""
    offenders = []
    for rel in _GATED_FILES:
        text = _read(rel)
        for needle in _FORBIDDEN:
            if needle in text:
                offenders.append((rel, needle))
    assert not offenders, (
        f"Stale PQC terminology found: {offenders}. "
        f"Use FIPS designations only (FIPS 203/204/205); see Phase 48 D-04/D-08."
    )
