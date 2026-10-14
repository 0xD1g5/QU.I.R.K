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
    find_stale_mapping,
    find_unmapped,
    main,
    new_note_frontmatter,
    parse_note,
    render_note,
    resolve_target,
    tracked_markdown,
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


# --------------------------------------------------------------------------
# 225-REVIEW CR-01: ownership guard -- never overwrite a note that is not
# provably a sync of its MAPPING source; preserve extra keys (LF and CRLF).
# --------------------------------------------------------------------------

def test_write_refuses_mismatched_source_note_byte_identical(tmp_path):
    repo = _repo(tmp_path, {"docs/a.md": "# A\nnew\n"})
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "A.md"
    original = ("---\nproject: QU.I.R.K.\nsource: docs/other.md\n"
                "updated: 2020-01-01\n---\n\nhand-authored operator note\n")
    note.write_bytes(original.encode("utf-8"))
    res = write_pair(repo, vault, "docs/a.md", "A.md", TODAY)
    assert res.status == "refused" and "docs/other.md" in res.detail
    assert note.read_bytes() == original.encode("utf-8"), (
        "CR-01: a MISMATCH note must be left byte-identical")
    # Negative control: the same note with the right source IS written.
    note.write_bytes(original.replace("docs/other.md", "docs/a.md")
                     .encode("utf-8"))
    assert write_pair(repo, vault, "docs/a.md", "A.md", TODAY).status == "written"


def test_main_write_leaves_mismatched_vault_note_untouched(tmp_path):
    vault = tmp_path / "vault"
    target = vault / MAPPING["docs/admin-guide.md"]
    target.parent.mkdir(parents=True)
    original = (b"---\nproject: QU.I.R.K.\nsource: docs/not-admin.md\n"
                b"updated: 2020-01-01\n---\n\nrepurposed note\n")
    target.write_bytes(original)
    # Every MAPPING source tracked, so the refusal is the ONLY red reason.
    code = main(["--write", "--vault-root", str(vault)],
                tracked=sorted(MAPPING), today=TODAY)
    assert code == 1, "CR-01: a refused pair must exit nonzero"
    assert target.read_bytes() == original


@pytest.mark.parametrize("original", [
    b"plain operator note with no frontmatter\n",
    b"---\nproject: QU.I.R.K.\nno closing fence\n",
    b"---\nproject: QU.I.R.K.\nupdated: 2020-01-01\n---\n\nno source key\n",
])
def test_write_refuses_unowned_note(tmp_path, original):
    repo = _repo(tmp_path, {"docs/a.md": "# A\n"})
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "A.md"
    note.write_bytes(original)
    for write in (False, True):
        res = write_pair(repo, vault, "docs/a.md", "A.md", TODAY, write=write)
        assert res.status == "refused", (write, res)
    assert note.read_bytes() == original


def test_write_preserves_extra_keys_lf(tmp_path):
    repo = _repo(tmp_path, {"docs/a.md": "# A\nchanged\n"})
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "A.md"
    note.write_bytes(b"---\nproject: QU.I.R.K.\ntype: reference\n"
                     b"source: docs/a.md\nupdated: 2020-01-01\n"
                     b"aliases: [Admin]\ntags: [quirk]\n---\n\n# A\nold\n")
    assert write_pair(repo, vault, "docs/a.md", "A.md", TODAY).status == "written"
    assert note.read_bytes() == (
        b"---\nproject: QU.I.R.K.\ntype: reference\nsource: docs/a.md\n"
        b"updated: " + TODAY.encode() + b"\naliases: [Admin]\ntags: [quirk]\n"
        b"---\n\n# A\nchanged\n")


def test_write_preserves_crlf_frontmatter_and_extra_keys(tmp_path):
    repo = _repo(tmp_path, {"docs/a.md": "# A\nchanged\n"})
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "A.md"
    note.write_bytes(b"---\r\nproject: QU.I.R.K.\r\nsource: docs/a.md\r\n"
                     b"updated: 2020-01-01\r\naliases: [Admin]\r\n---\r\n\r\n"
                     b"# A\nold\n")
    fm, body = parse_note(note.read_text(encoding="utf-8", newline=""))
    assert fm[-1] == "aliases: [Admin]" and body == "# A\nold\n"
    assert write_pair(repo, vault, "docs/a.md", "A.md", TODAY).status == "written"
    assert note.read_bytes() == (
        b"---\r\nproject: QU.I.R.K.\r\nsource: docs/a.md\r\nupdated: "
        + TODAY.encode() + b"\r\naliases: [Admin]\r\n---\r\n\r\n# A\nchanged\n")
    assert write_pair(repo, vault, "docs/a.md", "A.md", TODAY).status == "in-sync"


