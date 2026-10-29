#!/usr/bin/env python3
"""README command enumerator and live link checker.

Two subcommands, JSON on stdout, human notes on stderr:

``commands --readme PATH``
    Every shell command in README.md, found by walking the markdown-it token
    stream (fenced bash/sh/shell/console blocks, plus inline code that starts
    with a known tool name). No hand-kept list: a command added to the README
    appears here on the next run. Each record carries its README line number.

``links --source file:PATH | pypi:VERSION [--substitute-ref REF]``
    Extract every href/src/srcset target and HTTP-check it. In ``pypi`` mode
    the long description is taken from the PyPI JSON API and rendered with
    ``readme-renderer[md]`` (the PyPI HTML page sits behind a JS challenge).
    Relative links are reported broken: they do not resolve on PyPI.

Exit codes (same contract as ``scripts/branch_ci_state.py``):
    0  every link resolved (verdict ``green``)
    1  at least one link is broken (verdict ``red``)
    2  unknown: network failure, missing renderer, transient server error.
       Unknown wins over green, never the reverse.

URL extraction is a local copy of the logic in
``tests/test_readme_links_pinned.py`` so the pypi mode can run from a tools
venv outside the repository; ``tests/test_readme_audit.py`` proves the two
return the same set. Fetched content is only parsed, never executed.

Dependencies: stdlib + markdown-it-py (and readme-renderer[md] for pypi mode).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Callable, Iterable, List, Optional

SHELL_LANGS = ("bash", "sh", "shell", "console")
INLINE_PREFIXES = (
    "pip", "python", "quirk", "playwright", "gh", "pypi-attestations",
    "docker", "git",
)
USER_AGENT = "quirk-readme-audit"
PYPI_JSON = "https://pypi.org/pypi/quirk-scanner/{version}/json"

Fetcher = Callable[[str, float], int]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def _md():
    from markdown_it import MarkdownIt

    return MarkdownIt("commonmark").enable("table")


def enumerate_commands(text: str) -> List[dict]:
    """Return one record per shell command found in Markdown ``text``."""
    records: List[dict] = []
    fence_id = 0

    def walk(tokens, block_line):
        for tok in tokens:
            line = tok.map[0] + 1 if tok.map else block_line
            if tok.type == "fence":
                lang = (tok.info or "").strip().split()[0:1]
                if lang and lang[0] in SHELL_LANGS:
                    nonlocal fence_id
                    fence_id += 1
                    _fence_records(tok, fence_id, records)
            elif tok.type == "code_inline":
                content = tok.content.strip()
                first = content.split(None, 1)[0] if content else ""
                if first in INLINE_PREFIXES:
                    records.append({
                        "fence_id": None, "line": block_line,
                        "text": content, "kind": "inline",
                    })
            if tok.children:
                walk(tok.children, line)

    walk(_md().parse(text), 1)
    return records


def _fence_records(tok, fence_id: int, out: List[dict]) -> None:
    start = (tok.map[0] + 2) if tok.map else 1
    pending: Optional[str] = None
    pending_line = start
    for offset, raw in enumerate(tok.content.split("\n")):
        line_no = start + offset
        stripped = raw.strip()
        if pending is None:
            if not stripped or stripped.startswith("#"):
                continue
            pending, pending_line = stripped, line_no
        else:
            pending = pending + " " + stripped
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
            continue
        if pending.startswith("$ "):
            pending = pending[2:]
        out.append({
            "fence_id": fence_id, "line": pending_line,
            "text": pending, "kind": "fence",
        })
        pending = None
    if pending:
        out.append({
            "fence_id": fence_id, "line": pending_line,
            "text": pending, "kind": "fence",
        })


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------


class _HtmlUrls(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: List[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value is None:
                continue
            if name in ("href", "src"):
                self.urls.append(value.strip())
            elif name == "srcset":
                first = value.strip().split(",")[0].split()
                if first:
                    self.urls.append(first[0])

    handle_startendtag = handle_starttag


def html_urls(fragment: str) -> List[str]:
    parser = _HtmlUrls()
    parser.feed(fragment)
    parser.close()
    return parser.urls


def markdown_urls(text: str) -> List[str]:
    """Every link, image and raw-HTML target in Markdown ``text``."""
    urls: List[str] = []

    def walk(tokens):
        for tok in tokens:
            if tok.type == "link_open":
                urls.append(tok.attrGet("href"))
            elif tok.type == "image":
                urls.append(tok.attrGet("src"))
            elif tok.type in ("html_inline", "html_block"):
                urls.extend(html_urls(tok.content))
            if tok.children:
                walk(tok.children)

    walk(_md().parse(text))
    return urls


_PIN_BLOB = re.compile(r"(/(?:blob|tree|raw)/)v\d+\.\d+\.\d+(?=/)")
_PIN_RAW = re.compile(
    r"(raw\.githubusercontent\.com/[^/]+/[^/]+/)v\d+\.\d+\.\d+(?=/)")


def substitute_ref(url: str, ref: str) -> str:
    url = _PIN_BLOB.sub(lambda m: m.group(1) + ref, url)
    return _PIN_RAW.sub(lambda m: m.group(1) + ref, url)


def default_fetcher(url: str, timeout: float) -> int:
    """HTTP status for ``url``. HEAD first, GET on 403/405. URLError raises."""
    def attempt(method: str) -> int:
        req = urllib.request.Request(
            url, method=method, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code

    status = attempt("HEAD")
    if status in (403, 405):
        status = attempt("GET")
    return status


def default_json_loader(version: str, timeout: float) -> dict:
    req = urllib.request.Request(
        PYPI_JSON.format(version=version),
        headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _is_transient(status: int) -> bool:
    return status == 429 or status >= 500


def check_links(urls: Iterable[str], fetcher: Fetcher, timeout: float) -> dict:
    ok: List[str] = []
    broken: List[dict] = []
    unknown: List[str] = []
    for url in dict.fromkeys(urls):
        if not re.match(r"^https?://", url):
            broken.append({"url": url, "status": "relative-or-unsupported"})
            continue
        try:
            status = fetcher(url, timeout)
        except (urllib.error.URLError, OSError, TimeoutError):
            unknown.append(url)
            continue
        if _is_transient(status):
            unknown.append(url)
        elif status >= 400:
            broken.append({"url": url, "status": status})
        else:
            ok.append(url)
    if unknown:
        verdict = "unknown"
    elif broken:
        verdict = "red"
    else:
        verdict = "green"
    return {"checked": len(ok) + len(broken) + len(unknown), "ok": ok,
            "broken": broken, "unknown": unknown, "verdict": verdict}


def _source_text(source: str, timeout: float, json_loader) -> Optional[str]:
    kind, _, value = source.partition(":")
    if kind == "file":
        with open(value, encoding="utf-8") as fh:
            return fh.read()
    if kind == "pypi":
        try:
            from readme_renderer.markdown import render
        except ImportError:
            print("readme-renderer[md] is not installed; pypi mode cannot "
                  "render the description (verdict unknown)", file=sys.stderr)
            return None
        data = json_loader(value, timeout)
        description = data.get("info", {}).get("description") or ""
        rendered = render(description)
        if rendered is None:
            print("readme-renderer refused the description", file=sys.stderr)
            return None
        return "<div>" + rendered + "</div>"
    raise SystemExit(f"unsupported --source {source!r}")


def _links(args, fetcher: Fetcher, json_loader) -> int:
    report = {"source": args.source}
    try:
        text = _source_text(args.source, args.timeout, json_loader)
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
        print(f"could not load source: {exc}", file=sys.stderr)
        text = None
    if text is None:
        report.update({"checked": 0, "ok": [], "broken": [], "unknown": [],
                       "verdict": "unknown"})
        print(json.dumps(report, indent=2))
        return 2
    kind = args.source.partition(":")[0]
    raw = html_urls(text) if kind == "pypi" else markdown_urls(text)
    urls = [u for u in raw if u and not u.startswith(("#", "mailto:"))]
    if args.substitute_ref:
        urls = [substitute_ref(u, args.substitute_ref) for u in urls]
    report.update(check_links(urls, fetcher, args.timeout))
    print(json.dumps(report, indent=2))
    return {"green": 0, "red": 1, "unknown": 2}[report["verdict"]]


def main(argv=None, fetcher: Fetcher = default_fetcher,
         json_loader=default_json_loader) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("commands", help="enumerate README shell commands")
    pc.add_argument("--readme", required=True)
    pl = sub.add_parser("links", help="check README links")
    pl.add_argument("--source", required=True,
                    help="file:PATH or pypi:VERSION")
    pl.add_argument("--substitute-ref", default=None)
    pl.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)

    if args.cmd == "commands":
        with open(args.readme, encoding="utf-8") as fh:
            cmds = enumerate_commands(fh.read())
        print(json.dumps({"readme": args.readme, "commands": cmds}, indent=2))
        return 0
    return _links(args, fetcher, json_loader)


if __name__ == "__main__":
    sys.exit(main())
