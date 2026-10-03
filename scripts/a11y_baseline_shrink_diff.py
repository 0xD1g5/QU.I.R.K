#!/usr/bin/env python3
"""Answer one question: is every regenerated a11y baseline a shrink?

Phase 222.1 D-11 / D-12 (BRAND-08).  The contrast and axe ratchets fail on
improvement as well as regression, so baselines legitimately move.  Only a
shrink is allowed: every changed baseline value is a deletion or a decrease.

Two modes:

``axe OLD_DIR NEW_DIR``
    Compare ``baseline-*.json`` axe count baselines.  Passes only when every
    (file, rule) count in NEW is <= the OLD count, no new (file, rule) key
    exists, the file sets are equal, and ``countRange`` is unchanged on every
    retained entry.  The ``generated`` timestamp is ignored.

``ratio OLD_JSON NEW_JSON``
    Compare flat contrast-ratio baselines.  Ratios are NOT counts: a "better"
    ratio is a higher number, so the only legal change is deleting a key (the
    pair now passes).  Passes only when NEW keys are a subset of OLD keys and
    every retained value is byte-equal (RESEARCH Pitfall 6).  Keys starting
    with ``_`` (e.g. ``_comment``) are not measurements and are ignored.

Exit codes: 0 pass, 1 any non-shrink.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

AxeKey = tuple[str, str]
AxeValue = tuple[int, object]


def load_axe_dir(path: Path) -> tuple[dict[AxeKey, AxeValue], set[str]]:
    """Map (file name, rule) -> (count, countRange) for every baseline-*.json."""
    path = Path(path)
    entries: dict[AxeKey, AxeValue] = {}
    files: set[str] = set()
    for fp in sorted(path.glob("baseline-*.json")):
        files.add(fp.name)
        data = json.loads(fp.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            key = (fp.name, entry["rule"])
            count, rng = entries.get(key, (0, None))
            entries[key] = (count + int(entry.get("count", 0)), entry.get("countRange", rng))
    return entries, files


def axe_shrink_violations(old_dir: Path, new_dir: Path) -> tuple[list[str], list[str]]:
    """Return (markdown rows for every changed key, failure strings)."""
    old, old_files = load_axe_dir(old_dir)
    new, new_files = load_axe_dir(new_dir)
    rows: list[str] = []
    failures: list[str] = []

    if old_files != new_files:
        only_old = sorted(old_files - new_files)
        only_new = sorted(new_files - old_files)
        failures.append(f"file set differs: only in old {only_old}, only in new {only_new}")

    for key in sorted(set(old) | set(new)):
        name, rule = key
        old_count = old[key][0] if key in old else 0
        new_count = new[key][0] if key in new else 0
        if key not in old:
            verdict = "NEW KEY"
            failures.append(f"NEW KEY {name} {rule}: absent in old, count {new_count} in new")
        elif new_count > old_count:
            verdict = "INCREASE"
            failures.append(f"INCREASE {name} {rule}: {old_count} -> {new_count}")
        elif new_count < old_count:
            verdict = "SHRINK"
        else:
            verdict = "unchanged"
        if key in old and key in new and old[key][1] != new[key][1]:
            failures.append(f"countRange changed {name} {rule}: {old[key][1]!r} -> {new[key][1]!r}")
            verdict = "COUNTRANGE CHANGED"
        if verdict != "unchanged":
            rows.append(f"| {name} | {rule} | {old_count} | {new_count} | {verdict} |")
    return rows, failures


def _measurements(data: dict) -> dict:
    return {k: v for k, v in data.items() if not k.startswith("_")}


def ratio_shrink_violations(old: dict, new: dict) -> list[str]:
    """Failures for a ratio baseline: new keys, or any retained value that moved."""
    old_m, new_m = _measurements(old), _measurements(new)
    failures: list[str] = []
    for key in sorted(set(new_m) - set(old_m)):
        failures.append(f"NEW KEY {key}: {new_m[key]}")
    for key in sorted(set(new_m) & set(old_m)):
        if new_m[key] != old_m[key]:
            failures.append(f"CHANGED {key}: {old_m[key]} -> {new_m[key]}")
    return failures


def _report(failures: list[str], ok_message: str) -> int:
    if failures:
        print("FAILURES:")
        for line in failures:
            print(f" - {line}")
        return 1
    print(f"PASS: {ok_message}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    axe = sub.add_parser("axe", help="compare axe count baseline directories")
    axe.add_argument("old_dir", type=Path)
    axe.add_argument("new_dir", type=Path)
    ratio = sub.add_parser("ratio", help="compare flat ratio baseline JSON files")
    ratio.add_argument("old_json", type=Path)
    ratio.add_argument("new_json", type=Path)
    args = parser.parse_args(argv)

    if args.mode == "axe":
        rows, failures = axe_shrink_violations(args.old_dir, args.new_dir)
        print("| file | rule | old | new | verdict |")
        print("|---|---|---|---|---|")
        for row in rows:
            print(row)
        return _report(failures, f"every axe baseline count is <= old ({len(rows)} changed)")

    old = json.loads(args.old_json.read_text(encoding="utf-8"))
    new = json.loads(args.new_json.read_text(encoding="utf-8"))
    old_m, new_m = _measurements(old), _measurements(new)
    print("| key | old | new | verdict |")
    print("|---|---|---|---|")
    for key in sorted(set(old_m) | set(new_m)):
        if key not in new_m:
            print(f"| {key} | {old_m[key]} | - | DELETED |")
        elif key not in old_m:
            print(f"| {key} | - | {new_m[key]} | NEW KEY |")
        elif old_m[key] != new_m[key]:
            print(f"| {key} | {old_m[key]} | {new_m[key]} | CHANGED |")
    failures = ratio_shrink_violations(old, new)
    return _report(failures, "new keys are a subset of old keys; retained values unchanged")


if __name__ == "__main__":
    sys.exit(main())