def test_atomic_write_never_follows_a_planted_temp_symlink(tmp_path):
    """225-REVIEW WR-06: a symlink at the old fixed temp name must not be
    followed, and the target must end up a regular file inside the vault."""
    repo = _repo(tmp_path, {"docs/a.md": "# A\nnew\n"})
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"precious\n")
    (vault / "A.md.tmp-sync").symlink_to(outside)
    assert write_pair(repo, vault, "docs/a.md", "A.md", TODAY).status == "created"
    assert outside.read_bytes() == b"precious\n"
    note = vault / "A.md"
    assert note.is_file() and not note.is_symlink()
    assert note.read_text(encoding="utf-8").endswith("# A\nnew\n")
    assert oct(note.stat().st_mode & 0o777) == oct(0o644)
    leftovers = [p.name for p in vault.iterdir()
                 if p.name not in ("A.md", "A.md.tmp-sync")]
    assert not leftovers, f"temp files leaked: {leftovers}"


def test_atomic_write_refuses_symlinked_target(tmp_path):
    from scripts.sync_vault_guides import _atomic_write
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"precious\n")
    link = tmp_path / "note.md"
    link.symlink_to(outside)
    with pytest.raises(VaultPathError):
        _atomic_write(link, "clobber\n")
    assert outside.read_bytes() == b"precious\n"


def test_stale_mapping_key_is_reported_and_fails_check(tmp_path, capsys):
    """225-REVIEW WR-05: a MAPPING source that is no longer tracked fails."""
    tracked = sorted(set(MAPPING) - {"docs/admin-guide.md"})
    assert find_stale_mapping(tracked, MAPPING) == ["docs/admin-guide.md"]
    assert find_stale_mapping(sorted(MAPPING), MAPPING) == [], "negative control"
    vault = tmp_path / "vault"
    vault.mkdir()
    assert main(["--write", "--vault-root", str(vault)],
                tracked=sorted(MAPPING), today=TODAY) == 0, "green control"
    capsys.readouterr()
    assert main(["--check", "--vault-root", str(vault)],
                tracked=tracked, today=TODAY) == 1
    assert "STALE MAPPING: docs/admin-guide.md" in capsys.readouterr().err


def test_every_mapping_source_is_tracked():
    stale = set(MAPPING) - set(_tracked())
    assert not stale, (
        f"225-REVIEW WR-05: MAPPING rows whose source is not tracked: "
        f"{sorted(stale)}; remove or rename them in scripts/sync_vault_guides.py")


# --------------------------------------------------------------------------
# 225-REVIEW WR-04: drive main() end to end against a temporary git repo, so
# the exit-0 path, --write, and the real tracked_markdown() run in CI.
# --------------------------------------------------------------------------

def _git_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    root = _repo(tmp_path, files)
    git = shutil.which("git")
    if git is None:
        pytest.fail("git binary not available; this gate requires git")
    for argv in (["init", "-q"], ["add", "-A"]):
        res = run_fork_safe([git, "-C", str(root), *argv], timeout=30)
        assert res.returncode == 0, res.stderr
    return root


def test_tracked_markdown_filter_on_temp_repo(tmp_path):
    root = _git_repo(tmp_path, {
        "README.md": "r\n", "docs/a.md": "a\n", "docs/connectors/b.md": "b\n",
        "docs/x.txt": "x\n", "sub/c.md": "c\n", "notes.txt": "n\n"})
    (root / "docs/untracked.md").write_text("u\n", encoding="utf-8")
    assert tracked_markdown(root) == [
        "README.md", "docs/a.md", "docs/connectors/b.md"]


def test_tracked_markdown_matches_independent_enumeration():
    assert tracked_markdown(REPO_ROOT) == _tracked()


def test_main_end_to_end_check_write_check_on_temp_repo(tmp_path, capsys):
    files = {src: f"# {src}\nbody\n" for src in MAPPING}
    files["README.md"] = "readme\n"  # EXEMPT
    repo = _git_repo(tmp_path, files)
    vault = tmp_path / "vault"
    vault.mkdir()
    argv = ["--vault-root", str(vault)]
    assert main(["--check", *argv], repo_root=repo, today=TODAY) == 1, (
        "empty vault: every pair is missing")
    assert main(["--write", *argv], repo_root=repo, today=TODAY) == 0
    note = vault / MAPPING["docs/admin-guide.md"]
    fm, body = parse_note(note.read_text(encoding="utf-8"))
    assert body == "# docs/admin-guide.md\nbody\n"
    assert "source: docs/admin-guide.md" in fm
    capsys.readouterr()
    assert main(["--check", "--json", *argv], repo_root=repo, today=TODAY) == 0
    import json
    report = json.loads(capsys.readouterr().out)
    assert report["exit"] == 0 and len(report["pairs"]) == len(MAPPING)
    assert {p["status"] for p in report["pairs"]} == {"in-sync"}
    # Negative control: drift one source -> red again, and --write repairs it.
    (repo / "docs/admin-guide.md").write_text("changed\n", encoding="utf-8")
    assert main(["--check", *argv], repo_root=repo, today=TODAY) == 1
    assert main(["--write", *argv], repo_root=repo, today=TODAY) == 0
    assert parse_note(note.read_text(encoding="utf-8"))[1] == "changed\n"
    # --repo-root CLI flag reaches the same code path.
    assert main(["--check", "--repo-root", str(repo), *argv], today=TODAY) == 0
