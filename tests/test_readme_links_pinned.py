"""README links must resolve when PyPI renders the README (Phase 232 POLISH-04).

PyPI renders ``README.md`` outside the repository, so a repo-relative link
such as ``[Guide](docs/getting-started.md)`` resolves against pypi.org and
404s there (todo 261014). D-11: every in-body link to a repo file is
``https://github.com/0xD1g5/QU.I.R.K/blob/v<version>/<path>`` and every link to
a repo directory is ``.../tree/v<version>/<path>``. Anchors are kept.

D-12, why a parser and not a line grep: the badge links on README lines 9-11
(``LICENSE``, ``SECURITY.md``, ``docs/release-process.md#...``) share a line
with an ``http`` image URL, so "lines without http" misses them. The links are
collected with a small stdlib tokenizer (fenced blocks and inline code spans
blanked first; inline links/images, reference definitions, autolinks, and raw
HTML ``href``/``src``/``srcset``). A differential node checks that tokenizer
against an independent markdown-it-py walk, with a floor, so a blind spot in
the tokenizer turns the gate red instead of silently shrinking what it checks
(memory feedback_measure_with_a_method_independent_of_the_audited_code).

Why git objects and not the working tree: an untracked local file would make a
working-tree existence check pass locally and fail in CI (memory
feedback_local_path_exists_is_not_ci). Path kind and anchor headings are read
from ``git cat-file -t HEAD:<path>`` and ``git show HEAD:<path>``, through
``run_fork_safe`` (direct process spawning in tests/ is blocked by
tests/test_cli_helper_usage.py).

D-13, the Phase 235 coupling: the pin is derived from
``tests.pyproject_helpers.pyproject_version()``. The release bump to the next
version turns this gate red until the README pins move with it, exactly like
the image pins in tests/test_readme_brand_logo.py and tests/test_readme_hero.py.
A link to a file added after the last tag is still correct: it resolves once the
bumped version is tagged. The live "HTTP 200 on the PyPI page" check is Phase
235's (LAUNCH-03), not this file's.
"""
from __future__ import annotations

import re
import shutil
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import unquote, urlsplit

from tests.cli_helpers import run_fork_safe
from tests.pyproject_helpers import pyproject_version

REPO_ROOT = Path(__file__).resolve().parent.parent
VERSION = pyproject_version()
OWNER_REPO = "0xD1g5/QU.I.R.K"
GITHUB_REPO = f"https://github.com/{OWNER_REPO}/"
RAW_REPO = f"https://raw.githubusercontent.com/{OWNER_REPO}/"

# Measured in plan 232-04 at 818fa6cd (before the rewrite) and again after it:
# the stdlib tokenizer and the markdown-it-py walk both return the same 38-URL
# multiset (research also measured 38, at 66c4dd83). The rewrite changes link
# targets only, so the count is unchanged. A drop below this means links were lost.
URL_FLOOR = 38

# Repo-host paths that are not file/directory links and need no tag pin.
_ALLOWED_REPO_PREFIXES = ("actions/",)
_ALLOWED_REPO_EXACT = ("releases",)

KindOf = Callable[[str], Optional[str]]


# ---------------------------------------------------------------------------
# Tokenizer (pure functions)
# ---------------------------------------------------------------------------

_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_CODE_SPAN = re.compile(r"(`+)(.+?)(?<!`)\1(?!`)")
_INLINE_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_REF_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)", re.M)
_AUTOLINK = re.compile(r"<([A-Za-z][A-Za-z0-9+.\-]{1,31}:[^<>\s]*)>")


def _blank(s: str) -> str:
    return re.sub(r"[^\n]", " ", s)


