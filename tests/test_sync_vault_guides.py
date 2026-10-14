"""Phase 225 D-05/D-06: tests for scripts/sync_vault_guides.py.

Logic tests run against a temporary vault (CI-safe). The completeness test
enumerates the real ``git ls-files``. ``test_live_vault_in_sync`` reads the
operator's real Obsidian vault and skips in CI (registered in
tests/skip_registry.py as environment_capability).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from scripts.sync_vault_guides import (
    EXEMPT,
    EXEMPT_GLOBS,
    MAPPING,
    VaultPathError,
    cross_check,
    diff_count,
    find_unmapped,
    main,
    new_note_frontmatter,
    parse_note,
    render_note,
    resolve_target,
    write_pair,
)
from tests.cli_helpers import run_fork_safe

REPO_ROOT = Path(__file__).resolve().parent.parent
FIX = "python -m scripts.sync_vault_guides --write"
TODAY = "2026-10-13"


def _tracked() -> list[str]:
    git = shutil.which("git")
    if git is None:
        pytest.fail("git binary not available; this gate requires a checkout")
    res = run_fork_safe([git, "-C", str(REPO_ROOT), "ls-files", "-z"], timeout=30)
    assert res.returncode == 0, f"git ls-files failed: {res.stderr!r}"
    files = [p for p in res.stdout.split("\0") if p]
    assert files, "git ls-files returned nothing; refusing to pass vacuously"
    return sorted(p for p in files if p.endswith(".md")
                  and (p.startswith("docs/") or "/" not in p))


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="")
    return root


def test_parse_note_strips_exactly_one_separator():
    fm, body = parse_note("---\nproject: QU.I.R.K.\nupdated: x\n---\n\n\nBody\n")
    assert fm == ["project: QU.I.R.K.", "updated: x"]
    assert body == "\nBody\n", "Phase 225 D-05: strip exactly one blank"
    assert parse_note("no frontmatter\n") == ([], "no frontmatter\n")


def test_render_preserves_frontmatter_and_extra_keys():
    fm = ["project: QU.I.R.K.", "type: reference", "status: complete",
          "source: docs/x.md", "updated: 2020-01-01", "aliases: [x]"]
    out = render_note(fm, "Body\n", TODAY)
    fm2, body = parse_note(out)
    assert body == "Body\n"
    assert [a for a, b in zip(fm, fm2) if a != b] == ["updated: 2020-01-01"]
    assert fm2[-1] == "aliases: [x]" and "type: reference" in fm2
    assert "updated: " + TODAY in fm2


def test_write_is_idempotent_and_keeps_updated(tmp_path):
    repo = _repo(tmp_path, {"docs/a.md": "# A\nline\n"})
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "A.md"
    note.write_text(render_note(
        ["project: QU.I.R.K.", "type: guide", "status: active",
         "source: docs/a.md", "updated: 2020-01-01"], "# A\nline\n", "2020-01-01"),
        encoding="utf-8", newline="")
    mtime = note.stat().st_mtime_ns
    res = write_pair(repo, vault, "docs/a.md", "A.md", TODAY)
    assert res.status == "in-sync"
    assert note.stat().st_mtime_ns == mtime
    assert "updated: 2020-01-01" in note.read_text(encoding="utf-8")
    (repo / "docs/a.md").write_text("# A\nchanged\n", encoding="utf-8", newline="")
    assert write_pair(repo, vault, "docs/a.md", "A.md", TODAY).status == "written"
    assert write_pair(repo, vault, "docs/a.md", "A.md", "2030-01-01").status == "in-sync"
    assert f"updated: {TODAY}" in note.read_text(encoding="utf-8")


def test_new_connector_note_has_five_keys(tmp_path):
    repo = _repo(tmp_path, {"docs/connectors/gcp.md": "# GCP\n"})
    vault = tmp_path / "vault"
    vault.mkdir()
    res = write_pair(repo, vault, "docs/connectors/gcp.md",
                     "Guides/Connectors/GCP.md", TODAY)
    assert res.status == "created"
    text = (vault / "Guides/Connectors/GCP.md").read_text(encoding="utf-8")
    assert text == ("---\nproject: QU.I.R.K.\ntype: guide\nstatus: active\n"
                    "source: docs/connectors/gcp.md\nupdated: " + TODAY +
                    "\n---\n\n# GCP\n")
    assert len(new_note_frontmatter("x", TODAY)) == 5


def test_write_refuses_target_outside_vault_root(tmp_path):
    repo = _repo(tmp_path, {"docs/a.md": "x\n"})
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (vault / "link.md").symlink_to(outside / "t.md")
    for rel in ("../escape.md", str(tmp_path / "abs.md"), "link.md"):
        with pytest.raises(VaultPathError):
            write_pair(repo, vault, "docs/a.md", rel, TODAY)
    with pytest.raises(VaultPathError):
        resolve_target(vault, "../escape.md")
    assert not (tmp_path / "escape.md").exists()
    assert not (tmp_path / "abs.md").exists()
    assert not list(outside.iterdir())


def test_drifted_body_is_counted():
    a = "one\ntwo\nthree\n"
    assert diff_count(a, a) == 0, "negative control"
    assert diff_count(a, "one\nTWO\nthree\n") > 0
    assert diff_count(a, "one\nTWO\nTHREE\n") >= 4


def test_unmapped_tracked_doc_is_flagged(tmp_path):
    assert find_unmapped(["docs/new-thing.md", "docs/admin-guide.md"],
                         MAPPING, EXEMPT, EXEMPT_GLOBS) == ["docs/new-thing.md"]
    vault = tmp_path / "vault"
    vault.mkdir()
    assert main(["--check", "--vault-root", str(vault)],
                tracked=["docs/new-thing.md"], today=TODAY) == 1


def test_completeness_every_tracked_md_is_mapped_or_exempt():
    tracked = _tracked()
    bad = find_unmapped(tracked, MAPPING, EXEMPT, EXEMPT_GLOBS)
    assert not bad, (
        f"Phase 225 D-06: tracked docs neither MAPPED nor EXEMPT: {bad}; add "
        "each to MAPPING or EXEMPT (with a reason) in scripts/sync_vault_guides.py")
    assert all(reason.strip() for reason in EXEMPT.values())


def test_vault_root_absent_exits_2(tmp_path):
    assert main(["--check", "--vault-root", str(tmp_path / "nope")],
                tracked=["docs/admin-guide.md"], today=TODAY) == 2


def test_cross_check_reports_source_disagreement():
    mapping = {"docs/a.md": "Guides/A.md"}
    msgs = cross_check(
        mapping,
        {"Guides/A.md": "docs/other.md",
         "Guides/Stray.md": "docs/gone.md"},
        {"docs/a.md"})
    assert any(m.startswith("MISMATCH Guides/A.md") for m in msgs)
    assert any("unmapped vault note Guides/Stray.md" in m
               and "no tracked file" in m for m in msgs)


def test_live_vault_in_sync():
    """Pitfall 7: once this exists, editing a mapped doc turns the LOCAL
    suite red until the vault is re-synced, by design. CI skips it."""
    root = Path(os.environ.get("QUIRK_VAULT_ROOT")
                or Path.home() / "vaults/Digs/20_Dev-Work/QUIRK")
    if not root.is_dir():
        pytest.skip(f"vault root absent: {root}; a skip is not a pass")
    code = main(["--check", "--vault-root", str(root)], tracked=_tracked())
    assert code == 0, (
        f"Phase 225 D-06: vault out of sync (exit {code}); run `{FIX}`")
