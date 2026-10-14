"""Scripted, reproducible README hero capture (Phase 225 D-10).

Why this exists: the UAT-85-08 hand capture depended on a chaos-lab profile being
up and was never reproducible; the dashboard gauges drew mirrored for six months
and nobody noticed. This script starts a loopback uvicorn against the canonical
``./quirk-output/quirk.db``, opens the executive page in the dark theme at 2x DPR,
guards against capturing the login form / unbuilt placeholder, corroborates by
geometry that each gauge is NOT mirrored, and writes a PNG.

Run: ``.venv/bin/python -m scripts.capture_readme_hero [--out PATH] ...``

Local-only tooling (Playwright is a ``dashboard`` extra). The operator's visual
confirmation remains the acceptance; the arc-reach check is corroboration only.
The canonical DB is never mutated: sha256 is compared before and after.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from quirk.dashboard.api.routes.pdf import IMAGE_SETTLE_PREDICATE

REPO_ROOT = Path(__file__).resolve().parent.parent

_PLACEHOLDER_SIGNATURE = "npm run build"
_SIDEBAR_NAV = 'nav[aria-label="Dashboard navigation"]'
_LOGIN_FORM = 'form[aria-label="Dashboard login"]'
_BRAND_NAME = "QU.I.R.K."
_GAUGES_CARD = "div.flex.flex-wrap.justify-around.gap-8"
_MAX_PNG_BYTES = 1_048_576
_REACH_TOLERANCE = 0.02
_EXPECTED_GAUGES = 7
_SUBSCORE_ORDER = (
    "hygiene", "modern_tls", "identity_trust",
    "agility_signals", "data_at_rest", "data_in_motion",
)

_REACH_JS = """(sel) => {
  const card = document.querySelector(sel);
  if (!card) return null;
  return Array.from(card.querySelectorAll('svg')).map(svg => {
    const p = svg.querySelectorAll('path');
    if (p.length < 1) return null;
    const n = d => d.match(/-?\\d+(\\.\\d+)?/g).map(Number);
    const t = n(p[0].getAttribute('d'));
    const sx = t[0], r = t[2];
    if (p.length < 2) return {label: svg.closest('div.flex-col')?.innerText || '', reach: 0};
    const f = n(p[1].getAttribute('d'));
    return {label: (svg.closest('div.flex-col')?.innerText || '').replace(/\\s+/g, ' ').trim(),
            reach: (f[f.length - 2] - sx) / (2 * r)};
  }).filter(Boolean);
}"""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()


@contextlib.contextmanager
def serve_dashboard(db_path: Path):
    """Background a loopback uvicorn serving the dashboard app; yield its origin."""
    port = _free_port()
    env = dict(os.environ)
    env["QUIRK_DB_PATH"] = str(db_path)
    env["QUIRK_SERVE_PORT"] = str(port)
    # Auth passthrough only when BOTH token sources resolve empty.
    env.pop("QUIRK_API_TOKEN", None)
    tmp = tempfile.mkdtemp(prefix="quirk-hero-")
    env["QUIRK_CONFIG_PATH"] = os.path.join(tmp, "absent", "config.yaml")
    # close_fds=False and no cwd: avoids the macOS fork() SIGSEGV path.
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "quirk.dashboard.api.app:app",
         "--host", "127.0.0.1", "--port", str(port)],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        close_fds=False,
    )
    origin = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 30
        ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                if urllib.request.urlopen(f"{origin}/api/health", timeout=2).status == 200:
                    ready = True
                    break
            except OSError:
                pass
            time.sleep(1)
        if not ready:
            proc.kill()
            out = b""
            with contextlib.suppress(Exception):
                out = proc.communicate(timeout=10)[0] or b""
            raise SystemExit(
                f"SERVER_NOT_READY: uvicorn did not answer {origin}/api/health in 30s "
                f"(exit={proc.returncode}):\n" + out.decode("utf-8", "replace")
            )
        yield origin
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                with contextlib.suppress(Exception):
                    proc.wait(timeout=10)
        with contextlib.suppress(Exception):
            if proc.stdout is not None:
                proc.stdout.close()


def assert_spa_mounted(page) -> None:
    """Abort (named) if the page is the placeholder, the login form, or an empty shell."""
    if _PLACEHOLDER_SIGNATURE in page.content():
        raise SystemExit(
            "PLACEHOLDER_PAGE: served the unbuilt-dashboard placeholder; run `npm run build`."
        )
    root_children = page.evaluate(
        "() => { const r = document.getElementById('root'); return r ? r.children.length : -1; }"
    )
    if root_children <= 0:
        raise SystemExit(f"SPA_NOT_MOUNTED: #root has {root_children} children.")
    if page.locator(_LOGIN_FORM).count() != 0:
        raise SystemExit(
            "LOGIN_FORM: landed on the login form; an API token resolved in the served process."
        )
    if page.locator(_SIDEBAR_NAV).count() == 0:
        raise SystemExit("NO_SIDEBAR_NAV: authenticated shell sidebar nav is absent.")
    logo = page.locator("aside").get_by_role("img", name=_BRAND_NAME).first
    if not logo.is_visible():
        raise SystemExit("NO_BRAND_LOGO: sidebar brand logo not visible (viewport < 1024?).")


def _expected_reach(score: float, max_value: float) -> float:
    return (1 - math.cos(math.pi * (score / max_value))) / 2


def _png_size(path: Path) -> tuple[int, int]:
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("BAD_PNG: output is not a PNG.")
    return struct.unpack(">II", head[16:24])


def capture(args, origin: str, scan: dict, evidence: dict) -> None:
    from playwright.sync_api import sync_playwright  # lazy: `dashboard` extra

    W, H = args.width, args.height
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(
                viewport={"width": W, "height": H},
                device_scale_factor=2,
                color_scheme="dark",
                reduced_motion="reduce",
            )
            ctx.add_init_script("window.localStorage.setItem('quirk-ui-theme', 'dark')")
            page = ctx.new_page()
            page.goto(origin + "/", wait_until="networkidle")
            page.wait_for_selector("main h1")
            assert_spa_mounted(page)
            page.wait_for_function(
                "(sel) => document.querySelectorAll(sel + ' svg').length >= 7",
                arg=_GAUGES_CARD,
            )
            page.evaluate("() => document.fonts.ready")
            page.wait_for_function(IMAGE_SETTLE_PREDICATE)
            page.wait_for_timeout(500)

            rows = page.evaluate(_REACH_JS, _GAUGES_CARD)
            if not rows or len(rows) != _EXPECTED_GAUGES:
                raise SystemExit(
                    f"GAUGE_COUNT: expected {_EXPECTED_GAUGES} gauges, got "
                    f"{0 if not rows else len(rows)}."
                )
            subs = scan["score"]["subscores"]
            expected_inputs = [(scan["score"]["score"], 100)] + [
                (subs[k], 25) for k in _SUBSCORE_ORDER
            ]
            table = []
            bad = []
            for row, (val, mx) in zip(rows, expected_inputs):
                exp = _expected_reach(float(val), mx)
                delta = row["reach"] - exp
                table.append({
                    "label": row["label"], "value": val, "max": mx,
                    "reach": round(row["reach"], 4),
                    "expected": round(exp, 4), "delta": round(delta, 4),
                })
                if abs(delta) > _REACH_TOLERANCE:
                    bad.append(table[-1])
            evidence["reach"] = table
            if bad:
                raise SystemExit(f"GAUGE_MIRRORED: arc reach differs from expected: {bad}")

            box = page.locator(_GAUGES_CARD).bounding_box()
            scroll_y = page.evaluate("() => window.scrollY")
            card_top = box["y"] + scroll_y
            card_bottom = card_top + box["height"]
            clip = {"x": 0, "y": 0, "width": W,
                    "height": math.ceil(card_bottom + args.pad)}
            evidence["clip"] = clip
            evidence["card_bottom"] = card_bottom
            page.screenshot(path=str(out), full_page=True, clip=clip, animations="disabled")
        finally:
            browser.close()

    pw_, ph_ = _png_size(out)
    nbytes = out.stat().st_size
    evidence["png"] = {"width": pw_, "height": ph_, "bytes": nbytes, "path": str(out)}
    if nbytes >= _MAX_PNG_BYTES:
        raise SystemExit(f"PNG_TOO_LARGE: {nbytes} >= {_MAX_PNG_BYTES} bytes.")
    if ph_ != 2 * clip["height"]:
        raise SystemExit(f"PNG_TRUNCATED: png_height {ph_} != 2 * clip.height {clip['height']}.")
    if not card_bottom <= clip["y"] + clip["height"]:
        raise SystemExit("CARD_CUT_OFF: gauges card bottom lies outside the clip.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--width", type=int, default=1680)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--out", default="docs/images/dashboard-hero.png")
    ap.add_argument("--db", default=str(REPO_ROOT / "quirk-output" / "quirk.db"))
    ap.add_argument("--pad", type=int, default=24)
    ap.add_argument("--evidence-json", default=None)
    args = ap.parse_args(argv)

    if args.width < 1024:
        raise SystemExit("BAD_WIDTH: --width must be >= 1024 (sidebar logo is `hidden lg:block`).")
    db = Path(args.db).resolve()
    if not db.is_file():
        raise SystemExit(f"DB_MISSING: {db} does not exist; refusing to start.")

    before = _sha256(db)
    evidence: dict = {"db": str(db), "db_sha256_before": before,
                      "viewport": {"width": args.width, "height": args.height}}
    with serve_dashboard(db) as origin:
        scan = json.loads(_get(origin + "/api/scan/latest"))
        score = scan.get("score") or {}
        evidence["scan"] = {"id": scan.get("scan_id") or scan.get("id"),
                            "timestamp": scan.get("timestamp") or scan.get("scan_timestamp")}
        evidence["score"] = score
        evidence["meta"] = scan.get("meta")
        html = _get(origin + "/").decode("utf-8", "replace")
        import re
        m = re.search(r"assets/(index-[A-Za-z0-9_-]+\.js)", html)
        if not m:
            raise SystemExit("NO_BUNDLE: served index.html references no assets/index-*.js.")
        evidence["bundle"] = m.group(1)
        if not (REPO_ROOT / "quirk" / "dashboard" / "static" / "assets" / m.group(1)).is_file():
            raise SystemExit(f"STATIC_MISSING: {m.group(1)} not in quirk/dashboard/static/assets.")
        try:
            capture(args, origin, {"score": score}, evidence)
        finally:
            pass
    after = _sha256(db)
    evidence["db_sha256_after"] = after
    text = json.dumps(evidence, indent=2, default=str)
    print(text)
    if args.evidence_json:
        Path(args.evidence_json).write_text(text + "\n")
    if before != after:
        print("DB_MUTATED: canonical DB hash changed during capture.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
