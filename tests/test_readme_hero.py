"""Static contract for the README hero image (Phase 225 D-08/D-09/D-12).

PyPI renders the README outside the repository, so a repo-relative image path
shows as a broken image there; the hero must use an absolute
raw.githubusercontent.com URL (D-08). The PNG is a 2x-DPR capture of the
executive summary, kept under 1 MiB (D-09). Regenerate it with
``python -m scripts.capture_readme_hero``.

PNG bounds: width 2048..3600 (2x DPR of a 1024..1800 css-px viewport; the
approved capture is 3360 wide); height only has to be positive because the
capture sizes its viewport to the content, so height varies (approved: 2362).
"""

import shutil
import struct
from pathlib import Path

from tests.cli_helpers import run_fork_safe

REPO_ROOT = Path(__file__).resolve().parent.parent
HERO_REL = "docs/images/dashboard-hero.png"
RAW_HERO = "https://raw.githubusercontent.com/0xD1g5/QU.I.R.K/main/" + HERO_REL
MAX_BYTES = 1_048_576
LEDGERS = {"docs/doc-classification.jsonl", "docs/doc-claim-ledger.jsonl"}
TEXT_SUFFIXES = {".md", ".py", ".txt", ".rst", ".toml", ".yml", ".yaml", ".json", ".ts", ".tsx"}


