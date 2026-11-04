#!/usr/bin/env python3
"""Verdict for the 3.15 smoke leg's unpinned-resolve assertion (235.1 D-02).

An unpinned ``pip install quirk-scanner`` on an unsupported interpreter must
never silently select an OLDER release (pip backtracks to 5.21.0 on 3.15 while
the newer releases are capped ``<3.15``).

PASS only when pip's resolve fails with ResolutionImpossible, fails with "no
candidate" (every release excluded by Requires-Python: pip prints "Ignored the
following versions that require a different python version" next to "(from
versions: none)"), or selects a quirk-scanner >= the version under test.
Network failures, a bare "(from versions: none)" (an unreachable index prints
the same line without the "Ignored" line, so it proves nothing), a report with
no quirk-scanner, and any other non-zero exit are FAIL: unknown is never green.

Stdlib only and Python 3.9-safe: it is copied into a bare python container and
also runs on the macOS host python3.
"""
import argparse
import json
import os
import re
import sys

NETWORK_RE = re.compile(
    r"Could not fetch URL|NewConnectionError|Max retries|"
    r"Temporary failure in name resolution|Network is unreachable"
)
IGNORED_RE = re.compile(
    r"Ignored the following versions that require a different python version"
)


def _release(version):
    """Numeric release tuple from the leading digits-and-dots of ``version``."""
    m = re.match(r"\d+(?:\.\d+)*", str(version).strip())
    if not m:
        return ()
    return tuple(int(p) for p in m.group(0).split("."))


def _norm(name):
    return re.sub(r"[-_.]+", "-", str(name)).lower()


def verdict(report, output_text, rc, expected):
    """Return ``("PASS"|"FAIL", message)``."""
    if not expected or not _release(expected):
        return "FAIL", "no version under test"
    output_text = output_text or ""
    if rc != 0:
        if NETWORK_RE.search(output_text):
            return "FAIL", "pip could not reach the index; unknown is never green"
        if "(from versions: none)" in output_text:
            if IGNORED_RE.search(output_text):
                # IN-02 / D-02: the index answered and every release was
                # excluded by Requires-Python: no older release is selectable.
                return "PASS", "unpinned resolve finds no candidate (every release excluded by Requires-Python)"
            return "FAIL", "pip could not reach the index; unknown is never green"
        if "ResolutionImpossible" in output_text:
            return "PASS", "unpinned resolve fails (no older release selectable)"
        return "FAIL", "pip rc %s without ResolutionImpossible" % rc
    picked = []
    installs = report.get("install") if isinstance(report, dict) else None
    for item in installs if isinstance(installs, list) else []:
        meta = item.get("metadata") if isinstance(item, dict) else None
        if isinstance(meta, dict) and _norm(meta.get("name", "")) == "quirk-scanner":
            picked.append(str(meta.get("version", "")))
    if not picked:
        return "FAIL", "pip succeeded but selected no quirk-scanner"
    if _release(picked[0]) < _release(expected):
        return "FAIL", "unpinned resolve selected older quirk-scanner %s" % picked[0]
    return "PASS", "selected %s >= %s" % (picked[0], expected)


def _load_report(path):
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--report", default="")
    ap.add_argument("--output", default="")
    ap.add_argument("--rc", type=int, required=True)
    ap.add_argument("--expected", default="")
    args = ap.parse_args(argv)
    text = ""
    if args.output and os.path.isfile(args.output):
        with open(args.output, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    state, msg = verdict(_load_report(args.report), text, args.rc, args.expected)
    print("%s: %s" % (state, msg))
    return 0 if state == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