def strip_code(text: str) -> str:
    """Blank fenced code blocks and inline code spans, keeping line count."""
    out: list[str] = []
    fence: str | None = None
    for line in text.split("\n"):
        if fence is None:
            m = _FENCE_OPEN.match(line)
            if m and not (m.group(1)[0] == "`" and "`" in line[m.end():]):
                fence = m.group(1)
                out.append(_blank(line))
                continue
            out.append(_CODE_SPAN.sub(lambda mm: _blank(mm.group(0)), line))
        else:
            # CommonMark: a closing fence uses the same char, at least as long.
            closing = re.match(r"^ {0,3}(" + re.escape(fence[0]) + r"{%d,})\s*$" % len(fence), line)
            if closing:
                fence = None
            out.append(_blank(line))
    return "\n".join(out)


class _HtmlUrls(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag, attrs):  # noqa: D401 - HTMLParser hook
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


def html_urls(fragment: str) -> list[str]:
    p = _HtmlUrls()
    p.feed(fragment)
    p.close()
    return p.urls


def collect_urls(text: str) -> list[str]:
    """Every link/image/HTML target in Markdown ``text``, code excluded."""
    body = strip_code(text)
    urls = [m.group(1) for m in _INLINE_LINK.finditer(body)]
    urls += [m.group(1) for m in _REF_DEF.finditer(body)]
    urls += [m.group(1) for m in _AUTOLINK.finditer(body)]
    urls += html_urls(body)
    return urls


def markdown_it_urls(text: str) -> list[str]:
    """Independent walk with markdown-it-py (CommonMark + tables)."""
    from markdown_it import MarkdownIt

    md = MarkdownIt("commonmark").enable("table")
    urls: list[str] = []

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

    walk(md.parse(text))
    return urls


# ---------------------------------------------------------------------------
# Classifier (pure functions, injectable git lookups)
# ---------------------------------------------------------------------------


def split_repo_url(url: str) -> tuple[str, str, str, str] | None:
    """Return ``(form, ref, path, fragment)`` for a pinned-shape repo URL.

    ``form`` is ``blob``, ``tree`` or ``raw``. Returns None for any URL that is
    not a blob/tree/raw repo URL.
    """
    parts = urlsplit(url)
    if parts.netloc == "github.com" and parts.path.startswith(f"/{OWNER_REPO}/"):
        rest = parts.path[len(f"/{OWNER_REPO}/"):]
        m = re.match(r"^(blob|tree)/([^/]+)/(.*)$", rest)
        if m:
            return m.group(1), m.group(2), unquote(m.group(3)), parts.fragment
        return None
    if parts.netloc == "raw.githubusercontent.com" and parts.path.startswith(f"/{OWNER_REPO}/"):
        rest = parts.path[len(f"/{OWNER_REPO}/"):]
        ref, _, path = rest.partition("/")
        return "raw", ref, unquote(path), parts.fragment
    return None


def classify(url: str, version: str, kind_of: KindOf | None = None) -> str | None:
    """Return a ``category: message`` violation for ``url``, or None if it is fine.

    Categories: ``relative`` (no scheme, including fragment-only), ``host`` (an
    unknown repo-host shape), ``unpinned`` (ref is not ``v{version}``), ``kind``
    (blob/tree/raw does not match the object type at HEAD, or path missing).
    ``kind_of`` maps a repo path to ``blob``/``tree``/None; skipped when None.
    """
    parts = urlsplit(url)
    if not parts.scheme:
        return f"relative: {url}"
    split = split_repo_url(url)
    if split is None:
        if parts.netloc == "github.com" and parts.path.startswith(f"/{OWNER_REPO}"):
            rest = parts.path[len(f"/{OWNER_REPO}/"):]
            if rest in _ALLOWED_REPO_EXACT or rest.startswith(_ALLOWED_REPO_PREFIXES):
                return None
            return f"host: unrecognised repo URL shape {url}"
        return None
    form, ref, path, _frag = split
    want = f"v{version}"
    if ref != want:
        return f"unpinned: {url} (ref {ref!r}, expected {want!r})"
    if kind_of is not None:
        clean = path.rstrip("/")
        kind = kind_of(clean)
        expected = "tree" if form == "tree" else "blob"
        if kind is None:
            return f"kind: {url} -> {clean!r} does not exist at HEAD"
        if kind != expected:
            return f"kind: {url} uses /{form}/ but HEAD:{clean} is a {kind}"
    return None


