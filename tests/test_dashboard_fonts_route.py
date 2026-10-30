"""The dashboard serves its bundled JetBrains Mono font (POLISH-01, audit W15).

Before Phase 232 the built CSS requested ``/fonts/JetBrainsMono%5Bwght%5D.ttf``
but nothing mounted ``/fonts``, so the request fell through to the SPA
catch-all and came back ``200 text/html`` with ``<!doctype html>`` as the
body. The browser silently discarded it and the dashboard never rendered in
its brand font.

Per CONTEXT D-02 the URL set is read from the built CSS
(``quirk/dashboard/static/assets/*.css``) at test time rather than hard-coded,
so a renamed or newly added font face is covered automatically, and both the
regular and the italic face are probed.

The content type is asserted as exactly ``font/ttf``. That is deterministic
only because ``app.py`` registers ``mimetypes.add_type("font/ttf", ".ttf")``:
on python:3.10/3.11-slim (no ``/etc/mime.types``) ``guess_type`` returns
``None`` for ``.ttf`` and Starlette falls back to ``text/plain`` (RESEARCH
Pitfall 1).
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

STATIC = Path(__file__).resolve().parent.parent / "quirk" / "dashboard" / "static"

_FONT_URL_RE = re.compile(r"url\((/fonts/[^)\s]+)\)")
_TRUETYPE_MAGIC = b"\x00\x01\x00\x00"


def _css_font_urls() -> list[str]:
    css_files = sorted((STATIC / "assets").glob("*.css"))
    assert css_files, f"no built CSS under {STATIC / 'assets'}"
    css = "".join(p.read_text(encoding="utf-8") for p in css_files)
    urls = sorted(set(_FONT_URL_RE.findall(css)))
    assert len(urls) >= 2, (
        f"expected regular + italic font URLs in built CSS, got {urls}"
    )
    assert any("Italic" in u for u in urls), (
        f"expected an italic font URL in built CSS, got {urls}"
    )
    return urls


def _is_spa_index(content: bytes) -> bool:
    return b"<!doctype" in content.lower()


def test_built_css_font_urls_are_served_as_fonts(dashboard_client):
    for url in _css_font_urls():
        r = dashboard_client.get(url)
        assert r.status_code == 200, (url, r.status_code)
        assert r.headers["content-type"] == "font/ttf", (
            url,
            r.headers["content-type"],
            r.content[:16],
        )
        assert r.content[:4] == _TRUETYPE_MAGIC, (url, r.content[:16])
        on_disk = STATIC / unquote(url.lstrip("/"))
        assert on_disk.is_file(), on_disk
        assert r.content == on_disk.read_bytes(), url


def test_missing_font_is_404_not_spa(dashboard_client):
    r = dashboard_client.get("/fonts/does-not-exist.ttf")
    assert r.status_code == 404, (r.status_code, r.content[:32])
    assert not _is_spa_index(r.content)


def test_fonts_mount_rejects_traversal(dashboard_client):
    # T-232-01: a path-traversal probe out of the fonts dir must not reach
    # static/index.html (or anything else) through the /fonts mount.
    r = dashboard_client.get("/fonts/%2e%2e/index.html")
    assert r.status_code == 404, (r.status_code, r.content[:32])
    assert not _is_spa_index(r.content)


def test_fonts_mount_registered_before_spa_catch_all():
    from quirk.dashboard.api.app import create_app

    paths = [getattr(route, "path", None) for route in create_app().routes]
    assert "/fonts" in paths, paths
    assert "/{full_path:path}" in paths, paths
    assert paths.index("/fonts") < paths.index("/{full_path:path}"), paths
    assert paths[-1] == "/{full_path:path}", paths
