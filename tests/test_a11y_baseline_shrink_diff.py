"""Can-fail probes for scripts/a11y_baseline_shrink_diff.py (Phase 222.1 D-12).

Each non-shrink shape must exit 1, and each legal shrink must exit 0, so a
green run of the script against real baselines is evidence and not a tautology.
"""

import json
from pathlib import Path

from scripts import a11y_baseline_shrink_diff as sd


def _entry(rule, count, **extra):
    return {"rule": rule, "count": count, "impact": "serious", **extra}


def _write_dir(root: Path, files: dict, generated: str = "t0") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for name, entries in files.items():
        (root / name).write_text(
            json.dumps({"route": name, "generated": generated, "entries": entries}),
            encoding="utf-8",
        )
    return root


def _axe(tmp_path, old_files, new_files, capsys, new_generated="t0"):
    old = _write_dir(tmp_path / "old", old_files)
    new = _write_dir(tmp_path / "new", new_files, generated=new_generated)
    rc = sd.main(["axe", str(old), str(new)])
    return rc, capsys.readouterr().out


BASE = {"baseline-a.json": [_entry("color-contrast", 1), _entry("label", 2)]}


def test_axe_identical_dirs_pass(tmp_path, capsys):
    rc, out = _axe(tmp_path, BASE, BASE, capsys)
    assert rc == 0
    assert "PASS" in out


def test_axe_entry_removed_is_shrink(tmp_path, capsys):
    new = {"baseline-a.json": [_entry("label", 2)]}
    rc, out = _axe(tmp_path, BASE, new, capsys)
    assert rc == 0
    assert "SHRINK" in out


def test_axe_count_decrease_is_shrink(tmp_path, capsys):
    new = {"baseline-a.json": [_entry("color-contrast", 1), _entry("label", 1)]}
    rc, out = _axe(tmp_path, BASE, new, capsys)
    assert rc == 0
    assert "SHRINK" in out


def test_axe_count_increase_fails(tmp_path, capsys):
    new = {"baseline-a.json": [_entry("color-contrast", 2), _entry("label", 2)]}
    rc, out = _axe(tmp_path, BASE, new, capsys)
    assert rc == 1
    assert "INCREASE" in out


def test_axe_new_key_fails(tmp_path, capsys):
    new = {"baseline-a.json": BASE["baseline-a.json"] + [_entry("region", 1)]}
    rc, out = _axe(tmp_path, BASE, new, capsys)
    assert rc == 1
    assert "NEW KEY" in out


def test_axe_file_set_difference_fails(tmp_path, capsys):
    new = {**BASE, "baseline-b.json": [_entry("label", 1)]}
    rc, out = _axe(tmp_path, BASE, new, capsys)
    assert rc == 1
    assert "file set differs" in out


def test_axe_missing_file_fails(tmp_path, capsys):
    old = {**BASE, "baseline-b.json": [_entry("label", 1)]}
    rc, out = _axe(tmp_path, old, BASE, capsys)
    assert rc == 1
    assert "file set differs" in out


def test_axe_countrange_change_fails(tmp_path, capsys):
    old = {"baseline-a.json": [_entry("label", 2, countRange=[1, 2])]}
    new = {"baseline-a.json": [_entry("label", 2, countRange=[1, 3])]}
    rc, out = _axe(tmp_path, old, new, capsys)
    assert rc == 1
    assert "countRange" in out


def test_axe_generated_timestamp_ignored(tmp_path, capsys):
    rc, out = _axe(tmp_path, BASE, BASE, capsys, new_generated="t1-different")
    assert rc == 0
    assert "PASS" in out


def _ratio(tmp_path, old, new, capsys):
    o, n = tmp_path / "o.json", tmp_path / "n.json"
    o.write_text(json.dumps(old), encoding="utf-8")
    n.write_text(json.dumps(new), encoding="utf-8")
    rc = sd.main(["ratio", str(o), str(n)])
    return rc, capsys.readouterr().out


RATIO = {"_comment": "x", "light|accent|a": 3.15, "dark|critical|b": 4.23}


def test_ratio_key_deleted_passes(tmp_path, capsys):
    new = {"_comment": "x", "dark|critical|b": 4.23}
    rc, out = _ratio(tmp_path, RATIO, new, capsys)
    assert rc == 0
    assert "DELETED" in out


def test_ratio_retained_value_changed_upward_fails(tmp_path, capsys):
    new = {"_comment": "x", "light|accent|a": 3.2, "dark|critical|b": 4.23}
    rc, out = _ratio(tmp_path, RATIO, new, capsys)
    assert rc == 1
    assert "CHANGED" in out


def test_ratio_new_key_fails(tmp_path, capsys):
    new = {**RATIO, "light|high|c": 2.0}
    rc, out = _ratio(tmp_path, RATIO, new, capsys)
    assert rc == 1
    assert "NEW KEY" in out


def test_ratio_comment_change_passes(tmp_path, capsys):
    new = {**RATIO, "_comment": "a different explanatory note"}
    rc, out = _ratio(tmp_path, RATIO, new, capsys)
    assert rc == 0
    assert "PASS" in out