def github_slug(heading: str) -> str:
    """GitHub heading anchor: lowercase, drop chars outside [\\w\\- ], spaces -> '-'."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


_ATX = re.compile(r"^ {0,3}#{1,6}[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")


def heading_slugs(markdown: str) -> set[str]:
    """All heading anchors GitHub would generate (with -1, -2 de-duplication)."""
    seen: Counter[str] = Counter()
    slugs: set[str] = set()
    for line in strip_code(markdown).split("\n"):
        m = _ATX.match(line)
        if not m:
            continue
        base = github_slug(m.group(1))
        slug = base if seen[base] == 0 else f"{base}-{seen[base]}"
        seen[base] += 1
        slugs.add(slug)
    return slugs


# ---------------------------------------------------------------------------
# Git object lookups (committed objects at HEAD, never the working tree)
# ---------------------------------------------------------------------------

_GIT = shutil.which("git") or "/usr/bin/git"


def _git_kind(path: str) -> str | None:
    r = run_fork_safe([_GIT, "-C", str(REPO_ROOT), "cat-file", "-t", f"HEAD:{path}"])
    return r.stdout.strip() if r.returncode == 0 else None


def _git_show(path: str) -> str:
    r = run_fork_safe([_GIT, "-C", str(REPO_ROOT), "show", f"HEAD:{path}"], check=True)
    return r.stdout


def _readme() -> str:
    return (REPO_ROOT / "README.md").read_text(encoding="utf-8")


def _violations(category: str, kind_of: KindOf | None = None) -> list[str]:
    out = []
    for url in collect_urls(_readme()):
        v = classify(url, VERSION, kind_of)
        if v and v.split(":", 1)[0] in category.split("|"):
            out.append(v)
    return out


# ---------------------------------------------------------------------------
# Gate nodes against the real README
# ---------------------------------------------------------------------------


def test_readme_has_no_relative_links():
    bad = _violations("relative")
    assert not bad, (
        f"POLISH-04 D-11: {len(bad)} README link(s) are repo-relative and 404 on PyPI; "
        f"pin them to {GITHUB_REPO}blob|tree/v{VERSION}/<path>:\n" + "\n".join(bad)
    )


def test_readme_repo_links_pinned_to_pyproject_version():
    bad = _violations("unpinned|host")
    assert not bad, (
        f"POLISH-04 D-12/D-13: README repo links must be pinned to v{VERSION} "
        "(pyproject.toml); a version bump must move every pin:\n" + "\n".join(bad)
    )


def test_readme_pinned_paths_exist_with_matching_kind():
    bad = _violations("kind", kind_of=_git_kind)
    assert not bad, (
        "POLISH-04 D-11: every pinned path must exist at HEAD, with /blob/ for files "
        "and /tree/ for directories (git cat-file -t):\n" + "\n".join(bad)
    )


def test_readme_pinned_anchors_resolve():
    bad = []
    cache: dict[str, set[str]] = {}
    checked = 0
    for url in collect_urls(_readme()):
        split = split_repo_url(url)
        if not split or not split[3]:
            continue
        _form, _ref, path, frag = split
        path = path.rstrip("/")
        if path not in cache:
            cache[path] = heading_slugs(_git_show(path)) if _git_kind(path) == "blob" else set()
        checked += 1
        if unquote(frag) not in cache[path]:
            bad.append(f"{url}: no heading in HEAD:{path} slugs to #{frag}")
    assert not bad, "POLISH-04: README anchors must match a heading:\n" + "\n".join(bad)


def test_tokenizer_matches_markdown_it():
    # markdown-it-py arrives with the core `rich` dependency. No skip: a missing
    # parser must fail loudly (an unregistered skip is also rejected by
    # tests/test_skip_registry.py).
    text = _readme()
    ours = Counter(collect_urls(text))
    theirs = Counter(markdown_it_urls(text))
    assert ours == theirs, (
        "POLISH-04 D-12: the stdlib tokenizer disagrees with markdown-it-py; fix the "
        f"tokenizer.\nonly stdlib: {ours - theirs}\nonly markdown-it: {theirs - ours}"
    )
    assert sum(ours.values()) >= URL_FLOOR, (
        f"POLISH-04: only {sum(ours.values())} README URLs found, floor is {URL_FLOOR}"
    )


# ---------------------------------------------------------------------------
# Detector unit cases (literal strings, injected lookups)
# ---------------------------------------------------------------------------

_V = "1.2.3"


def _kinds(mapping: dict[str, str]) -> KindOf:
    return mapping.get


def test_detector_flags_relative_link():
    assert classify("docs/a.md", _V).startswith("relative:")
    assert classify("#section", _V).startswith("relative:")
    assert collect_urls("[x](docs/a.md)") == ["docs/a.md"]


def test_detector_flags_unpinned_branch():
    v = classify(f"{GITHUB_REPO}blob/main/a.md", _V)
    assert v and v.startswith("unpinned:")


def test_detector_flags_stale_tag():
    v = classify(f"{GITHUB_REPO}blob/v0.0.0/a.md", _V)
    assert v and v.startswith("unpinned:")
    v = classify(f"{RAW_REPO}v0.0.0/docs/x.png", _V)
    assert v and v.startswith("unpinned:")


def test_detector_flags_blob_for_directory():
    kinds = _kinds({"docs/connectors": "tree", "a.md": "blob"})
    v = classify(f"{GITHUB_REPO}blob/v{_V}/docs/connectors/", _V, kinds)
    assert v and v.startswith("kind:")
    v = classify(f"{GITHUB_REPO}tree/v{_V}/a.md", _V, kinds)
    assert v and v.startswith("kind:")
    v = classify(f"{GITHUB_REPO}blob/v{_V}/missing.md", _V, kinds)
    assert v and v.startswith("kind:")
    assert classify(f"{GITHUB_REPO}tree/v{_V}/docs/connectors", _V, kinds) is None
    assert classify(f"{GITHUB_REPO}blob/v{_V}/a.md#x", _V, kinds) is None


def test_detector_flags_unknown_repo_host_shape():
    v = classify(f"{GITHUB_REPO}wiki/Home", _V)
    assert v and v.startswith("host:")
    assert classify(f"{GITHUB_REPO}releases", _V) is None
    assert classify(f"{GITHUB_REPO}actions/workflows/x.yml", _V) is None
    assert classify("https://pypi.org/project/quirk-scanner/", _V) is None


def test_detector_ignores_fenced_and_inline_code():
    text = (
        "before\n"
        "```bash\n"
        "[x](docs/in-fence.md)\n"
        "```\n"
        "~~~~\n"
        "[y](docs/in-tilde.md)\n"
        "~~~~\n"
        "use `[z](docs/in-span.md)` and ``[w](docs/in-double.md)`` here\n"
        "[real](docs/real.md)\n"
    )
    assert collect_urls(text) == ["docs/real.md"]
    assert strip_code(text).count("\n") == text.count("\n")


def test_detector_nested_badge_yields_both_urls():
    urls = collect_urls("[![a](https://img.shields.io/x)](LICENSE)")
    assert Counter(urls) == Counter(["https://img.shields.io/x", "LICENSE"])


def test_detector_collects_html_href_src_srcset():
    text = '<source srcset="https://e/a.svg 1x, https://e/b.svg 2x">\n<a href="x.md"><img src="i.png"></a>\n'
    assert Counter(collect_urls(text)) == Counter(["https://e/a.svg", "x.md", "i.png"])


def test_github_slug_rule():
    assert github_slug("Parrot OS / Kali / Debian (PEP 668)") == "parrot-os--kali--debian-pep-668"
    assert (
        github_slug("Attestation Verification (for downstream consumers)")
        == "attestation-verification-for-downstream-consumers"
    )
    assert heading_slugs("# A\n## A\n```\n# B\n```\n") == {"a", "a-1"}