def _readme() -> str:
    return (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _tracked() -> list[str]:
    r = run_fork_safe([shutil.which("git") or "/usr/bin/git", "-C", str(REPO_ROOT), "ls-files", "-z"], check=True)
    return [p for p in r.stdout.split("\0") if p]


def test_readme_hero_uses_absolute_raw_url():
    assert _readme().count(f"]({RAW_HERO})") == 1, (
        "Phase 225 D-08: README must embed the hero exactly once by absolute raw URL "
        "so it renders on PyPI"
    )


def test_readme_has_no_relative_docs_images_link():
    assert "](docs/images/" not in _readme(), (
        "Phase 225 D-08: a repo-relative image link breaks on PyPI"
    )


def test_hero_png_dimensions_and_size():
    path = REPO_ROOT / HERO_REL
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "Phase 225 D-09: hero is not a PNG"
    width, height = struct.unpack(">II", data[16:24])
    assert 2048 <= width <= 3600, (
        f"Phase 225 D-09: width {width} not a 2x capture; "
        "re-run python -m scripts.capture_readme_hero"
    )
    assert height > 0
    assert len(data) < MAX_BYTES, f"Phase 225 D-09: hero is {len(data)} bytes (>= 1 MiB)"


def test_no_orphan_images_in_docs_images():
    tracked = _tracked()
    images = [p for p in tracked if p.startswith("docs/images/")]
    assert images, "Phase 225 D-12: no tracked docs/images/* found"
    corpus = ""
    for p in tracked:
        if p in LEDGERS or p.startswith("docs/images/"):
            continue
        if Path(p).suffix.lower() not in TEXT_SUFFIXES:
            continue
        f = REPO_ROOT / p
        if f.is_file():
            corpus += f.read_text(encoding="utf-8", errors="ignore")
    orphans = [p for p in images if Path(p).name not in corpus]
    assert not orphans, f"Phase 225 D-12: orphan images (no tracked doc references them): {orphans}"


# --------------------------------------------------------------------------
# 225-REVIEW CR-02: the capture serves a snapshot, never the canonical DB, and
# checks the canonical fingerprint (incl. -wal/-journal) on every exit path.
# --------------------------------------------------------------------------

def _make_db(path: Path) -> None:
    import sqlite3

    con = sqlite3.connect(str(path))
    con.execute("create table scan_jobs (id integer primary key, status text)")
    con.execute("insert into scan_jobs (status) values ('running')")
    con.commit()
    con.close()


def test_snapshot_db_is_a_consistent_copy_and_leaves_canonical_untouched(tmp_path):
    import sqlite3

    from scripts.capture_readme_hero import db_fingerprint, snapshot_db

    canon = tmp_path / "canon dir" / "quirk.db"  # space: exercises the URI form
    canon.parent.mkdir()
    _make_db(canon)
    before_bytes = canon.read_bytes()
    before = db_fingerprint(canon)
    snapdir = tmp_path / "snap"
    snapdir.mkdir()
    snap = snapshot_db(canon, snapdir)
    con = sqlite3.connect(str(snap))
    assert con.execute("select status from scan_jobs").fetchall() == [("running",)]
    # What the app's lifespan does to the DB it serves -- here, the COPY.
    con.execute("update scan_jobs set status='failed'")
    con.execute("alter table scan_jobs add column extra text")
    con.commit()
    con.close()
    assert canon.read_bytes() == before_bytes
    assert db_fingerprint(canon) == before
    assert sorted(p.name for p in canon.parent.iterdir()) == ["quirk.db"], (
        "the read-only snapshot must not leave a journal/wal next to the canonical DB")


def test_db_fingerprint_covers_wal_sidecar(tmp_path):
    from scripts.capture_readme_hero import db_fingerprint

    db = tmp_path / "quirk.db"
    _make_db(db)
    base = db_fingerprint(db)
    assert base["quirk.db-wal"] is None
    (tmp_path / "quirk.db-wal").write_bytes(b"x")
    assert db_fingerprint(db) != base, "a -wal change must change the fingerprint"


def test_main_never_serves_canonical_and_checks_db_on_abort(tmp_path, monkeypatch, capsys):
    import pytest

    import scripts.capture_readme_hero as hero

    canon = tmp_path / "quirk.db"
    _make_db(canon)
    served: list[Path] = []

    def fake_run(args, db, evidence):  # stands in for the uvicorn + Playwright leg
        served.append(db)
        db.write_bytes(db.read_bytes() + b"\0")  # the server writes its DB
    monkeypatch.setattr(hero, "_run", fake_run)
    assert hero.main(["--db", str(canon), "--out", str(tmp_path / "o.png")]) == 0
    assert served and served[0].resolve() != canon.resolve()
    assert not served[0].exists(), "snapshot temp dir must be removed"
    capsys.readouterr()

    def mutating_abort(args, db, evidence):  # canonical mutated, then abort
        canon.write_bytes(canon.read_bytes() + b"\0")
        raise SystemExit("GAUGE_COUNT: simulated abort")
    monkeypatch.setattr(hero, "_run", mutating_abort)
    with pytest.raises(SystemExit, match="GAUGE_COUNT"):
        hero.main(["--db", str(canon), "--out", str(tmp_path / "o.png")])
    assert "DB_MUTATED" in capsys.readouterr().err, (
        "CR-02: the canonical-DB check must run on abort paths too")


class _FakeProc:
    """Stands in for the uvicorn Popen so the leak test needs no server."""

    def __init__(self, *a, **kw):
        self.returncode = None
        self.stdout = None
        self.popen_kwargs = kw

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = 0

    kill = terminate

    def wait(self, timeout=None):
        return self.returncode

    def communicate(self, timeout=None):
        return (b"", b"")


class _FakeResp:
    status = 200

    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_capture_run_leaves_no_temp_dirs(tmp_path, monkeypatch):
    """225-REVIEW WR-02: the snapshot dir, the scoped-config/report dir and
    every serve_dashboard scratch dir are removed -- on success AND abort."""
    import json
    import tempfile

    import pytest

    import scripts.capture_readme_hero as hero

    fake_repo = tmp_path / "repo"
    (fake_repo / "quirk-output").mkdir(parents=True)
    for name in ("report-20260928-132139.html", "run-stats-20260928-132139.json"):
        (fake_repo / "quirk-output" / name).write_text("x", encoding="utf-8")
    (fake_repo / "config.yaml").write_text("api_token: s3cret\n", encoding="utf-8")
    canon = tmp_path / "quirk.db"
    _make_db(canon)
    tmproot = tmp_path / "tmproot"
    tmproot.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmproot))
    monkeypatch.setattr(hero, "REPO_ROOT", fake_repo)
    procs: list[_FakeProc] = []

    def popen(*a, **kw):
        procs.append(_FakeProc(*a, **kw))
        return procs[-1]
    monkeypatch.setattr(hero.subprocess, "Popen", popen)
    meta = json.dumps({"meta": {"scanned_at": "2026-09-28T13:21:39"}}).encode()
    monkeypatch.setattr(hero.urllib.request, "urlopen",
                        lambda *a, **kw: _FakeResp(meta))
    seen: dict = {}

    def fake_capture(args, db, cfg_path, evidence):
        seen["cfg"] = Path(cfg_path)
        assert seen["cfg"].is_file() and seen["cfg"].is_relative_to(tmproot)
        assert "s3cret" in seen["cfg"].read_text(encoding="utf-8")
    monkeypatch.setattr(hero, "_capture_with_server", fake_capture)
    assert hero.main(["--db", str(canon), "--out", str(tmp_path / "o.png")]) == 0
    assert seen["cfg"] and not seen["cfg"].exists()
    assert len(procs) == 1, "the probe server ran through the real serve_dashboard"
    assert list(tmproot.iterdir()) == [], "temp dirs leaked on success"

    def boom(args, db, cfg_path, evidence):
        raise SystemExit("GAUGE_COUNT: simulated abort")
    monkeypatch.setattr(hero, "_capture_with_server", boom)
    with pytest.raises(SystemExit, match="GAUGE_COUNT"):
        hero.main(["--db", str(canon), "--out", str(tmp_path / "o.png")])
    assert list(tmproot.iterdir()) == [], "temp dirs leaked on abort"
